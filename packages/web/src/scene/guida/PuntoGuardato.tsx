/*
 * PuntoGuardato.tsx
 * Fa seguire il mezzo ai livelli di dettaglio della città.
 *
 * Il problema: tessere, monumenti (useTesseraGuardata) ed edifici montati
 * col kit (KitEdifici) decidono cosa disegnare in dettaglio guardando il
 * "target" dei controlli della telecamera (`controls.target` di React Three
 * Fiber), cioè il punto attorno a cui girano gli OrbitControls. In guida gli
 * OrbitControls non ci sono, quindi il dettaglio restava fermo nell'origine.
 *
 * La soluzione, senza toccare quei componenti: si registra come `controls`
 * un piccolo oggetto con solo il campo `target`, e a ogni fotogramma si
 * mette il target sul mezzo. Per la città il "punto guardato" diventa così
 * il mezzo del giocatore.
 *
 * Va messo dentro <Physics>, dopo il veicolo (usa la posizione già
 * aggiornata in questo fotogramma).
 */

import { useEffect, useRef, type RefObject } from "react"
import { useFrame, useThree } from "@react-three/fiber"
import { Vector3, type Group } from "three"

type PuntoGuardatoProps = {
  /** Il gruppo da seguire: il mezzo disegnato. */
  readonly seguitoRef: RefObject<Group | null>
}

function PuntoGuardato({ seguitoRef }: PuntoGuardatoProps) {
  const set = useThree((s) => s.set)
  const controlliRef = useRef({ target: new Vector3() })

  // Registrazione dei finti controlli: è lo stato di React Three Fiber, un
  // sistema esterno a questo componente; alla fine si tolgono
  useEffect(() => {
    // R3F si aspetta un oggetto di Three.js: a chi legge serve solo il target
    set({ controls: controlliRef.current as never })
    return () => set({ controls: null })
  }, [set])

  useFrame(() => {
    seguitoRef.current?.getWorldPosition(controlliRef.current.target)
  })

  return null
}

export default PuntoGuardato
