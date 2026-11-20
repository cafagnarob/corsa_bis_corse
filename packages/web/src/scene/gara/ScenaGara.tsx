/*
 * ScenaGara.tsx
 * La gara sul circuito della città (Fase 2 del GDD). Si apre con
 * ?scena=gara (e ?seme=... per un'altra città).
 *
 * Per ora: le tessere del giro e le loro vicine, la fisica, la linea del
 * circuito sulla strada e il pilota sul traguardo. Checkpoint, giri, tempi
 * e avversari arrivano nei passi successivi.
 *
 * Se la città del seme non ha un circuito, al posto della scena c'è un
 * messaggio che invita a provare un altro seme.
 */

import { Suspense, useRef, type CSSProperties } from "react"
import { Physics } from "@react-three/rapier"

import Palcoscenico from "../Palcoscenico"
import CampoCitta from "../guida/CampoCitta"
import { GRAVITA } from "../guida/parametri"
import RiquadroGuida from "../guida/RiquadroGuida"
import { GARA } from "./datiGara"
import LineaGara from "./LineaGara"

const stileMessaggio: CSSProperties = {
  position: "fixed",
  inset: 0,
  display: "grid",
  placeItems: "center",
  padding: 24,
  background: "#1f2b27",
  color: "#e8f0e0",
  font: "16px/1.5 ui-monospace, monospace",
  textAlign: "center",
}

function ScenaGara() {
  const tachimetroRef = useRef<HTMLDivElement>(null)

  if (!GARA)
    return (
      <div style={stileMessaggio}>
        Questa città non ha un circuito. Prova un altro seme, per esempio
        ?scena=gara&seme=roma
      </div>
    )

  return (
    <>
      <Palcoscenico
        telecamera={{ posizione: GARA.partenza.posizione, fov: 55, vicino: 1 }}
      >
        {/* Si aspetta il motore fisico (WebAssembly) e i modelli della città */}
        <Suspense fallback={null}>
          <Physics gravity={[0, -GRAVITA, 0]} timeStep={1 / 60}>
            <CampoCitta
              gruppi={GARA.gruppi}
              trimesh={GARA.trimesh}
              cunei={GARA.cunei}
              centro={GARA.centro}
              partenza={GARA.partenza}
              tachimetroRef={tachimetroRef}
            >
              <LineaGara punti={GARA.linea3d} />
            </CampoCitta>
          </Physics>
        </Suspense>
      </Palcoscenico>

      <RiquadroGuida tachimetroRef={tachimetroRef} />
    </>
  )
}

export default ScenaGara
