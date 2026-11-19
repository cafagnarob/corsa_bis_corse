/*
 * datiQuartieri.ts
 * Dati della vista mappa dei quartieri, calcolati una volta dalla città di
 * datiCitta.ts: il nome di ogni quartiere con il punto in cui appendere
 * l'etichetta, e le geometrie di confini e aree.
 */

import { centroTessera, chiave, type Hex } from "@corsa-bis/engine"

import { CITTA } from "../citta/datiCitta"
import { quotaSuperiore } from "../tessere/misure"
import { geometrieQuartieri } from "./geometrieQuartieri"
import type { NomeDaMostrare } from "./NomiQuartieri"

// Strati di ogni tessera, per sapere a che altezza appendere i cartellini
const STRATI = new Map(CITTA.tessere.map((t) => [chiave(t.hex), t.strati]))

/** Baricentro di un quartiere, 140 unità sopra la sua tessera più alta. */
function puntoEtichetta(tessere: readonly Hex[]): [number, number, number] {
  const centri = tessere.map(centroTessera)
  const x = centri.reduce((s, p) => s + p.x, 0) / centri.length
  const z = centri.reduce((s, p) => s + p.z, 0) / centri.length
  const strati = Math.max(...tessere.map((h) => STRATI.get(chiave(h)) ?? 1))
  return [x, quotaSuperiore(strati) + 140, z]
}

/** Nome e posizione dell'etichetta di ogni quartiere. */
export const NOMI: NomeDaMostrare[] = CITTA.quartieri.map((q) => ({
  id: q.id,
  nome: q.nome,
  frazione: q.frazione,
  posizione: puntoEtichetta(q.tessere),
}))

/** Contorni e aree colorate dei quartieri. */
export const GEOMETRIE_QUARTIERI = geometrieQuartieri(CITTA)
