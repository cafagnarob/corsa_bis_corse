/*
 * rampe.test.ts
 * Rampe tra tessere di quota diversa: dove stanno, quanto alzano i punti
 * e la strada della tessera bassa che si ferma dove comincia la rampa.
 */

import {
  centroTessera,
  chiave,
  generaCitta,
  generaStrade,
  popolaCitta,
  puntoLato,
  tracciatoTessera,
  versoInterno,
  vicina,
  type Connettore,
  type Rampa,
} from "@corsa-bis/engine"
import { describe, expect, it } from "vitest"
import { PASSO_STRATO } from "../tessere/misure"
import { costruisciStrade } from "./costruisciStrade"
import { lunghezzaRampa, quotaRampa } from "./rampe"

const citta = popolaCitta(generaCitta("castelfiume"))
const rete = generaStrade(citta)
const strati = new Map(citta.tessere.map((t) => [chiave(t.hex), t.strati]))

describe("rampe", () => {
  it("stanno nella tessera bassa, su un lato con strada, con un salto di 1 o 2 strati", () => {
    const rampe = rete.rampe
    expect(rampe.length).toBeGreaterThan(0)
    for (const r of rampe) {
      expect(rete.connettori.get(chiave(r.hex))![r.lato]).toBe(r.classe)
      expect(
        strati.get(chiave(vicina(r.hex, r.lato)))! - strati.get(chiave(r.hex))!,
      ).toBe(r.salto)
      expect(rete.rettilinei.get(chiave(r.hex))![r.lato]).toBe(
        lunghezzaRampa(r.salto),
      )
    }
  })

  it("dove c’è la rampa la strada parte dal lato con un rettilineo, anche se poi curva (innesto su un viale)", () => {
    // viale passante 0 → 3 e una urbana che si innesta dal lato 1, con la rampa sul lato 1
    const connettori: Connettore[] = [
      "viale",
      "urbana",
      "nessuna",
      "viale",
      "nessuna",
      "nessuna",
    ]
    const L = lunghezzaRampa(1)
    const innesto = tracciatoTessera(connettori, null, [
      0,
      L,
      0,
      0,
      0,
      0,
    ]).tratti.find((t) => t.lato === 1)!
    const p0 = puntoLato(1)
    const d = versoInterno(1)
    for (const p of innesto.punti) {
      const lungo = (p.x - p0.x) * d.x + (p.z - p0.z) * d.z // distanza dal lato verso l'interno
      if (lungo > L) continue
      // nei primi 61: sull'asse della rampa, diretto verso l'interno
      expect(Math.abs((p.x - p0.x) * -d.z + (p.z - p0.z) * d.x)).toBeLessThan(
        1e-6,
      )
      expect(p.tx * d.x + p.tz * d.z).toBeCloseTo(1, 6)
    }
  })

  it("alzano di tutto il dislivello sul lato, di niente in fondo e fuori dall’impronta", () => {
    const r: Rampa = {
      hex: { q: 2, r: -1 },
      lato: 1,
      classe: "urbana",
      salto: 2,
    }
    const c = centroTessera(r.hex)
    const l = puntoLato(r.lato)
    const verso = {
      x: -l.x / Math.hypot(l.x, l.z),
      z: -l.z / Math.hypot(l.x, l.z),
    } // dal lato verso il centro
    const punto = (d: number) =>
      [c.x + l.x + verso.x * d, c.z + l.z + verso.z * d] as const
    expect(quotaRampa([r], ...punto(0))).toBeCloseTo(2 * PASSO_STRATO, 6)
    expect(quotaRampa([r], ...punto(lunghezzaRampa(2) / 2))).toBeCloseTo(
      PASSO_STRATO,
      6,
    )
    expect(quotaRampa([r], ...punto(lunghezzaRampa(2) + 1))).toBe(0)
    // spostati di lato oltre la larghezza della rampa (27,5 per l'urbana): niente
    expect(
      quotaRampa([r], c.x + l.x + verso.z * 40, c.z + l.z - verso.x * 40),
    ).toBe(0)
  })

  it("la strada della tessera bassa si ferma dove comincia la rampa", () => {
    const connettori: Connettore[] = [
      "urbana",
      "nessuna",
      "nessuna",
      "urbana",
      "nessuna",
      "nessuna",
    ]
    const tracciato = tracciatoTessera(connettori)
    const L = lunghezzaRampa(1)
    const lato0 = puntoLato(0)
    const vicinoAlLato = (g: ReturnType<typeof costruisciStrade>) => {
      const pos = g.asfalto.getAttribute("position")
      let min = Infinity
      for (let i = 0; i < pos.count; i++)
        min = Math.min(
          min,
          Math.hypot(pos.getX(i) - lato0.x, pos.getZ(i) - lato0.z),
        )
      return min
    }
    // senza rampa l'asfalto arriva al lato (i vertici più vicini sono ai bordi, a mezza carreggiata: 18,2)
    expect(vicinoAlLato(costruisciStrade(tracciato))).toBeLessThan(18.3)
    // con la rampa sul lato 0 l'asfalto comincia 61 unità più indietro
    expect(
      vicinoAlLato(costruisciStrade(tracciato, [L, 0, 0, 0, 0, 0])),
    ).toBeGreaterThan(L - 1)
  })
})
