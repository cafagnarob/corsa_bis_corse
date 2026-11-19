/*
 * tracciati.ts
 * Il tracciato delle strade dentro una tessera: le linee di mezzeria, con la
 * direzione in ogni punto, calcolate dai connettori (GDD: "Geometria della
 * tessera e strade", stesse regole di cb_basi.py in Blender).
 *
 * Coordinate LOCALI della tessera, in unità di gioco: origine al centro,
 * x = est, z = sud (nord = -z). I connettori stanno al punto medio dei lati,
 * a distanza APOTEMA dal centro; ogni strada parte perpendicolare al suo lato,
 * così continua dritta nella tessera vicina.
 *
 * Casi:
 * - un viale che attraversa la tessera (esattamente 2 lati a viale): una curva
 *   continua da lato a lato (rettilineo o curva larga); le altre strade si
 *   innestano perpendicolari sul viale (incroci a T);
 * - un solo connettore: strada a fondo cieco fino al centro;
 * - due connettori della stessa classe: una curva da lato a lato;
 * - tutti gli altri casi: un incrocio al centro, raggiunto da ogni lato.
 *   - se la rete ha messo una rotonda nella tessera: ogni strada arriva dritta
 *   fino alla mezzeria dell'anello, che si percorre in senso antiorario.
 *
 *
 *  * Rampe: dove sul lato c'è una rampa (rettilinei[lato] > 0) la strada parte
 * con un rettilineo lungo quanto la rampa, perpendicolare al lato, e curva
 * solo dopo; così la rampa (un pezzo dritto) e la strada combaciano.
 *
 * Funzione pura: dipende solo da connettori, rotonda e rettilinei. Tessere
 * uguali hanno lo stesso tracciato (e la grafica può riusarlo).
 *
 * Funzione pura: dipende solo dai connettori e dalla rotonda. Tessere uguali
 * hanno lo stesso tracciato (e la grafica può riusarlo).
 */

import { APOTEMA, LATI, type Lato } from "./esagoni"
import type { ClasseStrada, Connettore, TipoRotonda } from "./strade"

/** Un punto della mezzeria con la direzione di marcia (versore tx, tz). */
export type PuntoTracciato = {
  readonly x: number
  readonly z: number
  readonly tx: number
  readonly tz: number
}

/**
 * Come finisce un tratto: sul lato della tessera, in un incrocio al centro,
 * innestato su un viale, a fondo cieco, sull'anello di una rotonda;
 * 'anello' è l'anello stesso (un tratto chiuso, percorso in senso antiorario).
 */
export type Estremo =
  | "lato"
  | "incrocio"
  | "innesto"
  | "cieco"
  | "rotonda"
  | "anello"

export type Tratto = {
  readonly classe: ClasseStrada
  readonly punti: readonly PuntoTracciato[] // dall'inizio alla fine
  readonly inizio: Estremo
  readonly fine: Estremo
  readonly lato: Lato | null // lato da cui parte (se inizio = 'lato')
}

/** Misure di una rotonda al centro della tessera (raggio della mezzeria dell'anello e larghezza). */
export type Rotonda = {
  readonly tipo: TipoRotonda
  readonly raggio: number // mezzeria dell'anello
  readonly larghezza: number // carreggiata dell'anello
  readonly isola: number // raggio dell'isola centrale
}

export type TracciatoTessera = {
  readonly tratti: readonly Tratto[]
  /** Centro dell'incrocio, se c'è un incrocio al centro della tessera. */
  readonly incrocio: { readonly x: number; readonly z: number } | null
  readonly rotonda: Rotonda | null
}

/** Misure delle rotonde a scala ×5,2: stanno comode dentro la tessera (apotema 173). */
export const MISURE_ROTONDA: Record<
  TipoRotonda,
  { raggio: number; larghezza: number }
> = {
  compatta: { raggio: 52, larghezza: 26 },
  ampia: { raggio: 68, larghezza: 34 },
}

const PASSO = 4 // distanza indicativa tra due punti della mezzeria

type V = { x: number; z: number }
const piu = (a: V, b: V): V => ({ x: a.x + b.x, z: a.z + b.z })
const per = (a: V, k: number): V => ({ x: a.x * k, z: a.z * k })
const meno = (a: V, b: V): V => ({ x: a.x - b.x, z: a.z - b.z })
const lung = (a: V) => Math.hypot(a.x, a.z)

/** Punto medio del lato (dove sta il connettore). */
export function puntoLato(lato: Lato): V {
  const a = (lato * Math.PI) / 3
  return { x: APOTEMA * Math.cos(a), z: -APOTEMA * Math.sin(a) }
}

