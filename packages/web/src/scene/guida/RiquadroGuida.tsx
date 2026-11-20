/*
 * RiquadroGuida.tsx
 * Il riquadro HTML in basso al centro, fuori dal Canvas: tachimetro (il
 * veicolo ci scrive dentro tramite il ref, senza passare dallo stato React)
 * e promemoria dei comandi. Stretto e centrato: su schermi piccoli il testo
 * va a capo e resta leggibile.
 */

import type { CSSProperties, RefObject } from "react"

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

type RiquadroGuidaProps = {
  readonly tachimetroRef: RefObject<HTMLDivElement | null>
}

function RiquadroGuida({ tachimetroRef }: RiquadroGuidaProps) {
  return (
    <div style={stileRiquadro}>
      <div ref={tachimetroRef} style={stileTachimetro}>
        0 km/h
      </div>
      WASD o frecce · Spazio freno a mano · R ripristino
    </div>
  )
}

export default RiquadroGuida
