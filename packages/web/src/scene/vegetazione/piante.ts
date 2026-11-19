/*
 * piante.ts
 * Dove vanno alberi, cespugli e siepi in una tessera (GDD: "Alberi, cespugli
 * e siepe di cartone" e "Vegetazione esportata", 18 novembre; decisioni del
 * 18 novembre: città più verde, siepe solo nei quartieri residenziali,
 * Abete_Festoni sempre, alberi e cespugli veri nelle isole delle rotonde).
 *
 * Funzione pura: dai dati della tessera (tipo, tracciato delle strade,
 * volumi rimasti, monumento della rotonda) restituisce le piante in
 * coordinate LOCALI della tessera (origine al centro, x = est, z = sud).
 * Il caso viene dal seme della città e dalla posizione della tessera: una
 * tessera ha sempre le stesse piante.
 *
 * Come si sceglie un punto libero (campionamento "a dischi"): si provano
 * punti a caso nella tessera e si tiene solo chi
 * - sta dentro l'esagono, lontano dal bordo almeno quanto la chioma (non
 *   sporge oltre lo scalino di cartone);
 * - non tocca strade e marciapiedi (con un margine, che lascia posto anche
 *   alla siepe), né il cerchio della rotonda;
 * - non tocca i volumi (gli edifici segnaposto);
 * - è abbastanza lontano dalle piante già messe (somma dei due raggi).
 *
 * La siepe va sull'erba appena fuori dal marciapiede di viali e strade
 * urbane, a moduli da 20,8 unità (4 m × 5,2), solo nei quartieri
 * residenziali; si interrompe dove arriva un'altra strada, la rotonda o il
 * bordo della tessera, e ogni tanto per un varco (cancello, passo carrabile).
 */

import {
  APOTEMA,
  Casuale,
  type ClasseStrada,
  LATI,
  puntoLato,
  type Hex,
  type Rotonda,
  type TipoTessera,
  type TracciatoTessera,
  type Tratto,
} from "@corsa-bis/engine"
import { PROFILO } from "../strade/profili"

export type Pianta =
  | "Abete"
  | "Abete_Festoni"
  | "Albero_Tondo"
  | "Albero_Goccia"
  | "Cespuglio_Cupola"
  | "Cespuglio_Nuvola"
  | "Siepe"

/** Una pianta messa nella tessera: punto (locale), rotazione attorno a Y, scala (già × 5,2). */
export type PiantaPosata = {
  readonly pianta: Pianta
  readonly x: number
  readonly z: number
  readonly angolo: number
  readonly scala: number
}

/** Un volume rimasto nella tessera (centro, larghezza lungo x, profondità lungo z). */
export type Ingombro = {
  readonly x: number
  readonly z: number
  readonly larghezza: number
  readonly profondita: number
}

/** Scala dei modelli: metri reali → unità di gioco. */
const SCALA = 5.2
/** Mezza larghezza della chioma, in unità di gioco (circa, a scala 1). */
const RAGGIO: Record<Exclude<Pianta, "Siepe">, number> = {
  Abete: 11,
  Abete_Festoni: 10,
  Albero_Tondo: 12,
  Albero_Goccia: 7,
  Cespuglio_Cupola: 5,
  Cespuglio_Nuvola: 6,
}
/** Spazio tenuto libero oltre il marciapiede (lì c'è la siepe dei viali). */
const MARGINE_STRADA = 6
/** Distanza della siepe dal bordo del marciapiede (centro della siepe). */
const SIEPE_FUORI = 2.5
/** Lunghezza di un modulo di siepe (4 m × 5,2). */
export const MODULO_SIEPE = 4 * SCALA

/**
 * Quanto è verde la città: moltiplica il numero di alberi e cespugli di ogni
 * tessera. Con 1 una città di 90 tessere ha circa 1.000 alberi e 900 cespugli
 * (circa 700 mila triangoli in tutto con il LOD1): se la scena rallenta, si
 * abbassa qui.
 */
export const DENSITA = 1

