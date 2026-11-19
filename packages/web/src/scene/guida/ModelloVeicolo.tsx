/*
 * ModelloVeicolo.tsx
 * Il modello di cartone del mezzo (utilitaria.glb), mosso dalla fisica:
 * ruote che girano, ruote davanti che sterzano, scocca che sta alla giusta
 * altezza sopra le ruote.
 *
 * Il file .glb (GDD, "Formato dell'export"): metri reali, davanti +X,
 * origine a terra, sei LOD. LOD0-LOD2 hanno lo scheletro (Rig) con le ossa
 * di ruote, sterzo e porte; le animazioni sono "slider": non si riproducono,
 * si sceglie il fotogramma.
 * - Ruota: fotogrammi 1-25 = un giro completo di tutte le ruote;
 * - Sterzo: fotogramma 1 = −35°, 2 = dritto, 3 = +35° (positivo = sinistra,
 *   come in Rapier).
 *
 * Come funziona:
 * 1. useGLTF carica il file (sospende finché non arriva: in Veicolo c'è il
 *    Suspense con il modellino provvisorio);
 * 2. si fa una COPIA con SkeletonUtils.clone: clone() normale farebbe
 *    condividere lo scheletro tra le copie, e due mezzi si muoverebbero
 *    insieme. Si tiene solo il LOD0 (in terza persona il mezzo è sempre
 *    vicino), si scala ×5,2 e si regolano i materiali;
 * 3. un AnimationMixer con le clip Ruota e Sterzo in pausa: a ogni
 *    fotogramma si sceglie il loro tempo dai valori del controller di Rapier
 *    e si applica la posa con mixer.update(0);
 * 4. la sospensione: le ossa non hanno un movimento verticale delle ruote,
 *    quindi si alza o si abbassa tutto il modello secondo la sospensione
 *    media. La scocca beccheggia e rolla comunque, perché lo fa il corpo
 *    fisico che la contiene.
 */

import { useEffect, useMemo, useRef, type RefObject } from "react"
import { useFrame } from "@react-three/fiber"
import { useGLTF } from "@react-three/drei"
import {
  AnimationClip,
  AnimationMixer,
  type AnimationAction,
  type Material,
  type Mesh,
  type MeshStandardMaterial,
  type Object3D,
} from "three"
import { clone as cloneConScheletro } from "three/examples/jsm/utils/SkeletonUtils.js"
import type { DynamicRayCastVehicleController } from "@dimforge/rapier3d-compat"

import { INTENSITA_LUCI } from "../mezzi/modelloMezzo"
import { tempoRuota, tempoSterzo } from "./clipVeicolo"
import { SCALA, type ParametriVeicolo } from "./parametri"

const FILE = "/models/mezzi/utilitaria.glb"
const DECODER_DRACO = "/draco/"

/** Nitidezza della texture vista di sbieco, come per gli altri mezzi. */
const ANISOTROPIA = 8

/* ------------------------------------------------------------------------
 * Preparazione del modello (una volta per copia)
 * --------------------------------------------------------------------- */

type ModelloPronto = {
  readonly radice: Object3D
  readonly mixer: AnimationMixer
  readonly ruota: AnimationAction
  readonly sterzo: AnimationAction
}

/** Copia il modello, tiene solo il LOD0, regola i materiali e prepara le clip. */
function preparaModello(scena: Object3D, clip: AnimationClip[]): ModelloPronto {
  const radice = cloneConScheletro(scena)
  radice.scale.setScalar(SCALA)

  radice.traverse((o) => {
    // Solo il LOD0: gli altri LOD servono agli avversari lontani, non qui
    if (/^LOD[1-5]$/.test(o.name)) o.visible = false

    const mesh = o as Mesh
    if (!mesh.isMesh) return
    // Le mesh con lo scheletro si muovono fuori dal loro riquadro di
    // partenza: senza questo, Three.js potrebbe credere che siano fuori
    // schermo e non disegnarle (GDD: frustumCulled = false sulle skinned)
    mesh.frustumCulled = false
    // Copia del materiale: si cambia la copia, non quello in cache di useGLTF
    mesh.material = regolaMateriale(mesh.material as Material)
  })

  const mixer = new AnimationMixer(radice)
  const inPausa = (nome: string) => {
    const c = AnimationClip.findByName(clip, nome)
    if (!c) throw new Error(`Clip "${nome}" mancante in ${FILE}`)
    const azione = mixer.clipAction(c)
    azione.play()
    azione.paused = true // slider: il tempo lo decidiamo noi
    return azione
  }
  return { radice, mixer, ruota: inPausa("Ruota"), sterzo: inPausa("Sterzo") }
}

/** Copia del materiale con luci tarate e texture nitida (come modelloMezzo.ts). */
function regolaMateriale(m: Material): Material {
  const copia = m.clone() as MeshStandardMaterial
  copia.emissiveIntensity = INTENSITA_LUCI
  if (copia.map) copia.map.anisotropy = ANISOTROPIA
  return copia
}

/* ------------------------------------------------------------------------
 * Componente
 * --------------------------------------------------------------------- */

type ModelloVeicoloProps = {
  readonly parametri: ParametriVeicolo
  readonly controllerRef: RefObject<DynamicRayCastVehicleController | null>
}

function ModelloVeicolo({ parametri: p, controllerRef }: ModelloVeicoloProps) {
  const { scene, animations } = useGLTF(FILE, DECODER_DRACO)
  const modello = useMemo(
    () => preparaModello(scene, animations),
    [scene, animations],
  )

  // Le parti da muovere a ogni fotogramma passano da un ref: per React il
  // modello preparato è un valore fisso, quello che cambia è dentro Three.js
  const partiRef = useRef<ModelloPronto | null>(null)
  useEffect(() => {
    partiRef.current = modello
    return () => {
      modello.mixer.stopAllAction() // il modello sparisce: fermiamo le clip
      partiRef.current = null
    }
  }, [modello])

  useFrame(() => {
    const c = controllerRef.current
    const parti = partiRef.current
    if (!c || !parti) return

    // Ruote: la rotazione di una ruota dietro (tutte girano insieme nella clip)
    parti.ruota.time = tempoRuota(c.wheelRotation(2) ?? 0)
    // Sterzo: l'angolo della ruota anteriore sinistra
    parti.sterzo.time = tempoSterzo(c.wheelSteering(0) ?? 0)
    parti.mixer.update(0) // applica la posa dei tempi scelti, senza far avanzare niente

    // Altezza: il centro ruota del modello sta a un raggio da terra; lo
    // portiamo dove la fisica dice che stanno le ruote (attacco − sospensione)
    let sospensione = 0
    for (let i = 0; i < 4; i++)
      sospensione += c.wheelSuspensionLength(i) ?? p.sospensioni.riposo * SCALA
    sospensione /= 4
    parti.radice.position.y =
      p.ruote.attacco * SCALA - sospensione - p.ruote.raggio * SCALA
  })

  return <primitive object={modello.radice} />
}

// Comincia a scaricare il modello subito, prima che serva
useGLTF.preload(FILE, DECODER_DRACO)

export default ModelloVeicolo
