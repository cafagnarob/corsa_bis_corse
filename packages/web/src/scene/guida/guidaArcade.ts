/*
 * guidaArcade.ts
 * Le regole di guida: dai comandi del pilota e dalla velocità del mezzo a
 * quello che ogni ruota deve fare (spinta del motore, freno, sterzo,
 * aderenza laterale). Funzioni pure, senza Rapier né React: il veicolo le
 * chiama prima di ogni passo fisico e passa il risultato al controller di
 * Rapier. Così le regole si leggono e si testano da sole.
 *
 * Le regole, in breve:
 * - gas: spinta piena fino al 90% della velocità massima, poi cala fino a 0;
 * - freno: frena se il mezzo va avanti; da quasi fermo diventa retromarcia;
 * - gas mentre si va indietro: prima frena, poi riparte in avanti;
 * - senza comandi il mezzo rallenta piano da solo (attriti) e da fermo
 *   resta fermo, anche in salita;
 * - lo sterzo gira meno quando si va forte, così ad alta velocità il mezzo
 *   non si scompone;
 * - freno a mano: blocca le ruote dietro e toglie loro aderenza laterale,
 *   quindi il retro scivola (derapata).
 *
 * Unità: velocità in unità di gioco al secondo (vedi SCALA in parametri.ts),
 * angoli in radianti, forze e impulsi nelle unità di Rapier.
 */

import type { Comandi } from "./comandi"
import { SCALA, kmhInUnita, type ParametriVeicolo } from "./parametri"

/* ------------------------------------------------------------------------
 * Ruote
 * Ordine fisso in tutto il codice: 0 anteriore sinistra, 1 anteriore destra,
 * 2 posteriore sinistra, 3 posteriore destra.
 * --------------------------------------------------------------------- */

export type Ruota = {
  /** Punto di attacco della sospensione, in unità di gioco, nel sistema del mezzo. */
  readonly attacco: readonly [number, number, number]
  readonly anteriore: boolean
}

/** Le quattro ruote del mezzo, nell'ordine fisso, in unità di gioco. */
export function ruoteVeicolo(p: ParametriVeicolo): readonly Ruota[] {
  const davanti = p.ruote.asseAnteriore * SCALA // +X
  const dietro = p.ruote.assePosteriore * SCALA
  const z = (p.ruote.carreggiata / 2) * SCALA // destra +Z
  const y = p.ruote.attacco * SCALA
  return [
    { attacco: [davanti, y, -z], anteriore: true },
    { attacco: [davanti, y, z], anteriore: true },
    { attacco: [dietro, y, -z], anteriore: false },
    { attacco: [dietro, y, z], anteriore: false },
  ]
}

/* ------------------------------------------------------------------------
 * Valori fissi delle regole (da tarare)
 * --------------------------------------------------------------------- */

/** Sotto questa velocità (km/h) il mezzo è "quasi fermo": il freno diventa retromarcia. */
const QUASI_FERMO_KMH = 2

/** Rallentamento senza comandi, in m/s²: attrito delle gomme e dell'aria. */
const DECELERAZIONE_IN_FOLLE = 1.5

/** Quanto più forte frena il freno a mano rispetto al freno normale, sulle ruote dietro. */
const FORZA_FRENO_A_MANO = 0.5

/** Da dove la spinta del motore comincia a calare, come frazione della velocità massima. */
const INIZIO_LIMITATORE = 0.9

/* ------------------------------------------------------------------------
 * Risultato
 * --------------------------------------------------------------------- */

export type Guida = {
  readonly motore: readonly number[] // forza del motore per ruota
  readonly freno: readonly number[] // impulso frenante massimo per ruota, per passo
  readonly sterzo: number // angolo delle ruote davanti, radianti (+ = sinistra, convenzione di Rapier)
  readonly laterale: readonly number[] // aderenza laterale per ruota
}

/** Quali ruote spingono, per tipo di trazione. */
function ruoteMotrici(p: ParametriVeicolo): readonly boolean[] {
  switch (p.motore.trazione) {
    case "anteriore":
      return [true, true, false, false]
    case "posteriore":
      return [false, false, true, true]
    case "integrale":
      return [true, true, true, true]
  }
}

