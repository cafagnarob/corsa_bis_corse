/*
 * Monumenti.tsx
 * I monumenti al centro delle rotonde (monumenti.glb), messi da raggruppa.ts:
 * statue nelle rotonde compatte dei quartieri, statua equestre nelle ampie.
 *
 * Sono mesh ferme: una InstancedMesh per monumento e per LOD, una chiamata di
 * disegno ciascuna. LOD0 per le rotonde della tessera guardata e delle sei
 * vicine, LOD1 per le altre (come strati e cime, useTesseraGuardata).
 */

import { useMemo } from "react"
import { dividiPerTessera } from "../tessere/lod"
import { useTesseraGuardata } from "../tessere/useTesseraGuardata"
import Istanze from "./Istanze"
import { useMonumenti } from "./modelliMonumenti"
import type { GruppiCitta } from "./raggruppa"

type MonumentiProps = { gruppi: GruppiCitta }

function Monumenti({ gruppi }: MonumentiProps) {
  const modelli = useMonumenti()
  const guardata = useTesseraGuardata()
  const divisi = useMemo(
    () =>
      [...gruppi.monumenti].map(
        ([nome, voci]) => [nome, dividiPerTessera(voci, guardata)] as const,
      ),
    [gruppi, guardata],
  )

  return (
    // dispose={null}: geometrie e materiali vengono dal .glb in cache
    <group dispose={null}>
      {divisi.flatMap(([nome, perLod]) =>
        ([0, 1] as const).map((lod) => {
          // se un LOD manca nel file si usa l'altro
          const modello =
            modelli.get(nome)?.[lod] ?? modelli.get(nome)?.[1 - lod]
          const matrici = perLod[lod]
          return modello && matrici.length > 0 ? (
            <Istanze
              key={`${nome}-${lod}`}
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

export default Monumenti