type Pesi = Partial<Record<Pianta, number>>
type Regola = {
  readonly alberi: readonly [number, number]
  readonly cespugli: readonly [number, number]
  readonly specie: Pesi
  readonly scala?: readonly [number, number]
}

const CESPUGLI: Pesi = { Cespuglio_Cupola: 1, Cespuglio_Nuvola: 1 }

/** Quante piante e quali, per tipo di tessera (città verde: decisione del 18 novembre). */
const REGOLE: Record<TipoTessera, Regola> = {
  parco: {
    alberi: [22, 30],
    cespugli: [12, 16],
    specie: { Abete: 3, Abete_Festoni: 1, Albero_Tondo: 3, Albero_Goccia: 2 },
  },
  villette: {
    alberi: [8, 11],
    cespugli: [7, 9],
    specie: { Albero_Tondo: 3, Albero_Goccia: 2, Abete_Festoni: 1 },
  },
  popolare: {
    alberi: [6, 9],
    cespugli: [4, 6],
    specie: { Albero_Tondo: 3, Albero_Goccia: 1, Abete_Festoni: 1 },
  },
  nuove_costruzioni: {
    alberi: [7, 10],
    cespugli: [5, 7],
    specie: { Albero_Goccia: 2, Albero_Tondo: 2, Abete_Festoni: 1 },
    scala: [0.85, 1.0],
  },
  strada: {
    alberi: [7, 11],
    cespugli: [3, 5],
    specie: { Abete: 3, Albero_Goccia: 2, Abete_Festoni: 1 },
  },
  uffici_commercio: {
    alberi: [2, 3],
    cespugli: [6, 8],
    specie: { Albero_Goccia: 1 },
  },
  industriale: {
    alberi: [2, 3],
    cespugli: [0, 0],
    specie: { Albero_Goccia: 1, Abete: 1 },
  },
  centro_storico: { alberi: [0, 0], cespugli: [4, 6], specie: {} },
}

/**
 * Quartieri residenziali con la siepe lungo le strade. Le villette no: dal
 * 19 novembre il loro lotto ha il muretto proprio sul bordo del marciapiede
 * (edifici/villette.ts), e la siepe ci finiva dentro.
 */
const CON_SIEPE_TESSERA: ReadonlySet<TipoTessera> = new Set([
  "popolare",
  "nuove_costruzioni",
])
/**
 * Strade con la siepe ai lati: viali e strade urbane. Nei quartieri
 * residenziali i viali sono rari (le arterie li attraversano poco), quasi
 * tutte le strade sono urbane: con i soli viali la siepe quasi non si vedeva.
 */
const CON_SIEPE: ReadonlySet<ClasseStrada> = new Set(["viale", "urbana"])
/**
 * Probabilità che un modulo di siepe manchi: è il varco del cancello o del
 * passo carrabile. Rompe la fila continua e risparmia triangoli (ogni modulo
 * costa 216 triangoli nel LOD1): con 0,35 una città di 72 tessere ha circa
 * 490 moduli invece di 750.
 */
const VARCHI = 0.35

const scegli = (rng: Casuale, pesi: Pesi): Pianta =>
  rng.scegliPesato(
    (Object.entries(pesi) as [Pianta, number][]).map(([valore, peso]) => ({
      valore,
      peso,
    })),
  )

/** Distanza di un punto dalla mezzeria di un tratto (i punti sono fitti: basta il più vicino). */
function distanzaDa(x: number, z: number, t: Tratto): number {
  let min = Infinity
  for (const p of t.punti) min = Math.min(min, Math.hypot(x - p.x, z - p.z))
  return min
}

/** Metà dell'ingombro di una strada: carreggiata più marciapiede. */
const mezzaStrada = (t: Tratto) =>
  PROFILO[t.classe].carreggiata / 2 + PROFILO[t.classe].marciapiede

