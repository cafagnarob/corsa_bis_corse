/*
 * colori.ts
 * I colori degli edifici, copiati da kit_edifici.json ("costanti"): intonaci
 * di ogni famiglia, stucco, cemento chiaro. Valori lineari 0-1 come in
 * Blender; se in Blender cambiano, vanno cambiati anche qui.
 */

import type { Rgb } from "./progetto"

export const INTONACI_BORGO: Record<string, Rgb> = {
  ocra: [0.74, 0.45, 0.14],
  terracotta: [0.66, 0.26, 0.13],
  siena: [0.82, 0.58, 0.2],
  rosa: [0.8, 0.45, 0.38],
  crema: [0.86, 0.74, 0.52],
}

export const INTONACI_PALAZZONI: Record<string, Rgb> = {
  cemento: [0.6, 0.58, 0.54],
  beige: [0.74, 0.66, 0.53],
  giallino: [0.78, 0.7, 0.47],
  verdino: [0.56, 0.6, 0.52],
  mattone: [0.58, 0.32, 0.23],
  azzurrino: [0.58, 0.64, 0.68],
}

export const STUCCO: Rgb = [0.92, 0.88, 0.78]
export const CEMENTO_CHIARO: Rgb = [0.78, 0.76, 0.71]
/** Kraft nudo (sopraelevazioni, coperture): non è nel JSON, è il colore medio della texture del kraft. */
export const KRAFT: Rgb = [0.62, 0.47, 0.3]

/** Villette: colori vivaci (INTONACI_VILLE in cb_edifici.py); cornicione e a volte il muretto bianchi. */
export const INTONACI_VILLE: Record<string, Rgb> = {
  giallo: [0.92, 0.74, 0.3],
  arancio: [0.9, 0.52, 0.28],
  rosa: [0.9, 0.58, 0.58],
  azzurro: [0.5, 0.7, 0.84],
  menta: [0.58, 0.8, 0.66],
  lilla: [0.72, 0.62, 0.82],
  bianco: [0.92, 0.9, 0.86],
}
export const BIANCO: Rgb = [0.92, 0.9, 0.86]

/** Capannoni: lamiere (INTONACI_CAPANNONI), più il kraft nudo due volte su sei. */
export const INTONACI_CAPANNONI: Record<string, Rgb> = {
  lamiera: [0.56, 0.58, 0.59],
  lamiera_scura: [0.4, 0.42, 0.44],
  verde_ind: [0.38, 0.49, 0.41],
  azzurro_ind: [0.46, 0.56, 0.63],
}
/** La palazzina degli uffici davanti al capannone (UFFICI). */
export const UFFICI: Record<string, Rgb> = {
  uff_bianco: [0.86, 0.85, 0.81],
  uff_grigio: [0.7, 0.7, 0.68],
}

/** Grattacieli: grigi e azzurri (INTONACI_GRATTACIELI), una scatola di un colore diverso dall'altra. */
export const INTONACI_GRATTACIELI: Record<string, Rgb> = {
  grigio_gr: [0.66, 0.68, 0.7],
  grigio_scuro_gr: [0.42, 0.45, 0.49],
  azzurro_gr: [0.55, 0.68, 0.8],
  blu_gr: [0.3, 0.42, 0.58],
  argento_gr: [0.8, 0.81, 0.82],
  petrolio_gr: [0.26, 0.44, 0.48],
}

/** Palazzi a corte: intonaci ottocenteschi (INTONACI_CORTE); cornici, marcapiani e cornicioni color stucco. */
export const INTONACI_CORTE: Record<string, Rgb> = {
  rosa_antico: [0.8, 0.55, 0.48],
  salvia: [0.58, 0.64, 0.48],
  polvere: [0.56, 0.64, 0.7],
  paglia: [0.86, 0.72, 0.44],
  perla: [0.78, 0.76, 0.7],
}
