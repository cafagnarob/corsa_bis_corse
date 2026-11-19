/*
 * esagoni.ts
 * Geometria della griglia esagonale di Castelfiume, come nel GDD.
 *
 * - Tessere "a punta in alto", raggio 200 unità (= lato).
 * - Coordinate assiali (q, r): q cresce verso est, r verso sud-est.
 * - Lati numerati da 0 = est, poi in senso antiorario (1 NE, 2 NO, 3 O,
 *   4 SO, 5 SE). Il lato i di una tessera tocca il lato (i + 3) mod 6
 *   della vicina.
 * - Mondo: x = est, z = sud (in Three.js -Z è nord).
 *
 * Solo funzioni pure: stesso ingresso, stessa uscita, nessun effetto esterno.
 */

export const RAGGIO_TESSERA = 200
export const APOTEMA = (RAGGIO_TESSERA * Math.sqrt(3)) / 2 // centro → metà di un lato: 173,2

/** Posizione di una tessera sulla griglia. */
export type Hex = { readonly q: number; readonly r: number }

/** Numero di un lato: 0 = est, poi in senso antiorario. */
export type Lato = 0 | 1 | 2 | 3 | 4 | 5

export const LATI: readonly Lato[] = [0, 1, 2, 3, 4, 5]

/** Spostamento verso la vicina su ciascun lato (tabella del GDD). */
const DIREZIONI: Readonly<Record<Lato, Hex>> = {
  0: { q: 1, r: 0 }, // est
  1: { q: 1, r: -1 }, // nord-est
  2: { q: 0, r: -1 }, // nord-ovest
  3: { q: -1, r: 0 }, // ovest
  4: { q: -1, r: 1 }, // sud-ovest
  5: { q: 0, r: 1 }, // sud-est
}

/** Il lato della vicina che tocca il lato `lato` di questa tessera. */
export function latoOpposto(lato: Lato): Lato {
  return ((lato + 3) % 6) as Lato
}

/** La tessera confinante sul lato indicato. */
export function vicina(h: Hex, lato: Lato): Hex {
  const d = DIREZIONI[lato]
  return { q: h.q + d.q, r: h.r + d.r }
}

/** Le sei vicine, nell'ordine dei lati (0 = est, ...). */
export function vicine(h: Hex): Hex[] {
  return LATI.map((lato) => vicina(h, lato))
}

/** Numero di passi tra due tessere (0 = stessa tessera, 1 = vicine). */
export function distanza(a: Hex, b: Hex): number {
  const dq = a.q - b.q
  const dr = a.r - b.r
  return (Math.abs(dq) + Math.abs(dr) + Math.abs(dq + dr)) / 2
}

/** Centro della tessera nel mondo, in unità di gioco. */
export function centroTessera(h: Hex): { x: number; z: number } {
  return {
    x: RAGGIO_TESSERA * Math.sqrt(3) * (h.q + h.r / 2),
    z: RAGGIO_TESSERA * 1.5 * h.r, // 300 × r
  }
}

/** Chiave testuale unica, per usare una tessera come chiave di una Map. */
export function chiave(h: Hex): string {
  return `${h.q},${h.r}`
}

/**
 * Tutte le tessere entro `raggio` passi dal centro (centro compreso):
 * 1, 7, 19, 37, 61... tessere per raggio 0, 1, 2, 3, 4.
 */
export function areaEsagonale(centro: Hex, raggio: number): Hex[] {
  const area: Hex[] = []
  for (let q = -raggio; q <= raggio; q++) {
    // per ogni colonna q, i valori di r che restano entro la distanza
    const rMin = Math.max(-raggio, -q - raggio)
    const rMax = Math.min(raggio, -q + raggio)
    for (let r = rMin; r <= rMax; r++) {
      area.push({ q: centro.q + q, r: centro.r + r })
    }
  }
  return area
}
