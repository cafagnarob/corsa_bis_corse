/*
 * treTessere.test.ts
 * Le tre tessere della prova: in fila, collegate da strade, con la rampa
 * giusta e senza rotonde; sempre le stesse per lo stesso seme.
 */
import { describe, expect, it } from "vitest"
import {
  chiave,
  generaCitta,
  generaStrade,
  popolaCitta,
  vicina,
} from "@corsa-bis/engine"
import { scegliTreTessere } from "./treTessere"

const SEMI = ["castelfiume", "barletta", "prova"]

describe("scegliTreTessere", () => {
  for (const seme of SEMI) {
    const citta = popolaCitta(generaCitta(seme))
    const rete = generaStrade(citta)
    const scelta = scegliTreTessere(citta, rete)

    it(`${seme}: trova tre tessere in fila con la rampa al centro`, () => {
      expect(scelta).not.toBeNull()
      if (!scelta) return
      const [partenza, bassa, alta] = scelta.tessere
      expect(chiave(scelta.rampa.hex)).toBe(chiave(bassa))
      expect(chiave(vicina(bassa, scelta.rampa.lato))).toBe(chiave(alta))
      // La partenza sta dalla parte opposta della rampa
      const opposto = ((scelta.rampa.lato + 3) % 6) as 0 | 1 | 2 | 3 | 4 | 5
      expect(chiave(vicina(bassa, opposto))).toBe(chiave(partenza))
    })

    it(`${seme}: strade dritte e nessuna rotonda`, () => {
      if (!scelta) return
      const [partenza, bassa] = scelta.tessere
      const opposto = (scelta.rampa.lato + 3) % 6
      expect(rete.connettori.get(chiave(bassa))?.[opposto]).not.toBe("nessuna")
      expect(
        rete.connettori.get(chiave(partenza))?.[scelta.rampa.lato],
      ).not.toBe("nessuna")
      expect(rete.rotonde.has(chiave(bassa))).toBe(false)
      expect(rete.rotonde.has(chiave(partenza))).toBe(false)
    })
  }

  it("stessa città, stessa scelta", () => {
    const c = popolaCitta(generaCitta("castelfiume"))
    expect(scegliTreTessere(c, generaStrade(c))).toEqual(
      scegliTreTessere(c, generaStrade(c)),
    )
  })
})
