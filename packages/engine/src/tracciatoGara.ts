/*
 * tracciatoGara.ts
 * Dal circuito (circuito.ts) a quello che serve per correre:
 * - la LINEA: la mezzeria del giro, un punto ogni PASSO unità, con la
 *   distanza dal traguardo (s) e la mezza larghezza della carreggiata;
 * - la TRAIETTORIA ideale: la linea che taglia le curve restando dentro la
 *   carreggiata, base della guida degli avversari;
 * - i CHECKPOINT: porte perpendicolari alla strada, in ordine, il primo sul
 *   traguardo; un giro conta solo se si passano tutte;
 * - due funzioni per la gara: quando una porta viene attraversata nel verso
 *   giusto (attraversaCheckpoint) e a che punto del giro sta un mezzo
 *   (progressoSulGiro).
 *
 * Tutto in pianta (x, z), in unità di gioco. Le quote le aggiunge la scena.
 */

import type { Circuito } from "./circuito"
import { chiaveTratto, puntoSulTratto, type GrafoStradale } from "./grafo"
import type { ClasseStrada } from "./strade"

/* ------------------------------------------------------------------------
 * Opzioni
 * --------------------------------------------------------------------- */

export type OpzioniTracciato = {
  /** Distanza tra due punti della linea, in unità. */
  readonly passo: number
  /** Distanza tra due checkpoint, in unità (circa 200 m reali). */
  readonly distanzaCheckpoint: number
  /** Mezza larghezza della carreggiata per classe (web: strade/profili.ts). */
  readonly mezzaCarreggiata: Readonly<Record<ClasseStrada, number>>
  /** Spazio da lasciare tra traiettoria e bordo: mezzo mezzo più un poco. */
  readonly margine: number
  /** Passate di levigatura della traiettoria: più passate, curve più tagliate. */
  readonly passate: number
}

export const OPZIONI_TRACCIATO: OpzioniTracciato = {
  passo: 5,
  distanzaCheckpoint: 1040,
  mezzaCarreggiata: { viale: 36.4, urbana: 18.2, stretta: 11 },
  margine: 6,
  passate: 300,
}

/* ------------------------------------------------------------------------
 * Risultato
 * --------------------------------------------------------------------- */

export type PuntoLinea = {
  readonly x: number
  readonly z: number
  /** Distanza dal traguardo lungo la mezzeria. */
  readonly s: number
  /** Direzione di marcia (vettore unitario). */
  readonly tx: number
  readonly tz: number
  /** Mezza larghezza della carreggiata in questo punto. */
  readonly mezzaLarghezza: number
}

export type Checkpoint = {
  readonly indice: number // 0 = traguardo
  readonly x: number
  readonly z: number
  /** Direzione di marcia: la porta si passa andando in questo verso. */
  readonly tx: number
  readonly tz: number
  /** Mezza larghezza della porta (la carreggiata). */
  readonly mezzaLarghezza: number
  /** Distanza dal traguardo. */
  readonly s: number
}

export type TracciatoGara = {
  readonly linea: readonly PuntoLinea[]
  readonly traiettoria: readonly { readonly x: number; readonly z: number }[]
  readonly checkpoint: readonly Checkpoint[]
  /** Lunghezza del giro lungo la mezzeria. */
  readonly lunghezza: number
}

/* ------------------------------------------------------------------------
 * Costruzione
 * --------------------------------------------------------------------- */

/** Linea, traiettoria e checkpoint di un circuito. */
export function tracciatoGara(
  grafo: GrafoStradale,
  circuito: Circuito,
  opzioni: OpzioniTracciato = OPZIONI_TRACCIATO,
): TracciatoGara {
  const linea = mezzeria(grafo, circuito, opzioni)
  const lunghezza = linea.at(-1)!.s + distanza(linea.at(-1)!, linea[0])
  return {
    linea,
    traiettoria: traiettoria(linea, opzioni),
    checkpoint: checkpoint(linea, lunghezza, opzioni),
    lunghezza,
  }
}

const distanza = (a: { x: number; z: number }, b: { x: number; z: number }) =>
  Math.hypot(a.x - b.x, a.z - b.z)

/**
 * La mezzeria del giro, un punto ogni `passo` unità circa, dal traguardo
 * fino a poco prima di tornarci (il giro è chiuso: il punto dopo l'ultimo è
 * il primo). Punti doppi (dove due pezzi si toccano) si saltano.
 */
function mezzeria(
  grafo: GrafoStradale,
  circuito: Circuito,
  o: OpzioniTracciato,
): PuntoLinea[] {
  const grezzi: { x: number; z: number; mezza: number }[] = []
  for (const p of circuito.pezzi) {
    const t = grafo.tratti.get(chiaveTratto(p.tessera, p.tratto))!
    const mezza = o.mezzaCarreggiata[t.classe]
    const n = Math.max(1, Math.ceil(Math.abs(p.a - p.da) / o.passo))
    for (let i = 0; i < n; i++) {
      const q = puntoSulTratto(t, p.da + ((p.a - p.da) * i) / n)
      const ultimo = grezzi.at(-1)
      if (!ultimo || distanza(ultimo, q) > o.passo / 4)
        grezzi.push({ x: q.x, z: q.z, mezza })
    }
  }

  // Distanze progressive e direzione (dal punto prima al punto dopo)
  const n = grezzi.length
  let s = 0
  return grezzi.map((p, i) => {
    if (i > 0) s += distanza(grezzi[i - 1], p)
    const prima = grezzi[(i - 1 + n) % n]
    const dopo = grezzi[(i + 1) % n]
    const l = distanza(prima, dopo) || 1
    return {
      x: p.x,
      z: p.z,
      s,
      tx: (dopo.x - prima.x) / l,
      tz: (dopo.z - prima.z) / l,
      mezzaLarghezza: p.mezza,
    }
  })
}

