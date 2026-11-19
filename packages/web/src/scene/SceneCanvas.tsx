/*
 * SceneCanvas.tsx
 * Contenitore della scena 3D di Corsa Bis.
 *
 * Cosa fa:
 * - crea il <Canvas> di React Three Fiber, cioè l'area in cui Three.js disegna;
 * - imposta la telecamera prospettica adatta alle nostre unità (1 unità = 1 m,
 *   tessere con raggio 200);
 * - aggiunge le luci: una luce ambiente debole e una luce direzionale calda e
 *   bassa, come nel GDD (effetto plastico);
 * - aggiunge OrbitControls per ruotare, spostare e zoomare con il mouse;
 * - per ora mostra una griglia di riferimento al posto del tavolo.
 *
 * Convenzione degli assi in Three.js: Y verso l'alto, il tavolo è il piano XZ,
 * +X = est, -Z = nord (come +Y in Blender).
 */

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
import NomiQuartieri, { type NomeDaMostrare } from "./quartieri/NomiQuartieri"
import { quotaSuperiore } from "./tessere/misure"
import Prestazioni from "./Prestazioni"
import { raggruppa } from "./citta/raggruppa"
import CittaIstanziata from "./citta/CittaIstanziata"
import { Suspense, useRef, useState, type CSSProperties } from "react"
import { geometrieQuartieri } from "./quartieri/geometrieQuartieri"
import ConfiniQuartieri from "./quartieri/ConfiniQuartieri"
import AreeQuartieri from "./quartieri/AreeQuartieri"
import { datiVie } from "./vie/datiVie"
import { nuovaSelezione } from "./vie/selezione"
import NomiVie from "./vie/NomiVie"
import EvidenziaVie from "./vie/EvidenziaVie"
import StradeSelezionabili from "./vie/StradeSelezionabili"
import { generaGrafo } from "../../../engine/src/grafo"
import { altezzeTessere } from "./linee/nelMondo"
import { useLinee } from "./linee/useLinee"
import PinFermate from "./linee/PinFermate"
import SpaghiLinee from "./linee/SpaghiLinee"
import SuoloLinee from "./linee/SuoloLinee"
import PannelloLinee from "./linee/PannelloLinee"
import MezziLinee from "./linee/MezziLinee"
import PulsanteCammino from "./camminata/PulsanteCammino"
import Camminata from "./camminata/Camminata"
import { creaNegozioOrologio } from "./tempo/negozioOrologio"
import ErroreScena from "./ErroreScena"
import Tempo from "./tempo/Tempo"
import PannelloTempo from "./tempo/PannelloTempo"
import Simulazione from "./simulazione/Simulazione"
import { creaSimulazione } from "./simulazione/negozioSimulazione"
import AttesaFermate from "./simulazione/AttesaFermate"
import PannelloPasseggeri from "./simulazione/PannelloPasseggeri"
import { creaPasseggeri } from "./simulazione/negozioPasseggeri"
import Pedoni from "./simulazione/Pedoni"

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

const SEME =
  new URLSearchParams(window.location.search).get("seme") ?? "castelfiume"
const CITTA = popolaCitta(generaCitta(SEME))
// Quota delle tessere, per sapere a che altezza appendere i cartellini
const STRATI = new Map(CITTA.tessere.map((t) => [chiave(t.hex), t.strati]))
const RETE = generaStrade(CITTA)
// costanti di modulo, dopo RETE (sostituisci la riga di GRUPPI)
const STRADARIO = generaStradario(CITTA, RETE)
// costanti di modulo
const GRAFO = generaGrafo(CITTA, RETE, STRADARIO)
const ALTEZZE = altezzeTessere(CITTA, RETE)
const GRUPPI = raggruppa(CITTA, RETE, STRADARIO)
// l'orologio del gioco: uno solo, condiviso da scena e pannello
const OROLOGIO = creaNegozioOrologio()
const SIMULAZIONE = creaSimulazione(GRAFO) // usa il nome che ha il tuo grafo
const PASSEGGERI = creaPasseggeri({
  seme: SEME,
  altezze: ALTEZZE,
  citta: CITTA,
  grafo: GRAFO,
  orologio: OROLOGIO,
  simulazione: SIMULAZIONE,
})
const CONTESTO_VIE = { citta: CITTA, rete: RETE, stradario: STRADARIO }
const DATI_VIE = datiVie(CONTESTO_VIE)

// Nomi dei quartieri: calcolati una volta, come la città
const NOMI: NomeDaMostrare[] = CITTA.quartieri.map((q) => ({
  id: q.id,
  nome: q.nome,
  frazione: q.frazione,
  posizione: puntoEtichetta(q.tessere),
}))

const GEOMETRIE_QUARTIERI = geometrieQuartieri(CITTA)

