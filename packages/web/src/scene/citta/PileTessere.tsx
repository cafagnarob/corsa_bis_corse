/*
 * PileTessere.tsx
 * Disegna le pile delle tessere (strati e cime) e le rampe tra tessere di
 * quota diversa, con i pezzi di tessere.glb e le texture di Blender, in due
 * livelli di dettaglio:
 * - LOD0 (bordi storti con l'onda) per la tessera guardata e le sei vicine;
 * - LOD1 (esagono semplice) per tutte le altre.
 *
 * Quale tessera si guarda: useTesseraGuardata (il punto attorno a cui gira
 * la telecamera); quando si passa a un'altra tessera si rifanno le istanze,
 * una volta.
 *
 * Si disegnano solo le parti che si vedono:
 * - strati: il bordo (un materiale per livello, sempre più chiaro);
 * - cime: la faccia (per tipo: erba, asfalto, selciato) e il bordo;
 * - rampe: carreggiata, marciapiedi, strisce, bordo e fianchi (il sotto è
 *   nascosto dai fianchi).
 * Sopra degli strati (coperto dalla cima), sotto degli strati e sotto della
 * cima non si vedono mai: la telecamera non scende sotto il tavolo.
 *
 * Chiamate di disegno: (livelli + tipi di cima + 1 + parti delle rampe
 * presenti) × 2 LOD.
 */

import { useMemo } from "react"
import type { BufferGeometry, Material, Matrix4 } from "three"
import {
  useGeometrieTessere,
  type Lod,
  type ParteTessera,
} from "../tessere/geometrie"
import { dividiPerLod, dividiPerTessera } from "../tessere/lod"
import { useTesseraGuardata } from "../tessere/useTesseraGuardata"
import {
  useMaterialiTessere,
  type MaterialiTessere,
} from "../tessere/materiali"
import { MATERIALI_STRADA } from "../strade/materiali"
import Istanze from "./Istanze"
import type { GruppiCitta } from "./raggruppa"

type PileTessereProps = { gruppi: GruppiCitta }

const LOD: readonly Lod[] = [0, 1]

/** Le parti di una rampa che si disegnano, con il loro materiale. */
const PARTI_RAMPA = (
  m: MaterialiTessere,
): readonly (readonly [ParteTessera, Material])[] => [
  ["Strada", m.asfalto],
  ["Marciapiede", m.cemento],
  ["Striscia", MATERIALI_STRADA.segni],
  ["Bordo", m.bordoRampa],
  ["Fianco", m.fiancoRampa],
]

function PileTessere({ gruppi }: PileTessereProps) {
  const geometrie = useGeometrieTessere()
  const materiali = useMaterialiTessere()
  const guardata = useTesseraGuardata()

  // matrici divise per LOD: [vicine, lontane] per ogni livello e tipo di cima
  const divise = useMemo(() => {
    const strati = [...gruppi.strati].map(
      ([livello, m]) => [livello, dividiPerLod(m, guardata)] as const,
    )
    const cime = [...gruppi.cime].map(
      ([tipo, m]) => [tipo, dividiPerLod(m, guardata)] as const,
    )
    // il bordo della cima è uguale per tutti i tipi: una sola istanza per LOD
    const bordiCima = dividiPerLod([...gruppi.cime.values()].flat(), guardata)
    const rampe = [...gruppi.rampe].map(
      ([pezzo, voci]) => [pezzo, dividiPerTessera(voci, guardata)] as const,
    )
    return { strati, cime, bordiCima, rampe }
  }, [gruppi, guardata])

  const strato = geometrie.get("Strato")
  const cima = geometrie.get("Cima")
  if (!strato || !cima) return null

  /** Un'InstancedMesh, solo se ha geometria e almeno una copia. */
  const istanze = (
    k: string,
    geometria: BufferGeometry | undefined,
    materiale: Material,
    matrici: Matrix4[],
  ) =>
    geometria && matrici.length > 0 ? (
      <Istanze
        key={k}
        geometria={geometria}
        materiale={materiale}
        matrici={matrici}
      />
    ) : null

  return (
    <group dispose={null}>
      {LOD.map((lod) => [
        ...divise.strati.map(([livello, m]) =>
          istanze(
            `strato-${livello}-${lod}`,
            strato[lod].Bordo,
            materiali.bordoStrato(livello),
            m[lod],
          ),
        ),
        ...divise.cime.map(([tipo, m]) =>
          istanze(
            `cima-${tipo}-${lod}`,
            cima[lod].Faccia,
            materiali.cime[tipo],
            m[lod],
          ),
        ),
        istanze(
          `bordo-cima-${lod}`,
          cima[lod].Bordo,
          materiali.bordoCima,
          divise.bordiCima[lod],
        ),
        ...divise.rampe.flatMap(([pezzo, m]) =>
          PARTI_RAMPA(materiali).map(([parte, materiale]) =>
            istanze(
              `${pezzo}-${parte}-${lod}`,
              geometrie.get(pezzo)?.[lod][parte],
              materiale,
              m[lod],
            ),
          ),
        ),
      ])}
    </group>
  )
}

export default PileTessere