/**
 * La traiettoria ideale: ogni punto si sposta solo di lato (lungo la
 * normale alla strada) e a ogni passata va verso la media dei due vicini.
 * È come tendere un elastico lungo il giro: le curve si tagliano e i
 * rettilinei restano dritti. Lo spostamento resta entro la carreggiata
 * meno il margine.
 */
function traiettoria(
  linea: readonly PuntoLinea[],
  o: OpzioniTracciato,
): { x: number; z: number }[] {
  const n = linea.length
  // Normale a sinistra della direzione di marcia (visto dall'alto)
  const nx = linea.map((p) => p.tz)
  const nz = linea.map((p) => -p.tx)
  const limite = linea.map((p) => Math.max(0, p.mezzaLarghezza - o.margine))
  const lato = new Float64Array(n) // spostamento di ogni punto lungo la normale

  const pos = (i: number) => ({
    x: linea[i].x + nx[i] * lato[i],
    z: linea[i].z + nz[i] * lato[i],
  })

  for (let k = 0; k < o.passate; k++) {
    for (let i = 0; i < n; i++) {
      const a = pos((i - 1 + n) % n)
      const b = pos((i + 1) % n)
      // Il punto medio dei vicini, riportato sulla normale di questo punto
      const mx = (a.x + b.x) / 2 - linea[i].x
      const mz = (a.z + b.z) / 2 - linea[i].z
      const voluto = mx * nx[i] + mz * nz[i]
      lato[i] = Math.max(-limite[i], Math.min(limite[i], voluto))
    }
  }
  return linea.map((_, i) => pos(i))
}

/** I checkpoint: uno sul traguardo, poi uno circa ogni `distanzaCheckpoint`. */
function checkpoint(
  linea: readonly PuntoLinea[],
  lunghezza: number,
  o: OpzioniTracciato,
): Checkpoint[] {
  const quanti = Math.max(3, Math.round(lunghezza / o.distanzaCheckpoint))
  const out: Checkpoint[] = []
  let j = 0
  for (let k = 0; k < quanti; k++) {
    const s = (lunghezza * k) / quanti
    while (j + 1 < linea.length && linea[j + 1].s <= s) j++
    const p = linea[j]
    out.push({
      indice: k,
      x: p.x,
      z: p.z,
      tx: p.tx,
      tz: p.tz,
      mezzaLarghezza: p.mezzaLarghezza,
      s: p.s,
    })
  }
  return out
}

/* ------------------------------------------------------------------------
 * Funzioni per la gara
 * --------------------------------------------------------------------- */

/**
 * Vero se andando da `prima` a `dopo` un mezzo passa la porta nel verso di
 * marcia: prima era dietro la porta, dopo è davanti, e nel punto in cui
 * l'ha passata stava dentro la sua larghezza (più una tolleranza).
 */
export function attraversaCheckpoint(
  c: Checkpoint,
  prima: { x: number; z: number },
  dopo: { x: number; z: number },
  tolleranza = 10,
): boolean {
  // Distanza (con segno) dalla porta lungo la direzione di marcia
  const avanti = (p: { x: number; z: number }) =>
    (p.x - c.x) * c.tx + (p.z - c.z) * c.tz
  const a = avanti(prima)
  const b = avanti(dopo)
  if (!(a < 0 && b >= 0)) return false
  // Punto di passaggio e sua distanza laterale dal centro della porta
  const t = a / (a - b)
  const x = prima.x + (dopo.x - prima.x) * t
  const z = prima.z + (dopo.z - prima.z) * t
  const laterale = Math.abs((x - c.x) * -c.tz + (z - c.z) * c.tx)
  return laterale <= c.mezzaLarghezza + tolleranza
}

/**
 * A che punto del giro sta un mezzo in (x, z): la distanza dal traguardo
 * del punto della linea più vicino. Si cerca vicino a `sPrecedente` (entro
 * `finestra` unità avanti e indietro): così un incrocio dove il giro passa
 * due volte non confonde, e il calcolo è veloce.
 */
export function progressoSulGiro(
  tracciato: TracciatoGara,
  x: number,
  z: number,
  sPrecedente: number,
  finestra = 200,
): number {
  const { linea, lunghezza } = tracciato
  const passo = lunghezza / linea.length // passo medio tra due punti
  const centro = indiceDi(linea, sPrecedente)
  const quanti = Math.ceil(finestra / passo)
  let migliore = sPrecedente
  let minima = Infinity
  for (let k = -quanti; k <= quanti; k++) {
    const i = (((centro + k) % linea.length) + linea.length) % linea.length
    const d = Math.hypot(linea[i].x - x, linea[i].z - z)
    if (d < minima) {
      minima = d
      migliore = linea[i].s
    }
  }
  return migliore
}

/** L'indice del punto della linea con la s più vicina (ricerca binaria). */
function indiceDi(linea: readonly PuntoLinea[], s: number): number {
  let basso = 0
  let alto = linea.length - 1
  while (basso < alto) {
    const m = (basso + alto + 1) >> 1
    if (linea[m].s <= s) basso = m
    else alto = m - 1
  }
  return basso
}
