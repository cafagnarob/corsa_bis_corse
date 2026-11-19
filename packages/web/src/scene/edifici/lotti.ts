/*
 * lotti.ts
 * Dove stanno gli edifici su una tessera: lungo le strade, con la facciata a
 * filo del marciapiede (GDD: città italiana, case allineate sui fronti).
 * Funzione pura sulle coordinate della tessera (centro = 0, 0), in unità di
 * gioco; la chiama raggruppa.ts per ogni tessera.
 *
 * Per ogni strada della tessera (il tracciato, senza l'anello delle rotonde)
 * e per ognuno dei suoi due lati si cammina lungo la strada e si prova a
 * mettere un edificio dopo l'altro (il generatore della famiglia dà il
 * prossimo progetto dal seme):
 * - la facciata guarda la strada e sta sul bordo esterno del marciapiede,
 *   più un rientro (il borgo pochi centimetri, come le facciate sfalsate
 *   del kit; i palazzoni qualche metro, con il giardinetto davanti);
 * - l'edificio va bene se tutta la sua impronta sta dentro la tessera, non
 *   tocca nessuna strada o marciapiede (né l'incrocio, né la rotonda) e non
 *   tocca gli edifici già messi; altrimenti si avanza di un passo e si
 *   riprova (dopo un po' di tentativi si cambia progetto);
 * - tra un edificio e il successivo: nel borgo case attaccate, a volte un
 *   vicolo di 4 m; tra i palazzoni 6-14 m.
 * Poi l'interno degli isolati, ognuno a modo suo (decisione del 19 novembre):
 * - borgo: dietro la prima fila di case passa un vicolo di 4 m e sull'altro
 *   lato del vicolo nasce una seconda fila che gli fa fronte; poi un altro
 *   vicolo e una terza fila, finché c'è posto (il labirinto del centro
 *   storico, come l'isolato con vicolo di Blender). Dove la strada finisce
 *   prima del bordo della tessera o dietro le curve resta spazio: lo riempie
 *   una griglia di vicoli dritti nel verso della strada più lunga, che
 *   attraversa tutta la tessera. I vicoli sono "strade finte": gli edifici
 *   non ci vanno sopra;
 * - palazzoni: dietro il fronte si provano righe parallele a ogni strada,
 *   ogni 4 m da 12 a 40 m dal marciapiede; dove un palazzone ci sta lo si
 *   mette (qui solo torri: le stecche sono troppo lunghe per l'interno della
 *   tessera), girato verso la strada, a 6 m da tutti gli altri: file sfalsate
 *   nel verde, come nei quartieri popolari degli anni '60-'70.
 * Quello che resta libero (curve, angoli, giardini) lo riempie la
 * vegetazione: le impronte tornano a raggruppa come ingombri.
 *
 * - villette: lotti uno accanto all'altro col muretto sul marciapiede, e
 *   dietro altre file di lotti (righe parallele, come i palazzoni);
 * - capannoni: righe parallele più lontane, i capannoni sono grandi;
 * - grattacieli: torri sottili a righe, con la piazzetta davanti;
 * - per tutte le famiglie a righe, alla fine, righe dritte che attraversano
 *   tutta la tessera nel verso della strada più lunga: riempiono quello che
 *   le strade non raggiungono (le tessere con una strada sola o con la
 *   rotonda restavano mezze vuote).
 *
 * Quello che va a filo del marciapiede è il lato davanti dell'IMPRONTA del
 * progetto (progetto.ts), non la facciata: nella villetta è il muretto del
 * lotto, nel capannone la palazzina degli uffici che sta davanti.
 *
 * Famiglie per tipo di tessera: centro storico → borgo, popolare →
 * palazzi a corte se è vicino al centro storico (vicinoAlCentro, lo decide
 * raggruppa.ts), altrimenti palazzoni, villette → villette, industriale → capannoni, uffici e
 * commercio → grattacieli. Le nuove costruzioni per ora restano alle scatole
 * segnaposto.
 */

