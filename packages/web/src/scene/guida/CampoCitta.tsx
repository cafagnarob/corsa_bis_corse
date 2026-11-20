/*
 * CampoCitta.tsx
 * Un pezzo di città pronto per guidarci sopra: il disegno (CittaIstanziata),
 * la fisica (trimesh di cime e fianchi delle tessere e un cuneo convesso per
 * ogni rampa, da collisioniTessere.ts), il tavolo sotto e il pilota.
 *
 * È la base comune del campo a tre tessere (CampoTessere) e della gara
 * (ScenaGara): cambiano solo le tessere e la partenza, che arrivano da fuori.
 * `children` sono le cose in più del campo (per esempio la linea del giro).
 *
 * Va messo dentro <Physics> e dentro un <Suspense> (modelli e texture della
 * città si caricano).
 */

import type { ReactNode, RefObject } from "react"
import {
  ConvexHullCollider,
  CuboidCollider,
  RigidBody,
  TrimeshCollider,
} from "@react-three/rapier"

import CittaIstanziata from "../citta/CittaIstanziata"
import type { raggruppa } from "../citta/raggruppa"
import type { Partenza } from "./campi"
import { QUOTA_TAVOLO, type Trimesh } from "./collisioniTessere"
import Pilota from "./Pilota"

/** Lato del tavolo sotto le tessere, in unità di gioco (circa 1,5 km). */
const LATO_TAVOLO = 8000

type CampoCittaProps = {
  readonly gruppi: ReturnType<typeof raggruppa>
  readonly trimesh: Trimesh
  readonly cunei: readonly Float32Array[]
  /** Centro del tavolo, in pianta. */
  readonly centro: { readonly x: number; readonly z: number }
  readonly partenza: Partenza
  readonly tachimetroRef: RefObject<HTMLDivElement | null>
  readonly children?: ReactNode
}

function CampoCitta({
  gruppi,
  trimesh,
  cunei,
  centro,
  partenza,
  tachimetroRef,
  children,
}: CampoCittaProps) {
  return (
    <>
      {/* Il disegno delle tessere, come nella città */}
      <CittaIstanziata gruppi={gruppi} />

      {/* La fisica delle tessere: forme invisibili */}
      <RigidBody type="fixed" colliders={false}>
        <TrimeshCollider args={[trimesh.vertici, trimesh.indici]} />
        {cunei.map((punti, i) => (
          <ConvexHullCollider key={i} args={[punti]} />
        ))}
      </RigidBody>

      {/* Il tavolo: panno verde, con la faccia superiore sotto le pile */}
      <RigidBody
        type="fixed"
        colliders={false}
        position={[centro.x, QUOTA_TAVOLO, centro.z]}
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

      {children}

      <Pilota partenza={partenza} tachimetroRef={tachimetroRef} />
    </>
  )
}

export default CampoCitta
