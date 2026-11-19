/*
 * parametri.ts
 * I numeri che decidono come si guida un mezzo, uno per classe del GDD.
 * Per ora c'è solo l'utilitaria, il mezzo del prototipo (Fase 1).
 *
 * Come leggerli:
 * - le misure sono in METRI REALI, le velocità in km/h, le accelerazioni in
 *   m/s²: così si confrontano con un'auto vera. La conversione in unità di
 *   gioco (×5,2, la scala grafica del GDD) la fa il codice con SCALA;
 * - sono valori di partenza da tarare guidando: la fisica è arcade, conta
 *   come si sente, non che sia esatta.
 *
 * Assi del mezzo (come i modelli di Blender): davanti +X, sopra +Y,
 * destra +Z. L'origine è al centro della scocca.
 */

/** Unità di gioco per metro reale (scala grafica del GDD). */
export const SCALA = 5.2

/** Accelerazione di gravità in unità di gioco al secondo quadrato. */
export const GRAVITA = 9.81 * SCALA

/** Da km/h a unità di gioco al secondo. */
export const kmhInUnita = (kmh: number) => (kmh / 3.6) * SCALA

/** Da unità di gioco al secondo a km/h. */
export const unitaInKmh = (u: number) => (u / SCALA) * 3.6

export type Trazione = "anteriore" | "posteriore" | "integrale"

export type ParametriVeicolo = {
  readonly nome: string

  /** Ingombro della scocca, in metri. */
  readonly scocca: {
    readonly lunghezza: number
    readonly larghezza: number
    readonly altezza: number
    /** Di quanto il baricentro sta sotto il centro della scocca: più basso = si ribalta meno. */
    readonly baricentroSotto: number
  }

  /** Massa in kg: decide chi sposta chi negli urti. */
  readonly massa: number

  readonly ruote: {
    readonly raggio: number
    /** Posizione x dell'asse anteriore (positiva, davanti al centro). */
    readonly asseAnteriore: number
    /** Posizione x dell'asse posteriore (negativa, dietro al centro). */
    readonly assePosteriore: number
    /** Distanza tra i centri delle ruote destra e sinistra. */
    readonly carreggiata: number
    /** Quota dell'attacco delle sospensioni rispetto al centro della scocca. */
    readonly attacco: number
  }

  readonly sospensioni: {
    readonly riposo: number // lunghezza a riposo, metri
    readonly corsaMassima: number // metri
    readonly rigidezza: number // più alta = più rigida
    readonly compressione: number // smorzamento quando si comprime
    readonly rilascio: number // smorzamento quando si estende
  }

  readonly motore: {
    readonly trazione: Trazione
    readonly accelerazione: number // m/s² a gas pieno, da fermo
    readonly velocitaMassima: number // km/h
    readonly velocitaRetromarcia: number // km/h
  }

  readonly freni: {
    readonly decelerazione: number // m/s² a freno pieno
  }

  readonly sterzo: {
    readonly angoloMassimo: number // gradi, da fermo
    readonly angoloInVelocita: number // gradi, alla velocità massima
  }

  readonly aderenza: {
    /**
     * Presa massima della gomma, come multiplo del peso sulla ruota: 2 vuol
     * dire che il mezzo può curvare o frenare fino a circa 2 g. Vale per
     * tutte le direzioni (in Rapier è il "friction slip").
     */
    readonly presa: number
    readonly laterale: number // rigidezza in curva: 1 = normale, sotto 1 la gomma scivola prima
    readonly lateraleFrenoAMano: number // laterale delle ruote dietro col freno a mano: derapata
  }
}

/* ------------------------------------------------------------------------
 * Utilitaria (classe Leggeri)
 * Misure dal modello di Blender (utilitaria.glb: 3,6 × 1,62 × 1,5 m,
 * ruote r 0,30 m; assi e carreggiata letti dalle ossa del rig).
 * Agile e svelta a partire, non velocissima. Trazione posteriore: con il
 * freno a mano il retro scivola volentieri, come vuole una guida arcade.
 *
 * Provati in una simulazione senza grafica (Rapier, passo 1/60 s):
 * 0-100 km/h in 4,6 s; da 140 km/h a fermo in 63 m; curva a 50 km/h con
 * raggio di circa 18 m (1,6 g); a 130 km/h con sterzo pieno non si
 * ribalta; freno a mano a 70 km/h: il retro scivola fino a circa 50°.
 * --------------------------------------------------------------------- */

export const UTILITARIA: ParametriVeicolo = {
  nome: "Utilitaria",
  scocca: {
    lunghezza: 3.61,
    larghezza: 1.62,
    altezza: 1.1, // la scatola della fisica, più bassa del modello (tetto escluso)
    baricentroSotto: 0.3,
  },
  massa: 850,
  ruote: {
    raggio: 0.3,
    asseAnteriore: 1.2, // dalle ossa Sterzo_Ant del modello
    assePosteriore: -1.15, // dalle ossa Ruota_Post
    carreggiata: 1.24, // ruote a ±0,62 m
    attacco: -0.25,
  },
  sospensioni: {
    riposo: 0.25,
    corsaMassima: 0.15,
    rigidezza: 24,
    compressione: 4.4,
    rilascio: 2.3,
  },
  motore: {
    trazione: "posteriore",
    accelerazione: 6,
    velocitaMassima: 140,
    velocitaRetromarcia: 25,
  },
  freni: {
    decelerazione: 12,
  },
  sterzo: {
    angoloMassimo: 30, // il modello di Blender arriva a ±35°
    angoloInVelocita: 6,
  },
  aderenza: {
    presa: 2,
    laterale: 1,
    lateraleFrenoAMano: 0.12,
  },
}
