/*
 * campi.ts
 * I campi di prova della guida e la scelta dall'indirizzo:
 *
 *   ?scena=guida               pavimento piatto con rampa e scatole (piano)
 *   ?scena=guida&prova=tessere tre tessere vere della città con una rampa
 *
 * Qui sta anche il tipo Partenza, che ogni campo dà al veicolo: dove nasce
 * e dove guarda (e dove torna con il ripristino).
 */

/** Dove nasce il mezzo e dove guarda. */
export type Partenza = {
  /** Posizione in unità di gioco: un po' sopra il suolo, il mezzo ci cade sopra. */
  readonly posizione: readonly [number, number, number]
  /** Angolo attorno a Y in radianti: 0 = verso +X (est). */
  readonly direzione: number
}

export type NomeCampo = "piano" | "tessere"

/** Il campo chiesto dall'indirizzo; qualunque altro valore porta al piano. */
export function campoDallIndirizzo(): NomeCampo {
  return new URLSearchParams(window.location.search).get("prova") === "tessere"
    ? "tessere"
    : "piano"
}
