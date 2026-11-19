/*
 * datiCitta.ts
 * Genera Castelfiume una volta sola, dal seme letto nell'indirizzo
 * (?seme=...), e la mette a disposizione di tutti i moduli che ne hanno
 * bisogno: la scena che la disegna oggi, la fisica e le piste domani.
 *
 * Come funziona: sono costanti di modulo. Il codice qui sotto gira la prima
 * volta che un file importa questo modulo, e il risultato resta in memoria;
 * gli import successivi ricevono gli stessi oggetti, senza ricalcolarli.
 * Stesso seme, stessa città.
 *
 * L'ordine conta: ogni passo usa il risultato del precedente.
 */

import {
  generaCitta,
  generaStradario,
  generaStrade,
  popolaCitta,
} from "@corsa-bis/engine"

import { raggruppa } from "./raggruppa"

/** Il seme della partita: dall'indirizzo, oppure "castelfiume". */
export const SEME =
  new URLSearchParams(window.location.search).get("seme") ?? "castelfiume"

/** Forma della città, quartieri, tipi e nomi delle tessere. */
export const CITTA = popolaCitta(generaCitta(SEME))

/** Rete stradale gerarchica: arterie, urbane, strette, rotonde e rampe. */
export const RETE = generaStrade(CITTA)

/** Le vie con i loro nomi. */
export const STRADARIO = generaStradario(CITTA, RETE)

/** Tutto quello che si disegna, raggruppato in InstancedMesh per tipo. */
export const GRUPPI = raggruppa(CITTA, RETE, STRADARIO)
