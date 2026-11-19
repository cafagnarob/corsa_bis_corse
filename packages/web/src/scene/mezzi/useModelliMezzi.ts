/*
 * useModelliMezzi.ts
 * Carica i modelli dei mezzi delle linee (public/models/mezzi/) e li prepara
 * una volta sola per l'instancing (modelloMezzo.ts):
 * - minibus  → minibus.glb
 * - bus      → bus12.glb (bus urbano 12 m)
 * - snodato  → bus18.glb (snodato 18 m, con lo snodo che si piega)
 * Per ognuno: i LOD da 1 a 5 e le misure (lunghezza, altezza, giunto dello
 * snodo).
 *
 * useGLTF sospende il componente finché i file non sono arrivati: chi lo usa
 * sta dentro <Suspense>. Le mesh sono compresse con Draco: si usa il decoder
 * locale in public/draco/, così il gioco non dipende da un CDN esterno.
 */

import type { TipoMezzo } from "@corsa-bis/engine"
import { useGLTF } from "@react-three/drei"
import { useMemo } from "react"
import {
  misureMezzo,
  preparaMezzo,
  type LodMezzo,
  type MisureMezzo,
} from "./modelloMezzo"

const FILE: Record<TipoMezzo, string> = {
  minibus: "/models/mezzi/minibus.glb",
  bus: "/models/mezzi/bus12.glb",
  snodato: "/models/mezzi/bus18.glb",
}
const DECODER_DRACO = "/draco/"
const TIPI = Object.keys(FILE) as TipoMezzo[]

export type ModelloMezzo = {
  readonly lod: (LodMezzo | null)[]
  readonly misure: MisureMezzo
}

export function useModelliMezzi(): Record<TipoMezzo, ModelloMezzo> {
  const caricati = useGLTF(
    TIPI.map((t) => FILE[t]),
    DECODER_DRACO,
  )
  return useMemo(
    () =>
      Object.fromEntries(
        TIPI.map((t, i) => [
          t,
          {
            lod: preparaMezzo(caricati[i].scene),
            misure: misureMezzo(caricati[i].scene),
          },
        ]),
      ) as Record<TipoMezzo, ModelloMezzo>,
    [caricati],
  )
}

// comincia a scaricarli subito, prima che servano
for (const t of TIPI) useGLTF.preload(FILE[t], DECODER_DRACO)
