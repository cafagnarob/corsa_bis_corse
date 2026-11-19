/*
 * ScenaProvaGuida.tsx
 * Scena di prova della Fase 1 del GDD: qui si rende divertente guidare
 * l'utilitaria, prima di metterla nella città. Si apre con ?scena=guida.
 *
 * Cosa c'è:
 * - il mondo fisico di Rapier (<Physics>), con la gravità in unità di gioco
 *   e un passo fisso di 1/60 di secondo;
 * - un pavimento piatto di circa 385 × 385 m con una griglia: le linee che
 *   scorrono sotto il mezzo fanno capire la velocità;
 * - una rampa per provare salti e atterraggi;
 * - qualche scatola di cartone da spingere, per provare gli urti;
 * - il veicolo, la telecamera che lo insegue e una luce di riempimento che
 *   accompagna la telecamera (il retro del mezzo non resta mai in ombra);
 * - fuori dal Canvas, un riquadro con i comandi e il tachimetro.
 *
 * Non importa niente da datiCitta.ts: la città non viene generata.
 */

import { Suspense, useRef, type CSSProperties } from "react"
import { CuboidCollider, Physics, RigidBody } from "@react-three/rapier"
import type { Group } from "three"

import Palcoscenico from "../Palcoscenico"
import LuceRiempimento from "./LuceRiempimento"
import TelecameraInseguimento from "./TelecameraInseguimento"
import Veicolo from "./Veicolo"
import { GRAVITA, SCALA } from "./parametri"

/* ------------------------------------------------------------------------
 * Misure del campo di prova, in unità di gioco
 * --------------------------------------------------------------------- */

const LATO_PAVIMENTO = 2000 // circa 385 m
const PARTENZA: [number, number, number] = [0, 8, 0]

// Rampa: una scatola inclinata, metà affondata nel pavimento
const RAMPA = {
  posizione: [260, 0, 0] as [number, number, number],
  inclinazione: (12 * Math.PI) / 180, // 12° di salita
  mezzeMisure: [60, 6, 40] as [number, number, number], // 120 × 12 × 80 unità
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

/* ------------------------------------------------------------------------
 * Riquadro dei comandi (HTML fuori dal Canvas)
 * In basso al centro, stretto: su schermi piccoli va a capo e resta leggibile.
 * --------------------------------------------------------------------- */

const stileRiquadro: CSSProperties = {
  position: "fixed",
  bottom: 12,
  left: "50%",
  transform: "translateX(-50%)",
  maxWidth: "calc(100vw - 24px)",
  padding: "8px 14px",
  background: "rgba(20, 30, 28, 0.8)",
  color: "#e8f0e0",
  font: "13px/1.5 ui-monospace, monospace",
  borderRadius: 6,
  textAlign: "center",
  pointerEvents: "none",
}

const stileTachimetro: CSSProperties = { fontSize: 22, fontWeight: 700 }

/* ------------------------------------------------------------------------
 * Componente
 * --------------------------------------------------------------------- */

function ScenaProvaGuida() {
  const seguito = useRef<Group>(null)
  const tachimetro = useRef<HTMLDivElement>(null)

  return (
    <>
      <Palcoscenico
        telecamera={{ posizione: [-40, 20, 0], fov: 55, vicino: 1 }}
      >
        {/* Physics scarica il motore fisico (WebAssembly): finché non è pronto, niente */}
        <Suspense fallback={null}>
          <Physics gravity={[0, -GRAVITA, 0]} timeStep={1 / 60}>
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
                args={[
                  LATO_PAVIMENTO,
                  LATO_PAVIMENTO / 20,
                  "#5d6b52",
                  "#76866a",
                ]}
                position={[0, 0.05, 0]}
              />
            </RigidBody>

            {/* Rampa: si sale verso +X */}
            <RigidBody
              type="fixed"
              position={RAMPA.posizione}
              rotation={[0, 0, RAMPA.inclinazione]}
            >
              <mesh>
                <boxGeometry
                  args={
                    RAMPA.mezzeMisure.map((m) => m * 2) as [
                      number,
                      number,
                      number,
                    ]
                  }
                />
                <meshStandardMaterial color="#b89a6a" />
              </mesh>
            </RigidBody>

            {/* Scatole di cartone: corpi dinamici leggeri */}
            {SCATOLE.map((posizione, i) => (
              <RigidBody key={i} position={posizione} mass={20}>
                <mesh>
                  <boxGeometry
                    args={[LATO_SCATOLA, LATO_SCATOLA, LATO_SCATOLA]}
                  />
                  <meshStandardMaterial color="#c8a97e" />
                </mesh>
              </RigidBody>
            ))}

            <Veicolo
              partenza={PARTENZA}
              seguitoRef={seguito}
              tachimetroRef={tachimetro}
            />

            {/* Dopo il veicolo e dentro Physics: segue la posizione già aggiornata */}
            <TelecameraInseguimento seguitoRef={seguito} />
            {/* Dopo la telecamera: la luce parte da dove la telecamera è appena arrivata */}
            <LuceRiempimento seguitoRef={seguito} />
          </Physics>
        </Suspense>
      </Palcoscenico>

      <div style={stileRiquadro}>
        <div ref={tachimetro} style={stileTachimetro}>
          0 km/h
        </div>
        WASD o frecce · Spazio freno a mano · R ripristino
      </div>
    </>
  )
}

export default ScenaProvaGuida
