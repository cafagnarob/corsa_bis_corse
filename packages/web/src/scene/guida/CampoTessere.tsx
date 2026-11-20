/*
 * CampoTessere.tsx
 * Il secondo campo di prova: tre tessere vere di Castelfiume in fila, con
 * strade, edifici, piante e una rampa (datiCampoTessere.ts). Si parte dalla
 * prima tessera e si sale sulla rampa verso la terza.
 *
 * Due cose diverse per la stessa città:
 * - il DISEGNO è quello della città (CittaIstanziata), fatto solo con le
 *   tre tessere;
 * - la FISICA usa forme semplici (collisioniTessere.ts): una trimesh per
 *   cima e fianchi delle tessere e un cuneo convesso per ogni rampa. Sotto
 *   c'è il tavolo, così chi esce dalle tessere cade sul panno e si può
 *   tornare indietro con R.
 *
 * Va messo dentro <Physics>, e dentro un <Suspense> (modelli e texture della
 * città si caricano).
 */

import type { RefObject } from "react"
import {
  ConvexHullCollider,
  CuboidCollider,
  RigidBody,
  TrimeshCollider,
} from "@react-three/rapier"

import CittaIstanziata from "../citta/CittaIstanziata"
import { QUOTA_TAVOLO } from "./collisioniTessere"
import {
  CENTRO_CAMPO,
  CUNEI_RAMPE,
  GRUPPI_TESSERE,
  PARTENZA_TESSERE,
  TRIMESH_TESSERE,
} from "./datiCampoTessere"
import Pilota from "./Pilota"

/** Lato del tavolo sotto le tessere, in unità di gioco (circa 770 m). */
const LATO_TAVOLO = 4000

type CampoTessereProps = {
  readonly tachimetroRef: RefObject<HTMLDivElement | null>
}

function CampoTessere({ tachimetroRef }: CampoTessereProps) {
  return (
    <>
      {/* Il disegno delle tre tessere, come nella città */}
      <CittaIstanziata gruppi={GRUPPI_TESSERE} />

      {/* La fisica delle tessere: forme invisibili */}
      <RigidBody type="fixed" colliders={false}>
        <TrimeshCollider
          args={[TRIMESH_TESSERE.vertici, TRIMESH_TESSERE.indici]}
        />
        {CUNEI_RAMPE.map((punti, i) => (
          <ConvexHullCollider key={i} args={[punti]} />
        ))}
      </RigidBody>

      {/* Il tavolo: panno verde, con la faccia superiore sotto le pile */}
      <RigidBody
        type="fixed"
        colliders={false}
        position={[CENTRO_CAMPO.x, QUOTA_TAVOLO, CENTRO_CAMPO.z]}
      >
        <CuboidCollider
          args={[LATO_TAVOLO / 2, 5, LATO_TAVOLO / 2]}
          position={[0, -5, 0]}
        />
        <mesh rotation={[-Math.PI / 2, 0, 0]}>
          <planeGeometry args={[LATO_TAVOLO, LATO_TAVOLO]} />
          <meshStandardMaterial color="#4f6a5c" />
        </mesh>
      </RigidBody>

      <Pilota partenza={PARTENZA_TESSERE} tachimetroRef={tachimetroRef} />
    </>
  )
}

export default CampoTessere
