/*
 * datiCampoTessere.ts
 * I dati del campo di prova "tessere": una città generata dal seme, da cui
 * si prendono solo tre tessere in fila con una rampa (treTessere.ts), e
 * tutto quello che serve per disegnarle e per la fisica.
 *
 * Come datiCitta.ts sono costanti di modulo: si calcolano una volta, la
 * prima volta che il modulo viene importato. Non si importa datiCitta.ts
 * perché quello raggruppa per il disegno TUTTA la città; qui si raggruppano
 * solo le tre tessere, molto più in fretta.
 *
 * Il seme si legge dall'indirizzo (?seme=...), come per la città: ogni seme
 * dà una prova diversa, sempre la stessa per lo stesso seme.
 */

import {
  centroTessera,
  chiave,
  generaCitta,
  generaStradario,
  generaStrade,
  popolaCitta,
  type CittaPopolata,
} from "@corsa-bis/engine"

import { raggruppa } from "../citta/raggruppa"
import type { Partenza } from "./campi"
import { puntiRampa, quotaGuida, trimeshTessere } from "./collisioniTessere"
import { scegliTreTessere } from "./treTessere"

const SEME =
  new URLSearchParams(window.location.search).get("seme") ?? "castelfiume"

const CITTA = popolaCitta(generaCitta(SEME))
const RETE = generaStrade(CITTA)
const STRADARIO = generaStradario(CITTA, RETE)

const SCELTA = scegliTreTessere(CITTA, RETE)
if (!SCELTA)
  throw new Error(
    `Nessuna rampa adatta alla prova nella città "${SEME}": prova un altro seme`,
  )

const CHIAVI = new Set(SCELTA.tessere.map(chiave))

/** La città con solo le tre tessere: il resto (rete, stradario) resta intero. */
const CITTA_RIDOTTA: CittaPopolata = {
  ...CITTA,
  tessere: CITTA.tessere.filter((t) => CHIAVI.has(chiave(t.hex))),
}

/** Quanti strati ha una delle tre tessere. */
const stratiDi = (k: string) =>
  CITTA_RIDOTTA.tessere.find((t) => chiave(t.hex) === k)?.strati ?? 1

/** Tutto il disegno delle tre tessere (strade, edifici, piante…). */
export const GRUPPI_TESSERE = raggruppa(CITTA_RIDOTTA, RETE, STRADARIO)

/** Cima e fianchi delle tre tessere, per la fisica. */
export const TRIMESH_TESSERE = trimeshTessere(CITTA_RIDOTTA.tessere)

/** Un cuneo per ogni rampa dentro le tre tessere. */
export const CUNEI_RAMPE = RETE.rampe
  .filter((r) => CHIAVI.has(chiave(r.hex)))
  .map((r) => puntiRampa(r, stratiDi(chiave(r.hex))))

/** Partenza: sulla strada della prima tessera, guardando verso la rampa. */
export const PARTENZA_TESSERE: Partenza = {
  posizione: [
    SCELTA.puntoPartenza.x,
    quotaGuida(stratiDi(chiave(SCELTA.tessere[0]))) + 8,
    SCELTA.puntoPartenza.z,
  ],
  direzione: SCELTA.direzione,
}

/** Centro del campo (media dei tre centri, in pianta): ci si mette il tavolo. */
const CENTRI = SCELTA.tessere.map(centroTessera)
export const CENTRO_CAMPO = {
  x: CENTRI.reduce((s, c) => s + c.x, 0) / CENTRI.length,
  z: CENTRI.reduce((s, c) => s + c.z, 0) / CENTRI.length,
}
