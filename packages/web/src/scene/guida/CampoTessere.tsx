/*
 * CampoTessere.tsx
 * Il secondo campo di prova: tre tessere vere di Castelfiume in fila, con
 * strade, edifici, piante e una rampa (datiCampoTessere.ts). Si parte dalla
 * prima tessera e si sale sulla rampa verso la terza.
 *
 * Disegno, fisica, tavolo e pilota sono quelli comuni di CampoCitta.tsx.
 * Va messo dentro <Physics> e dentro un <Suspense>.
 */

import type { RefObject } from "react"

import CampoCitta from "./CampoCitta"
import {
  CENTRO_CAMPO,
  CUNEI_RAMPE,
  GRUPPI_TESSERE,
  PARTENZA_TESSERE,
  TRIMESH_TESSERE,
} from "./datiCampoTessere"

type CampoTessereProps = {
  readonly tachimetroRef: RefObject<HTMLDivElement | null>
}

function CampoTessere({ tachimetroRef }: CampoTessereProps) {
  return (
    <CampoCitta
      gruppi={GRUPPI_TESSERE}
      trimesh={TRIMESH_TESSERE}
      cunei={CUNEI_RAMPE}
      centro={CENTRO_CAMPO}
      partenza={PARTENZA_TESSERE}
      tachimetroRef={tachimetroRef}
    />
  )
}

export default CampoTessere
