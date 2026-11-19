/*
 * ScenaCitta.tsx
 * La città intera vista dall'alto, da esplorare con il mouse: tessere,
 * strade, edifici, vegetazione e la vista mappa dei quartieri.
 *
 * Usa il Palcoscenico per Canvas e luci; i dati arrivano già pronti da
 * datiCitta.ts e datiQuartieri.ts, quindi qui c'è solo il disegno.
 * La telecamera è OrbitControls; quella in terza persona sta nella scena
 * della guida.
 */

import { Suspense } from "react"
import { OrbitControls } from "@react-three/drei"

import Palcoscenico from "../Palcoscenico"
import CittaIstanziata from "./CittaIstanziata"
import { GRUPPI } from "./datiCitta"
import NomiQuartieri from "../quartieri/NomiQuartieri"
import ConfiniQuartieri from "../quartieri/ConfiniQuartieri"
import AreeQuartieri from "../quartieri/AreeQuartieri"
import { GEOMETRIE_QUARTIERI, NOMI } from "../quartieri/datiQuartieri"

function ScenaCitta() {
  return (
    <Palcoscenico>
      {/*
        Suspense non mostra nulla (fallback null) finché modelli e texture
        della città e dei nomi non sono caricati.
      */}
      <Suspense fallback={null}>
        <CittaIstanziata gruppi={GRUPPI} />
        <NomiQuartieri nomi={NOMI} />
      </Suspense>

      {/* Vista mappa: confini e aree compaiono solo da lontano */}
      <ConfiniQuartieri geometria={GEOMETRIE_QUARTIERI.contorni} />
      <AreeQuartieri aree={GEOMETRIE_QUARTIERI.aree} />

      {/*
        Controlli della telecamera con il mouse:
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
    </Palcoscenico>
  )
}

export default ScenaCitta