/** Direzione perpendicolare al lato, verso l'interno della tessera. */
export function versoInterno(lato: Lato): V {
  const a = (lato * Math.PI) / 3
  return { x: -Math.cos(a), z: Math.sin(a) }
}

/**
 * Curva di Bézier cubica da p0 (partendo in direzione d0) a p3 (arrivando in
 * direzione d3), campionata a passi regolari, con la tangente in ogni punto.
 */
function curva(p0: V, d0: V, p3: V, d3: V): PuntoTracciato[] {
  const L = lung(meno(p3, p0))
  const k = L * 0.4
  const p1 = piu(p0, per(d0, k))
  const p2 = meno(p3, per(d3, k))
  const n = Math.max(2, Math.ceil(L / PASSO))
  const punti: PuntoTracciato[] = []
  for (let i = 0; i <= n; i++) {
    const t = i / n
    const u = 1 - t
    const p = piu(
      piu(per(p0, u * u * u), per(p1, 3 * u * u * t)),
      piu(per(p2, 3 * u * t * t), per(p3, t * t * t)),
    )
    const d = piu(
      piu(per(meno(p1, p0), 3 * u * u), per(meno(p2, p1), 6 * u * t)),
      per(meno(p3, p2), 3 * t * t),
    )
    const l = lung(d) || 1
    punti.push({ x: p.x, z: p.z, tx: d.x / l, tz: d.z / l })
  }
  return punti
}

/** Nessun rettilineo: nessuna rampa sui sei lati. */
export const SENZA_RETTILINEI: readonly number[] = [0, 0, 0, 0, 0, 0]

/** Il punto a `l` unità dal lato, verso l'interno, e la direzione verso l'interno. */
function dopoIlRettilineo(lato: Lato, l: number): { p: V; d: V } {
  const d = versoInterno(lato)
  return { p: piu(puntoLato(lato), per(d, l)), d }
}

/** Il rettilineo dal lato verso l'interno, lungo `l` (vuoto se l = 0), percorso nella direzione `d`. */
function rettilineo(da: V, a: V, d: V): PuntoTracciato[] {
  const L = lung(meno(a, da))
  if (L < 1e-6) return []
  const n = Math.max(1, Math.ceil(L / PASSO))
  return Array.from({ length: n + 1 }, (_, i) => {
    const t = i / n
    return {
      x: da.x + (a.x - da.x) * t,
      z: da.z + (a.z - da.z) * t,
      tx: d.x,
      tz: d.z,
    }
  })
}

/** Unisce due spezzate che si toccano, senza ripetere il punto in comune. */
const unisci = (a: PuntoTracciato[], b: PuntoTracciato[]) =>
  a.length === 0 ? b : b.length === 0 ? a : [...a, ...b.slice(1)]

/** Dal lato al centro della tessera, in linea retta. */
function versoCentro(lato: Lato): PuntoTracciato[] {
  const d = versoInterno(lato)
  return curva(puntoLato(lato), d, { x: 0, z: 0 }, d)
}

/**
 * Dal lato `da` al lato `a`, partendo e arrivando perpendicolari ai lati;
 * con una rampa su un lato, il tratto vicino a quel lato è dritto.
 */
function daLatoALato(
  da: Lato,
  a: Lato,
  rettilinei: readonly number[],
): PuntoTracciato[] {
  const inizio = dopoIlRettilineo(da, rettilinei[da])
  const fine = dopoIlRettilineo(a, rettilinei[a])
  const uscita = per(fine.d, -1) // verso il lato `a`, cioè fuori dalla tessera
  return unisci(
    unisci(
      rettilineo(puntoLato(da), inizio.p, inizio.d),
      curva(inizio.p, inizio.d, fine.p, uscita),
    ),
    rettilineo(fine.p, puntoLato(a), uscita),
  )
}

/**
 * Dal lato `da` fino a un punto della strada `su`, arrivando perpendicolare
 * (incrocio a T). Il punto è il più vicino al lato tra quelli della parte
 * centrale della strada (dal 25% al 75%), per non innestarsi sul bordo.
 */
