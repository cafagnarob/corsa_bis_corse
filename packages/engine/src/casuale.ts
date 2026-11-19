/*
 * casuale.ts
 * Generatore di numeri casuali deterministico (con seed) del motore.
 *
 * Regola del GDD: la simulazione non usa MAI Math.random(). Stesso seme,
 * stessa sequenza: partite riproducibili, sfide condivise, salvataggi esatti.
 *
 * - Algoritmo: Mulberry32 (stato di 32 bit, veloce, buona qualità per un gioco).
 * - Seme di testo trasformato in numero con l'hash FNV-1a.
 * - Ogni sistema (città, contratti, eventi...) usa un flusso separato,
 *   così un'estrazione in più in un sistema non cambia gli altri.
 * - Lo stato è un solo numero: si salva e si riprende da dove si era.
 *
 * ATTENZIONE: cambiare l'algoritmo cambia tutte le città e rompe i salvataggi.
 * Il test "valori di riferimento" esiste per accorgersene.
 */

/** Hash FNV-1a a 32 bit: trasforma un testo in un numero intero senza segno. */
export function hashTesto(testo: string): number {
  let h = 0x811c9dc5
  for (let i = 0; i < testo.length; i++) {
    h ^= testo.charCodeAt(i)
    h = Math.imul(h, 0x01000193) // moltiplicazione a 32 bit
  }
  return h >>> 0 // ">>> 0" = interpreta come intero senza segno
}

export class Casuale {
  #stato: number // "#" = campo privato: da fuori non si può toccare

  /** Seme di testo ("castelfiume") o stato numerico salvato in precedenza. */
  constructor(seme: string | number) {
    this.#stato = typeof seme === "number" ? seme >>> 0 : hashTesto(seme)
  }

  /** Stato attuale: da salvare per riprendere la sequenza con `new Casuale(stato)`. */
  get stato(): number {
    return this.#stato
  }

  /** Decimale tra 0 (compreso) e 1 (escluso). È il cuore: tutto il resto passa da qui. */
  decimale(): number {
    this.#stato = (this.#stato + 0x6d2b79f5) >>> 0
    let t = this.#stato
    t = Math.imul(t ^ (t >>> 15), t | 1)
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61)
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296 // diviso 2^32
  }

  /** Intero tra min e max, entrambi compresi. */
  intero(min: number, max: number): number {
    if (!Number.isInteger(min) || !Number.isInteger(max) || max < min) {
      throw new RangeError(`intervallo non valido: ${min}..${max}`)
    }
    return min + Math.floor(this.decimale() * (max - min + 1))
  }

  /** Vero con probabilità p (0 = mai, 1 = sempre). */
  probabilita(p: number): boolean {
    return this.decimale() < p
  }

  /** Un elemento a caso della lista. */
  scegli<T>(lista: readonly T[]): T {
    if (lista.length === 0) throw new RangeError("lista vuota")
    return lista[this.intero(0, lista.length - 1)]
  }

  /** Un elemento a caso, con probabilità proporzionale al peso. */
  scegliPesato<T>(voci: readonly { valore: T; peso: number }[]): T {
    const totale = voci.reduce((somma, v) => somma + Math.max(0, v.peso), 0)
    if (totale <= 0) throw new RangeError("nessun peso positivo")
    let soglia = this.decimale() * totale
    for (const v of voci) {
      soglia -= Math.max(0, v.peso)
      if (soglia < 0) return v.valore
    }
    return voci[voci.length - 1].valore // solo per sicurezza con gli arrotondamenti
  }

  /** Copia mescolata della lista (algoritmo di Fisher-Yates); l'originale non cambia. */
  mescola<T>(lista: readonly T[]): T[] {
    const copia = [...lista]
    for (let i = copia.length - 1; i > 0; i--) {
      const j = this.intero(0, i)
      ;[copia[i], copia[j]] = [copia[j], copia[i]] // scambio
    }
    return copia
  }
}

/** Generatore dedicato a un sistema del gioco, indipendente dagli altri. */
export function flusso(seme: string, nome: string): Casuale {
  return new Casuale(`${seme}/${nome}`)
}
