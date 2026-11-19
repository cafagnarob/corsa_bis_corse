/*
 * palazzoni.ts
 * I palazzoni anni '60-'70 dei quartieri popolari, dal seme: le regole di
 * palazzone() in cb_edifici.py, ridotte a quello che serve al guscio.
 *
 * - stecca (due volte su tre, se chi chiama non sceglie la forma): 9-14 moduli, profonda 4, 4-5 piani, un vano
 *   scala ogni 5-6 colonne; torre: 5-6 × 5 moduli, 6-7 piani, una scala al
 *   centro;
 * - un colore spento a caso (cemento, beige, giallino, verdino, mattone,
 *   azzurrino);
 * - al terra androni vetrati sotto i vani scala, a volte negozi nelle stecche;
 * - sul fronte balconi a nastro (nell'atlante sono dentro i riquadri
 *   Pal_..._Balcone), portafinestre e finestre alternate tra i vani; sul
 *   retro finestre con la tapparella su, a metà o giù (come le tapparelle
 *   abbassate a caso del kit);
 * - testate quasi cieche (Pal_Testata, con le fasce dei solai), a volte una
 *   finestra;
 * - in cima il parapetto (Fascia_Parapetto_Pal) e un torrino per ogni vano
 *   scala sul tetto piano.
 * Antenne e serbatoi sono pezzi del kit: arriveranno con la vista a piedi.
 */

import type { Casuale } from "@corsa-bis/engine"
import { INTONACI_PALAZZONI, KRAFT } from "./colori"
import { H_PIANO, H_TERRA, MODULO, T, type Progetto } from "./progetto"

const PARAPETTO = 0.72

export function generaPalazzone(
  rng: Casuale,
  forma?: "stecca" | "torre",
): Progetto {
  const stecca = forma ? forma === "stecca" : rng.scegli([true, true, false])
  const nW = stecca ? rng.intero(9, 14) : rng.intero(5, 6)
  const piani = stecca ? rng.intero(4, 5) : rng.intero(6, 7)
  const nD = stecca ? 4 : 5
  const colore = INTONACI_PALAZZONI[rng.scegli(Object.keys(INTONACI_PALAZZONI))]
  const pari = rng.intero(0, 1) // da che colonna partono le portefinestre

  // vani scala: uno ogni 5-6 colonne nella stecca, al centro nella torre
  let vani: number[]
  if (stecca) {
    const passo = rng.intero(5, 6)
    vani = []
    for (let k = Math.floor(passo / 2); k < nW; k += passo) vani.push(k)
    if (nW - 1 - vani[vani.length - 1] < 2 && vani.length > 1)
      vani[vani.length - 1] = nW - 3
  } else vani = [Math.floor(nW / 2)]
  const vano = (k: number) => vani.includes(k)
  const negozi = stecca && rng.probabilita(0.5)

  // tapparella abbassata a caso: come le f di palazzone() (0, 0, 0,25, 0,5, 0,7, 1)
  const tapparella = () =>
    rng.scegli([
      "Pal_Finestra_Su",
      "Pal_Finestra_Su",
      "Pal_Finestra_Meta",
      "Pal_Finestra_Meta",
      "Pal_Finestra_Giu",
      "Pal_Finestra_Giu",
    ])

  const terraFronte = Array.from({ length: nW }, (_, k) =>
    vano(k)
      ? "Pal_Terra_Androne"
      : negozi
        ? rng.scegli(["Terra_Vetrina", "Terra_Vetrina", "Terra_Serranda"])
        : "Terra_Parete",
  )
  const fronte: (string | null)[][] = [terraFronte]
  const retro: (string | null)[][] = [
    Array.from({ length: nW }, (_, k) =>
      vano(nW - 1 - k) ? "Pal_Terra_Androne" : "Terra_Parete",
    ),
  ]
  const testata = () => {
    const righe: (string | null)[][] = [
      Array.from({ length: nD }, () => "Terra_Parete"),
    ]
    for (let p = 1; p <= piani; p++)
      righe.push(
        Array.from({ length: nD }, (_, k) =>
          k === 1 && rng.probabilita(0.5) ? tapparella() : "Pal_Testata",
        ),
      )
    return righe
  }
  for (let p = 1; p <= piani; p++) {
    fronte.push(
      Array.from({ length: nW }, (_, k) =>
        vano(k)
          ? "Pal_Vano_Scala"
          : (k + pari) % 2 === 0
            ? rng.probabilita(0.2)
              ? "Pal_Portafinestra_Balcone_Chiusa"
              : "Pal_Portafinestra_Balcone"
            : "Pal_Finestra_Balcone",
      ),
    )
    retro.push(
      Array.from({ length: nW }, (_, k) =>
        vano(nW - 1 - k) ? "Pal_Vano_Scala" : tapparella(),
      ),
    )
  }
  const caselle = {
    Fronte: fronte,
    Destra: testata(),
    Sinistra: testata(),
    Retro: retro,
  }
  // il parapetto in cima a tutte le pareti
  for (const righe of Object.values(caselle))
    righe.push(righe[0].map(() => "Fascia_Parapetto_Pal"))

  const H = H_TERRA + H_PIANO * piani
  return {
    famiglia: stecca ? "stecca" : "torre",
    nW,
    nD,
    righe: [
      H_TERRA,
      ...Array.from({ length: piani }, () => H_PIANO),
      PARAPETTO,
    ],
    caselle,
    colore,
    fasce: [],
    tetto: { tipo: "piano", copertura: KRAFT },
    // un torrino (2 × 2 moduli di base, un piano) sopra ogni vano scala, appoggiato al fronte
    scatole: vani.map((v) => ({
      x: -MODULO,
      z: MODULO * v,
      quota: H,
      larghezza: MODULO,
      profondita: MODULO + 2 * T,
      altezza: H_PIANO,
      colore,
    })),
  }
}