import {
  APOTEMA,
  Casuale,
  type Hex,
  type TipoTessera,
  type TracciatoTessera,
} from "@corsa-bis/engine"
import { PROFILO } from "../strade/profili"
import type { Ingombro } from "../vegetazione/piante"
import { generaBorgo } from "./borgo"
import { generaCapannone } from "./capannoni"
import { generaCorte } from "./corte"
import { generaGrattacielo } from "./grattacieli"
import { generaPalazzone } from "./palazzoni"
import { impronta, SCALA_EDIFICI, type Progetto } from "./progetto"
import { generaVilletta } from "./villette"

/** Un edificio messo sulla tessera. */
export type Lotto = {
  readonly progetto: Progetto
  /** Angolo in basso a destra della facciata (l'origine del progetto), coordinate della tessera. */
  readonly x: number
  readonly z: number
  /** Rotazione attorno a Y: porta il +X del progetto verso la strada. */
  readonly angolo: number
  /** I quattro angoli dell'impronta (coordinate della tessera). */
  readonly angoli: readonly (readonly [number, number])[]
  /** Rettangolo allineato agli assi che contiene l'impronta (per la vegetazione). */
  readonly ingombro: Ingombro
}

/** Come si riempie l'interno degli isolati, dietro i fronti delle strade. */
type Interno =
  /** Borgo: anelli di vicoli larghi `vicolo` m dietro file di case profonde fino a `fila` m. */
  | {
      readonly tipo: "vicoli"
      readonly vicolo: number
      readonly fila: number
      readonly anelli: number
      readonly rientro: (rng: Casuale) => number
    }
  /** Palazzoni: righe parallele alle strade, da `da` a `a` m dal bordo del marciapiede, ogni `passo` m; l'edificio va dove c'è posto. */
  | {
      readonly tipo: "file"
      readonly da: number
      readonly a: number
      readonly passo: number
      readonly genera: (rng: Casuale) => Progetto
    }

type Regola = {
  readonly genera: (rng: Casuale) => Progetto
  /** Rientro della facciata dal marciapiede (m). */
  readonly rientro: (rng: Casuale) => number
  /** Spazio dopo un edificio (m). */
  readonly stacco: (rng: Casuale) => number
  /** Distanza minima da ogni altro edificio (m); negativa = si possono toccare. */
  readonly distanza: number
  readonly interno?: Interno
}

/** Passo con cui si avanza lungo la strada quando un edificio non ci sta. */
const PASSO = 6
/** Tentativi con lo stesso progetto prima di cambiarlo. */
const TENTATIVI = 12
/** Distanza dal bordo della tessera. */
const MARGINE_TESSERA = 2
/** Tolleranza sul marciapiede (la facciata ci sta sopra a filo) e tra edifici attaccati. */
const TOLLERANZA = 1

const REGOLE: Partial<Record<TipoTessera, Regola>> = {
  centro_storico: {
    genera: generaBorgo,
    rientro: (rng) => rng.decimale() * 0.35,
    stacco: (rng) => (rng.probabilita(0.2) ? 4 : 0),
    distanza: -TOLLERANZA / SCALA_EDIFICI,
    // vicolo di 4 m come nell'isolato di Blender; la fila più profonda del borgo è 3 moduli (6,16 m) più il rientro
    interno: {
      tipo: "vicoli",
      vicolo: 4,
      fila: 6.5,
      anelli: 3,
      rientro: (rng) => rng.decimale() * 0.35,
    },
  },
  popolare: {
    genera: generaPalazzone,
    rientro: (rng) => 4 + rng.decimale() * 4,
    stacco: (rng) => 6 + rng.decimale() * 8,
    distanza: 6,
    // si provano righe ogni 4 m dietro il fronte: dove un palazzone ci sta (a 6 m da tutti gli altri), lo si mette
    // dentro ci stanno quasi solo le torri (10-12 m): le stecche (18-28 m) restano sul fronte
    interno: {
      tipo: "file",
      da: 12,
      a: 40,
      passo: 4,
      genera: (rng) => generaPalazzone(rng, "torre"),
    },
  },
  villette: {
    genera: generaVilletta,
    // il muretto sta sul marciapiede; tra un lotto e l'altro poco spazio (i muretti non si sovrappongono)
    rientro: () => 0,
    stacco: (rng) => 0.3 + rng.decimale() * 1.7,
    distanza: -TOLLERANZA / SCALA_EDIFICI,
    // dietro, altre file di lotti: il lotto è profondo 12-17 m
    interno: { tipo: "file", da: 14, a: 40, passo: 4, genera: generaVilletta },
  },
  industriale: {
    genera: generaCapannone,
    // piazzali stretti davanti e tra i capannoni: la zona industriale è fitta
    rientro: (rng) => 1.5 + rng.decimale() * 1.5,
    stacco: (rng) => 3 + rng.decimale() * 3,
    distanza: 3,
    interno: { tipo: "file", da: 12, a: 42, passo: 4, genera: generaCapannone },
  },
  uffici_commercio: {
    genera: generaGrattacielo,
    // torri sottili (6-8 m) con la piazzetta davanti, a 5 m l'una dall'altra
    rientro: (rng) => 2 + rng.decimale() * 2,
    stacco: (rng) => 4 + rng.decimale() * 6,
    distanza: 5,
    interno: {
      tipo: "file",
      da: 12,
      a: 40,
      passo: 4,
      genera: generaGrattacielo,
    },
  },
}

