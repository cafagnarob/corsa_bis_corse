/*
 * borgo.ts
 * Le palazzine del borgo del centro storico, dal seme: le regole di
 * genera_palazzina() in cb_edifici.py, ridotte a quello che serve al guscio.
 *
 * - 1-3 moduli di facciata, profonde 2-3, 1-3 piani sopra il terra, un
 *   colore a caso tra gli intonaci del borgo;
 * - al terra almeno un ingresso (porta o portone), il resto botteghe
 *   (vetrina, serranda) o muro; sulle vetrine a volte la tenda o l'insegna,
 *   su qualche porta la pensilina (nell'atlante sono riquadri a parte);
 * - colonne di aperture coerenti su tutti i piani; a volte un balcone al
 *   primo piano;
 * - sulle altre pareti: al terra muro (la porta sul retro), sopra finestre
 *   all'80%;
 * - persiane: nell'atlante la finestra ha le persiane aperte o chiuse; per
 *   ora chiuse una volta su dieci (con la vitalità cambierà);
 * - marcapiano sopra il terra e cornicione in cima, color crema;
 * - tetto a una falda di ondulato (10°) che scende verso il retro, oppure
 *   terrazzo con il parapetto e a volte una sopraelevazione di kraft.
 * Comignoli, antenne, serbatoi, scale esterne e panni sono pezzi del kit:
 * arriveranno con la vista a piedi.
 */

import type { Casuale } from "@corsa-bis/engine"
import { INTONACI_BORGO, KRAFT } from "./colori"
import {
  H_PIANO,
  H_TERRA,
  MODULO,
  T,
  type Parete,
  type Progetto,
} from "./progetto"

/** Pendenza della falda (FALDA_A in kit_edifici.json) e sporgenza. */
const FALDA = { pendenza: 0.1745, sporto: 0.3 }
const PARAPETTO = 0.9

export function generaBorgo(rng: Casuale): Progetto {
  const nW = rng.scegli([1, 2, 2, 3])
  const nD = rng.scegli([2, 3])
  const piani = rng.scegli([1, 2, 2, 3])
  const nomeColore = rng.scegli(Object.keys(INTONACI_BORGO))
  const colore = INTONACI_BORGO[nomeColore]

  // terra: almeno un ingresso, il resto botteghe o muro
  const terra = Array.from({ length: nW }, () =>
    rng.scegli([
      "Terra_Vetrina",
      "Terra_Vetrina",
      "Terra_Serranda",
      "Terra_Parete",
    ]),
  )
  terra[rng.intero(0, nW - 1)] = rng.scegli([
    "Terra_Porta",
    "Terra_Porta",
    "Terra_Portone",
  ])
  // botteghe: tenda o insegna sulle vetrine, pensilina su qualche porta
  const terraAtlante = terra.map((t) => {
    if (t === "Terra_Vetrina")
      return rng.probabilita(0.6)
        ? "Terra_Vetrina_Tenda"
        : rng.probabilita(0.7)
          ? "Terra_Vetrina_Insegna"
          : t
    if (t === "Terra_Porta" && rng.probabilita(0.5))
      return "Terra_Porta_Pensilina"
    return t
  })

  // piani: colonne coerenti, balcone al primo piano
  const colonne = Array.from({ length: nW }, () =>
    rng.probabilita(0.85) ? "finestra" : "parete",
  )
  const kBalcone =
    piani > 0 && rng.probabilita(0.5) ? rng.intero(0, nW - 1) : null
  const finestra = () =>
    rng.probabilita(0.1) ? "Piano_Finestra_Chiusa" : "Piano_Finestra_Aperta"
  const fronte: (string | null)[][] = [terraAtlante]
  for (let p = 1; p <= piani; p++)
    fronte.push(
      colonne.map((c, k) =>
        k === kBalcone && p === 1
          ? "Piano_Portafinestra_Balcone"
          : c === "finestra"
            ? finestra()
            : "Piano_Parete",
      ),
    )

  // le altre pareti: come palazzo() in cb_edifici.py
  const altra = (parete: Parete, n: number) => {
    const righe: (string | null)[][] = [
      Array.from({ length: n }, (_, k) =>
        parete === "Retro" && k === 0 ? "Terra_Porta" : "Terra_Parete",
      ),
    ]
    for (let p = 1; p <= piani; p++)
      righe.push(
        Array.from({ length: n }, () =>
          rng.probabilita(0.8) ? finestra() : "Piano_Parete",
        ),
      )
    return righe
  }

  const falda = rng.probabilita(0.55)
  const righe = [H_TERRA, ...Array.from({ length: piani }, () => H_PIANO)]
  const caselle = {
    Fronte: fronte,
    Destra: altra("Destra", nD),
    Sinistra: altra("Sinistra", nD),
    Retro: altra("Retro", nW),
  }
  const H = H_TERRA + H_PIANO * piani
  const W = nW * MODULO
  const D = nD * MODULO + 2 * T

  // terrazzo: parapetto (una riga senza riquadri: intonaco) e forse la sopraelevazione di kraft nell'angolo dietro a sinistra
  const scatole =
    !falda && rng.probabilita(0.6)
      ? [
          {
            x: -D + MODULO + 2 * T,
            z: W - MODULO,
            quota: H,
            larghezza: MODULO,
            profondita: MODULO + 2 * T,
            altezza: H_PIANO,
            colore: KRAFT,
          },
        ]
      : []
  if (!falda) {
    righe.push(PARAPETTO)
    for (const p of Object.values(caselle)) p.push(p[0].map(() => null))
  }

  return {
    famiglia: "borgo",
    nW,
    nD,
    righe,
    caselle,
    colore,
    fasce: [
      ...(piani > 0
        ? [
            {
              cella: "Fascia_Marcapiano",
              quota: H_TERRA - 0.08,
              colore: INTONACI_BORGO.crema,
            },
          ]
        : []),
      {
        cella: "Fascia_Cornicione",
        quota: H - 0.3,
        colore: INTONACI_BORGO.crema,
      },
    ],
    tetto: falda
      ? { tipo: "falda", ...FALDA }
      : { tipo: "piano", copertura: KRAFT },
    scatole,
  }
}
