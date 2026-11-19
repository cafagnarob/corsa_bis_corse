/*
 * popola.ts
 * Dà un'identità alla città generata da citta.ts (GDD: "Quartieri" e "Nomi").
 *
 * - Ogni quartiere riceve un CARATTERE (popolare, villette, misto, industriale,
 *   nuovo) che decide le probabilità dei tipi di tessera al suo interno.
 *   Le tessere interne e quelle di bordo hanno pesi diversi: dentro più densità
 *   e servizi, ai bordi case più basse e verde.
 * - Ogni quartiere riceve un NOME secondo la tabella del GDD (Porta..., Borgo...,
 *   Villaggio..., Colle..., Zona Industriale..., nomi commerciali).
 *
 * Usa un flusso casuale suo ('quartieri'): cambiare queste regole non cambia
 * la forma della città, che dipende solo dal flusso 'citta'.
 */

import { flusso, type Casuale } from "./casuale"
import type { Citta, Quartiere, TesseraCitta } from "./citta"
import { centroTessera, chiave, distanza, vicine, type Hex } from "./esagoni"

export type TipoTessera =
  | "centro_storico"
  | "popolare" // residenziale anni '60-'70, palazzoni
  | "villette"
  | "nuove_costruzioni"
  | "uffici_commercio"
  | "industriale"
  | "parco"
  | "strada"

export type Carattere =
  | "centro"
  | "popolare"
  | "villette"
  | "misto"
  | "industriale"
  | "nuovo"

export type TesseraTipizzata = TesseraCitta & { readonly tipo: TipoTessera }
export type QuartiereConNome = Quartiere & {
  readonly carattere: Carattere
  readonly nome: string
}

export type CittaPopolata = {
  readonly seme: string
  readonly tessere: readonly TesseraTipizzata[]
  readonly quartieri: readonly QuartiereConNome[]
}

type Pesi = Partial<Record<TipoTessera, number>>

/** Pesi dei tipi di tessera per carattere: tessere interne e tessere di bordo. */
export const TIPI_PER_CARATTERE: Record<
  Exclude<Carattere, "centro">,
  { interno: Pesi; bordo: Pesi }
> = {
  popolare: {
    interno: { popolare: 6, uffici_commercio: 2, parco: 1 },
    bordo: { popolare: 4, villette: 2, parco: 2 },
  },
  villette: {
    interno: { villette: 6, uffici_commercio: 1, parco: 1 },
    bordo: { villette: 5, parco: 3 },
  },
  misto: {
    interno: { uffici_commercio: 4, popolare: 3, nuove_costruzioni: 1 },
    bordo: { popolare: 3, villette: 2, parco: 1 },
  },
  industriale: {
    interno: { industriale: 7, uffici_commercio: 1 },
    bordo: { industriale: 4, parco: 1 },
  },
  nuovo: {
    interno: { nuove_costruzioni: 5, uffici_commercio: 2, parco: 1 },
    bordo: { nuove_costruzioni: 4, villette: 2, parco: 2 },
  },
}

// ---------- nomi (GDD: tabella "Nomi") ----------

const NOMI = {
  porta: [
    "Porta Sole",
    "Porta Ferrata",
    "Porta Nuova",
    "Porta Leone",
    "Porta San Felice",
    "Porta Marina",
  ],
  borgo: [
    "Borgo Vecchio",
    "Borgo Fiorito",
    "Borgo dei Mulini",
    "San Vito",
    "Santa Lucia",
    "San Rocco",
    "Sant'Anna",
    "San Biagio",
    "Santa Chiara",
    "Borgo Antico",
  ],
  villaggio: [
    "Villaggio Aurora",
    "Quartiere Pini",
    "Villaggio Primavera",
    "Quartiere Olimpia",
    "Villaggio del Sole",
    "Quartiere Gioia",
  ],
  colle: [
    "Poggio Alto",
    "Colle dei Mandorli",
    "Monte Verde",
    "Poggio degli Ulivi",
    "Colle Bello",
    "Monte Fiorito",
  ],
  commerciale: [
    "Le Terrazze",
    "Parco dei Tigli",
    "Le Magnolie",
    "Residenza Belvedere",
    "I Giardini",
    "Corte dei Gelsi",
  ],
}

/** Distributore di nomi senza ripetizioni: ogni lista è mescolata una volta. */
function creaNomi(rng: Casuale) {
  const mazzi = Object.fromEntries(
    Object.entries(NOMI).map(([k, lista]) => [k, rng.mescola(lista)]),
  ) as Record<keyof typeof NOMI, string[]>
  const usati = new Set<string>()
  return {
    pesca(lista: keyof typeof NOMI): string {
      const nome = mazzi[lista].pop() ?? `${NOMI[lista][0]} ${usati.size + 1}` // lista finita: numero
      usati.add(nome)
      return nome
    },
    /** Il primo nome della lista non ancora usato; se lo sono tutti, il primo con un numero. */
    primoLibero(...proposte: string[]): string {
      let nome = proposte.find((p) => !usati.has(p))
      for (let n = 2; nome === undefined; n++) {
        if (!usati.has(`${proposte[0]} ${n}`)) nome = `${proposte[0]} ${n}`
      }
      usati.add(nome)
      return nome
    },
  }
}