/** Baricentro di un quartiere, sopra la sua tessera più alta. */
function puntoEtichetta(tessere: readonly Hex[]): [number, number, number] {
  const c = tessere.map(centroTessera)
  const x = c.reduce((s, p) => s + p.x, 0) / c.length
  const z = c.reduce((s, p) => s + p.z, 0) / c.length
  const strati = Math.max(...tessere.map((h) => STRATI.get(chiave(h)) ?? 1))
  return [x, quotaSuperiore(strati) + 140, z]
}
function SceneCanvas() {
  const pannello = useRef<HTMLDivElement>(null)
  const selezioneRef = useRef(nuovaSelezione())
  const [linee, invia] = useLinee(GRAFO)
  const [aPiedi, setAPiedi] = useState(false)
  // a piedi niente vie evidenziate: si toglie anche quella cliccata o sotto il mouse
  const cambiaCammino = () => {
    selezioneRef.current.sopra = -1
    selezioneRef.current.fissata = -1
    document.body.style.cursor = "auto"
    setAPiedi((a) => !a)
  }
  const lineaAttiva = linee.linee.linee.find((l) => l.id === linee.attiva)
  return (
    <>
      <ErroreScena>
        <Canvas
          // Neutral: i colori arrivano a schermo come li abbiamo scelti
          // (il predefinito, ACES Filmic, li scurisce e li desatura)
          gl={{ toneMapping: NeutralToneMapping, stencil: true }}
          camera={{ position: [0, 3000, 3600], fov: 40, near: 10, far: 40000 }}
          onPointerMissed={() => {
            selezioneRef.current.fissata = -1
          }}
        >
          {lineaAttiva?.stato === "bozza" && (
            <SuoloLinee
              geometrie={[GRUPPI.strade.asfalto, GRUPPI.strade.marciapiedi]}
              grafo={GRAFO}
              linea={lineaAttiva}
              invia={invia}
            />
          )}
          <Tempo orologio={OROLOGIO} />
          <SpaghiLinee
            linee={linee.linee.linee}
            grafo={GRAFO}
            altezze={ALTEZZE}
          />
          <Simulazione
            linee={linee.linee.linee}
            orologio={OROLOGIO}
            simulazione={SIMULAZIONE}
          />
          <MezziLinee
            grafo={GRAFO}
            altezze={ALTEZZE}
            simulazione={SIMULAZIONE}
            passeggeri={PASSEGGERI}
          />
          <AttesaFermate
            linee={linee.linee.linee}
            grafo={GRAFO}
            altezze={ALTEZZE}
            passeggeri={PASSEGGERI}
            orologio={OROLOGIO}
          />
          <Suspense fallback={null}>
            <Pedoni passeggeri={PASSEGGERI} orologio={OROLOGIO} />
          </Suspense>
          <Suspense fallback={null}>
            <PinFermate
              linee={linee.linee.linee}
              grafo={GRAFO}
              altezze={ALTEZZE}
              invia={invia}
              attiva={linee.attiva}
            />
          </Suspense>

          {/*
        Luce emisferica al posto della luce ambiente:
        args = [colore dall'alto, colore dal basso, intensità].
        Dall'alto una luce chiara e calda, dal basso il riflesso del panno verde:
        le facce in ombra restano leggibili e colorate, non nere.
      */}
          <hemisphereLight args={["#fff4e3", "#4f6a5c", 1.4]} />

          {/* Luce "della lampada": calda ma meno arancione, più forte */}
          <directionalLight
            position={[300, 400, 200]}
            intensity={2.2}
            color="#fff0db"
          />

          {/*
        Tre tessere di prova. Suspense mostra "niente" (fallback null)
        finché le texture del flock non sono caricate.
        Posizioni dalla formula del GDD; nel prossimo passo le calcolerà
        il motore a partire da (q, r).
      */}
          <Suspense fallback={null}>
            <CittaIstanziata gruppi={GRUPPI} />
            {!aPiedi && (
              <StradeSelezionabili
                asfalto={GRUPPI.strade.asfalto}
                viaPerTriangolo={GRUPPI.viaPerTriangolo}
                selezioneRef={selezioneRef}
              />
            )}
            <EvidenziaVie contesto={CONTESTO_VIE} selezioneRef={selezioneRef} />
            <NomiVie
              vie={DATI_VIE}
              collegate={STRADARIO.collegate}
              selezioneRef={selezioneRef}
            />
            <NomiQuartieri nomi={NOMI} />
          </Suspense>
          <ConfiniQuartieri geometria={GEOMETRIE_QUARTIERI.contorni} />
          <AreeQuartieri aree={GEOMETRIE_QUARTIERI.aree} />
          {/*
        Controlli della telecamera con il mouse, con limiti:
        - maxPolarAngle: quanto la telecamera può scendere verso l'orizzonte.
          0 = guarda dritto dall'alto, Math.PI / 2 = rasoterra.
          Ci fermiamo poco sopra l'orizzonte, così non si va mai sotto il tavolo.
        - minPolarAngle: 0 lascia arrivare alla vista dall'alto (utile per la vista 2D).
        - minDistance / maxDistance: limiti dello zoom, in metri.
      */}
          <OrbitControls
            makeDefault
            enabled={!aPiedi}
            maxPolarAngle={Math.PI / 2 - 0.15}
            minPolarAngle={0}
            minDistance={50}
            maxDistance={15000}
          />
          {aPiedi && <Camminata altezze={ALTEZZE} />}
          <Prestazioni pannelloRef={pannello} />
        </Canvas>
      </ErroreScena>
      {/* fuori dal canvas: un normale elemento HTML fisso nell'angolo */}
      <div ref={pannello} style={stilePannello} />
      <PannelloLinee stato={linee} grafo={GRAFO} invia={invia} />
      <PulsanteCammino aPiedi={aPiedi} cambia={cambiaCammino} />
      <PannelloTempo orologio={OROLOGIO} />
      <PannelloPasseggeri linee={linee.linee.linee} passeggeri={PASSEGGERI} />
    </>
  )
}

export default SceneCanvas
