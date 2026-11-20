/*
 * ScenaProvaGuida.tsx
 * Scena di prova della Fase 1 del GDD: qui si rende divertente guidare,
 * prima di portare il mezzo nella città. Si apre con ?scena=guida.
 *
 * Due campi di prova, scelti dall'indirizzo (campi.ts):
 *   ?scena=guida                 CampoPiano: pavimento, rampa, scatole
 *   ?scena=guida&prova=tessere   CampoTessere: tre tessere vere con una rampa
 *
 * Qui stanno le parti comuni: il Palcoscenico, il mondo fisico di Rapier
 * (<Physics>, gravità in unità di gioco, passo fisso di 1/60 di secondo) e,
 * fuori dal Canvas, il riquadro con tachimetro e comandi (RiquadroGuida). Il campo porta il
 * suo suolo, i suoi oggetti e il pilota.
 *
 * I campi sono caricati con lazy(), come le scene in App.tsx: aprendo il
 * piano non si genera la città delle tessere.
 */

import { lazy, Suspense, useRef } from "react"
import { Physics } from "@react-three/rapier"

import Palcoscenico from "../Palcoscenico"
import { campoDallIndirizzo, type NomeCampo } from "./campi"
import { GRAVITA } from "./parametri"
import RiquadroGuida from "./RiquadroGuida"

const CAMPI = {
  piano: lazy(() => import("./CampoPiano")),
  tessere: lazy(() => import("./CampoTessere")),
} satisfies Record<NomeCampo, unknown>

// Letto una volta: cambiare campo vuol dire cambiare indirizzo e ricaricare
const Campo = CAMPI[campoDallIndirizzo()]

/* ------------------------------------------------------------------------
 * Componente
 * --------------------------------------------------------------------- */

function ScenaProvaGuida() {
  const tachimetroRef = useRef<HTMLDivElement>(null)

  return (
    <>
      <Palcoscenico
        telecamera={{ posizione: [-40, 20, 0], fov: 55, vicino: 1 }}
      >
        {/* Si aspetta il motore fisico (WebAssembly) e i file del campo */}
        <Suspense fallback={null}>
          <Physics gravity={[0, -GRAVITA, 0]} timeStep={1 / 60}>
            <Campo tachimetroRef={tachimetroRef} />
          </Physics>
        </Suspense>
      </Palcoscenico>

      <RiquadroGuida tachimetroRef={tachimetroRef} />
    </>
  )
}

export default ScenaProvaGuida