/**
 * Il popolare vicino al centro storico (al massimo DISTANZA_CORTE tessere) ha i palazzi a corte
 * invece dei palazzoni: il residenziale cresce per anelli (GDD). I blocchi stanno a filo strada
 * come il borgo, con un passaggio di 4-8 m tra un blocco e l'altro; dietro, altri blocchi.
 */
const CORTE: Regola = {
  genera: generaCorte,
  rientro: (rng) => rng.decimale() * 0.3,
  stacco: (rng) => 4 + rng.decimale() * 4,
  distanza: 3,
  interno: { tipo: "file", da: 16, a: 40, passo: 4, genera: generaCorte },
}
export const DISTANZA_CORTE = 2

/** Tipi di tessera che hanno edifici veri (gli altri tengono le scatole). */
export const CON_EDIFICI = new Set(Object.keys(REGOLE) as TipoTessera[])

type V = readonly [number, number]

/** Vero se il punto sta dentro l'esagono della tessera (punta in alto: lati dritti a x = ±apotema). */
function dentroTessera([x, z]: V, margine: number) {
  const a = APOTEMA - margine
  return (
    Math.abs(x) <= a && Math.abs(x) / 2 + (Math.abs(z) * Math.sqrt(3)) / 2 <= a
  )
}

/** Distanza di un punto da un segmento. */
function daSegmento(
  px: number,
  pz: number,
  ax: number,
  az: number,
  bx: number,
  bz: number,
) {
  const dx = bx - ax
  const dz = bz - az
  const l = dx * dx + dz * dz || 1
  const t = Math.max(0, Math.min(1, ((px - ax) * dx + (pz - az) * dz) / l))
  return Math.hypot(px - (ax + dx * t), pz - (az + dz * t))
}

/** Punti di controllo di un'impronta: angoli, centro e punti lungo i lati ogni 8 unità. */
function campioni(angoli: readonly V[]): V[] {
  const out: V[] = []
  for (let i = 0; i < 4; i++) {
    const [ax, az] = angoli[i]
    const [bx, bz] = angoli[(i + 1) % 4]
    const n = Math.max(1, Math.ceil(Math.hypot(bx - ax, bz - az) / 8))
    for (let k = 0; k < n; k++)
      out.push([ax + ((bx - ax) * k) / n, az + ((bz - az) * k) / n])
  }
  out.push([
    (angoli[0][0] + angoli[2][0]) / 2,
    (angoli[0][1] + angoli[2][1]) / 2,
  ])
  return out
}

