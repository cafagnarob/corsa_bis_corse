/*
 * raggruppa.ts
 * Prepara la città per un disegno veloce: invece di una mesh per ogni pezzo
 * di ogni tessera, raccoglie i pezzi UGUALI di tutta la città.
 *
 * - Strati: per ogni livello (1, 2, 3...) l'elenco delle posizioni → una
 *   InstancedMesh per livello.
 * - Cime: per ogni tipo di cima l'elenco delle posizioni → una InstancedMesh.
 * - Edifici: sulle tessere delle famiglie già fatte (centro storico →
 *   borgo, popolare → palazzi a corte vicino al centro storico e palazzoni più
 *   fuori, villette, industriale → capannoni, uffici → grattacieli) gli
 *   edifici lungo le strade (edifici/lotti.ts),
 *   con la matrice che porta il progetto nel mondo; le loro impronte sono
 *   ingombri per la vegetazione.
 * - Volumi segnaposto: sulle altre tessere, per ogni colore posizione e
 *   misure (scala del cubo).
 * - Isole delle rotonde: per ogni materiale posizione e misure del cilindro.
 * - Strade: la città non si muove, quindi le strade di tutte le tessere si
 *   fondono in tre sole geometrie (asfalto, marciapiedi, segni). Per ogni
 *   triangolo dell'asfalto si ricorda la via a cui appartiene.
 * - Piante: per ogni pianta di vegetazione.glb (Albero_Tondo, Siepe, ...)
 *   tessera e matrice: alberi e cespugli nei posti liberi della tessera,
 *   siepe lungo i viali dei quartieri, piante nelle isole delle rotonde
 *   (vegetazione/piante.ts).
 * - Monumenti: per ogni monumento (Oratore, Equestre, ...) tessera e matrice,
 *   al centro dell'isola della rotonda, scalato e girato verso il viale
 *   principale (isole.ts).
 * - Rampe: per ogni pezzo (Rampa_urbana_1, ...) tessera e matrice, sul
 *   connettore della tessera bassa e ruotata di lato × 60°; la strada della
 *   tessera bassa si accorcia dove comincia la rampa.
 *
 * Funzione pura: riceve città e rete, restituisce dati. Il componente
 * CittaIstanziata li trasforma in mesh.
 */

import {
  centroTessera,
  chiave,
  distanza,
  puntoLato,
  type CittaPopolata,
  type Hex,
  type ReteStradale,
  type Stradario,
} from "@corsa-bis/engine"

import {
  BufferAttribute,
  BufferGeometry,
  Matrix4,
  Quaternion,
  Vector3,
} from "three"
import { mergeGeometries } from "three/examples/jsm/utils/BufferGeometryUtils.js"
import { geometrieDi, tracciatoDi } from "../strade/cache"
import {
  decorazioneIsola,
  monumentoIsola,
  partiIsola,
  raggioIsola,
  SOPRA_ISOLA,
  VASCA,
  type MaterialeIsola,
} from "../strade/isole"
import { ASPETTO, sovrapponeStrade } from "../tessere/aspetto"
import type { TipoCima } from "../tessere/materiali"
import { quotaCima, quotaStrato, quotaSuperiore } from "../tessere/misure"
import { pezzoRampa } from "../strade/rampe"
import type { EdificioPosato } from "../edifici/gusci"
import { CON_EDIFICI, DISTANZA_CORTE, lottiTessera } from "../edifici/lotti"
import { SCALA_EDIFICI } from "../edifici/progetto"
import {
  pianteIsola,
  pianteTessera,
  type Ingombro,
  type PiantaPosata,
} from "../vegetazione/piante"

export type GruppiCitta = {
  readonly strati: ReadonlyMap<number, Matrix4[]> // livello → posizioni
  readonly cime: ReadonlyMap<TipoCima, Matrix4[]>
  readonly volumi: ReadonlyMap<string, Matrix4[]> // colore → posizione e scala
  /** Gli edifici veri (gusci), con la matrice progetto → mondo. */
  readonly edifici: readonly EdificioPosato[]
  readonly isole: ReadonlyMap<MaterialeIsola, Matrix4[]>
  /** Pezzo del .glb (Rampa_urbana_1, ...) → tessera bassa e matrice di ogni rampa. */
  readonly rampe: ReadonlyMap<string, VoceRampa[]>
  /** Monumento (Oratore, Equestre, ...) → tessera e matrice di ogni copia. */
  readonly monumenti: ReadonlyMap<string, VocePezzo[]>
  /** Pianta (Albero_Tondo, Siepe, ...) → tessera e matrice di ogni copia. */
  readonly piante: ReadonlyMap<string, VocePezzo[]>
  readonly strade: {
    readonly asfalto: BufferGeometry
    readonly marciapiedi: BufferGeometry
    readonly segni: BufferGeometry
  }
  /** Per ogni triangolo dell'asfalto fuso, l'id della via (-1 = incrocio): serve al mouse. */
  readonly viaPerTriangolo: Int32Array
}