function innesto(
  da: Lato,
  su: readonly PuntoTracciato[],
  rettilinei: readonly number[],
): PuntoTracciato[] {
  const { p: p0, d } = dopoIlRettilineo(da, rettilinei[da]) // con la rampa, la curva parte dopo il rettilineo
  const centrali = su.slice(
    Math.floor(su.length * 0.25),
    Math.ceil(su.length * 0.75),
  )
  const meta = centrali.reduce((m, p) =>
    lung(meno(p, p0)) < lung(meno(m, p0)) ? p : m,
  )
  let normale: V = { x: -meta.tz, z: meta.tx }
  if ((meta.x - p0.x) * normale.x + (meta.z - p0.z) * normale.z < 0)
    normale = per(normale, -1)
  return unisci(rettilineo(puntoLato(da), p0, d), curva(p0, d, meta, normale))
}

/** Anello della rotonda: un cerchio chiuso percorso in senso antiorario (visto dall'alto). */
function anello(raggio: number): PuntoTracciato[] {
  const n = Math.ceil((2 * Math.PI * raggio) / PASSO)
  return Array.from({ length: n + 1 }, (_, i) => {
    const a = (i / n) * 2 * Math.PI // nord = -z, quindi antiorario = angolo crescente su (x, -z)
    return {
      x: raggio * Math.cos(a),
      z: -raggio * Math.sin(a),
      tx: -Math.sin(a),
      tz: -Math.cos(a),
    }
  })
}

/**
 * Dal lato fino alla mezzeria dell'anello, in linea retta verso il centro.
 * Il ramo finisce sotto la carreggiata dell'anello: così anche un viale largo
 * si raccorda senza spigoli che sporgono fuori dalla rotonda.
 */
function versoRotonda(lato: Lato, raggio: number): PuntoTracciato[] {
  const d = versoInterno(lato)
  const p0 = puntoLato(lato)
  return curva(p0, d, piu(p0, per(d, APOTEMA - raggio)), d)
}

export function tracciatoTessera(
  connettori: readonly Connettore[],
  tipoRotonda: TipoRotonda | null = null,
  rettilinei: readonly number[] = SENZA_RETTILINEI,
): TracciatoTessera {
  const lati = LATI.filter((l) => connettori[l] !== "nessuna")
  const classe = (l: Lato) => connettori[l] as ClasseStrada
  const viali = lati.filter((l) => classe(l) === "viale")

  // nessuna strada
  if (lati.length === 0) return { tratti: [], incrocio: null, rotonda: null }

  // rotonda al centro: ogni strada arriva sull'anello
  if (tipoRotonda) {
    const { raggio, larghezza } = MISURE_ROTONDA[tipoRotonda]
    const tratti: Tratto[] = lati.map((l) => ({
      classe: classe(l),
      punti: versoRotonda(l, raggio),
      inizio: "lato",
      fine: "rotonda",
      lato: l,
    }))
    tratti.push({
      classe: "urbana",
      punti: anello(raggio),
      inizio: "anello",
      fine: "anello",
      lato: null,
    })
    return {
      tratti,
      incrocio: null,
      rotonda: {
        tipo: tipoRotonda,
        raggio,
        larghezza,
        isola: raggio - larghezza / 2,
      },
    }
  }

  // fondo cieco
  if (lati.length === 1) {
    const l = lati[0]
    return {
      tratti: [
        {
          classe: classe(l),
          punti: versoCentro(l),
          inizio: "lato",
          fine: "cieco",
          lato: l,
        },
      ],
      incrocio: null,
      rotonda: null,
    }
  }

  // viale passante, con eventuali innesti
  if (viali.length === 2) {
    const [a, b] = viali
    const passante = daLatoALato(a, b, rettilinei)
    const tratti: Tratto[] = [
      {
        classe: "viale",
        punti: passante,
        inizio: "lato",
        fine: "lato",
        lato: a,
      },
    ]
    for (const l of lati) {
      if (classe(l) === "viale") continue
      tratti.push({
        classe: classe(l),
        punti: innesto(l, passante, rettilinei),
        inizio: "lato",
        fine: "innesto",
        lato: l,
      })
    }
    return { tratti, incrocio: null, rotonda: null }
  }

  // due strade della stessa classe: una sola curva
  if (lati.length === 2 && classe(lati[0]) === classe(lati[1])) {
    const [a, b] = lati
    return {
      tratti: [
        {
          classe: classe(a),
          punti: daLatoALato(a, b, rettilinei),
          inizio: "lato",
          fine: "lato",
          lato: a,
        },
      ],
      incrocio: null,
      rotonda: null,
    }
  }

  // incrocio al centro
  return {
    tratti: lati.map((l) => ({
      classe: classe(l),
      punti: versoCentro(l),
      inizio: "lato" as const,
      fine: "incrocio" as const,
      lato: l,
    })),
    incrocio: { x: 0, z: 0 },
    rotonda: null,
  }
}
