/*
 * datiVie.test.ts
 * Controlla che ogni via abbia un posto per il nome dentro la città e una
 * forma da evidenziare.
 */
import { describe, expect, it } from "vitest"
import {
  generaCitta,
  generaStradario,
  generaStrade,
  popolaCitta,
} from "@corsa-bis/engine"
import { datiVie, formaVia } from "./datiVie"

const citta = popolaCitta(generaCitta("barletta"))
const rete = generaStrade(citta)
const stradario = generaStradario(citta, rete)
const contesto = { citta, rete, stradario }

describe("datiVie", () => {
  it("ogni via ha un nome, un punto valido e una direzione unitaria", () => {
    const dati = datiVie(contesto)
    expect(dati).toHaveLength(stradario.vie.length)
    for (const d of dati) {
      expect(d.nome.length).toBeGreaterThan(0)
      expect(
        Number.isFinite(d.etichetta.x + d.etichetta.y + d.etichetta.z),
      ).toBe(true)
      expect(Math.hypot(d.etichetta.tx, d.etichetta.tz)).toBeCloseTo(1, 1)
    }
    expect(dati.some((d) => d.arteria)).toBe(true)
  })

  it("la forma di una via ha triangoli ed è riusata dalla cache", () => {
    const via = stradario.vie[0]
    const forma = formaVia(contesto, via)
    expect(forma.getAttribute("position").count).toBeGreaterThan(0)
    expect(formaVia(contesto, via)).toBe(forma)
  })
})