/** Un pezzo da disegnare: la tessera che lo contiene (per il LOD) e dove sta. */
export type VocePezzo = { readonly hex: Hex; readonly matrice: Matrix4 }
/** Una rampa da disegnare. */
export type VoceRampa = VocePezzo

/** Aggiunge un elemento all'elenco di una chiave, creandolo se manca. */
function aggiungi<K, V>(mappa: Map<K, V[]>, k: K, v: V) {
  const lista = mappa.get(k)
  if (lista) lista.push(v)
  else mappa.set(k, [v])
}

/** Matrice di posizione (x, y, z) e scala (sx, sy, sz). */
const matrice = (x: number, y: number, z: number, sx = 1, sy = 1, sz = 1) =>
  new Matrix4().makeScale(sx, sy, sz).setPosition(x, y, z)

/** Unisce più geometrie in una; con l'elenco vuoto restituisce una geometria vuota. */
const fondi = (lista: BufferGeometry[]) =>
  lista.length > 0 ? mergeGeometries(lista) : new BufferGeometry()

/**
 * UV proiettate dall'alto, in unità di gioco (u = x, v = z, come le facce
 * di tessere.glb): la texture ripetibile continua da una tessera all'altra.
 * Si calcolano DOPO la fusione, sulle coordinate del mondo.
 */
function uvDallAlto(g: BufferGeometry): BufferGeometry {
  const pos = g.getAttribute("position")
  if (!pos) return g
  const uv = new Float32Array(pos.count * 2)
  for (let i = 0; i < pos.count; i++) {
    uv[2 * i] = pos.getX(i)
    uv[2 * i + 1] = pos.getZ(i)
  }
  g.setAttribute("uv", new BufferAttribute(uv, 2))
  return g
}