/** Fuori dal cerchio della rotonda (isola, anello e marciapiede esterno) di almeno r. */
const fuoriRotonda = (
  x: number,
  z: number,
  r: number,
  rotonda: Rotonda | null,
) =>
  !rotonda ||
  Math.hypot(x, z) >
    rotonda.raggio + rotonda.larghezza / 2 + PROFILO.urbana.marciapiede + r

/** Dentro l'esagono, con almeno r dal bordo. */
function dentroEsagono(x: number, z: number, r: number): boolean {
  for (const l of LATI) {
    const p = puntoLato(l)
    if ((x * p.x + z * p.z) / APOTEMA > APOTEMA - r) return false
  }
  return true
}

/** Le piante di una tessera, in coordinate locali. */
export function pianteTessera(
  seme: string,
  hex: Hex,
  tipo: TipoTessera,
  { tratti, rotonda }: TracciatoTessera,
  volumi: readonly Ingombro[],
): PiantaPosata[] {
  const rng = new Casuale(`${seme}/vegetazione/${hex.q},${hex.r}`)
  const regola = REGOLE[tipo]
  const strade = tratti.filter((t) => t.inizio !== "anello")
  const piante: PiantaPosata[] = []
  const raggi: number[] = [] // raggio di ogni pianta messa (per la distanza minima)

  const libero = (x: number, z: number, r: number) =>
    dentroEsagono(x, z, r) &&
    fuoriRotonda(x, z, r, rotonda) &&
    strade.every(
      (t) => distanzaDa(x, z, t) > mezzaStrada(t) + MARGINE_STRADA + r,
    ) &&
    volumi.every(
      (v) =>
        Math.abs(x - v.x) > v.larghezza / 2 + r + 2 ||
        Math.abs(z - v.z) > v.profondita / 2 + r + 2,
    ) &&
    piante.every((p, i) => Math.hypot(x - p.x, z - p.z) > r + raggi[i])

  /** Prova a mettere n piante scelte con i pesi dati; si ferma se non trova posto. */
  const metti = (n: number, specie: Pesi) => {
    if (Object.keys(specie).length === 0) return
    let messe = 0
    for (let tentativi = 0; messe < n && tentativi < n * 40; tentativi++) {
      const pianta = scegli(rng, specie) as Exclude<Pianta, "Siepe">
      const [min, max] = regola.scala ?? [0.85, 1.15]
      const k = min + (max - min) * rng.decimale()
      const r = RAGGIO[pianta] * k
      const x = (rng.decimale() * 2 - 1) * APOTEMA
      const z = (rng.decimale() * 2 - 1) * APOTEMA * 1.16
      if (!libero(x, z, r)) continue
      piante.push({
        pianta,
        x,
        z,
        angolo: rng.decimale() * Math.PI * 2,
        scala: SCALA * k,
      })
      raggi.push(r)
      messe++
    }
  }

  // prima la siepe (decide dove gli alberi non vanno), poi alberi, poi cespugli negli spazi rimasti
  if (CON_SIEPE_TESSERA.has(tipo)) {
    for (const s of siepe(strade, rotonda, volumi, rng)) {
      piante.push(s)
      raggi.push(MODULO_SIEPE / 2)
    }
  }
  metti(Math.round(rng.intero(...regola.alberi) * DENSITA), regola.specie)
  metti(Math.round(rng.intero(...regola.cespugli) * DENSITA), CESPUGLI)
  return piante
}

/**
 * I moduli di siepe lungo viali e strade urbane della tessera, sui due lati, sull'erba
 * appena fuori dal marciapiede. Un modulo va dove i suoi due capi e il centro
 * sono liberi da altre strade, dalla rotonda e dagli edifici (gli ingombri: i palazzi
 * a corte stanno a filo del marciapiede, e la siepe ci entrava dentro) e stanno dentro la tessera.
 */
