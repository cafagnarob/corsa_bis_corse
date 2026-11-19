/*
 * LuceRiempimento.tsx
 * Luce di riempimento che accompagna la telecamera in terza persona.
 *
 * Il problema: la luce "della lampada" del Palcoscenico ha una direzione
 * fissa. In terza persona vediamo quasi sempre il retro del mezzo, e quando
 * il mezzo va verso la lampada il retro resta in ombra: il cartone diventa
 * quasi nero.
 *
 * La soluzione, come nei set fotografici: una seconda luce, più debole,
 * che arriva da dietro e sopra la telecamera e punta sul mezzo. Così la
 * faccia che guardiamo è sempre illuminata, e la lampada fissa continua a
 * dare ombre e volume dagli altri lati.
 *
 * Come funziona: è una luce direzionale, cioè con raggi paralleli come il
 * sole; conta solo la direzione, da `position` verso il suo `target`. A ogni
 * fotogramma la posizione va un po' sopra la telecamera e il target sul
 * mezzo. Va messa dopo TelecameraInseguimento, così usa la telecamera già
 * spostata in questo fotogramma.
 */

import { useRef, type RefObject } from "react"
import { useFrame } from "@react-three/fiber"
import { Vector3, type DirectionalLight, type Group } from "three"

import { SCALA } from "./parametri"

/* ------------------------------------------------------------------------
 * Regolazioni (da tarare a occhio)
 * --------------------------------------------------------------------- */

const INTENSITA = 1.8
const COLORE = "#fff6ea" // bianco appena caldo, come la lampada ma più neutro
const SOPRA_TELECAMERA = 6 // metri: la luce scende un po' dall'alto, non piatta

type LuceRiempimentoProps = {
  /** Il mezzo da illuminare. */
  readonly seguitoRef: RefObject<Group | null>
}

function LuceRiempimento({ seguitoRef }: LuceRiempimentoProps) {
  const luceRef = useRef<DirectionalLight>(null)
  const mezzo = useRef(new Vector3()) // vettore di lavoro, riusato

  useFrame(({ camera }) => {
    const luce = luceRef.current
    const g = seguitoRef.current
    if (!luce || !g) return

    g.getWorldPosition(mezzo.current)
    luce.position.copy(camera.position)
    luce.position.y += SOPRA_TELECAMERA * SCALA
    luce.target.position.copy(mezzo.current)
    // Il target non è nella scena: la sua matrice va aggiornata a mano
    luce.target.updateMatrixWorld()
  })

  return <directionalLight ref={luceRef} intensity={INTENSITA} color={COLORE} />
}

export default LuceRiempimento
