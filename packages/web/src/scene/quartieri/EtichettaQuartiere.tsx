/*
 * EtichettaQuartiere.tsx
 * Cartellino con il nome di un quartiere, sospeso sopra il suo centro
 * (GDD, lente Quartieri: "il nome al centro").
 *
 * Usa <Html> di drei: un normale elemento HTML che segue un punto della scena
 * 3D. Il testo resta nitido a qualsiasi zoom e si scrive con il CSS.
 */

import { Html } from "@react-three/drei"
import type { CSSProperties } from "react"

type EtichettaQuartiereProps = {
  nome: string
  posizione: [number, number, number]
  frazione?: boolean
}

// Stile da cartellino di cartone
const stile: CSSProperties = {
  padding: "4px 10px",
  background: "#f3e6cc",
  border: "2px solid #8a6a45",
  borderRadius: 4,
  color: "#3d2e1f",
  font: "600 13px/1.2 system-ui, sans-serif",
  whiteSpace: "nowrap",
  boxShadow: "0 2px 0 rgba(0,0,0,0.25)",
  pointerEvents: "none", // non blocca il mouse sulla scena
  userSelect: "none",
}

function EtichettaQuartiere({
  nome,
  posizione,
  frazione = false,
}: EtichettaQuartiereProps) {
  return (
    <Html position={posizione} center>
      <div style={stile}>
        {nome}
        {frazione && <span style={{ fontWeight: 400 }}> · frazione</span>}
      </div>
    </Html>
  )
}

export default EtichettaQuartiere
