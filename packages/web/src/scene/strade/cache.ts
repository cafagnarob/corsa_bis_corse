/*
 * cache.ts
 * Tracciati e geometrie delle strade, calcolati una volta sola per ogni
 * combinazione di connettori e riusati da tutte le tessere uguali.
 * In una città ci sono decine di combinazioni diverse, non centinaia.
 *
 * Le rampe cambiano sia il tracciato (la strada parte dal lato con un
 * rettilineo lungo quanto la rampa) sia la geometria (la strada disegnata si
 * ferma dove comincia la rampa): i rettilinei per lato (rete.rettilinei)
 * fanno parte della chiave.
 */

import {
  SENZA_RETTILINEI,
  tracciatoTessera,
  type Connettore,
  type TipoRotonda,
  type TracciatoTessera,
} from "@corsa-bis/engine"
import { costruisciStrade, type GeometrieStrade } from "./costruisciStrade"

const tracciati = new Map<string, TracciatoTessera>()
const geometrie = new Map<string, GeometrieStrade>()

const chiaveDi = (
  connettori: readonly Connettore[],
  rotonda: TipoRotonda | null,
  rettilinei: readonly number[],
) => `${connettori.join()}|${rotonda ?? ""}|${rettilinei.join()}`

export function tracciatoDi(
  connettori: readonly Connettore[],
  rotonda: TipoRotonda | null = null,
  rettilinei: readonly number[] = SENZA_RETTILINEI,
): TracciatoTessera {
  const k = chiaveDi(connettori, rotonda, rettilinei)
  let t = tracciati.get(k)
  if (!t) {
    t = tracciatoTessera(connettori, rotonda, rettilinei)
    tracciati.set(k, t)
  }
  return t
}

export function geometrieDi(
  connettori: readonly Connettore[],
  rotonda: TipoRotonda | null = null,
  rettilinei: readonly number[] = SENZA_RETTILINEI,
): GeometrieStrade {
  const k = chiaveDi(connettori, rotonda, rettilinei)
  let g = geometrie.get(k)
  if (!g) {
    // la strada disegnata si ferma dove comincia la rampa: si taglia il rettilineo
    g = costruisciStrade(
      tracciatoDi(connettori, rotonda, rettilinei),
      rettilinei,
    )
    geometrie.set(k, g)
  }
  return g
}
