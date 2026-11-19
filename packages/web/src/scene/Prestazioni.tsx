/*
 * Prestazioni.tsx
 * Misura per lo sviluppo: FPS, chiamate di disegno, triangoli e geometrie in
 * memoria, aggiornata due volte al secondo.
 *
 * Va messo DENTRO il <Canvas> (legge gl.info a ogni fotogramma con useFrame),
 * ma scrive in un elemento HTML che sta FUORI dal canvas, ricevuto con un ref:
 * così il pannello resta fermo nell'angolo dello schermo. Nessuno stato React:
 * il testo si aggiorna direttamente, senza ridisegnare componenti.
 */

import { useFrame, useThree } from "@react-three/fiber"
import { useRef, type RefObject } from "react"

type PrestazioniProps = { pannelloRef: RefObject<HTMLDivElement | null> }

function Prestazioni({ pannelloRef }: PrestazioniProps) {
  const gl = useThree((s) => s.gl)
  const conteggio = useRef({ fotogrammi: 0, tempo: 0 })

  useFrame((_, delta) => {
    const c = conteggio.current
    c.fotogrammi++
    c.tempo += delta
    if (c.tempo < 0.5 || !pannelloRef.current) return

    // gl.info si azzera a ogni fotogramma: qui contiene i dati del fotogramma precedente
    const { calls, triangles } = gl.info.render
    pannelloRef.current.textContent =
      `FPS          ${Math.round(c.fotogrammi / c.tempo)}\n` +
      `disegni      ${calls}\n` +
      `triangoli    ${triangles.toLocaleString("it-IT")}\n` +
      `geometrie    ${gl.info.memory.geometries}`
    c.fotogrammi = 0
    c.tempo = 0
  })

  return null // non disegna niente nella scena
}

export default Prestazioni
