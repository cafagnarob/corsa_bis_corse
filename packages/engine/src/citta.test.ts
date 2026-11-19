/*
 * citta.test.ts
 * Test del generatore organico: controllano le regole del GDD su molti semi.
 */

import { describe, expect, it } from "vitest"
import { generaCitta, REGOLE_CITTA, type Citta } from "./citta"
import { chiave, vicine } from "./esagoni"

const SEMI = Array.from({ length: 40 }, (_, i) => `seme-${i}`)
const CITTA = SEMI.map(generaCitta) // generate una volta, usate da tutti i test

/** Tessere raggiungibili dal centro passando solo da tessere della città. */
function raggiungibili(c: Citta): number {
  const tutte = new Set(c.tessere.map((t) => chiave(t.hex)))
  const viste = new Set(["0,0"])
  const coda = [{ q: 0, r: 0 }]
  while (coda.length > 0) {
    const h = coda.pop()!
    for (const v of vicine(h)) {
      const k = chiave(v)
      if (tutte.has(k) && !viste.has(k)) {
        viste.add(k)
        coda.push(v)
      }
    }
  }
  return viste.size
}

describe("generaCitta", () => {
  it("stesso seme, stessa città", () => {
    expect(generaCitta("castelfiume")).toEqual(generaCitta("castelfiume"))
  })

  it("semi diversi, città diverse", () => {
    expect(generaCitta("castelfiume")).not.toEqual(generaCitta("fiumecastello"))
  })

  it("nessuna tessera occupata due volte", () => {
    for (const c of CITTA) {
      expect(new Set(c.tessere.map((t) => chiave(t.hex))).size).toBe(
        c.tessere.length,
      )
    }
  })

  it("niente isole: tutta la città è collegata al centro", () => {
    for (const c of CITTA) expect(raggiungibili(c)).toBe(c.tessere.length)
  })

  it("centro storico di 3-5 tessere e quartieri di 7-15", () => {
    const [cMin, cMax] = REGOLE_CITTA.tessereCentro
    const [qMin, qMax] = REGOLE_CITTA.tessereQuartiere
    for (const c of CITTA) {
      const [centro, ...altri] = c.quartieri
      expect(centro.tessere.length).toBeGreaterThanOrEqual(cMin)
      expect(centro.tessere.length).toBeLessThanOrEqual(cMax)
      for (const q of altri) {
        expect(q.tessere.length).toBeGreaterThanOrEqual(qMin)
        expect(q.tessere.length).toBeLessThanOrEqual(qMax)
      }
    }
  })

  it("al massimo 8 quartieri oltre al centro, e quasi sempre almeno 5", () => {
    const conti = CITTA.map((c) => c.quartieri.length - 1)
    expect(conti.every((n) => n <= REGOLE_CITTA.numeroQuartieri[1])).toBe(true)
    // un quartiere può non trovare spazio dopo molti tentativi: è raro
    expect(
      conti.filter((n) => n >= REGOLE_CITTA.numeroQuartieri[0]).length,
    ).toBeGreaterThanOrEqual(36)
  })

  it("compattezza: in ogni quartiere al massimo 2 tessere toccano meno di 2 tessere del quartiere", () => {
    for (const c of CITTA) {
      for (const q of c.quartieri) {
        const proprie = new Set(q.tessere.map(chiave))
        const deboli = q.tessere.filter(
          (h) => vicine(h).filter((v) => proprie.has(chiave(v))).length < 2,
        )
        expect(deboli.length).toBeLessThanOrEqual(2)
      }
    }
  })

  it("tessere vicine differiscono al massimo di 2 strati", () => {
    for (const c of CITTA) {
      const strati = new Map(c.tessere.map((t) => [chiave(t.hex), t.strati]))
      for (const t of c.tessere) {
        for (const v of vicine(t.hex)) {
          const sv = strati.get(chiave(v))
          if (sv !== undefined)
            expect(Math.abs(sv - t.strati)).toBeLessThanOrEqual(
              REGOLE_CITTA.saltoMax,
            )
        }
      }
    }
  })

  it("in alcune città ci sono frazioni collegate da tessere strada", () => {
    const conFrazioni = CITTA.filter((c) => c.quartieri.some((q) => q.frazione))
    expect(conFrazioni.length).toBeGreaterThan(0)
    for (const c of conFrazioni) {
      expect(c.tessere.some((t) => t.ruolo === "strada")).toBe(true)
    }
  })
})
