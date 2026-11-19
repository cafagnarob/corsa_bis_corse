/*
 * citta.ts
 * Generatore organico della città di partenza (GDD: "La città cresce in modo
 * organico" e "Quartieri").
 *
 * 1. Centro storico: 3-5 tessere attorno a (0, 0).
 * 2. Da 5 a 8 quartieri di 7-15 tessere, uno alla volta:
 *    - di solito nascono sul bordo della città e ci restano attaccati;
 *    - a volte sono FRAZIONI: nascono a 3-5 passi dalla città e la raggiungono
 *      con una fila di tessere strada (niente isole).
 * 3. Ogni zona cresce tessera per tessera tra le libere ai suoi bordi, con
 *    pesi: compattezza (dalla terza tessera in poi ogni nuova tessera tocca
 *    almeno 2 tessere della zona), terreno piano, un po' di caso.
 *    Mai più di 2 strati di salto tra tessere vicine (regola delle rampe).
 *
 * Tutto dipende solo dal seme: stesso seme, stessa città.
 */

import { flusso } from "./casuale"
import { centroTessera, chiave, distanza, vicine, type Hex } from "./esagoni"
import { creaTerreno } from "./terreno"

export type TipoCima = "erba" | "asfalto" | "selciato"
export type Ruolo = "centro" | "quartiere" | "strada"

export type TesseraCitta = {
  readonly hex: Hex
  readonly strati: number // 1 = pianura
  readonly ruolo: Ruolo
  readonly quartiere: number | null // 0 = centro storico; null = tessera strada
}

export type Quartiere = {
  readonly id: number
  readonly frazione: boolean // staccata dalla città, collegata da strade
  readonly tessere: readonly Hex[]
}

export type Citta = {
  readonly seme: string
  readonly tessere: readonly TesseraCitta[]
  readonly quartieri: readonly Quartiere[]
}

/** Regole di generazione, valori del GDD (da bilanciare). */
export const REGOLE_CITTA = {
  tessereCentro: [3, 5],
  numeroQuartieri: [5, 8],
  tessereQuartiere: [7, 15],
  probabilitaFrazione: 0.3,
  distanzaFrazione: [3, 5],
  tentativi: 12, // quante volte riprovare un quartiere che non riesce a crescere
  stratiMax: 5,
  saltoMax: 2, // strati di differenza ammessi tra tessere vicine
} as const

const R = REGOLE_CITTA
const ORIGINE: Hex = { q: 0, r: 0 }
const RAGGIO_TERRENO = 2500 // le colline sono sparse in un cerchio di 2,5 km
const PESO_SALTO = [1, 0.5, 0.15] // 0, 1 o 2 strati di salto con la zona

