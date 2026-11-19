/*
 * Veicolo.tsx
 * Il mezzo guidato dal giocatore: corpo rigido di Rapier, controller a raggi
 * sulle ruote e, per ora, un modellino provvisorio fatto di scatole (scocca,
 * abitacolo e quattro ruote). Il modello di cartone di Blender arriverà con
 * ModelloVeicolo.tsx.
 *
 * Come funziona:
 * 1. La scocca è un RigidBody dinamico con una scatola come collisore. Il
 *    baricentro è abbassato (massProperties) così il mezzo non si ribalta.
 * 2. Al montaggio si crea il controller di Rapier (DynamicRayCastVehicle
 *    Controller): ogni ruota lancia un raggio verso il basso, e dal punto in
 *    cui tocca il suolo nascono sospensione, aderenza e spinta.
 * 3. Prima di ogni passo fisico (useBeforePhysicsStep) si leggono i comandi,
 *    si rende graduale lo sterzo, si calcola cosa fa ogni ruota con le
 *    regole di guidaArcade.ts e si passa tutto al controller.
 * 4. A ogni fotogramma (useFrame) si posizionano le ruote disegnate:
 *    altezza della sospensione, angolo di sterzo e rotazione.
 *
 * Due ref arrivano da fuori: `seguitoRef` (il gruppo che la telecamera
 * insegue) e `tachimetroRef` (un elemento HTML dove scrivere i km/h).
 * Il suffisso Ref non è solo stile: il linter (React Compiler) riconosce
 * dal nome che sono ref, e quindi che si possono modificare fuori dal
 * disegno del componente; con un altro nome segnala un errore.
 */

import { useEffect, useRef, type RefObject } from "react"
import { useFrame } from "@react-three/fiber"
import {
  CuboidCollider,
  RigidBody,
  useBeforePhysicsStep,
  useRapier,
  type RapierRigidBody,
} from "@react-three/rapier"
import type { Group } from "three"
import type { DynamicRayCastVehicleController } from "@dimforge/rapier3d-compat"

import { sterzoGraduale } from "./comandi"
import { calcolaGuida, ruoteVeicolo } from "./guidaArcade"
import {
  SCALA,
  UTILITARIA,
  unitaInKmh,
  type ParametriVeicolo,
} from "./parametri"
import { useComandi } from "./useComandi"

type VeicoloProps = {
  /** Dove nasce il mezzo, e dove torna con il ripristino (unità di gioco). */
  readonly partenza: readonly [number, number, number]
  readonly parametri?: ParametriVeicolo
  /** Gruppo che la telecamera insegue: segue la posizione disegnata (interpolata). */
  readonly seguitoRef?: RefObject<Group | null>
  /** Elemento HTML in cui scrivere la velocità. */
  readonly tachimetroRef?: RefObject<HTMLDivElement | null>
}

/** Ogni quanti secondi si aggiorna il tachimetro (più spesso sarebbe illeggibile). */
const INTERVALLO_TACHIMETRO = 0.1

