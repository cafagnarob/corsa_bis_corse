/*
 * scala.ts
 * La scala tra il mondo dei mezzi e le unità di gioco.
 *
 * La città è misurata in unità di gioco (una tessera ha raggio 200). I mezzi
 * invece sono modellini in metri reali ingranditi ×5,2 (GDD, "Scala": la
 * scala grafica dei mezzi). Quindi per un pilota 1 metro = 5,2 unità: un
 * viale largo 100 unità è circa 19 m, un circuito di 1,5 km è 7.800 unità.
 *
 * Sta nel motore perché serve sia alle regole (lunghezza dei circuiti) sia
 * alla grafica e alla fisica (web/scene/guida/parametri.ts la riesporta).
 */

/** Unità di gioco per metro reale (scala grafica dei mezzi). */
export const SCALA = 5.2

/** Da metri reali a unità di gioco. */
export const metriInUnita = (metri: number) => metri * SCALA

/** Da unità di gioco a metri reali. */
export const unitaInMetri = (unita: number) => unita / SCALA
