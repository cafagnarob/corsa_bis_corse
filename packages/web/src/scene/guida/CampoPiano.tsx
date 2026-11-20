/*
 * CampoPiano.tsx
 * Il primo campo di prova: un pavimento piatto di circa 385 × 385 m con una
 * griglia (le linee che scorrono fanno capire la velocità), una rampa per
 * provare salti e atterraggi e qualche scatola di cartone da spingere.
 * Il pilota parte al centro, verso +X.
 *
 * Va messo dentro <Physics>.
 */

import type { RefObject } from "react"
import { CuboidCollider, RigidBody } from "@react-three/rapier"

import type { Partenza } from "./campi"
import { SCALA } from "./parametri"
import Pilota from "./Pilota"

/* ------------------------------------------------------------------------
 * Misure del campo, in unità di gioco
 * --------------------------------------------------------------------- */

const LATO_PAVIMENTO = 2000 // circa 385 m
const PARTENZA: Partenza = { posizione: [0, 8, 0], direzione: 0 }

// Rampa: una scatola inclinata, metà affondata nel pavimento
const RAMPA = {
  posizione: [260, 0, 0] as [number, number, number],
  inclinazione: (12 * Math.PI) / 180, // 12° di salita
  misure: [120, 12, 80] as [number, number, number],
}

// Scatole di cartone: cubi di 1 m, leggeri, in una piccola pila
const LATO_SCATOLA = 1 * SCALA
const SCATOLE: [number, number, number][] = [
  [120, 0, 40],
  [120, 0, 46],
  [120, 0, 52],
  [120, 1, 43],
  [120, 1, 49],
  [120, 2, 46],
].map(([x, piano, z]) => [x, LATO_SCATOLA / 2 + piano * LATO_SCATOLA, z])

type CampoPianoProps = {
  readonly tachimetroRef: RefObject<HTMLDivElement | null>
}

function CampoPiano({ tachimetroRef }: CampoPianoProps) {
  return (
    <>
      {/* Pavimento: collisore spesso 10 unità, con la faccia superiore a y = 0 */}
      <RigidBody type="fixed" colliders={false}>
        <CuboidCollider
          args={[LATO_PAVIMENTO / 2, 5, LATO_PAVIMENTO / 2]}
          position={[0, -5, 0]}
        />
        <mesh rotation={[-Math.PI / 2, 0, 0]}>
          <planeGeometry args={[LATO_PAVIMENTO, LATO_PAVIMENTO]} />
          <meshStandardMaterial color="#8a9a7b" />
        </mesh>
        {/* Griglia: una linea ogni 20 unità (circa 4 m), appena sopra il pavimento */}
        <gridHelper
          args={[LATO_PAVIMENTO, LATO_PAVIMENTO / 20, "#5d6b52", "#76866a"]}
          position={[0, 0.05, 0]}
        />
      </RigidBody>

      {/* Rampa: si sale verso +X (il collisore lo calcola Rapier dalla mesh) */}
      <RigidBody
        type="fixed"
        position={RAMPA.posizione}
        rotation={[0, 0, RAMPA.inclinazione]}
      >
        <mesh>
          <boxGeometry args={RAMPA.misure} />
          <meshStandardMaterial color="#b89a6a" />
        </mesh>
      </RigidBody>

      {/* Scatole di cartone: corpi dinamici leggeri */}
      {SCATOLE.map((posizione, i) => (
        <RigidBody key={i} position={posizione} mass={20}>
          <mesh>
            <boxGeometry args={[LATO_SCATOLA, LATO_SCATOLA, LATO_SCATOLA]} />
            <meshStandardMaterial color="#c8a97e" />
          </mesh>
        </RigidBody>
      ))}

      <Pilota partenza={PARTENZA} tachimetroRef={tachimetroRef} />
    </>
  )
}

export default CampoPiano