/**
 * Impulso frenante per ruota che dà la decelerazione chiesta (m/s²) a tutto
 * il mezzo, con le quattro ruote a terra. Rapier usa il freno come limite
 * dell'impulso di attrito di una ruota in un passo: impulso = massa ×
 * decelerazione × durata del passo, diviso tra le quattro ruote.
 */
const impulsoFreno = (p: ParametriVeicolo, decelerazione: number, dt: number) =>
  (p.massa * decelerazione * SCALA * dt) / 4

/**
 * Cosa devono fare le ruote in questo passo.
 * @param comandi  i comandi del pilota, con lo sterzo già graduale
 * @param velocita velocità del mezzo lungo il suo asse, unità/s (negativa in retromarcia)
 * @param p        i parametri del mezzo
 * @param dt       durata del passo fisico, secondi
 */
export function calcolaGuida(
  comandi: Comandi,
  velocita: number,
  p: ParametriVeicolo,
  dt: number,
): Guida {
  const vMax = kmhInUnita(p.motore.velocitaMassima)
  const vRetro = kmhInUnita(p.motore.velocitaRetromarcia)
  const quasiFermo = Math.abs(velocita) < kmhInUnita(QUASI_FERMO_KMH)
  const spintaPiena = p.massa * p.motore.accelerazione * SCALA

  // --- Motore e freno: un valore per tutto il mezzo, poi diviso sulle ruote
  let spinta = 0 // + avanti, − indietro
  let frenata = 0 // decelerazione chiesta, m/s²

  if (comandi.gas > 0 && velocita < -kmhInUnita(QUASI_FERMO_KMH)) {
    // Va indietro e chiede gas: prima si ferma
    frenata = p.freni.decelerazione * comandi.gas
  } else if (comandi.gas > 0) {
    // Avanti: spinta piena, poi cala vicino alla velocità massima
    const limitatore = Math.min(
      1,
      Math.max(0, (vMax - velocita) / (vMax * (1 - INIZIO_LIMITATORE))),
    )
    spinta = spintaPiena * comandi.gas * limitatore
  } else if (comandi.freno > 0 && velocita > 0 && !quasiFermo) {
    // Va avanti e frena
    frenata = p.freni.decelerazione * comandi.freno
  } else if (comandi.freno > 0) {
    // Quasi fermo o già indietro: retromarcia, fino alla sua velocità massima
    const limitatore = Math.min(
      1,
      Math.max(0, (vRetro + velocita) / (vRetro * 0.2)),
    )
    spinta = -spintaPiena * 0.5 * comandi.freno * limitatore
  } else {
    // Nessun comando: rallenta piano; da fermo tiene il mezzo fermo
    frenata = quasiFermo ? p.freni.decelerazione : DECELERAZIONE_IN_FOLLE
  }

  const motrici = ruoteMotrici(p)
  const quante = motrici.filter(Boolean).length
  const motore = motrici.map((m) => (m ? spinta / quante : 0))

  const frenoBase = impulsoFreno(p, frenata, dt)
  const frenoAMano = comandi.frenoAMano
    ? impulsoFreno(p, p.freni.decelerazione * FORZA_FRENO_A_MANO, dt)
    : 0
  // Freno a mano solo dietro (ruote 2 e 3)
  const freno = [0, 1, 2, 3].map((i) =>
    i >= 2 ? Math.max(frenoBase, frenoAMano) : frenoBase,
  )

  // --- Sterzo: meno angolo quando si va forte
  const quota = Math.min(1, Math.abs(velocita) / vMax)
  const gradi =
    p.sterzo.angoloMassimo +
    (p.sterzo.angoloInVelocita - p.sterzo.angoloMassimo) * quota
  // Il nostro sterzo +1 è a destra; in Rapier l'angolo positivo gira a sinistra
  const sterzo = -comandi.sterzo * ((gradi * Math.PI) / 180)

  // --- Aderenza laterale: col freno a mano il retro scivola
  const laterale = [0, 1, 2, 3].map((i) =>
    i >= 2 && comandi.frenoAMano
      ? p.aderenza.lateraleFrenoAMano
      : p.aderenza.laterale,
  )

  return { motore, freno, sterzo, laterale }
}