function Veicolo({
  partenza,
  parametri: p = UTILITARIA,
  seguitoRef,
  tachimetroRef,
}: VeicoloProps) {
  const { world } = useRapier()
  const comandi = useComandi()
  const corpo = useRef<RapierRigidBody>(null)
  const controller = useRef<DynamicRayCastVehicleController | null>(null)
  const ruoteDisegnate = useRef<(Group | null)[]>([])
  // Stato che cambia a ogni passo: in un ref, mai nello stato React
  const stato = useRef({
    sterzo: 0,
    ripristinoPrima: false,
    tempoTachimetro: 0,
  })

  const ruote = ruoteVeicolo(p)
  // Metà delle misure della scocca, in unità di gioco (Rapier vuole le metà)
  const meta = {
    lunghezza: (p.scocca.lunghezza / 2) * SCALA,
    altezza: (p.scocca.altezza / 2) * SCALA,
    larghezza: (p.scocca.larghezza / 2) * SCALA,
  }
  const raggio = p.ruote.raggio * SCALA

  /*
   * Creazione del controller: serve il corpo rigido già nel mondo, quindi
   * si fa dopo il montaggio. È un sistema esterno a React (il mondo di
   * Rapier): useEffect lo crea e, alla fine, lo rimuove.
   */
  useEffect(() => {
    const scocca = corpo.current
    if (!scocca) return
    const c = world.createVehicleController(scocca)
    for (const r of ruoteVeicolo(p)) {
      const [x, y, z] = r.attacco
      c.addWheel(
        { x, y, z }, // punto di attacco
        { x: 0, y: -1, z: 0 }, // la sospensione scende
        { x: 0, y: 0, z: 1 }, // asse della ruota: da sinistra a destra
        p.sospensioni.riposo * SCALA,
        p.ruote.raggio * SCALA,
      )
    }
    for (let i = 0; i < c.numWheels(); i++) {
      c.setWheelSuspensionStiffness(i, p.sospensioni.rigidezza)
      c.setWheelSuspensionCompression(i, p.sospensioni.compressione)
      c.setWheelSuspensionRelaxation(i, p.sospensioni.rilascio)
      c.setWheelMaxSuspensionTravel(i, p.sospensioni.corsaMassima * SCALA)
      c.setWheelMaxSuspensionForce(i, 1e9) // nessun limite: decide la rigidezza
      c.setWheelFrictionSlip(i, p.aderenza.presa)
    }
    controller.current = c
    return () => {
      world.removeVehicleController(c)
      controller.current = null
    }
  }, [world, p])

  /* Prima di ogni passo fisico: dai comandi alle ruote. */
  useBeforePhysicsStep((mondo) => {
    const c = controller.current
    const scocca = corpo.current
    if (!c || !scocca) return
    const dt = mondo.timestep
    const s = stato.current
    const k = comandi.current

    // Ripristino: solo nel momento in cui il tasto viene premuto
    if (k.ripristino && !s.ripristinoPrima) {
      scocca.setTranslation(
        { x: partenza[0], y: partenza[1], z: partenza[2] },
        true,
      )
      scocca.setRotation({ x: 0, y: 0, z: 0, w: 1 }, true)
      scocca.setLinvel({ x: 0, y: 0, z: 0 }, true)
      scocca.setAngvel({ x: 0, y: 0, z: 0 }, true)
    }
    s.ripristinoPrima = k.ripristino

    s.sterzo = sterzoGraduale(s.sterzo, k.sterzo, dt)
    const g = calcolaGuida(
      { ...k, sterzo: s.sterzo },
      c.currentVehicleSpeed(),
      p,
      dt,
    )

    for (let i = 0; i < c.numWheels(); i++) {
      c.setWheelEngineForce(i, g.motore[i])
      c.setWheelBrake(i, g.freno[i])
      c.setWheelSideFrictionStiffness(i, g.laterale[i])
      c.setWheelSteering(i, ruote[i].anteriore ? g.sterzo : 0)
    }
    c.updateVehicle(dt)
  })

  /* A ogni fotogramma: ruote disegnate e tachimetro. */
  useFrame((_, delta) => {
    const c = controller.current
    if (!c) return

    ruoteDisegnate.current.forEach((ruota, i) => {
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

    const s = stato.current
    s.tempoTachimetro += delta
    if (tachimetroRef?.current && s.tempoTachimetro >= INTERVALLO_TACHIMETRO) {
      tachimetroRef.current.textContent = `${Math.round(Math.abs(unitaInKmh(c.currentVehicleSpeed())))} km/h`
      s.tempoTachimetro = 0
    }
  })

  return (
    <RigidBody
      ref={corpo}
      position={[...partenza]}
      colliders={false}
      canSleep={false} // un mezzo addormentato non risponde più ai comandi
      angularDamping={0.5}
    >
      {/*
        Collisore della scocca. massProperties: massa vera e baricentro
        abbassato; l'inerzia è quella di una scatola piena delle stesse misure.
      */}
      <CuboidCollider
        args={[meta.lunghezza, meta.altezza, meta.larghezza]}
        massProperties={{
          mass: p.massa,
          centerOfMass: { x: 0, y: -p.scocca.baricentroSotto * SCALA, z: 0 },
          principalAngularInertia: inerziaScatola(p.massa, meta),
          angularInertiaLocalFrame: { x: 0, y: 0, z: 0, w: 1 },
        }}
      />

      <group ref={seguitoRef}>
        {/*
          Modellino provvisorio: scocca arancio, abitacolo crema.
          La scocca disegnata è più stretta della carreggiata, così le ruote
          sporgono e si vedono girare (il collisore resta largo quanto il mezzo).
        */}
        <mesh>
          <boxGeometry
            args={[
              2 * meta.lunghezza,
              2 * meta.altezza,
              (p.ruote.carreggiata - 0.3) * SCALA,
            ]}
          />
          <meshStandardMaterial color="#d9772b" />
        </mesh>
        <mesh position={[-0.2 * SCALA, meta.altezza + 0.25 * SCALA, 0]}>
          <boxGeometry args={[1.8 * SCALA, 0.5 * SCALA, 1.4 * SCALA]} />
          <meshStandardMaterial color="#efe3c8" />
        </mesh>

        {ruote.map((_, i) => (
          <group
            key={i}
            ref={(g) => {
              ruoteDisegnate.current[i] = g
            }}
          >
            {/* Il cilindro nasce in piedi (asse Y): lo giriamo sull'asse Z */}
            <group>
              <mesh rotation={[Math.PI / 2, 0, 0]}>
                <cylinderGeometry args={[raggio, raggio, 0.2 * SCALA, 16]} />
                <meshStandardMaterial color="#3a3a3a" />
              </mesh>
              {/* Una razza chiara: senza, la ruota sembrerebbe ferma */}
              <mesh position={[0, 0, 0]}>
                <boxGeometry
                  args={[raggio * 1.6, raggio * 0.25, 0.22 * SCALA]}
                />
                <meshStandardMaterial color="#efe3c8" />
              </mesh>
            </group>
          </group>
        ))}
      </group>
    </RigidBody>
  )
}

/** Inerzia di una scatola piena, date le metà dei lati (unità di gioco). */
function inerziaScatola(
  massa: number,
  m: { lunghezza: number; altezza: number; larghezza: number },
) {
  const [a, b, c] = [2 * m.lunghezza, 2 * m.altezza, 2 * m.larghezza]
  return {
    x: (massa * (b * b + c * c)) / 12,
    y: (massa * (a * a + c * c)) / 12,
    z: (massa * (a * a + b * b)) / 12,
  }
}

export default Veicolo
