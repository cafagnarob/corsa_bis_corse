/*
 * misure.ts
 * Misure delle tessere in unità di gioco (1 unità = 1 m), come nel GDD
 * ("Tessere esagonali in Blender"). È l'unico punto in cui stanno:
 * geometrie, posizioni e, più avanti, il motore leggono da qui.
 *
 * Una tessera è una pila: N strati di cartone ondulato e, sopra, una cima
 * sottile (erba, asfalto o selciato). Tra un pezzo e l'altro c'è uno stacco
 * invisibile di 0,2 che evita lo sfarfallio delle facce coincidenti.
 * Con un solo strato la faccia superiore della cima è a quota 0.
 */

// Il raggio è una regola del gioco, non della grafica: lo definisce il motore
export { RAGGIO_TESSERA } from "@corsa-bis/engine"
export const SPESSORE_STRATO = 12
export const SPESSORE_CIMA = 2
export const STACCO = 0.2
export const PASSO_STRATO = SPESSORE_STRATO + STACCO // 12,2: di quanto sale ogni strato

// Faccia inferiore del primo strato: -14,2 (12 + 0,2 + 2 sotto lo zero)
const BASE_PILA = -(SPESSORE_STRATO + STACCO + SPESSORE_CIMA)

/** Quota della faccia inferiore dello strato k (1 = il più basso). */
export function quotaStrato(k: number): number {
  return BASE_PILA + PASSO_STRATO * (k - 1)
}

/** Quota della faccia inferiore della cima, posata sopra n strati. */
export function quotaCima(n: number): number {
  return BASE_PILA + PASSO_STRATO * n
}

/** Quota della faccia superiore della tessera: dove poggiano strade ed edifici. */
export function quotaSuperiore(n: number): number {
  return quotaCima(n) + SPESSORE_CIMA
}
