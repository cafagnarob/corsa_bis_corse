/*
 * terreno.ts
 * Funzione di quota del tabellone, generata dal seed (GDD: "Terreno: il
 * plastico a strati").
 *
 * Versione iniziale: somma di colline a campana (gaussiane) larghe 500-900
 * unità e alte 1-3 strati. Il risultato è morbido: tessere vicine
 * differiscono al massimo di 1-2 strati.
 * Più avanti: valle del fiume, poli in piano, colline ai margini.
 */

import type { Casuale } from "./casuale"

type Collina = { x: number; z: number; altezza: number; ampiezza: number }

/** Quota in strati (decimale, 0 = pianura) in un punto del mondo. */
export type FunzioneQuota = (x: number, z: number) => number

/**
 * Crea il terreno: `numero` colline sparse entro `raggioMondo` dal centro.
 * Usa il generatore ricevuto, quindi stesso seme = stesse colline.
 */
export function creaTerreno(
  rng: Casuale,
  raggioMondo: number,
  numero = 4,
): FunzioneQuota {
  const colline: Collina[] = Array.from({ length: numero }, () => ({
    x: (rng.decimale() * 2 - 1) * raggioMondo,
    z: (rng.decimale() * 2 - 1) * raggioMondo,
    altezza: 1 + rng.decimale() * 2, // 1-3 strati
    ampiezza: 500 + rng.decimale() * 400, // 500-900 unità
  }))

  return (x, z) =>
    colline.reduce((quota, c) => {
      const d2 = (x - c.x) ** 2 + (z - c.z) ** 2
      return quota + c.altezza * Math.exp(-d2 / (2 * c.ampiezza ** 2))
    }, 0)
}
