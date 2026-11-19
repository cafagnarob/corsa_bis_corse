/*
 * NomiQuartieri.tsx
 * I nomi dei quartieri scritti sul plastico, come su una mappa: testo 3D
 * steso sopra il quartiere, che compare solo allontanando la telecamera
 * (lente Quartieri del GDD, versione "a distanza").
 *
 * - Visibilità: dipende dalla distanza tra la telecamera e il punto che
 *   guarda (il target degli OrbitControls). Sotto la soglia il nome non c'è,
 *   poi appare in dissolvenza.
 * - Orientamento: il testo resta sdraiato ma gira attorno al suo centro per
 *   essere sempre leggibile dalla telecamera.
 *
 * Tutto si aggiorna in useFrame scrivendo direttamente sugli oggetti (ref),
 * senza stato React.
 */

import { Text } from "@react-three/drei"
import { useFrame, useThree } from "@react-three/fiber"
import { useRef } from "react"
import { Vector3, type Group, type Mesh } from "three"
import { fattoreZoom } from "./zoom"

const avanti = new Vector3() // riusato a ogni fotogramma: niente oggetti nuovi

/** Il testo di drei è un oggetto di troika-three-text con queste proprietà in più. */
type TestoTroika = Mesh & { fillOpacity: number; outlineOpacity: number }

export type NomeDaMostrare = {
  readonly id: number
  readonly nome: string
  readonly frazione: boolean
  readonly posizione: [number, number, number]
}

function NomeQuartiere({ nome, frazione, posizione }: NomeDaMostrare) {
  const gruppoRef = useRef<Group>(null)
  const testoRef = useRef<TestoTroika>(null)
  const camera = useThree((s) => s.camera)
  const controls = useThree((s) => s.controls) as unknown as {
    target: Vector3
  } | null

  useFrame(() => {
    const gruppo = gruppoRef.current
    const testo = testoRef.current
    if (!gruppo || !testo) return

    const opacita = fattoreZoom(camera, controls)
    gruppo.visible = opacita > 0.01
    testo.fillOpacity = opacita
    testo.outlineOpacity = opacita

    // 2. girare il testo (sdraiato) in modo che la sua "testa" punti dove guarda la telecamera
    camera.getWorldDirection(avanti)
    gruppo.rotation.y = Math.atan2(-avanti.x, -avanti.z)
  })

  return (
    <group ref={gruppoRef} position={posizione}>
      <Text
        ref={testoRef}
        rotation={[-Math.PI / 2, 0, 0]} // sdraiato sul piano, rivolto verso l'alto
        fontSize={frazione ? 80 : 110}
        letterSpacing={0.08}
        color="#fff6e6"
        outlineWidth={7}
        outlineColor="#3d2e1f"
        anchorX="center"
        anchorY="middle"
      >
        {nome.toUpperCase()}
      </Text>
    </group>
  )
}

type NomiQuartieriProps = { nomi: readonly NomeDaMostrare[] }

function NomiQuartieri({ nomi }: NomiQuartieriProps) {
  return (
    <>
      {nomi.map((n) => (
        <NomeQuartiere key={n.id} {...n} />
      ))}
    </>
  )
}

export default NomiQuartieri
