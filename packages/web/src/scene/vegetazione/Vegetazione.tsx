/*
 * Vegetazione.tsx
 * Alberi, cespugli e siepi di cartone (vegetazione.glb), messi da
 * raggruppa.ts con le regole di piante.ts.
 *
 * Sono mesh ferme: una InstancedMesh per pianta e per LOD (al massimo 14
 * chiamate di disegno per tutta la città, GDD). LOD0 per le piante della
 * tessera guardata e delle sei vicine, LOD1 per le altre
 * (useTesseraGuardata, come strati, cime e monumenti).
 */

import { useMemo } from "react"
import Istanze from "../citta/Istanze"
import type { GruppiCitta } from "../citta/raggruppa"
import { dividiPerTessera } from "../tessere/lod"
import { useTesseraGuardata } from "../tessere/useTesseraGuardata"
import { usePiante } from "./modelliPiante"

type VegetazioneProps = { gruppi: GruppiCitta }

function Vegetazione({ gruppi }: VegetazioneProps) {
  const modelli = usePiante()
  const guardata = useTesseraGuardata()
  const divise = useMemo(
    () =>
      [...gruppi.piante].map(
        ([pianta, voci]) => [pianta, dividiPerTessera(voci, guardata)] as const,
      ),
    [gruppi, guardata],
  )

  return (
    // dispose={null}: geometrie e materiali vengono dal .glb in cache
    <group dispose={null}>
      {divise.flatMap(([pianta, perLod]) =>
        ([0, 1] as const).map((lod) => {
          // se un LOD manca nel file si usa l'altro
          const modello =
            modelli.get(pianta)?.[lod] ?? modelli.get(pianta)?.[1 - lod]
          const matrici = perLod[lod]
          return modello && matrici.length > 0 ? (
            <Istanze
              key={`${pianta}-${lod}`}
              geometria={modello.geometria}
              materiale={modello.materiale}
              matrici={matrici}
            />
          ) : null
        }),
      )}
    </group>
  )
}

export default Vegetazione
