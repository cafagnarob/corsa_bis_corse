/*
 * Pilota.tsx
 * Tutto quello che serve al giocatore per guidare, uguale in ogni campo:
 * il veicolo, la telecamera che lo insegue, la luce di riempimento e il
 * punto guardato (il dettaglio della città segue il mezzo).
 *
 * I tre componenti condividono un ref, il gruppo disegnato del mezzo: il
 * veicolo lo riempie, telecamera e luce lo seguono. L'ordine conta: prima il
 * veicolo, poi la telecamera, poi la luce (che parte dalla telecamera già
 * spostata in questo fotogramma). Va messo dentro <Physics>.
 */

import { useRef, type RefObject } from "react"
import type { Group } from "three"

import type { Partenza } from "./campi"
import LuceRiempimento from "./LuceRiempimento"

import TelecameraInseguimento from "./TelecameraInseguimento"
import Veicolo from "./Veicolo"
import PuntoGuardato from "./PuntoGuardato"

type PilotaProps = {
  readonly partenza: Partenza
  /** Elemento HTML in cui il veicolo scrive la velocità. */
  readonly tachimetroRef: RefObject<HTMLDivElement | null>
}

function Pilota({ partenza, tachimetroRef }: PilotaProps) {
  const seguitoRef = useRef<Group>(null)

  return (
    <>
      <Veicolo
        partenza={partenza.posizione}
        direzione={partenza.direzione}
        seguitoRef={seguitoRef}
        tachimetroRef={tachimetroRef}
      />
      <TelecameraInseguimento seguitoRef={seguitoRef} />
      <LuceRiempimento seguitoRef={seguitoRef} />
      <PuntoGuardato seguitoRef={seguitoRef} />
    </>
  )
}

export default Pilota
