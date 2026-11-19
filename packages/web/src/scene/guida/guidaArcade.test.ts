/*
 * guidaArcade.test.ts
 * Le regole di guida, senza fisica: dato un comando e una velocità, cosa
 * devono fare le ruote.
 */
import { describe, expect, it } from "vitest"
import { COMANDI_FERMI, type Comandi } from "./comandi"
import { calcolaGuida, ruoteVeicolo } from "./guidaArcade"
import { UTILITARIA, kmhInUnita } from "./parametri"

const DT = 1 / 60
const guida = (comandi: Partial<Comandi>, kmh: number) =>
  calcolaGuida(
    { ...COMANDI_FERMI, ...comandi },
    kmhInUnita(kmh),
    UTILITARIA,
    DT,
  )

describe("ruoteVeicolo", () => {
  it("quattro ruote: davanti con x positiva, a destra con z positiva", () => {
    const r = ruoteVeicolo(UTILITARIA)
    expect(r).toHaveLength(4)
    expect(r.map((w) => w.anteriore)).toEqual([true, true, false, false])
    expect(r[0].attacco[0]).toBeGreaterThan(0) // anteriore sinistra davanti
    expect(r[0].attacco[2]).toBeLessThan(0) // e a sinistra
    expect(r[3].attacco[0]).toBeLessThan(0) // posteriore destra dietro
    expect(r[3].attacco[2]).toBeGreaterThan(0) // e a destra
  })
})

describe("calcolaGuida", () => {
  it("col gas spingono solo le ruote dietro (trazione posteriore)", () => {
    const g = guida({ gas: 1 }, 0)
    expect(g.motore[0]).toBe(0)
    expect(g.motore[1]).toBe(0)
    expect(g.motore[2]).toBeGreaterThan(0)
    expect(g.motore[3]).toBe(g.motore[2])
  })

  it("alla velocità massima il motore non spinge più", () => {
    const g = guida({ gas: 1 }, UTILITARIA.motore.velocitaMassima)
    expect(g.motore.every((f) => f === 0)).toBe(true)
  })

  it("andando avanti il freno frena e il motore tace", () => {
    const g = guida({ freno: 1 }, 50)
    expect(g.freno.every((f) => f > 0)).toBe(true)
    expect(g.motore.every((f) => f === 0)).toBe(true)
  })

  it("da fermo il freno diventa retromarcia", () => {
    const g = guida({ freno: 1 }, 0)
    expect(g.motore[2]).toBeLessThan(0)
  })

  it("in retromarcia non supera la sua velocità massima", () => {
    const g = guida({ freno: 1 }, -UTILITARIA.motore.velocitaRetromarcia)
    expect(g.motore.every((f) => f === 0)).toBe(true)
  })

  it("gas mentre va indietro: prima frena", () => {
    const g = guida({ gas: 1 }, -10)
    expect(g.freno.every((f) => f > 0)).toBe(true)
    expect(g.motore.every((f) => f === 0)).toBe(true)
  })

  it("senza comandi da fermo tiene il mezzo fermo più forte che in folle", () => {
    expect(guida({}, 0).freno[0]).toBeGreaterThan(guida({}, 60).freno[0])
  })

  it("sterzo a destra = angolo negativo (convenzione di Rapier)", () => {
    expect(guida({ sterzo: 1 }, 30).sterzo).toBeLessThan(0)
    expect(guida({ sterzo: -1 }, 30).sterzo).toBeGreaterThan(0)
  })

  it("lo sterzo gira meno quando si va forte", () => {
    const piano = Math.abs(guida({ sterzo: 1 }, 10).sterzo)
    const forte = Math.abs(guida({ sterzo: 1 }, 130).sterzo)
    expect(forte).toBeLessThan(piano)
  })

  it("il freno a mano frena e fa scivolare solo le ruote dietro", () => {
    const g = guida({ frenoAMano: true, gas: 1 }, 70)
    expect(g.freno[0]).toBe(0)
    expect(g.freno[2]).toBeGreaterThan(0)
    expect(g.laterale[2]).toBeLessThan(g.laterale[0])
  })
})
