/*
 * isole.ts — SEGNAPOSTO
 * Le parti dell'isola al centro di una rotonda, decorata secondo il quartiere:
 * - zone industriali e provinciali: cemento, semplice;
 * - quartieri residenziali e parchi: aiuola verde (alberi e cespugli veri:
 *   pianteIsola in vegetazione/piante.ts);
 * - uffici e commercio: piazzetta lastricata con fontana.
 *
 * Ogni parte è un cilindro (raggio e altezza) in coordinate della tessera,
 * con la base sulla faccia superiore: sono dati, che il disegno della città
 * raggruppa per materiale (instancing).
 *
 * MONUMENTI (GDD: "Monumenti al centro delle rotonde" e "Monumenti
 * esportati", 18 novembre). Al centro dell'isola, sopra l'aiuola:
 * - rotonde compatte nei quartieri residenziali e nei parchi: una delle
 *   quattro statue (oratore, pensatore, fiaccola, poeta), scelta dalla
 *   posizione della tessera così ogni città è sempre uguale; scala 5,2;
 * - rotonde ampie (arterie), se non sono industriali: la statua equestre,
 *   scala 6,5 (5,2 × 1,25);
 * - zone industriali e provinciali: niente (isola di cemento);
 * - uffici e commercio: resta la piazzetta con la fontana.
 * Il monumento guarda il viale principale della rotonda (il lato con la
 * strada più importante). Le piante dell'isola stanno tra il basamento (o la
 * fontana) e il cordolo.
 */

import {
  LATI,
  puntoLato,
  type Connettore,
  type Hex,
  type Lato,
  type Rotonda,
  type TipoTessera,
} from "@corsa-bis/engine"
import { QUOTE, SEGNI } from "./profili"

export type MaterialeIsola = "cemento" | "verde" | "piazza" | "pietra" | "acqua"

/** Colori dei materiali delle isole. */
export const COLORI_ISOLA: Record<MaterialeIsola, string> = {
  cemento: "#9d9a93",
  verde: "#6a8f50",
  piazza: "#c9a46a",
  pietra: "#d8d2c4",
  acqua: "#6f9fb8",
}

export type Decorazione = "cemento" | "verde" | "piazza"

const DECORAZIONE: Record<TipoTessera, Decorazione> = {
  industriale: "cemento",
  strada: "cemento",
  uffici_commercio: "piazza",
  centro_storico: "piazza", // non succede: nel centro storico non ci sono rotonde
  popolare: "verde",
  villette: "verde",
  nuove_costruzioni: "verde",
  parco: "verde",
}

/** Come è decorata l'isola nel quartiere: cemento (niente piante), verde o piazza. */
export const decorazioneIsola = (tipo: TipoTessera): Decorazione =>
  DECORAZIONE[tipo]

/** Raggio della vasca della fontana (in proporzione all'isola libera). */
export const VASCA = 0.4

export type ParteIsola = {
  readonly materiale: MaterialeIsola
  readonly x: number
  readonly y: number // base della parte, sopra la faccia superiore della tessera
  readonly z: number
  readonly raggio: number
  readonly altezza: number
}

/** Quota della faccia di sopra dell'isola (aiuola, cemento o piazza), sopra la tessera: lì poggia il monumento. */
export const SOPRA_ISOLA = QUOTE.marciapiede + 0.4

export type NomeMonumento =
  | "Oratore"
  | "Pensatore"
  | "Fiaccola"
  | "Poeta"
  | "Equestre"
const STATUE_COMPATTE: readonly NomeMonumento[] = [
  "Oratore",
  "Pensatore",
  "Fiaccola",
  "Poeta",
]

/** Scala dei monumenti (metri reali → unità di gioco): 5,2 nella rotonda compatta, × 1,25 nell'ampia. */
export const SCALA_MONUMENTI = { compatta: 5.2, ampia: 5.2 * 1.25 } as const

/** Raggio del basamento dei monumenti in unità di gioco, alla scala 5,2 (4,6 m × 5,2; GDD: r 24). */
const BASAMENTO = 24

export type Monumento = {
  readonly nome: NomeMonumento
  readonly scala: number
  /** Raggio del basamento in unità di gioco (24 nella compatta, 30 nell'ampia). */
  readonly basamento: number
  /** Direzione (dal centro della tessera) verso cui guarda: il viale principale. */
  readonly dx: number
  readonly dz: number
}

const IMPORTANZA: Record<Connettore, number> = {
  nessuna: 0,
  stretta: 1,
  urbana: 2,
  viale: 3,
}

/** Il lato con la strada più importante (a parità, il primo). */
export function latoPrincipale(connettori: readonly Connettore[]): Lato {
  return LATI.reduce(
    (migliore, l) =>
      IMPORTANZA[connettori[l]] > IMPORTANZA[connettori[migliore]]
        ? l
        : migliore,
    0 as Lato,
  )
}

/** Il monumento al centro della rotonda della tessera, o null se lì non ce n'è (GDD: "Dove"). */
export function monumentoIsola(
  rotonda: Rotonda,
  tipo: TipoTessera,
  hex: Hex,
  connettori: readonly Connettore[],
): Monumento | null {
  const decorazione = DECORAZIONE[tipo]
  if (decorazione === "cemento") return null // industria e provinciali: niente
  const verso = puntoLato(latoPrincipale(connettori))
  const l = Math.hypot(verso.x, verso.z)
  const direzione = { dx: verso.x / l, dz: verso.z / l }
  if (rotonda.tipo === "ampia") {
    const scala = SCALA_MONUMENTI.ampia
    return {
      nome: "Equestre",
      scala,
      basamento: (BASAMENTO * scala) / SCALA_MONUMENTI.compatta,
      ...direzione,
    }
  }
  if (decorazione === "piazza") return null // uffici: la piazzetta con la fontana
  // una delle quattro statue, sempre la stessa per la stessa tessera
  const n = (((hex.q * 7 + hex.r * 13) % 4) + 4) % 4
  return {
    nome: STATUE_COMPATTE[n],
    scala: SCALA_MONUMENTI.compatta,
    basamento: BASAMENTO,
    ...direzione,
  }
}

/** Raggio libero dell'isola, dentro il cordolo: lì stanno monumento e piante. */
export const raggioIsola = (rotonda: Rotonda) => rotonda.isola - SEGNI.cordolo

/** Le parti dell'isola (aiuola, cemento o piazza, fontana); con il monumento niente fontana. */
export function partiIsola(
  rotonda: Rotonda,
  tipo: TipoTessera,
  conMonumento = false,
): ParteIsola[] {
  const decorazione = DECORAZIONE[tipo]
  const r = raggioIsola(rotonda)
  const base = QUOTE.marciapiede
  const parti: ParteIsola[] = [
    {
      materiale: decorazione,
      x: 0,
      y: 0,
      z: 0,
      raggio: r,
      altezza: SOPRA_ISOLA,
    },
  ]

  // gli alberi e i cespugli dell'isola sono piante vere (vegetazione/piante.ts: pianteIsola)
  if (decorazione === "piazza" && conMonumento) return parti // rotonda ampia degli uffici: la statua al posto della fontana
  if (decorazione === "piazza") {
    // fontana: vasca di pietra con l'acqua
    parti.push({
      materiale: "pietra",
      x: 0,
      y: base + 0.4,
      z: 0,
      raggio: r * VASCA,
      altezza: 4,
    })
    parti.push({
      materiale: "acqua",
      x: 0,
      y: base + 0.4,
      z: 0,
      raggio: r * 0.33,
      altezza: 4.3,
    })
  }
  return parti
}
