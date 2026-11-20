/*
 * Palcoscenico.tsx
 * La base comune di tutte le scene 3D di Corsa Bis: crea il <Canvas> di React
 * Three Fiber con le luci del plastico, il controllo degli errori e il pannello
 * delle prestazioni. Il contenuto (città, scena di prova della guida, …) arriva
 * da fuori come `children`.
 *
 * Perché un componente a parte: la città e la scena di prova della guida
 * vogliono la stessa luce, la stessa resa dei colori e lo stesso pannello, ma
 * contenuti diversi. Così le impostazioni del Canvas stanno in un posto solo.
 *
 * Convenzione degli assi in Three.js: Y verso l'alto, il tavolo è il piano XZ,
 * +X = est, -Z = nord (come +Y in Blender).
 */

import { useRef, type CSSProperties, type ReactNode } from "react"
import { Canvas } from "@react-three/fiber"
import { NeutralToneMapping } from "three"

import ErroreScena from "./ErroreScena"
import Prestazioni from "./Prestazioni"

/* ------------------------------------------------------------------------
 * Telecamera iniziale
 * Ogni scena può scegliere da dove parte la telecamera; i valori predefiniti
 * vanno bene per la città vista dall'alto. La scena della guida poi la muove
 * da sola (telecamera in terza persona).
 * --------------------------------------------------------------------- */

export type TelecameraIniziale = {
  readonly posizione: readonly [number, number, number]
  readonly fov?: number // apertura verticale, in gradi
  readonly vicino?: number // piano vicino: sotto questa distanza non si disegna
  readonly lontano?: number // piano lontano: oltre questa distanza non si disegna
}

const TELECAMERA_PREDEFINITA: TelecameraIniziale = {
  posizione: [0, 3000, 3600],
  fov: 40,
  vicino: 10,
  lontano: 40000,
}

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

type PalcoscenicoProps = {
  readonly children: ReactNode
  readonly telecamera?: TelecameraIniziale
}

function Palcoscenico({
  children,
  telecamera = TELECAMERA_PREDEFINITA,
}: PalcoscenicoProps) {
  const pannello = useRef<HTMLDivElement>(null)
  const { posizione, fov = 40, vicino = 10, lontano = 40000 } = telecamera

  return (
    <>
      <ErroreScena>
        <Canvas
          // risoluzione: al massimo 1,5 pixel veri per pixel CSS. Sugli
          // schermi ad alta densità (2× o più) i pixel da colorare sarebbero
          // quasi il doppio, per una differenza che a schermo quasi non si vede.
          dpr={[1, 1.5]}
          // Neutral: i colori arrivano a schermo come li abbiamo scelti
          // (il predefinito, ACES Filmic, li scurisce e li desatura).
          gl={{ toneMapping: NeutralToneMapping }}
          camera={{
            position: [...posizione],
            fov,
            near: vicino,
            far: lontano,
          }}
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

          {children}

          <Prestazioni pannelloRef={pannello} />
        </Canvas>
      </ErroreScena>

      <div ref={pannello} style={stilePannello} />
    </>
  )
}

export default Palcoscenico
