/*
 * ConfiniQuartieri.tsx
 * I contorni colorati di tutti i quartieri (una sola mesh), che compaiono in
 * dissolvenza allontanando la telecamera, insieme ai nomi.
 * L'opacità si aggiorna in useFrame passando dal ref della mesh.
 */

import { useFrame, useThree } from "@react-three/fiber"
import { useRef } from "react"
import type { BufferGeometry, Mesh, MeshBasicMaterial } from "three"
import { fattoreZoom } from "./zoom"

type ConfiniQuartieriProps = { geometria: BufferGeometry }

function ConfiniQuartieri({ geometria }: ConfiniQuartieriProps) {
  const meshRef = useRef<Mesh>(null)
  const camera = useThree((s) => s.camera)
  const controls = useThree((s) => s.controls)

  useFrame(() => {
    const mesh = meshRef.current
    if (!mesh) return
    const f = fattoreZoom(camera, controls)
    mesh.visible = f > 0.01 // da vicino non si disegna proprio
    ;(mesh.material as MeshBasicMaterial).opacity = f
  })

  return (
    <mesh ref={meshRef} geometry={geometria}>
      {/* vertexColors: il colore di ogni quartiere è scritto nei vertici */}
      <meshBasicMaterial
        vertexColors
        transparent
        opacity={0}
        depthWrite={false}
        polygonOffset
        polygonOffsetFactor={-4}
        polygonOffsetUnits={-4}
      />
    </mesh>
  )
}

export default ConfiniQuartieri