function siepe(
  strade: readonly Tratto[],
  rotonda: Rotonda | null,
  volumi: readonly Ingombro[],
  rng: Casuale,
): PiantaPosata[] {
  const out: PiantaPosata[] = []
  for (const t of strade.filter((x) => CON_SIEPE.has(x.classe))) {
    const fuori = mezzaStrada(t) + SIEPE_FUORI
    // distanze progressive lungo la mezzeria
    const s = [0]
    for (let i = 1; i < t.punti.length; i++)
      s.push(
        s[i - 1] +
          Math.hypot(
            t.punti[i].x - t.punti[i - 1].x,
            t.punti[i].z - t.punti[i - 1].z,
          ),
      )
    const L = s[s.length - 1]
    const punto = (d: number) => {
      let i = 1
      while (i < s.length - 1 && s[i] < d) i++
      const a = t.punti[i - 1]
      const b = t.punti[i]
      const k = (d - s[i - 1]) / (s[i] - s[i - 1] || 1)
      return {
        x: a.x + (b.x - a.x) * k,
        z: a.z + (b.z - a.z) * k,
        tx: a.tx,
        tz: a.tz,
      }
    }
    for (const lato of [-1, 1]) {
      for (let d = 0; d + MODULO_SIEPE <= L; d += MODULO_SIEPE) {
        // i due capi e il centro del modulo, spostati a lato (+ = destra: (−tz, tx))
        const capi = [d, d + MODULO_SIEPE / 2, d + MODULO_SIEPE].map((v) => {
          const p = punto(v)
          return { x: p.x - p.tz * fuori * lato, z: p.z + p.tx * fuori * lato }
        })
        const buoni = capi.every(
          (c) =>
            dentroEsagono(c.x, c.z, 1) &&
            fuoriRotonda(c.x, c.z, 1, rotonda) &&
            strade.every(
              (o) => o === t || distanzaDa(c.x, c.z, o) > mezzaStrada(o) + 2,
            ) &&
            volumi.every(
              (v) =>
                Math.abs(c.x - v.x) > v.larghezza / 2 + 2 ||
                Math.abs(c.z - v.z) > v.profondita / 2 + 2,
            ),
        )
        if (!buoni || rng.decimale() < VARCHI) continue
        const [a, c, b] = capi
        // davanti del modulo (+X) lungo la strada: rotation.y = atan2(−dz, dx)
        out.push({
          pianta: "Siepe",
          x: c.x,
          z: c.z,
          angolo: Math.atan2(-(b.z - a.z), b.x - a.x),
          scala: SCALA,
        })
      }
    }
  }
  return out
}

/**
 * Le piante dell'isola di una rotonda, al posto dei vecchi cilindri: un
 * anello tra il basamento del monumento (o il centro) e il cordolo. Nella
 * rotonda compatta c'è posto solo per i cespugli; nell'ampia pioppi
 * (Albero_Goccia, stretti) e cespugli alternati.
 */
export function pianteIsola(
  seme: string,
  hex: Hex,
  rotonda: Rotonda,
  raggioIsola: number,
  basamento: number | null,
): PiantaPosata[] {
  const rng = new Casuale(`${seme}/isola/${hex.q},${hex.r}`)
  const dentro = basamento ?? raggioIsola * 0.35
  const giro = (raggioIsola + dentro) / 2
  const spazio = (raggioIsola - dentro) / 2 // mezza larghezza dell'anello libero
  const alberi = rotonda.tipo === "ampia" && spazio > RAGGIO.Albero_Goccia
  const n = alberi ? 10 : 8
  const out: PiantaPosata[] = []
  for (let i = 0; i < n; i++) {
    const a = (i / n) * Math.PI * 2
    const pianta: Pianta =
      alberi && i % 2 === 0
        ? "Albero_Goccia"
        : i % 2 === 0
          ? "Cespuglio_Cupola"
          : "Cespuglio_Nuvola"
    // la scala si riduce se la pianta non ci sta nell'anello
    const k = Math.min(
      1,
      (spazio - 0.5) / RAGGIO[pianta as Exclude<Pianta, "Siepe">],
    )
    out.push({
      pianta,
      x: Math.cos(a) * giro,
      z: Math.sin(a) * giro,
      angolo: rng.decimale() * Math.PI * 2,
      scala: SCALA * k,
    })
  }
  return out
}
