/*
 * aspetto.ts — SEGNAPOSTO
 * Come appare ogni tipo di tessera finché non arrivano i modelli di Blender:
 * - la cima (erba, asfalto, selciato);
 * - il colore e la disposizione dei volumi (scatole al posto degli edifici).
 *
 * Volumi in unità di gioco, con la scala grafica ×5,2 del GDD (circa 6-12
 * edifici per tessera). Coordinate rispetto al centro della tessera:
 * x = est, z = sud; tutti dentro l'esagono (|x| < 173, |z| < 200 - 0,58·|x|).
 *
 *  * Con la rotonda conta anche tutto il cerchio (isola, anello e marciapiede
 * esterno): senza, un volume al centro della tessera finirebbe nell'isola.
 */

import type { TracciatoTessera } from "@corsa-bis/engine"
import { PROFILO } from "../strade/profili"
import { type TipoTessera } from "@corsa-bis/engine"
import type { TipoCima } from "./materiali"

/** Un volume: posizione del centro di base, larghezza (x), profondità (z), altezza. */
export type Volume = readonly [
  x: number,
  z: number,
  larghezza: number,
  profondita: number,
  altezza: number,
]

export type Aspetto = {
  readonly cima: TipoCima
  readonly colore: string
  readonly volumi: readonly Volume[]
}

/**
 * Sei posizioni "tra le strade": verso i vertici dell'esagono (30°, 90°, ...),
 * a metà tra due direzioni di strada. Qui nessuna strada passa mai, nemmeno
 * un viale: ci stanno gli edifici grandi.
 */
const TRA_LE_STRADE: readonly (readonly [number, number])[] = [
  0, 1, 2, 3, 4, 5,
].map((k) => {
  const a = Math.PI / 6 + (k * Math.PI) / 3
  return [
    Math.round(148 * Math.cos(a)),
    Math.round(-148 * Math.sin(a)),
  ] as const
})

export const ASPETTO: Record<TipoTessera, Aspetto> = {
  centro_storico: {
    cima: "selciato",
    colore: "#d9a27a", // terracotta
    // isolati fitti attorno a una piazza vuota al centro
    volumi: [
      [-90, -60, 45, 40, 38],
      [-30, -75, 45, 40, 44],
      [40, -65, 50, 40, 35],
      [100, -40, 40, 45, 40],
      [-100, 20, 40, 50, 36],
      [95, 35, 45, 45, 42],
      [-40, 85, 50, 40, 34],
      [40, 85, 45, 40, 39],
    ],
  },
  popolare: {
    cima: "erba",
    colore: "#c9b8a0",
    // palazzoni lunghi e alti
    volumi: [
      [-60, -90, 100, 35, 70],
      [60, -20, 100, 35, 78],
      [-60, 50, 100, 35, 66],
      [50, 110, 80, 30, 60],
    ],
  },
  villette: {
    cima: "erba",
    colore: "#e8d3b0",
    // casette basse su una griglia larga
    volumi: [-90, 0, 90].flatMap((x) =>
      [-90, 0, 90].map((z): Volume => [x, z, 30, 30, 18]),
    ),
  },
  nuove_costruzioni: {
    cima: "erba",
    colore: "#f0e6d8",
    volumi: [
      [-70, -60, 55, 45, 45],
      [70, -60, 55, 45, 50],
      [-70, 60, 55, 45, 48],
      [70, 60, 55, 45, 44],
    ],
  },
  uffici_commercio: {
    cima: "asfalto",
    colore: "#9fb4c7",
    // torri alte, di altezze diverse, negli spicchi tra le strade
    volumi: TRA_LE_STRADE.map(
      ([x, z], i): Volume => [x, z, 38, 38, 85 + (i % 3) * 15],
    ),
  },
  industriale: {
    cima: "asfalto",
    colore: "#a7a39a",
    // capannoni bassi negli spicchi tra le strade
    volumi: TRA_LE_STRADE.map(([x, z]): Volume => [x, z, 50, 40, 22]),
  },
  parco: {
    cima: "erba",
    colore: "#5f7f4f",
    // niente volumi: il parco è fatto di alberi e cespugli veri (vegetazione/piante.ts)
    volumi: [],
  },
  strada: {
    cima: "erba",
    colore: "#000000",
    volumi: [], // solo la strada, nessun edificio
  },
}

/**
 * Vero se il volume finirebbe sopra una strada o un marciapiede della tessera:
 * si misura la distanza del centro del volume dalle mezzerie del tracciato.
 */
export function sovrapponeStrade(
  [x, z, larghezza, profondita]: Volume,
  { tratti, rotonda }: TracciatoTessera,
): boolean {
  const ingombro = (Math.hypot(larghezza, profondita) / 2) * 0.7 // "raggio" approssimato del volume
  if (
    rotonda &&
    Math.hypot(x, z) <
      rotonda.raggio +
        rotonda.larghezza / 2 +
        PROFILO.urbana.marciapiede +
        ingombro
  )
    return true
  return tratti.some((t) => {
    const { carreggiata, marciapiede } = PROFILO[t.classe]
    const limite = carreggiata / 2 + marciapiede + ingombro
    return t.punti.some((p) => Math.hypot(x - p.x, z - p.z) < limite)
  })
}