/** Due rettangoli (convessi) si sovrappongono? Separazione sugli assi dei lati. */
function sovrapposti(a: readonly V[], b: readonly V[]) {
  for (const poligono of [a, b])
    for (let i = 0; i < 4; i++) {
      const [x0, z0] = poligono[i]
      const [x1, z1] = poligono[(i + 1) % 4]
      const nx = z0 - z1
      const nz = x1 - x0
      const proietta = (p: readonly V[]) => p.map(([x, z]) => x * nx + z * nz)
      const pa = proietta(a)
      const pb = proietta(b)
      if (
        Math.max(...pa) <= Math.min(...pb) ||
        Math.max(...pb) <= Math.min(...pa)
      )
        return false // asse che li separa
    }
  return true
}

/** Rimpicciolisce un rettangolo verso il suo centro (per tollerare edifici attaccati). */
function stringi(p: readonly V[], d: number): V[] {
  const cx = (p[0][0] + p[2][0]) / 2
  const cz = (p[0][1] + p[2][1]) / 2
  return p.map(([x, z]) => {
    const l = Math.hypot(x - cx, z - cz) || 1
    return [x - ((x - cx) / l) * d, z - ((z - cz) / l) * d] as V
  })
}

/** Una strada del tracciato con le distanze progressive dei suoi punti. */
type Strada = {
  readonly punti: readonly { x: number; z: number }[]
  readonly s: number[]
  readonly lunghezza: number
  readonly limite: number
}

function strada(
  punti: readonly { x: number; z: number }[],
  limite: number,
): Strada {
  const s = [0]
  for (let i = 1; i < punti.length; i++)
    s.push(
      s[i - 1] +
        Math.hypot(punti[i].x - punti[i - 1].x, punti[i].z - punti[i - 1].z),
    )
  return { punti, s, lunghezza: s[s.length - 1], limite }
}

/** Punto e direzione (versore) a distanza d dall'inizio della strada. */
function lungoStrada(st: Strada, d: number) {
  let i = 1
  while (i < st.s.length - 1 && st.s[i] < d) i++
  const a = st.punti[i - 1]
  const b = st.punti[i]
  const l = st.s[i] - st.s[i - 1] || 1
  const k = (d - st.s[i - 1]) / l
  return {
    x: a.x + (b.x - a.x) * k,
    z: a.z + (b.z - a.z) * k,
    tx: (b.x - a.x) / l,
    tz: (b.z - a.z) / l,
  }
}

/** Una strada spostata di lato di `scosta` (vicoli dietro le case): stessi punti, spostati sulla destra del verso × lato. */
function parallela(
  st: Strada,
  lato: 1 | -1,
  scosta: number,
  limite: number,
): Strada {
  const n = st.punti.length
  const punti = st.punti.map((p, i) => {
    const a = st.punti[Math.max(0, i - 1)]
    const b = st.punti[Math.min(n - 1, i + 1)]
    const l = Math.hypot(b.x - a.x, b.z - a.z) || 1
    const tx = (b.x - a.x) / l
    const tz = (b.z - a.z) / l
    return { x: p.x - tz * lato * scosta, z: p.z + tx * lato * scosta }
  })
  return strada(punti, limite)
}

/** Una retta che attraversa tutta la tessera nel verso (tx, tz), a distanza `o` dal centro. */
function retta(tx: number, tz: number, o: number, limite: number): Strada {
  const punti = []
  for (let d = -APOTEMA * 1.2; d <= APOTEMA * 1.2; d += 8)
    punti.push({ x: tx * d - tz * o, z: tz * d + tx * o })
  return strada(punti, limite)
}

