/*
 * sceltaKit.test.ts
 * La scelta degli edifici da montare: solo dentro il raggio, prima i vicini,
 * interi solo quelli vicini, mai oltre il tetto di triangoli, e uno pesante
 * non blocca i leggeri.
 */

import { describe, expect, it } from "vitest"
import { scegliEdifici, stessaScelta } from "./sceltaKit"

describe("scelta degli edifici da montare", () => {
  // cinque edifici in fila sull'asse x, a 0, 100, 200, 300, 400
  const centri = new Float32Array([0, 0, 100, 0, 200, 0, 300, 0, 400, 0])
  const indici = (s: { i: number }[]) => s.map((x) => x.i)

  it("dentro il raggio, dal più vicino", () => {
    expect(
      indici(
        scegliEdifici(centri, 210, 0, () => 1, { raggio: 150, tetto: 1000 }),
      ),
    ).toEqual([2, 3, 1])
  })

  it("interi solo i vicini, gli altri senza bordi (pesano meno)", () => {
    const peso = (_: number, vicino: boolean) => (vicino ? 100 : 50)
    const s = scegliEdifici(centri, 0, 0, peso, {
      raggio: 1000,
      dettaglio: 150,
      tetto: 250,
    })
    expect(s).toEqual([
      { i: 0, vicino: true },
      { i: 1, vicino: true },
      { i: 2, vicino: false },
    ])
  })

  it("il tetto di triangoli: salta il pesante, prende i leggeri dopo", () => {
    const peso = (i: number) => (i === 1 ? 900 : 100)
    expect(
      indici(
        scegliEdifici(centri, 0, 0, peso, {
          raggio: 1000,
          dettaglio: 0,
          tetto: 500,
        }),
      ),
    ).toEqual([0, 2, 3, 4])
  })

  it("stessa scelta: stessi edifici con lo stesso dettaglio, in qualsiasi ordine", () => {
    expect(
      stessaScelta(
        [
          { i: 1, vicino: true },
          { i: 2, vicino: false },
        ],
        [
          { i: 2, vicino: false },
          { i: 1, vicino: true },
        ],
      ),
    ).toBe(true)
    expect(
      stessaScelta([{ i: 1, vicino: true }], [{ i: 1, vicino: false }]),
    ).toBe(false)
    expect(
      stessaScelta([{ i: 1, vicino: true }], [{ i: 2, vicino: true }]),
    ).toBe(false)
  })
})