export function generaCitta(seme: string): Citta {
  const rng = flusso(seme, "citta")
  const quota = creaTerreno(flusso(seme, "terreno"), RAGGIO_TERRENO, 6)

  // ---------- terreno: strati di una posizione qualsiasi (con cache) ----------
  const cacheStrati = new Map<string, number>()
  const strati = (h: Hex): number => {
    const k = chiave(h)
    let s = cacheStrati.get(k)
    if (s === undefined) {
      const { x, z } = centroTessera(h)
      s = Math.min(R.stratiMax, 1 + Math.round(quota(x, z)))
      cacheStrati.set(k, s)
    }
    return s
  }
  const salto = (a: Hex, b: Hex) => Math.abs(strati(a) - strati(b))

  // ---------- stato della città in costruzione ----------
  const occupate = new Map<string, TesseraCitta>()
  const quartieri: Quartiere[] = []
  const libera = (h: Hex) => !occupate.has(chiave(h))
  const occupa = (hex: Hex, ruolo: Ruolo, quartiere: number | null) =>
    occupate.set(chiave(hex), { hex, strati: strati(hex), ruolo, quartiere })

  /** Vero se `h` non supera il salto massimo con nessuna vicina già presa (città o `zona`). */
  const saltiOk = (h: Hex, zona?: Map<string, Hex>) =>
    vicine(h).every(
      (v) => (libera(v) && !zona?.has(chiave(v))) || salto(h, v) <= R.saltoMax,
    )

  /**
   * Fa crescere una zona da `inizio` fino a `dimensione` tessere.
   * Non occupa nulla: restituisce le tessere, e chi chiama decide se tenerle.
   */
  function cresci(inizio: Hex, dimensione: number): Hex[] {
    const zona = new Map<string, Hex>([[chiave(inizio), inizio]])

    while (zona.size < dimensione) {
      // candidati: tessere libere che toccano la zona
      const candidati = new Map<
        string,
        { hex: Hex; contatti: number; saltoMax: number }
      >()
      for (const h of zona.values()) {
        for (const v of vicine(h)) {
          const k = chiave(v)
          if (zona.has(k) || !libera(v) || !saltiOk(v, zona)) continue
          const c = candidati.get(k) ?? { hex: v, contatti: 0, saltoMax: 0 }
          c.contatti++
          c.saltoMax = Math.max(c.saltoMax, salto(v, h))
          candidati.set(k, c)
        }
      }

      // compattezza: dalla terza tessera in poi servono almeno 2 contatti
      const contattiMinimi = zona.size >= 2 ? 2 : 1
      const voci = [...candidati.values()]
        .filter((c) => c.contatti >= contattiMinimi && c.saltoMax <= R.saltoMax)
        .map((c) => ({
          valore: c.hex,
          peso: c.contatti ** 2 * PESO_SALTO[c.saltoMax],
        }))

      if (voci.length === 0) break // la zona è chiusa: si ferma qui
      const scelta = rng.scegliPesato(voci)
      zona.set(chiave(scelta), scelta)
    }
    return [...zona.values()]
  }

  /** Tessere libere attaccate alla città, raggiungibili senza salti troppo alti. */
  function bordoCitta(): Hex[] {
    const bordo = new Map<string, Hex>()
    for (const t of occupate.values()) {
      for (const v of vicine(t.hex)) {
        if (libera(v) && saltiOk(v)) bordo.set(chiave(v), v)
      }
    }
    return [...bordo.values()]
  }

  /**
   * Cerca il punto di partenza di una frazione a `passi` tessere dalla città,
   * con una ricerca in ampiezza sulle tessere libere: restituisce il punto e
   * la fila di tessere strada (passi - 1) che lo collega alla città.
   */
  function cercaFrazione(passi: number): { inizio: Hex; strada: Hex[] } | null {
    const padre = new Map<string, Hex | null>()
    let livello: Hex[] = []
    for (const t of occupate.values()) {
      padre.set(chiave(t.hex), null)
      livello.push(t.hex)
    }
    for (let d = 1; d <= passi; d++) {
      const prossimo: Hex[] = []
      for (const h of livello) {
        for (const v of vicine(h)) {
          const k = chiave(v)
          if (padre.has(k) || !libera(v) || !saltiOk(v)) continue
          padre.set(k, h)
          prossimo.push(v)
        }
      }
      livello = prossimo
    }
    if (livello.length === 0) return null

    // si preferiscono partenze in piano
    const inizio = rng.scegliPesato(
      livello.map((h) => ({ valore: h, peso: 1 / strati(h) })),
    )

    // si risale di padre in padre fino alla città: sono le tessere strada
    const strada: Hex[] = []
    let p = padre.get(chiave(inizio)) ?? null
    while (p && libera(p)) {
      strada.push(p)
      p = padre.get(chiave(p)) ?? null
    }
    return { inizio, strada }
  }

  // ---------- 1. centro storico ----------
  const centro = cresci(ORIGINE, rng.intero(...R.tessereCentro))
  centro.forEach((h) => occupa(h, "centro", 0))
  quartieri.push({ id: 0, frazione: false, tessere: centro })

  // ---------- 2. quartieri ----------
  const numero = rng.intero(...R.numeroQuartieri)
  for (let id = 1; id <= numero; id++) {
    const dimensione = rng.intero(...R.tessereQuartiere)
    const frazione = id > 2 && rng.probabilita(R.probabilitaFrazione) // i primi due sempre attaccati

    for (let tentativo = 0; tentativo < R.tentativi; tentativo++) {
      let inizio: Hex
      let strada: Hex[] = []

      if (frazione) {
        const trovata = cercaFrazione(rng.intero(...R.distanzaFrazione))
        if (!trovata) continue
        inizio = trovata.inizio
        strada = trovata.strada
        strada.forEach((h) => occupa(h, "strada", null)) // prima la strada, così la frazione non ci cresce sopra
      } else {
        const bordo = bordoCitta()
        if (bordo.length === 0) break
        // si preferiscono tessere lontane dal centro (lobi) e in piano
        inizio = rng.scegliPesato(
          bordo.map((h) => ({
            valore: h,
            peso: (1 + distanza(h, ORIGINE)) / strati(h),
          })),
        )
      }

      const zona = cresci(inizio, dimensione)
      if (zona.length >= R.tessereQuartiere[0]) {
        zona.forEach((h) => occupa(h, "quartiere", id))
        quartieri.push({ id, frazione, tessere: zona })
        break
      }
      strada.forEach((h) => occupate.delete(chiave(h))) // tentativo fallito: si toglie la strada
    }
  }

  return { seme, tessere: [...occupate.values()], quartieri }
}
