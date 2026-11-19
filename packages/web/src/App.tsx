/*
 * App.tsx
 * Componente radice di Corsa Bis: sceglie quale scena mostrare a tutto
 * schermo leggendo l'indirizzo.
 *
 *   /                  la città intera (ScenaCitta)
 *   /?scena=guida      la scena di prova della guida (ScenaProvaGuida)
 *   /?seme=barletta    la città generata da un altro seme
 *
 * Le scene sono caricate con lazy(): il file di una scena viene scaricato ed
 * eseguito solo quando serve. Così aprendo la prova della guida la città non
 * viene nemmeno generata (datiCitta.ts calcola tutto appena viene importato).
 * Suspense mostra il fallback mentre il file della scena arriva.
 */

import { lazy, Suspense } from "react"

const ScenaCitta = lazy(() => import("./scene/citta/ScenaCitta"))
const ScenaProvaGuida = lazy(() => import("./scene/guida/ScenaProvaGuida"))

/** Le scene disponibili, per nome nell'indirizzo. */
const SCENE = {
  citta: ScenaCitta,
  guida: ScenaProvaGuida,
} as const

type NomeScena = keyof typeof SCENE

/** Il nome della scena dall'indirizzo; un nome sconosciuto porta alla città. */
function scenaDallIndirizzo(): NomeScena {
  const nome = new URLSearchParams(window.location.search).get("scena")
  return nome !== null && nome in SCENE ? (nome as NomeScena) : "citta"
}

// Letta una volta: cambiare scena vuol dire cambiare indirizzo e ricaricare
const Scena = SCENE[scenaDallIndirizzo()]

function App() {
  return (
    <Suspense fallback={null}>
      <Scena />
    </Suspense>
  )
}

export default App
