/*
 * comandi.ts
 * I comandi di guida e come si ricavano dai tasti. Solo funzioni pure:
 * niente React, niente Three.js, niente fisica, quindi si testano da sole.
 *
 * Come funziona:
 * - Comandi: quello che il pilota chiede al mezzo in un istante (gas, freno,
 *   sterzo, freno a mano, ripristino). È lo stesso oggetto qualunque sia
 *   l'ingresso: tastiera oggi, gamepad e pulsanti touch domani.
 * - comandiDaiTasti: dai tasti premuti ai Comandi. I tasti sono identificati
 *   con KeyboardEvent.code, cioè la POSIZIONE fisica del tasto: WASD resta
 *   sotto la mano sinistra anche con tastiere AZERTY o QWERTZ.
 * - sterzoGraduale: la tastiera è tutto o niente (sterzo -1, 0 o +1), ma una
 *   ruota vera gira in un tempo. Questa funzione porta lo sterzo verso il
 *   valore chiesto un po' alla volta; la chiama il veicolo a ogni passo fisico.
 */

/** Quello che il pilota chiede al mezzo in un istante. */
export type Comandi = {
  readonly gas: number // 0 = rilasciato, 1 = a fondo
  readonly freno: number // 0..1; da fermo il freno diventa retromarcia
  readonly sterzo: number // -1 = tutto a sinistra, 0 = dritto, +1 = tutto a destra
  readonly frenoAMano: boolean // blocca le ruote posteriori: derapata
  readonly ripristino: boolean // riporta il mezzo sulla strada
}

/** Nessun comando: mezzo in folle, ruote dritte. */
export const COMANDI_FERMI: Comandi = {
  gas: 0,
  freno: 0,
  sterzo: 0,
  frenoAMano: false,
  ripristino: false,
}

/* ------------------------------------------------------------------------
 * Tastiera
 * Più tasti per la stessa azione: WASD e frecce. Il codice è quello di
 * KeyboardEvent.code (posizione fisica), non KeyboardEvent.key (la lettera).
 * --------------------------------------------------------------------- */

export type Azione =
  | "gas"
  | "freno"
  | "sinistra"
  | "destra"
  | "frenoAMano"
  | "ripristino"

export const TASTI: Readonly<Record<Azione, readonly string[]>> = {
  gas: ["KeyW", "ArrowUp"],
  freno: ["KeyS", "ArrowDown"],
  sinistra: ["KeyA", "ArrowLeft"],
  destra: ["KeyD", "ArrowRight"],
  frenoAMano: ["Space"],
  ripristino: ["KeyR"],
}

/** Tutti i tasti usati dalla guida: servono per bloccare lo scorrimento della pagina. */
export const TASTI_DI_GUIDA: ReadonlySet<string> = new Set(
  Object.values(TASTI).flat(),
)

/** Vero se almeno uno dei tasti dell'azione è premuto. */
const premuta = (premuti: ReadonlySet<string>, azione: Azione) =>
  TASTI[azione].some((codice) => premuti.has(codice))

/**
 * I comandi chiesti dai tasti premuti.
 * Sinistra e destra insieme si annullano (sterzo 0). Gas e freno invece
 * arrivano entrambi: è il veicolo a decidere cosa fare se sono premuti
 * insieme.
 */
export function comandiDaiTasti(premuti: ReadonlySet<string>): Comandi {
  const sinistra = premuta(premuti, "sinistra") ? 1 : 0
  const destra = premuta(premuti, "destra") ? 1 : 0
  return {
    gas: premuta(premuti, "gas") ? 1 : 0,
    freno: premuta(premuti, "freno") ? 1 : 0,
    sterzo: destra - sinistra,
    frenoAMano: premuta(premuti, "frenoAMano"),
    ripristino: premuta(premuti, "ripristino"),
  }
}

/* ------------------------------------------------------------------------
 * Sterzo graduale
 * Valori indicativi, da tarare con il prototipo: in quanti secondi lo
 * sterzo va da dritto a tutto girato, e quanto più svelto torna dritto
 * (rilasciare il tasto deve raddrizzare il mezzo in fretta).
 * --------------------------------------------------------------------- */

export const SECONDI_PER_STERZARE = 0.35
export const SECONDI_PER_RADDRIZZARE = 0.2

/**
 * Lo sterzo dopo `dt` secondi, partendo da `attuale` e andando verso
 * `chiesto` (entrambi tra -1 e +1). Non supera mai il valore chiesto.
 * Se il pilota torna verso il centro o inverte, usa la velocità di
 * raddrizzamento, più alta.
 */
export function sterzoGraduale(
  attuale: number,
  chiesto: number,
  dt: number,
): number {
  const differenza = chiesto - attuale
  if (differenza === 0) return chiesto

  // Verso il centro (o oltre, se inverte) si va più svelti
  const raddrizza =
    Math.abs(chiesto) < Math.abs(attuale) || chiesto * attuale < 0
  const secondi = raddrizza ? SECONDI_PER_RADDRIZZARE : SECONDI_PER_STERZARE
  const passo = dt / secondi // frazione dell'intera corsa (da 0 a 1) fatta in dt

  return Math.abs(differenza) <= passo
    ? chiesto
    : attuale + Math.sign(differenza) * passo
}
