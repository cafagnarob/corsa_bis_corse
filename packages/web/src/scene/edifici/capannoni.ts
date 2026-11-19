/*
 * capannoni.ts
 * I capannoni della zona industriale, dal seme: le regole di capannone() in
 * cb_edifici.py, ridotte a quello che serve al guscio.
 *
 * - scatoloni bassi e lunghi: 7 m alla gronda (una fascia di 4 m e una di
 *   3 m), lunghi un numero PARI di moduli (i denti dello shed sono da due);
 *   pareti di lamiera (grigia, scura, verde, azzurra o kraft nudo);
 * - misure ridotte rispetto a Blender (12-28 m × 10-14 m invece di
 *   20-40 × 12-20) perché una tessera è larga circa 66 m e la strada ne
 *   occupa il mezzo: così ci stanno, anche due per lato; quattro volte su
 *   dieci un capannone artigianale piccolo (8-16 × 8-10 m, uffici più rari)
 *   che riempie i buchi tra i grandi;
 * - sul fronte portoni sezionali larghi due moduli (Cap_Portone, poi la
 *   casella COPERTA), porte di servizio e lamiera; in alto il nastro di
 *   finestre (Cap_Finestrata) o la lamiera (Cap_Parete_Alta);
 * - fianchi e retro di lamiera, a volte la finestrata in alto sul retro e
 *   una porta su un fianco;
 * - tetto a SHED sette volte su dieci (denti di 4 m: canale 0,4, falda 3,6 a
 *   23° con la vetrata verticale), altrimenti piano con il parapetto;
 * - sette volte su dieci la palazzina degli uffici davanti, a filo strada,
 *   sull'estremità destra: un altro CORPO (2-3 moduli, terra e un piano,
 *   in muratura chiara, con marcapiano e cornicione).
 * Tettoie dei portoni, ciminiera, silos e pallet sono pezzi del kit:
 * arriveranno con la vista a piedi.
 */

import type { Casuale } from "@corsa-bis/engine"
import { INTONACI_BORGO, INTONACI_CAPANNONI, KRAFT, UFFICI } from "./colori"
import {
  COPERTA,
  H_PIANO,
  H_TERRA,
  type Parete,
  type Progetto,
} from "./progetto"

/** SHED_L, SHED_A di cb_edifici.py: dente di 4 m = canale 0,4 + falda 3,6. */
const SHED = { dente: 4, canale: 0.4, pendenza: (23 * Math.PI) / 180 }
const PARAPETTO = 0.72
/** Di quanto la palazzina degli uffici sta davanti al fronte del capannone (Vector((2.4, 0, 0)) in Blender). */
const AVANTI_UFFICI = 2.4

export function generaCapannone(rng: Casuale): Progetto {
  // quattro volte su dieci un capannone artigianale piccolo (8-16 × 8-10 m): riempie i buchi tra i grandi
  const piccolo = rng.probabilita(0.4)
  const nW = piccolo ? 2 * rng.intero(2, 4) : 2 * rng.intero(3, 7)
  const nD = piccolo ? rng.scegli([4, 5]) : rng.scegli([5, 6, 7])
  const nome = rng.scegli([
    ...Object.keys(INTONACI_CAPANNONI),
    "kraft",
    "kraft",
  ])
  const colore = nome === "kraft" ? KRAFT : INTONACI_CAPANNONI[nome]
  const shed = rng.probabilita(0.7)

  // fronte: portoni da due colonne, porte di servizio, lamiera (stesso ciclo di capannone())
  const terra: string[] = Array.from({ length: nW }, () => "Cap_Parete")
  let k = 1
  while (k < nW - 2) {
    if (rng.probabilita(0.55)) {
      terra[k] = "Cap_Portone"
      terra[k + 1] = COPERTA
      k += 3
    } else if (rng.probabilita(0.3)) {
      terra[k] = "Cap_Porta"
      k += 2
    } else k += 1
  }
  const nastro = rng.probabilita(0.7)
  const alto = Array.from({ length: nW }, () =>
    nastro && rng.probabilita(0.8) ? "Cap_Finestrata" : "Cap_Parete_Alta",
  )

  const lato = (n: number, retro: boolean, porta: boolean) => [
    Array.from({ length: n }, (_, kk) =>
      porta && kk === Math.floor(n / 2) ? "Cap_Porta" : "Cap_Parete",
    ),
    Array.from({ length: n }, () =>
      retro && rng.probabilita(0.5) ? "Cap_Finestrata" : "Cap_Parete_Alta",
    ),
  ]
  const caselle: Record<Parete, (string | null)[][]> = {
    Fronte: [terra, alto],
    Destra: lato(nD, false, rng.probabilita(0.5)),
    Sinistra: lato(nD, false, false),
    Retro: lato(nW, true, false),
  }
  const righe = [H_TERRA, H_PIANO]
  if (!shed) {
    righe.push(PARAPETTO)
    for (const r of Object.values(caselle)) r.push(r[0].map(() => null))
  }

  const uffici = rng.probabilita(piccolo ? 0.3 : 0.7)
    ? [{ progetto: palazzinaUffici(rng), x: AVANTI_UFFICI, y: 0, z: 0 }]
    : []

  return {
    famiglia: "capannone",
    nW,
    nD,
    righe,
    caselle,
    colore,
    fasce: [],
    tetto: shed
      ? { tipo: "shed", ...SHED }
      : { tipo: "piano", copertura: KRAFT },
    scatole: [],
    corpi: uffici,
  }
}

/** La palazzina degli uffici: 2-3 moduli, profonda uno, porta e vetrine al terra, finestre sopra, tetto piano. */
function palazzinaUffici(rng: Casuale): Progetto {
  const nW = rng.intero(2, 3)
  const nD = 1
  const colore = UFFICI[rng.scegli(Object.keys(UFFICI))]
  const lati = (n: number) => [
    Array.from({ length: n }, () => "Terra_Parete"),
    Array.from({ length: n }, () => "Piano_Finestra_Aperta"),
    Array.from({ length: n }, () => null),
  ]
  const H = H_TERRA + H_PIANO
  return {
    famiglia: "uffici",
    nW,
    nD,
    righe: [H_TERRA, H_PIANO, 0.4],
    caselle: {
      Fronte: [
        [
          "Terra_Porta",
          ...Array.from({ length: nW - 1 }, () => "Terra_Vetrina"),
        ],
        Array.from({ length: nW }, () => "Piano_Finestra_Aperta"),
        Array.from({ length: nW }, () => null),
      ],
      Destra: lati(nD),
      Sinistra: lati(nD),
      Retro: lati(nW),
    },
    colore,
    fasce: [
      {
        cella: "Fascia_Marcapiano",
        quota: H_TERRA - 0.08,
        colore: INTONACI_BORGO.crema,
      },
      {
        cella: "Fascia_Cornicione",
        quota: H + 0.4 - 0.3,
        colore: INTONACI_BORGO.crema,
      },
    ],
    tetto: { tipo: "piano", copertura: KRAFT },
    scatole: [],
  }
}