export function raggruppa(
  citta: CittaPopolata,
  rete: ReteStradale,
  stradario: Stradario,
): GruppiCitta {
  const strati = new Map<number, Matrix4[]>()
  const cime = new Map<TipoCima, Matrix4[]>()
  const volumi = new Map<string, Matrix4[]>()
  const edifici: EdificioPosato[] = []
  const isole = new Map<MaterialeIsola, Matrix4[]>()
  const strade = {
    asfalto: [] as BufferGeometry[],
    marciapiedi: [] as BufferGeometry[],
    segni: [] as BufferGeometry[],
  }
  const viaPerTriangolo: number[] = []

  const rampe = new Map<string, VoceRampa[]>()
  const monumenti = new Map<string, VocePezzo[]>()

  const piante = new Map<string, VocePezzo[]>()
  /** Mette una pianta della tessera (coordinate locali) nel mondo, alla quota y. */
  const pianta = (
    hex: Hex,
    x: number,
    z: number,
    y: number,
    p: PiantaPosata,
  ) => {
    const giro = new Quaternion().setFromAxisAngle(
      new Vector3(0, 1, 0),
      p.angolo,
    )
    aggiungi(piante, p.pianta, {
      hex,
      matrice: new Matrix4().compose(
        new Vector3(x + p.x, y, z + p.z),
        giro,
        new Vector3().setScalar(p.scala),
      ),
    })
  }

  const stratiDi = new Map(citta.tessere.map((t) => [chiave(t.hex), t.strati]))
  for (const r of rete.rampe) {
    const c = centroTessera(r.hex)
    const l = puntoLato(r.lato)
    const m = new Matrix4().makeRotationY((r.lato * Math.PI) / 3)
    m.setPosition(
      c.x + l.x,
      quotaSuperiore(stratiDi.get(chiave(r.hex))!),
      c.z + l.z,
    )
    aggiungi(rampe, pezzoRampa(r), { hex: r.hex, matrice: m })
  }

  // il popolare vicino al centro storico ha i palazzi a corte (edifici/lotti.ts)
  const centriStorici = citta.tessere
    .filter((t) => t.tipo === "centro_storico")
    .map((t) => t.hex)
  const vicinoAlCentro = (h: Hex) =>
    centriStorici.some((c) => distanza(c, h) <= DISTANZA_CORTE)

  for (const t of citta.tessere) {
    const { x, z } = centroTessera(t.hex)
    const k = chiave(t.hex)
    const sopra = quotaSuperiore(t.strati)
    const aspetto = ASPETTO[t.tipo]
    const connettori = rete.connettori.get(k)!
    const rotonda = rete.rotonde.get(k) ?? null
    const rettilinei = rete.rettilinei.get(k) // rampe sui lati di questa tessera
    const tracciato = tracciatoDi(connettori, rotonda, rettilinei)

    // pila di strati e cima
    for (let livello = 1; livello <= t.strati; livello++)
      aggiungi(strati, livello, matrice(x, quotaStrato(livello), z))
    aggiungi(cime, aspetto.cima, matrice(x, quotaCima(t.strati), z))

    // edifici lungo le strade (famiglie fatte) oppure volumi segnaposto che non stanno sulle strade
    const ingombri: Ingombro[] = []
    if (CON_EDIFICI.has(t.tipo))
      for (const l of lottiTessera(
        citta.seme,
        t.hex,
        t.tipo,
        tracciato,
        vicinoAlCentro(t.hex),
      )) {
        edifici.push({
          progetto: l.progetto,
          matrice: new Matrix4().compose(
            new Vector3(x + l.x, sopra, z + l.z),
            new Quaternion().setFromAxisAngle(new Vector3(0, 1, 0), l.angolo),
            new Vector3(SCALA_EDIFICI, SCALA_EDIFICI, SCALA_EDIFICI),
          ),
        })
        ingombri.push(l.ingombro)
      }
    else
      for (const v of aspetto.volumi) {
        if (sovrapponeStrade(v, tracciato)) continue
        const [vx, vz, larghezza, profondita, altezza] = v
        aggiungi(
          volumi,
          aspetto.colore,
          matrice(x + vx, sopra, z + vz, larghezza, altezza, profondita),
        )
        ingombri.push({ x: vx, z: vz, larghezza, profondita })
      }

    // alberi, cespugli e siepi nei posti liberi
    for (const p of pianteTessera(
      citta.seme,
      t.hex,
      t.tipo,
      tracciato,
      ingombri,
    ))
      pianta(t.hex, x, z, sopra, p)

    // isola della rotonda, con il monumento al centro
    if (tracciato.rotonda) {
      const monumento = monumentoIsola(
        tracciato.rotonda,
        t.tipo,
        t.hex,
        connettori,
      )
      for (const p of partiIsola(
        tracciato.rotonda,
        t.tipo,
        monumento !== null,
      )) {
        aggiungi(
          isole,
          p.materiale,
          matrice(x + p.x, sopra + p.y, z + p.z, p.raggio, p.altezza, p.raggio),
        )
      }
      // piante dell'isola, tra il monumento (o la fontana) e il cordolo; niente sul cemento
      const decorazione = decorazioneIsola(t.tipo)
      if (decorazione !== "cemento") {
        const r = raggioIsola(tracciato.rotonda)
        const dentro =
          monumento?.basamento ?? (decorazione === "piazza" ? r * VASCA : null)
        for (const p of pianteIsola(
          citta.seme,
          t.hex,
          tracciato.rotonda,
          r,
          dentro,
        ))
          pianta(t.hex, x, z, sopra + SOPRA_ISOLA, p)
      }
      if (monumento) {
        // davanti del modello (+X) verso il viale principale: rotation.y = atan2(−dz, dx)
        const giro = new Quaternion().setFromAxisAngle(
          new Vector3(0, 1, 0),
          Math.atan2(-monumento.dz, monumento.dx),
        )
        const m = new Matrix4().compose(
          new Vector3(x, sopra + SOPRA_ISOLA, z),
          giro,
          new Vector3().setScalar(monumento.scala),
        )
        aggiungi(monumenti, monumento.nome, { hex: t.hex, matrice: m })
      }
    }

    // strade: copie delle geometrie della tessera, spostate al loro posto
    const g = geometrieDi(connettori, rotonda, rettilinei)
    strade.asfalto.push(g.asfalto.clone().translate(x, sopra, z))
    strade.marciapiedi.push(g.marciapiedi.clone().translate(x, sopra, z))
    strade.segni.push(g.segni.clone().translate(x, sopra, z))
    // le geometrie si fondono nello stesso ordine: i triangoli restano allineati
    for (const tratto of g.trattoPerTriangolo) {
      viaPerTriangolo.push(
        tratto < 0 ? -1 : (stradario.viaDi.get(`${k}#${tratto}`) ?? -1),
      )
    }
  }

  return {
    strati,
    cime,
    volumi,
    edifici,
    isole,
    rampe,
    monumenti,
    piante,
    strade: {
      asfalto: uvDallAlto(fondi(strade.asfalto)),
      marciapiedi: uvDallAlto(fondi(strade.marciapiedi)),
      segni: fondi(strade.segni),
    },
    viaPerTriangolo: Int32Array.from(viaPerTriangolo),
  }
}
