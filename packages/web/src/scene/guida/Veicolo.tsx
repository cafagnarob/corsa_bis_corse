/*
 * Veicolo.tsx
 * Il mezzo guidato dal giocatore: corpo rigido di Rapier, controller a raggi
 * sulle ruote e il modello di cartone (ModelloVeicolo.tsx). Finché il
 * modello non è caricato si vede il modellino di scatole
 * (ModellinoProvvisorio.tsx).
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
 * 4. Il disegno legge il controller da solo (controllerRef): modello e
 *    modellino mettono ruote, sterzo e altezza dove dice la fisica.
 *    Qui a ogni fotogramma resta solo il tachimetro.
 *
 * Due ref arrivano da fuori: `seguitoRef` (il gruppo che la telecamera
 * insegue) e `tachimetroRef` (un elemento HTML dove scrivere i km/h).
 * Il suffisso Ref non è solo stile: il linter (React Compiler) riconosce
 * dal nome che sono ref, e quindi che si possono modificare fuori dal
 * disegno del componente; con un altro nome segnala un errore.
 */

import { Suspense, useEffect, useRef, type RefObject } from "react"
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
import ModellinoProvvisorio from "./ModellinoProvvisorio"
import ModelloVeicolo from "./ModelloVeicolo"
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
  /** Dove guarda alla partenza: angolo attorno a Y in radianti (0 = verso +X). */
  readonly direzione?: number
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
  direzione = 0,
  parametri: p = UTILITARIA,
  seguitoRef,
  tachimetroRef,
}: VeicoloProps) {
  const { world } = useRapier()
  const comandi = useComandi()
  const corpo = useRef<RapierRigidBody>(null)
  const controllerRef = useRef<DynamicRayCastVehicleController | null>(null)
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
    controllerRef.current = c
    return () => {
      world.removeVehicleController(c)
      controllerRef.current = null
    }
  }, [world, p])

  /* Prima di ogni passo fisico: dai comandi alle ruote. */
  useBeforePhysicsStep((mondo) => {
    const c = controllerRef.current
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
      // Rotazione di `direzione` attorno a Y, come quaternione (asse × seno della metà)
      scocca.setRotation(
        { x: 0, y: Math.sin(direzione / 2), z: 0, w: Math.cos(direzione / 2) },
        true,
      )
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

  /* A ogni fotogramma: il tachimetro. */
  useFrame((_, delta) => {
    const c = controllerRef.current
    if (!c) return

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
      rotation={[0, direzione, 0]}
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
        {/* Il modello di cartone; finché non è caricato, le scatole */}
        <Suspense
          fallback={
            <ModellinoProvvisorio parametri={p} controllerRef={controllerRef} />
          }
        >
          <ModelloVeicolo parametri={p} controllerRef={controllerRef} />
        </Suspense>
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