/** Gli edifici di una tessera, dal seme della città. */
export function lottiTessera(
  seme: string,
  hex: Hex,
  tipo: TipoTessera,
  tracciato: TracciatoTessera,
  vicinoAlCentro = false,
): Lotto[] {
  const { tratti, rotonda } = tracciato
  const regola = tipo === "popolare" && vicinoAlCentro ? CORTE : REGOLE[tipo]
  if (!regola) return []
  const rng = new Casuale(`${seme}/edifici/${hex.q},${hex.r}`)
  const strade = tratti
    .filter((t) => t.inizio !== "anello" && t.punti.length > 1)
    .map((t) =>
      strada(
        t.punti,
        PROFILO[t.classe].carreggiata / 2 + PROFILO[t.classe].marciapiede,
      ),
    )
  /** Quello che un edificio non deve toccare: le strade vere e, man mano, i vicoli. */
  const ostacoli: Strada[] = [...strade]
  const raggioRotonda = rotonda
    ? rotonda.raggio + rotonda.larghezza / 2 + PROFILO.urbana.marciapiede
    : 0
  const lotti: Lotto[] = []

  /** L'impronta non tocca strade, vicoli, marciapiedi, rotonda né il bordo della tessera, e sta alla distanza giusta dagli altri edifici. */
  const libera = (angoli: readonly V[]) => {
    if (!angoli.every((p) => dentroTessera(p, MARGINE_TESSERA))) return false
    const punti = campioni(angoli)
    const cx = (angoli[0][0] + angoli[2][0]) / 2
    const cz = (angoli[0][1] + angoli[2][1]) / 2
    const raggio = Math.hypot(angoli[0][0] - cx, angoli[0][1] - cz)
    if (
      rotonda &&
      punti.some(([x, z]) => Math.hypot(x, z) < raggioRotonda - TOLLERANZA)
    )
      return false
    for (const st of ostacoli)
      for (let i = 1; i < st.punti.length; i++) {
        const a = st.punti[i - 1]
        const b = st.punti[i]
        // segmento troppo lontano dall'impronta: non serve guardarlo punto per punto
        if (daSegmento(cx, cz, a.x, a.z, b.x, b.z) > raggio + st.limite)
          continue
        if (
          punti.some(
            ([x, z]) =>
              daSegmento(x, z, a.x, a.z, b.x, b.z) < st.limite - TOLLERANZA,
          )
        )
          return false
      }
    // negativo = si possono toccare (case attaccate), positivo = spazio libero attorno
    const sagoma = stringi(angoli, -regola.distanza * SCALA_EDIFICI)
    return !lotti.some((l) => sovrapposti(sagoma, l.angoli))
  }

  /**
   * Cammina lungo una strada (vera o finta) e mette un edificio dopo l'altro sul lato dato. Restituisce quanti ne ha messi.
   * `passo`: di quanto si avanza quando non ci sta; le righe interne usano un passo doppio (sono tante e costano).
   */
  const posa = (
    st: Strada,
    lato: 1 | -1,
    rientro: (rng: Casuale) => number,
    genera = regola.genera,
    passo = PASSO,
  ) => {
    let messi = 0
    let d = 0
    let progetto: Progetto | null = null
    let tentativi = 0
    while (d < st.lunghezza) {
      progetto ??= genera(rng)
      const imp = impronta(progetto)
      const W = (imp.z1 - imp.z0) * SCALA_EDIFICI
      const D = (imp.x1 - imp.x0) * SCALA_EDIFICI
      if (d + W > st.lunghezza) break
      const c = lungoStrada(st, d + W / 2)
      // la strada a destra del verso del tratto è (−tz, tx); la facciata guarda la strada
      const rx = -c.tz
      const rz = c.tx
      const f = st.limite + rientro(rng) * SCALA_EDIFICI
      const nx = -lato * rx // normale della facciata (verso la strada)
      const nz = -lato * rz
      const zx = -nz // il +Z del progetto (la sinistra di chi guarda la facciata)
      const zz = nx
      const px = c.x + lato * rx * f - zx * (W / 2) // angolo davanti a destra dell'impronta
      const pz = c.z + lato * rz * f - zz * (W / 2)
      const angoli: V[] = [
        [px, pz],
        [px + zx * W, pz + zz * W],
        [px + zx * W - nx * D, pz + zz * W - nz * D],
        [px - nx * D, pz - nz * D],
      ]
      if (libera(angoli)) {
        const xs = angoli.map((p) => p[0])
        const zs = angoli.map((p) => p[1])
        // l'origine del progetto (angolo in basso a destra della facciata principale) rispetto all'impronta
        const ox = imp.x1 * SCALA_EDIFICI
        const oz = imp.z0 * SCALA_EDIFICI
        lotti.push({
          progetto,
          x: px - nx * ox - zx * oz,
          z: pz - nz * ox - zz * oz,
          angolo: Math.atan2(-nz, nx),
          angoli,
          ingombro: {
            x: (Math.min(...xs) + Math.max(...xs)) / 2,
            z: (Math.min(...zs) + Math.max(...zs)) / 2,
            larghezza: Math.max(...xs) - Math.min(...xs),
            profondita: Math.max(...zs) - Math.min(...zs),
          },
        })
        messi++
        d += W + regola.stacco(rng) * SCALA_EDIFICI
        progetto = null
        tentativi = 0
      } else {
        d += passo
        if (++tentativi >= TENTATIVI) {
          progetto = null
          tentativi = 0
        }
      }
    }
    return messi
  }

  // 1. i fronti delle strade, sui due lati
  for (const st of strade)
    for (const lato of [1, -1] as const) posa(st, lato, regola.rientro)

  // 2. l'interno degli isolati
  const interno = regola.interno
  if (interno?.tipo === "vicoli") {
    // anelli di vicoli paralleli alle strade, ognuno con una fila di case che gli fa fronte dal lato lontano dalla strada
    const vicolo = interno.vicolo * SCALA_EDIFICI
    const fila = interno.fila * SCALA_EDIFICI
    for (let anello = 1; anello <= interno.anelli; anello++) {
      let messi = 0
      for (const st of strade)
        for (const lato of [1, -1] as const) {
          const scosta =
            st.limite + fila + vicolo / 2 + (anello - 1) * (fila + vicolo)
          const v = parallela(st, lato, scosta, vicolo / 2)
          ostacoli.push(v)
          messi += posa(v, lato, interno.rientro)
        }
      if (messi === 0) break
    }
    // quello che resta (dove la strada finisce prima del bordo, o dietro una curva): una griglia di vicoli
    // dritti nel verso della strada più lunga, che attraversa tutta la tessera
    const lunga = strade.reduce<Strada | null>(
      (m, st) => (!m || st.lunghezza > m.lunghezza ? st : m),
      null,
    )
    if (lunga) {
      const c = lungoStrada(lunga, lunga.lunghezza / 2)
      const passo = fila + vicolo
      const fase = rng.decimale() * passo
      for (let o = -APOTEMA - fase; o <= APOTEMA; o += passo) {
        const v = retta(c.tx, c.tz, o, vicolo / 2)
        ostacoli.push(v)
        posa(v, 1, interno.rientro)
      }
    }
  } else if (interno?.tipo === "file") {
    // file parallele a ogni strada, nel verde dietro i palazzoni del fronte, che guardano verso la strada
    for (let m = interno.da; m <= interno.a; m += interno.passo)
      for (const st of strade)
        for (const lato of [1, -1] as const)
          posa(
            parallela(st, lato, st.limite + m * SCALA_EDIFICI, 0),
            lato,
            () => 0,
            interno.genera,
            2 * PASSO,
          )
    // dove le strade non arrivano (una strada sola, una rotonda, un angolo lontano): righe dritte nel verso
    // della strada più lunga, che attraversano tutta la tessera, come la griglia dei vicoli del borgo
    const lunga = strade.reduce<Strada | null>(
      (m, st) => (!m || st.lunghezza > m.lunghezza ? st : m),
      null,
    )
    if (lunga) {
      const c = lungoStrada(lunga, lunga.lunghezza / 2)
      const passo = interno.passo * SCALA_EDIFICI
      for (let o = -APOTEMA; o <= APOTEMA; o += passo)
        for (const lato of [1, -1] as const)
          posa(
            retta(c.tx, c.tz, o, 0),
            lato,
            () => 0,
            interno.genera,
            2 * PASSO,
          )
    }
  }
  // i blocchi a corte sono grandi (14-22 × 12-22 m): dove non ce ne sta nemmeno uno (le tessere con la
  // rotonda grande dei viali in mezzo) il quartiere resta popolare, con i palazzoni
  if (lotti.length === 0 && regola === CORTE)
    return lottiTessera(seme, hex, tipo, tracciato, false)
  return lotti
}
