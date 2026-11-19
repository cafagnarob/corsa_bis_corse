/*
 * SceneCanvas.tsx
 * Contenitore della scena 3D di Corsa Bis (versione corse).
 *
 * Cosa fa:
 * - genera la città una volta sola, a livello di modulo, dal seme letto
 *   nell'indirizzo (?seme=...); stesso seme, stessa città;
 * - crea il <Canvas> di React Three Fiber, cioè l'area in cui Three.js disegna;
 * - imposta la telecamera prospettica per le unità di gioco (scala grafica ×5,2,
 *   tessere con raggio 200 unità);
 * - aggiunge le luci del plastico: luce emisferica e luce direzionale calda;
 * - disegna la città (tessere, strade, edifici, vegetazione) e la vista mappa
 *   dei quartieri (nomi, confini e aree, visibili solo da lontano);
 * - per ora usa OrbitControls: la telecamera in terza persona dietro il mezzo
 *   arriverà con il prototipo di guida (Fase 1 del GDD).
 *
 * Convenzione degli assi in Three.js: Y verso l'alto, il tavolo è il piano XZ,
 * +X = est, -Z = nord (come +Y in Blender).
 */

import { Suspense, useRef, type CSSProperties } from "react"
import { Canvas } from "@react-three/fiber"
import { OrbitControls } from "@react-three/drei"
import { NeutralToneMapping } from "three"

import {
  centroTessera,
  chiave,
  generaCitta,
  generaStradario,
  generaStrade,
  popolaCitta,
  type Hex,
} from "@corsa-bis/engine"

import ErroreScena from "./ErroreScena"
import Prestazioni from "./Prestazioni"
import CittaIstanziata from "./citta/CittaIstanziata"
import { raggruppa } from "./citta/raggruppa"
import { quotaSuperiore } from "./tessere/misure"
import NomiQuartieri, { type NomeDaMostrare } from "./quartieri/NomiQuartieri"
import ConfiniQuartieri from "./quartieri/ConfiniQuartieri"
import AreeQuartieri from "./quartieri/AreeQuartieri"
import { geometrieQuartieri } from "./quartieri/geometrieQuartieri"

/* ------------------------------------------------------------------------
 * Dati della città
 * Calcolati una volta sola, quando il modulo viene caricato: non dipendono
 * da React e non cambiano durante la partita. L'ordine conta, perché ogni
 * passo usa il risultato del precedente.
 * --------------------------------------------------------------------- */

const SEME =
  new URLSearchParams(window.location.search).get("seme") ?? "castelfiume"

const CITTA = popolaCitta(generaCitta(SEME)) // forma, quartieri, tipi e nomi
const RETE = generaStrade(CITTA) // rete stradale gerarchica
const STRADARIO = generaStradario(CITTA, RETE) // vie e loro nomi
const GRUPPI = raggruppa(CITTA, RETE, STRADARIO) // tutto in InstancedMesh per tipo

/* ------------------------------------------------------------------------
 * Quartieri (vista mappa)
 * Per ogni quartiere: nome e punto in cui appendere l'etichetta, più le
 * geometrie di confini e aree.
 * --------------------------------------------------------------------- */

// Strati di ogni tessera, per sapere a che altezza appendere i cartellini
const STRATI = new Map(CITTA.tessere.map((t) => [chiave(t.hex), t.strati]))

/** Baricentro di un quartiere, 140 unità sopra la sua tessera più alta. */
function puntoEtichetta(tessere: readonly Hex[]): [number, number, number] {
  const centri = tessere.map(centroTessera)
  const x = centri.reduce((s, p) => s + p.x, 0) / centri.length
  const z = centri.reduce((s, p) => s + p.z, 0) / centri.length
  const strati = Math.max(...tessere.map((h) => STRATI.get(chiave(h)) ?? 1))
  return [x, quotaSuperiore(strati) + 140, z]
}

const NOMI: NomeDaMostrare[] = CITTA.quartieri.map((q) => ({
  id: q.id,
  nome: q.nome,
  frazione: q.frazione,
  posizione: puntoEtichetta(q.tessere),
}))

const GEOMETRIE_QUARTIERI = geometrieQuartieri(CITTA)

/* ------------------------------------------------------------------------
 * Pannello delle prestazioni
 * Elemento HTML fisso nell'angolo, fuori dal Canvas: Prestazioni ci scrive
 * dentro direttamente, senza passare dallo stato React.
 * --------------------------------------------------------------------- */

const stilePannello: CSSProperties = {
  position: "fixed",
  top: 8,
  left: 8,
  padding: "6px 10px",
  background: "rgba(20, 30, 28, 0.8)",
  color: "#e8f0e0",
  font: "12px/1.5 ui-monospace, monospace",
  borderRadius: 4,
  pointerEvents: "none",
  whiteSpace: "pre",
}

/* ------------------------------------------------------------------------
 * Componente
 * --------------------------------------------------------------------- */

function SceneCanvas() {
  const pannello = useRef<HTMLDivElement>(null)

  return (
    <>
      <ErroreScena>
        <Canvas
          // Neutral: i colori arrivano a schermo come li abbiamo scelti
          // (il predefinito, ACES Filmic, li scurisce e li desatura).
          gl={{ toneMapping: NeutralToneMapping }}
          camera={{ position: [0, 3000, 3600], fov: 40, near: 10, far: 40000 }}
        >
          {/*
            Luce emisferica al posto della luce ambiente:
            args = [colore dall'alto, colore dal basso, intensità].
            Dall'alto una luce chiara e calda, dal basso il riflesso del panno
            verde: le facce in ombra restano leggibili e colorate, non nere.
          */}
          <hemisphereLight args={["#fff4e3", "#4f6a5c", 1.4]} />

          {/* Luce "della lampada": calda, bassa e forte */}
          <directionalLight
            position={[300, 400, 200]}
            intensity={2.2}
            color="#fff0db"
          />

          {/*
            Suspense non mostra nulla (fallback null) finché modelli e
            texture della città e dei nomi non sono caricati.
          */}
          <Suspense fallback={null}>
            <CittaIstanziata gruppi={GRUPPI} />
            <NomiQuartieri nomi={NOMI} />
          </Suspense>

          {/* Vista mappa: confini e aree compaiono solo da lontano */}
          <ConfiniQuartieri geometria={GEOMETRIE_QUARTIERI.contorni} />
          <AreeQuartieri aree={GEOMETRIE_QUARTIERI.aree} />

          {/*
            Telecamera provvisoria, controllata con il mouse:
            - maxPolarAngle: quanto può scendere verso l'orizzonte
              (0 = dall'alto, Math.PI / 2 = rasoterra); ci fermiamo poco sopra,
              così non si va mai sotto il tavolo;
            - minPolarAngle: 0 permette la vista dall'alto;
            - minDistance / maxDistance: limiti dello zoom, in unità di gioco.
          */}
          <OrbitControls
            makeDefault
            maxPolarAngle={Math.PI / 2 - 0.15}
            minPolarAngle={0}
            minDistance={50}
            maxDistance={15000}
          />

          <Prestazioni pannelloRef={pannello} />
        </Canvas>
      </ErroreScena>

      <div ref={pannello} style={stilePannello} />
    </>
  )
}

export default SceneCanvas
