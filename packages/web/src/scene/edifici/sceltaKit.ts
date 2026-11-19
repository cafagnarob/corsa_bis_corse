/*
 * sceltaKit.ts
 * Quali edifici montare col kit attorno a chi cammina (GDD, "Vincoli di
 * peso"), e con quanto dettaglio:
 * - si guardano quelli entro RAGGIO dal punto, dal più vicino al più
 *   lontano;
 * - quelli entro DETTAGLIO sono VICINI: si montano interi. Gli altri si
 *   montano senza i bordi di cartone (le facce del taglio, EDI_Bordo), che
 *   sono circa metà dei triangoli del kit e a qualche metro non si vedono;
 * - si va avanti finché i pezzi non superano il TETTO di triangoli; uno
 *   troppo pesante viene saltato e non ferma i più leggeri dietro di lui.
 * Il resto della scena (tessere, strade, alberi, gusci) pesa già circa 400
 * mila triangoli a piedi: il tetto del kit tiene il totale sotto i 550 mila.
 * Funzione pura: le servono solo i centri degli edifici e quanto pesano.
 */

/** Distanza massima dal pedone (unità di gioco, 5,2 = 1 m). */
export const RAGGIO = 300
/** Entro questa distanza l'edificio si monta intero, bordi compresi (circa 25 m). */
export const DETTAGLIO = 130
/** Triangoli in tutto per gli edifici montati. */
export const TETTO = 130_000

/** Un edificio scelto, e se è abbastanza vicino da montarlo intero. */
export type Scelto = { readonly i: number; readonly vicino: boolean }

/**
 * Gli edifici da montare, dal più vicino. `centri` = x, z di ogni edificio uno dopo l'altro;
 * `peso(i, vicino)` = triangoli dell'edificio i montato intero (vicino) o senza bordi.
 */
export function scegliEdifici(
  centri: Float32Array,
  x: number,
  z: number,
  peso: (i: number, vicino: boolean) => number,
  { raggio = RAGGIO, dettaglio = DETTAGLIO, tetto = TETTO } = {},
): Scelto[] {
  const candidati: { i: number; d: number }[] = []
  for (let i = 0; i < centri.length / 2; i++) {
    const d = Math.hypot(centri[2 * i] - x, centri[2 * i + 1] - z)
    if (d <= raggio) candidati.push({ i, d })
  }
  candidati.sort((a, b) => a.d - b.d)
  const scelti: Scelto[] = []
  let triangoli = 0
  for (const { i, d } of candidati) {
    const vicino = d <= dettaglio
    const p = peso(i, vicino)
    if (triangoli + p > tetto) continue
    triangoli += p
    scelti.push({ i, vicino })
  }
  return scelti
}

/** Stessa scelta (in qualsiasi ordine, con lo stesso dettaglio)? Per non rimontare quando non cambia niente. */
export function stessaScelta(
  a: readonly Scelto[],
  b: readonly Scelto[],
): boolean {
  if (a.length !== b.length) return false
  const s = new Map(a.map((x) => [x.i, x.vicino]))
  return b.every((x) => s.get(x.i) === x.vicino)
}
