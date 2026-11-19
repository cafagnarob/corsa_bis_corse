/*
 * profili.ts
 * Misure delle strade e della segnaletica orizzontale, in unità di gioco, con
 * la scala grafica ×5,2 del GDD (decisione del 16 novembre): corsia 18,2,
 * viale 100, urbana 55, stretta 30 di larghezza totale.
 *
 * Segnaletica ispirata al Codice della Strada, semplificata per il plastico:
 * - viale: doppia linea continua al centro, tratteggio tra le corsie dello
 *   stesso senso, linee di margine continue;
 * - urbana: tratteggio al centro, linee di margine;
 * - stretta (centro storico): nessuna segnaletica.
 */

import type { ClasseStrada } from "@corsa-bis/engine"

export type Linea = { readonly offset: number; readonly tratteggiata: boolean }

export type Profilo = {
  readonly carreggiata: number // larghezza della carreggiata
  readonly marciapiede: number // larghezza di ciascun marciapiede
  readonly linee: readonly Linea[] // offset dalla mezzeria (+ = destra nel senso del tracciato)
  readonly attraversamenti: boolean // strisce pedonali agli incroci
}

const CORSIA = 18.2
const MARGINE = 1.6 // distanza delle linee di margine dal bordo della carreggiata

export const PROFILO: Record<ClasseStrada, Profilo> = {
  viale: {
    carreggiata: 4 * CORSIA, // 72,8
    marciapiede: 13.6,
    linee: [
      { offset: -1.4, tratteggiata: false },
      { offset: 1.4, tratteggiata: false }, // doppia continua
      { offset: -CORSIA, tratteggiata: true },
      { offset: CORSIA, tratteggiata: true }, // tra le corsie
      { offset: -2 * CORSIA + MARGINE, tratteggiata: false },
      { offset: 2 * CORSIA - MARGINE, tratteggiata: false },
    ],
    attraversamenti: true,
  },
  urbana: {
    carreggiata: 2 * CORSIA, // 36,4
    marciapiede: 9.3,
    linee: [
      { offset: 0, tratteggiata: true },
      { offset: -CORSIA + MARGINE, tratteggiata: false },
      { offset: CORSIA - MARGINE, tratteggiata: false },
    ],
    attraversamenti: true,
  },
  stretta: {
    carreggiata: 22,
    marciapiede: 4,
    linee: [],
    attraversamenti: false,
  },
}

export const SEGNI = {
  spessore: 0.9, // larghezza delle linee
  tratto: 20, // tratteggio: 20 pieno, 20 vuoto
  zebra: { striscia: 2.6, passo: 5.2, lunghezza: 13 },
  dente: { base: 5, altezza: 6, passo: 6.5 }, // "denti di squalo" (dare precedenza)
  distacco: 4, // spazio tra strisce pedonali e denti
  cordolo: 3, // cordolo attorno all'isola delle rotonde
} as const

/** Quote sopra la faccia superiore della tessera (fogli di cartone sovrapposti). */
export const QUOTE = {
  carreggiata: 0.3,
  segni: 0.34,
  marciapiede: 0.8,
} as const
