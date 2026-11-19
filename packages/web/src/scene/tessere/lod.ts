/*
 * lod.ts
 * Scelta del livello di dettaglio delle tessere (GDD: "LOD delle tessere"):
 * LOD0 per la tessera che la telecamera guarda e le sei vicine, LOD1 per
 * tutte le altre.
 *
 * - tesseraSotto: la tessera che contiene un punto del tavolo (x, z),
 *   l'inverso di centroTessera (coordinate assiali arrotondate con il
 *   metodo delle coordinate cubiche);
 * - dividiPerLod: separa le matrici delle istanze in vicine e lontane in
 *   base alla distanza del loro centro dal centro della tessera guardata;
 * - dividiPerTessera: lo stesso per i pezzi che non stanno al centro della
 *   loro tessera (le rampe, sul lato): decide la tessera che li contiene.
 */

import {
  centroTessera,
  distanza,
  RAGGIO_TESSERA,
  type Hex,
} from "@corsa-bis/engine"
import type { Matrix4 } from "three"

/** La tessera che contiene il punto (x, z). */
export function tesseraSotto(x: number, z: number): Hex {
  const r = z / (1.5 * RAGGIO_TESSERA)
  const q = x / (Math.sqrt(3) * RAGGIO_TESSERA) - r / 2
  // arrotondamento in coordinate cubiche (q + r + s = 0): si corregge la
  // coordinata che si è spostata di più
  const s = -q - r
  let rq = Math.round(q)
  let rr = Math.round(r)
  const rs = Math.round(s)
  const dq = Math.abs(rq - q)
  const dr = Math.abs(rr - r)
  const ds = Math.abs(rs - s)
  if (dq > dr && dq > ds) rq = -rr - rs
  else if (dr > ds) rr = -rq - rs
  return { q: rq + 0, r: rr + 0 } // + 0 toglie il -0
}

/** Distanza tra i centri di due tessere vicine. */
const PASSO = Math.sqrt(3) * RAGGIO_TESSERA
/** Entro questa distanza dal centro guardato una tessera è "vicina" (lei e le sei attorno). */
const SOGLIA_VICINE = PASSO * 1.1

/** Separa le matrici in [vicine, lontane] rispetto al centro della tessera guardata. */
export function dividiPerLod(
  matrici: readonly Matrix4[],
  guardata: Hex,
): [Matrix4[], Matrix4[]] {
  const c = centroTessera(guardata)
  const vicine: Matrix4[] = []
  const lontane: Matrix4[] = []
  for (const m of matrici) {
    const e = m.elements // posizione in e[12] (x) ed e[14] (z)
    ;(Math.hypot(e[12] - c.x, e[14] - c.z) < SOGLIA_VICINE
      ? vicine
      : lontane
    ).push(m)
  }
  return [vicine, lontane]
}

/** Separa le voci in [vicine, lontane] secondo la loro tessera (vicina = la guardata o una delle sei attorno). */
export function dividiPerTessera(
  voci: readonly { readonly hex: Hex; readonly matrice: Matrix4 }[],
  guardata: Hex,
): [Matrix4[], Matrix4[]] {
  const vicine: Matrix4[] = []
  const lontane: Matrix4[] = []
  for (const v of voci)
    (distanza(v.hex, guardata) <= 1 ? vicine : lontane).push(v.matrice)
  return [vicine, lontane]
}
