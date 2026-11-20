/*
 * datiGara.ts
 * Tutto quello che serve per correre sul circuito della città, calcolato
 * una volta dal seme (?seme=..., come per la città):
 * - la città, la rete, il grafo stradale;
 * - il circuito (motore: generaCircuito) e il suo tracciato con linea,
 *   traiettoria e checkpoint (motore: tracciatoGara), con le larghezze
 *   delle carreggiate prese dai profili delle strade disegnate;
 * - le tessere da disegnare: quelle del giro più le loro vicine, così ai
 *   lati della pista ci sono sempre edifici e non il vuoto;
 * - disegno raggruppato, forme per la fisica e partenza sul traguardo.
 *
 * Se la città non ha un circuito, GARA vale null e la scena lo dice.
 */

import {
  centroTessera,
  chiave,
  generaCircuito,
  generaCitta,
  generaGrafo,
  generaStradario,
  generaStrade,
  popolaCitta,
  tracciatoGara,
  OPZIONI_TRACCIATO,
  vicine,
  type CittaPopolata,
  type TracciatoGara,
} from "@corsa-bis/engine"

import { raggruppa } from "../citta/raggruppa"
import type { Partenza } from "../guida/campi"
import {
  puntiRampa,
  trimeshTessere,
  type Trimesh,
} from "../guida/collisioniTessere"
import { altezzeTessere, campione, quotaNelPunto } from "../strade/nelMondo"
import { PROFILO, QUOTE } from "../strade/profili"
import { tesseraSotto } from "../tessere/lod"

export type DatiGara = {
  readonly seme: string
  readonly tracciato: TracciatoGara
  readonly gruppi: ReturnType<typeof raggruppa>
  readonly trimesh: Trimesh
  readonly cunei: readonly Float32Array[]
  readonly centro: { readonly x: number; readonly z: number }
  readonly partenza: Partenza
  /** La mezzeria del giro in 3D, appena sopra l'asfalto (per disegnarla). */
  readonly linea3d: readonly [number, number, number][]
}

/** Di quanto la linea del giro sta sopra l'asfalto. */
const SOPRA_ASFALTO = 0.6

function preparaGara(seme: string): DatiGara | null {
  const citta = popolaCitta(generaCitta(seme))
  const rete = generaStrade(citta)
  const stradario = generaStradario(citta, rete)
  const grafo = generaGrafo(citta, rete, stradario)
  const circuito = generaCircuito(grafo, seme)
  if (!circuito) return null

  const tracciato = tracciatoGara(grafo, circuito, {
    ...OPZIONI_TRACCIATO,
    mezzaCarreggiata: {
      viale: PROFILO.viale.carreggiata / 2,
      urbana: PROFILO.urbana.carreggiata / 2,
      stretta: PROFILO.stretta.carreggiata / 2,
    },
  })

  // Tessere del giro e loro vicine (solo quelle che esistono)
  const esistono = new Set(citta.tessere.map((t) => chiave(t.hex)))
  const scelte = new Set<string>()
  for (const h of circuito.tessere)
    for (const v of [h, ...vicine(h)])
      if (esistono.has(chiave(v))) scelte.add(chiave(v))
  const ridotta: CittaPopolata = {
    ...citta,
    tessere: citta.tessere.filter((t) => scelte.has(chiave(t.hex))),
  }

  const strati = new Map(ridotta.tessere.map((t) => [chiave(t.hex), t.strati]))
  const altezze = altezzeTessere(citta, rete)

  // Partenza sul traguardo, nel verso di marcia
  const p = campione(
    grafo,
    altezze,
    circuito.traguardo,
    circuito.traguardo.verso ?? 1,
    0,
  )
  const partenza: Partenza = {
    posizione: [p.p[0], p.p[1] + QUOTE.carreggiata + 8, p.p[2]],
    direzione: Math.atan2(-p.dz, p.dx),
  }

  const centri = circuito.tessere.map(centroTessera)
  return {
    seme,
    tracciato,
    gruppi: raggruppa(ridotta, rete, stradario),
    trimesh: trimeshTessere(ridotta.tessere),
    cunei: rete.rampe
      .filter((r) => scelte.has(chiave(r.hex)))
      .map((r) => puntiRampa(r, strati.get(chiave(r.hex)) ?? 1)),
    centro: {
      x: centri.reduce((s, c) => s + c.x, 0) / centri.length,
      z: centri.reduce((s, c) => s + c.z, 0) / centri.length,
    },
    partenza,
    linea3d: tracciato.linea.map((q) => [
      q.x,
      quotaNelPunto(altezze, chiave(tesseraSotto(q.x, q.z)), q.x, q.z) +
        QUOTE.carreggiata +
        SOPRA_ASFALTO,
      q.z,
    ]),
  }
}

const SEME =
  new URLSearchParams(window.location.search).get("seme") ?? "castelfiume"

/** I dati della gara per il seme dell'indirizzo, o null se non c'è un circuito. */
export const GARA = preparaGara(SEME)
