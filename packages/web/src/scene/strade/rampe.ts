/*
 * rampe.ts
 * Le rampe tra tessere di quota diversa in scena (GDD: "Rampe" e "Rampe nel
 * codice", 18 novembre). Dove stanno lo decide il motore (rete.rampe): su
 * ogni lato con strada tra due tessere che differiscono di 1 o 2 strati,
 * dentro la tessera bassa. La rampa parte dal punto medio del lato (il
 * connettore) alla quota della tessera alta e scende dritta verso il centro
 * della tessera bassa per 5 × dislivello: 61 unità per 1 strato, 122 per 2.
 * Lì la strada del motore è un rettilineo (rete.rettilinei), così strada,
 * rampa e percorso dei mezzi combaciano.
 *
 * Nel .glb il pezzo Rampa_<classe>_<salto> ha l'origine sul connettore, alla
 * quota della tessera bassa, e scende verso −X: in scena si mette sul
 * connettore della tessera bassa, ruotato di lato × 60°.
 *
 * quotaRampa dà quanto la rampa alza un punto della tessera bassa: serve a
 * mezzi, spago e pin per salire lungo la rampa invece di saltare al lato.
 */

import {
  centroTessera,
  chiave,
  LUNGHEZZA_RAMPA_PER_STRATO,
  puntoLato,
  type ClasseStrada,
  type Rampa,
} from "@corsa-bis/engine"
import { PASSO_STRATO } from "../tessere/misure"
import { PROFILO } from "./profili"

export type { Rampa }

/** Lunghezza di una rampa: 61 per 1 strato, 122 per 2 (la stessa del motore). */
export const lunghezzaRampa = (salto: number) =>
  LUNGHEZZA_RAMPA_PER_STRATO * salto

/** Mezza larghezza della rampa: carreggiata più un marciapiede (viale 50, urbana 27,5, stretta 15). */
export const mezzaLarghezzaRampa = (classe: ClasseStrada) =>
  PROFILO[classe].carreggiata / 2 + PROFILO[classe].marciapiede

/** Nome del pezzo nel .glb: Rampa_urbana_1, Rampa_viale_2, ... */
export const pezzoRampa = (r: Rampa) => `Rampa_${r.classe}_${r.salto}`

/** Le rampe raggruppate per tessera (chiave "q,r"). */
export function rampePerTessera(rampe: readonly Rampa[]): Map<string, Rampa[]> {
  const per = new Map<string, Rampa[]>()
  for (const r of rampe)
    per.set(chiave(r.hex), [...(per.get(chiave(r.hex)) ?? []), r])
  return per
}

/**
 * Di quanto le rampe della tessera alzano il punto (x, z) del mondo: sul
 * connettore tutto il dislivello, in fondo alla rampa niente. Fuori
 * dall'impronta della rampa (lunghezza × larghezza) 0.
 */
export function quotaRampa(
  rampe: readonly Rampa[] | undefined,
  x: number,
  z: number,
): number {
  if (!rampe) return 0
  let su = 0
  for (const r of rampe) {
    const c = centroTessera(r.hex)
    const a = (r.lato * Math.PI) / 3
    // direzione verso il lato (fuori dalla tessera) e lungo il lato
    const fx = Math.cos(a)
    const fz = -Math.sin(a)
    const px = x - c.x
    const pz = z - c.z
    const lato = puntoLato(r.lato)
    const dalLato = (lato.x - px) * fx + (lato.z - pz) * fz // quanto manca al lato, verso l'interno
    const traverso = Math.abs(px * -fz + pz * fx - (lato.x * -fz + lato.z * fx))
    const L = lunghezzaRampa(r.salto)
    if (dalLato > L || traverso > mezzaLarghezzaRampa(r.classe)) continue
    su = Math.max(su, r.salto * PASSO_STRATO * (1 - Math.max(0, dalLato) / L))
  }
  return su
}