/** Punto cardinale del baricentro di un gruppo di tessere, visto dal centro città. */
function direzione(tessere: readonly Hex[]): string {
  const c = tessere.map(centroTessera)
  const x = c.reduce((s, p) => s + p.x, 0) / c.length
  const z = c.reduce((s, p) => s + p.z, 0) / c.length
  const gradi = ((Math.atan2(-z, x) * 180) / Math.PI + 360) % 360 // 0 = est, 90 = nord
  if (gradi >= 45 && gradi < 135) return "Nord"
  if (gradi >= 135 && gradi < 225) return "Ovest"
  if (gradi >= 225 && gradi < 315) return "Sud"
  return "Est"
}

// ---------- popolamento ----------

const ORIGINE: Hex = { q: 0, r: 0 }
export const MAX_INDUSTRIALI = 2 // zone industriali per città

export function popolaCitta(citta: Citta): CittaPopolata {
  const rng = flusso(citta.seme, "quartieri")
  const nomi = creaNomi(rng)
  const perChiave = new Map(citta.tessere.map((t) => [chiave(t.hex), t]))
  const idCentro = new Set(citta.quartieri[0]?.tessere.map(chiave))

  const tipi = new Map<string, TipoTessera>()
  const quartieri: QuartiereConNome[] = []
  const usati = new Map<Carattere, number>() // quanti quartieri per carattere, finora

  for (const q of citta.quartieri) {
    // --- carattere ---
    let carattere: Carattere
    if (q.id === 0) {
      carattere = "centro"
    } else {
      const d = Math.min(...q.tessere.map((h) => distanza(h, ORIGINE)))
      const base: [Carattere, number][] = [
        ["misto", d <= 3 ? 3 : 1],
        ["popolare", 3],
        ["villette", 1 + d * 0.3],
        ["industriale", d >= 3 || q.frazione ? 2 : 0.3], // lontano dalle case
        ["nuovo", 1.5],
      ]
      carattere = rng.scegliPesato(
        base.map(([c, peso]) => {
          const n = usati.get(c) ?? 0
          // varietà: ogni quartiere già uguale dimezza il peso; zone industriali al massimo 2
          const limite = c === "industriale" && n >= MAX_INDUSTRIALI ? 0 : 1
          return { valore: c, peso: peso * 0.5 ** n * limite }
        }),
      )
      usati.set(carattere, (usati.get(carattere) ?? 0) + 1)
    }

    // --- tipi delle tessere ---
    const proprie = new Set(q.tessere.map(chiave))
    for (const h of q.tessere) {
      if (carattere === "centro") {
        tipi.set(chiave(h), "centro_storico")
        continue
      }
      const diBordo = vicine(h).some((v) => !proprie.has(chiave(v)))
      const pesi = TIPI_PER_CARATTERE[carattere][diBordo ? "bordo" : "interno"]
      const voci = Object.entries(pesi).map(([tipo, peso]) => ({
        valore: tipo as TipoTessera,
        peso,
      }))
      tipi.set(chiave(h), rng.scegliPesato(voci))
    }

    // --- nome (la prima regola che vale, nell'ordine) ---
    const stratiMedi =
      q.tessere.reduce(
        (s, h) => s + (perChiave.get(chiave(h))?.strati ?? 1),
        0,
      ) / q.tessere.length
    const toccaCentro = q.tessere.some((h) =>
      vicine(h).some((v) => idCentro.has(chiave(v))),
    )
    let nome: string
    if (carattere === "centro") nome = "Centro Storico"
    else if (carattere === "industriale") {
      const dir = direzione(q.tessere)
      nome = nomi.primoLibero(
        `Zona Industriale ${dir}`,
        `Zona Artigianale ${dir}`,
      )
    } else if (carattere === "nuovo") nome = nomi.pesca("commerciale")
    else if (stratiMedi >= 3) nome = nomi.pesca("colle")
    else if (toccaCentro) nome = nomi.pesca("porta")
    else if (carattere === "popolare") nome = nomi.pesca("villaggio")
    else nome = nomi.pesca("borgo")

    quartieri.push({ ...q, carattere, nome })
  }

  const tessere = citta.tessere.map((t) => ({
    ...t,
    tipo:
      t.ruolo === "strada"
        ? ("strada" as const)
        : (tipi.get(chiave(t.hex)) ?? "parco"),
  }))

  return { seme: citta.seme, tessere, quartieri }
}
