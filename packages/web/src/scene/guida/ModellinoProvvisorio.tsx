/*
 * ModellinoProvvisorio.tsx
 * Il mezzo fatto di scatole: scocca arancio, abitacolo crema, quattro ruote
 * con una razza chiara. Si vede finché il modello di cartone (utilitaria.glb)
 * non è caricato: è il fallback del <Suspense> in Veicolo.tsx. Serve anche
 * per provare la fisica senza i file LFS.
 *
 * A ogni fotogramma legge dal controller di Rapier, per ogni ruota,
 * l'allungamento della sospensione, l'angolo di sterzo e la rotazione, e
 * sposta le ruote disegnate di conseguenza.
 */

import { useRef, type RefObject } from "react"
import { useFrame } from "@react-three/fiber"
import type { Group } from "three"
import type { DynamicRayCastVehicleController } from "@dimforge/rapier3d-compat"

import { ruoteVeicolo } from "./guidaArcade"
import { SCALA, type ParametriVeicolo } from "./parametri"

type ModellinoProvvisorioProps = {
  readonly parametri: ParametriVeicolo
  readonly controllerRef: RefObject<DynamicRayCastVehicleController | null>
}

function ModellinoProvvisorio({
  parametri: p,
  controllerRef,
}: ModellinoProvvisorioProps) {
  const ruoteDisegnateRef = useRef<(Group | null)[]>([])
  const ruote = ruoteVeicolo(p)
  const raggio = p.ruote.raggio * SCALA
  const lunghezza = p.scocca.lunghezza * SCALA
  const altezza = p.scocca.altezza * SCALA

  useFrame(() => {
    const c = controllerRef.current
    if (!c) return
    ruoteDisegnateRef.current.forEach((ruota, i) => {
      if (!ruota) return
      const [x, y, z] = ruote[i].attacco
      const sospensione =
        c.wheelSuspensionLength(i) ?? p.sospensioni.riposo * SCALA
      ruota.position.set(x, y - sospensione, z)
      ruota.rotation.y = c.wheelSteering(i) ?? 0
      // Il cerchione (primo figlio) gira attorno al suo asse; avanti = verso negativo
      const cerchione = ruota.children[0]
      if (cerchione) cerchione.rotation.z = -(c.wheelRotation(i) ?? 0)
    })
  })

  return (
    <group>
      {/*
        La scocca disegnata è più stretta della carreggiata, così le ruote
        sporgono e si vedono girare (il collisore resta largo quanto il mezzo).
      */}
      <mesh>
        <boxGeometry
          args={[lunghezza, altezza, (p.ruote.carreggiata - 0.3) * SCALA]}
        />
        <meshStandardMaterial color="#d9772b" />
      </mesh>
      <mesh position={[-0.2 * SCALA, altezza / 2 + 0.25 * SCALA, 0]}>
        <boxGeometry args={[1.8 * SCALA, 0.5 * SCALA, 1.2 * SCALA]} />
        <meshStandardMaterial color="#efe3c8" />
      </mesh>

      {ruote.map((_, i) => (
        <group
          key={i}
          ref={(g) => {
            ruoteDisegnateRef.current[i] = g
          }}
        >
          <group>
            {/* Il cilindro nasce in piedi (asse Y): lo giriamo sull'asse Z */}
            <mesh rotation={[Math.PI / 2, 0, 0]}>
              <cylinderGeometry args={[raggio, raggio, 0.2 * SCALA, 16]} />
              <meshStandardMaterial color="#3a3a3a" />
            </mesh>
            {/* Una razza chiara: senza, la ruota sembrerebbe ferma */}
            <mesh>
              <boxGeometry args={[raggio * 1.6, raggio * 0.25, 0.22 * SCALA]} />
              <meshStandardMaterial color="#efe3c8" />
            </mesh>
          </group>
        </group>
      ))}
    </group>
  )
}

export default ModellinoProvvisorio
