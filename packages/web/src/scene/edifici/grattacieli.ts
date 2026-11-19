/*
 * grattacieli.ts
 * I grattacieli delle tessere uffici e commercio, dal seme: le regole di
 * grattacielo() in cb_edifici.py, ridotte a quello che serve al guscio.
 *
 * - torri sottili: base di 3-4 × 3-4 moduli, 8-10 piani in tutto (terra di
 *   4 m e 7-9 piani da 3 m, fino a circa 32 m);
 * - 2-3 SCATOLE impilate, come scatole di cereali una sull'altra: ognuna
 *   più stretta di quella sotto e spostata verso il fondo o verso sinistra,
 *   ognuna con il suo colore (grigi e azzurri, mai due uguali di fila);
 * - ogni scatola ha le finestre a nastro (Gr_Nastro, due volte su tre) o è
 *   tutta vetrata (Gr_Vetrata), su tutte e quattro le pareti;
 * - al terra l'atrio vetrato (Gr_Terra_Vetrata) sul fronte e sui fianchi,
 *   muro sul retro;
 * - in cima a ogni scatola il coronamento (Gr_Coronamento, 1,12 m): sulle
 *   scatole di sotto è una fascia appena fuori dalla parete, sull'ultima è
 *   il parapetto del tetto piano;
 * - sull'ultima il locale macchine (una scatola grigio scuro di 2 × 2 m).
 * Nel progetto la scatola di base è il corpo principale, le altre sono
 * CORPI spostati in su (progetto.ts). Alette della scatola aperta e pennone
 * sono pezzi del kit: arriveranno con la vista a piedi.
 */

import type { Casuale } from "@corsa-bis/engine"
import { INTONACI_GRATTACIELI, KRAFT } from "./colori"
import {
  H_PIANO,
  H_TERRA,
  MODULO,
  T,
  type Corpo,
  type Parete,
  type Progetto,
  type Rgb,
} from "./progetto"

const CORONAMENTO = 1.12
const MACCHINE: Rgb = INTONACI_GRATTACIELI.grigio_scuro_gr

/** Una scatola del grattacielo: misure, piani, colore e modulo di facciata. */
type Scatola = {
  nW: number
  nD: number
  piani: number
  colore: Rgb
  modulo: string
  x: number
  y: number
  z: number
}

export function generaGrattacielo(rng: Casuale): Progetto {
  let nW = rng.intero(3, 4)
  let nD = rng.intero(3, 4)
  const tot = rng.intero(7, 9) // piani sopra il terra
  const nScatole = rng.scegli([2, 3, 3])

  // dove si taglia la torre: nScatole − 1 tagli diversi tra 2 e tot − 1
  const possibili = Array.from({ length: tot - 2 }, (_, i) => i + 2)
  const tagli: number[] = []
  while (tagli.length < nScatole - 1) {
    const t = rng.scegli(possibili.filter((x) => !tagli.includes(x)))
    tagli.push(t)
  }
  tagli.sort((a, b) => a - b)
  const confini = [0, ...tagli, tot]

  const scatole: Scatola[] = []
  let x = 0
  let y = 0
  let z = 0
  let prima: string | null = null
  for (let i = 0; i < nScatole; i++) {
    if (i > 0) {
      // più stretta (almeno da una parte) e spostata verso il fondo o verso sinistra
      let w = Math.max(2, nW - rng.scegli([0, 1, 1]))
      const d = Math.max(2, nD - rng.scegli([0, 1, 1]))
      if (w === nW && d === nD) w = Math.max(2, nW - 1)
      x -= MODULO * rng.intero(0, nD - d)
      z += MODULO * rng.intero(0, nW - w)
      nW = w
      nD = d
    }
    const nome: string = rng.scegli(
      Object.keys(INTONACI_GRATTACIELI).filter((c) => c !== prima),
    )
    prima = nome
    const piani = confini[i + 1] - confini[i]
    scatole.push({
      nW,
      nD,
      piani,
      colore: INTONACI_GRATTACIELI[nome],
      modulo: rng.scegli(["Gr_Nastro", "Gr_Nastro", "Gr_Vetrata"]),
      x,
      y,
      z,
    })
    y += (i === 0 ? H_TERRA : 0) + H_PIANO * piani
  }

  const progetti = scatole.map((s, i) =>
    scatola(s, i === 0, i === scatole.length - 1, rng),
  )
  const corpi: Corpo[] = scatole
    .slice(1)
    .map((s, i) => ({ progetto: progetti[i + 1], x: s.x, y: s.y, z: s.z }))
  return { ...progetti[0], famiglia: "grattacielo", corpi }
}

/** Il progetto di una scatola: terra vetrato se è la base, coronamento in cima, locale macchine se è l'ultima. */
function scatola(
  s: Scatola,
  base: boolean,
  ultima: boolean,
  rng: Casuale,
): Progetto {
  const righe = [
    ...(base ? [H_TERRA] : []),
    ...Array.from({ length: s.piani }, () => H_PIANO),
  ]
  const H = righe.reduce((a, b) => a + b, 0)
  const parete = (p: Parete, n: number) => {
    const r: string[][] = []
    if (base)
      r.push(
        Array.from({ length: n }, () =>
          p === "Retro" ? "Terra_Parete" : "Gr_Terra_Vetrata",
        ),
      )
    for (let k = 0; k < s.piani; k++)
      r.push(Array.from({ length: n }, () => s.modulo))
    if (ultima) r.push(Array.from({ length: n }, () => "Gr_Coronamento"))
    return r
  }
  return {
    famiglia: "scatola",
    nW: s.nW,
    nD: s.nD,
    righe: ultima ? [...righe, CORONAMENTO] : righe,
    caselle: {
      Fronte: parete("Fronte", s.nW),
      Destra: parete("Destra", s.nD),
      Sinistra: parete("Sinistra", s.nD),
      Retro: parete("Retro", s.nW),
    },
    colore: s.colore,
    // sulle scatole di sotto il coronamento è una fascia: la scatola sopra ci appoggia dentro
    fasce: ultima
      ? []
      : [{ cella: "Gr_Coronamento", quota: H, colore: s.colore }],
    tetto: ultima
      ? { tipo: "piano", copertura: KRAFT }
      : { tipo: "solaio", copertura: KRAFT },
    scatole: ultima
      ? [
          {
            x: -MODULO * rng.intero(0, s.nD - 2) - 0.5,
            z: 0.5 + MODULO * rng.intero(0, s.nW - 2),
            quota: H,
            larghezza: MODULO,
            profondita: MODULO + 2 * T,
            altezza: H_PIANO,
            colore: MACCHINE,
          },
        ]
      : [],
  }
}
