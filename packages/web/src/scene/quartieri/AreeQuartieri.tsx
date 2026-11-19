/*
 * AreeQuartieri.tsx
 * L'area di ogni quartiere (le facce superiori delle sue tessere): invisibile,
 * ma "sente" il mouse. Nella vista da lontano, passando sopra un quartiere,
 * l'area si illumina del suo colore, esattamente dentro i suoi confini.
 *
 * - Il passaggio del mouse si registra in un ref (nessuno stato React).
 * - L'opacità si avvicina gradualmente al valore voluto in useFrame, così
 *   l'accensione e lo spegnimento sono morbidi.
 * - Da vicino (fattore di zoom basso) l'evidenziazione non c'è.
 */

import { useFrame, useThree, type ThreeEvent } from "@react-three/fiber"
import { useRef } from "react"
import type { BufferGeometry, Mesh, MeshBasicMaterial } from "three"
import { coloreQuartiere } from "./geometrieQuartieri"
import { fattoreZoom } from "./zoom"

const OPACITA_EVIDENZIATO = 0.35
const RAPIDITA = 10 // quanto in fretta si accende e si spegne

type AreaQuartiereProps = { id: number; geometria: BufferGeometry }

function AreaQuartiere({ id, geometria }: AreaQuartiereProps) {
  const meshRef = useRef<Mesh>(null)
  const sopraRef = useRef(false) // il mouse è sopra questo quartiere?
  const camera = useThree((s) => s.camera)
  const controls = useThree((s) => s.controls)

  useFrame((_, delta) => {
    const mesh = meshRef.current
    if (!mesh) return
    const materiale = mesh.material as MeshBasicMaterial
    const obiettivo = sopraRef.current
      ? OPACITA_EVIDENZIATO * fattoreZoom(camera, controls)
      : 0
    // avvicinamento morbido, indipendente dagli FPS
    materiale.opacity +=
      (obiettivo - materiale.opacity) * (1 - Math.exp(-delta * RAPIDITA))
  })

  const entra = (e: ThreeEvent<PointerEvent>) => {
    e.stopPropagation() // solo il quartiere più vicino al mouse reagisce
    sopraRef.current = true
    if (fattoreZoom(camera, controls) > 0.5)
      document.body.style.cursor = "pointer"
  }
  const esce = () => {
    sopraRef.current = false
    document.body.style.cursor = "auto"
  }

  return (
    <mesh
      ref={meshRef}
      geometry={geometria}
      onPointerOver={entra}
      onPointerOut={esce}
    >
      {/* invisibile (opacità 0) ma presente: così il mouse lo "colpisce" */}
      <meshBasicMaterial
        color={coloreQuartiere(id)}
        transparent
        opacity={0}
        depthWrite={false}
        polygonOffset
        polygonOffsetFactor={-2}
        polygonOffsetUnits={-2}
      />
    </mesh>
  )
}

type AreeQuartieriProps = { aree: ReadonlyMap<number, BufferGeometry> }

function AreeQuartieri({ aree }: AreeQuartieriProps) {
  return (
    <>
      {[...aree].map(([id, geometria]) => (
        <AreaQuartiere key={id} id={id} geometria={geometria} />
      ))}
    </>
  )
}

export default AreeQuartieri
