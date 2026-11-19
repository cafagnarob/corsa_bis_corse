/*
 * comandi.test.ts
 * Dai tasti ai comandi, e lo sterzo che arriva un po' alla volta.
 */
import { describe, expect, it } from "vitest"
import {
  COMANDI_FERMI,
  SECONDI_PER_RADDRIZZARE,
  SECONDI_PER_STERZARE,
  comandiDaiTasti,
  sterzoGraduale,
} from "./comandi"

const tasti = (...codici: string[]) => new Set(codici)

describe("comandiDaiTasti", () => {
  it("senza tasti il mezzo è in folle con le ruote dritte", () => {
    expect(comandiDaiTasti(tasti())).toEqual(COMANDI_FERMI)
  })

  it("WASD e frecce fanno la stessa cosa", () => {
    expect(comandiDaiTasti(tasti("KeyW"))).toEqual(
      comandiDaiTasti(tasti("ArrowUp")),
    )
    expect(comandiDaiTasti(tasti("KeyA")).sterzo).toBe(-1)
    expect(comandiDaiTasti(tasti("ArrowRight")).sterzo).toBe(1)
  })

  it("sinistra e destra insieme si annullano", () => {
    expect(comandiDaiTasti(tasti("KeyA", "ArrowRight")).sterzo).toBe(0)
  })

  it("gas e freno insieme arrivano entrambi al veicolo", () => {
    const c = comandiDaiTasti(tasti("KeyW", "KeyS"))
    expect(c.gas).toBe(1)
    expect(c.freno).toBe(1)
  })

  it("freno a mano e ripristino", () => {
    const c = comandiDaiTasti(tasti("Space", "KeyR"))
    expect(c.frenoAMano).toBe(true)
    expect(c.ripristino).toBe(true)
  })

  it("i tasti che non c'entrano vengono ignorati", () => {
    expect(comandiDaiTasti(tasti("KeyQ", "Enter"))).toEqual(COMANDI_FERMI)
  })
})

describe("sterzoGraduale", () => {
  it("arriva a fondo corsa nel tempo previsto, non prima", () => {
    expect(sterzoGraduale(0, 1, SECONDI_PER_STERZARE / 2)).toBeCloseTo(0.5)
    expect(sterzoGraduale(0, 1, SECONDI_PER_STERZARE)).toBe(1)
  })

  it("non supera mai il valore chiesto", () => {
    expect(sterzoGraduale(0.9, 1, 1)).toBe(1)
    expect(sterzoGraduale(-0.9, -1, 1)).toBe(-1)
  })

  it("torna dritto più svelto di quanto sterza", () => {
    expect(SECONDI_PER_RADDRIZZARE).toBeLessThan(SECONDI_PER_STERZARE)
    expect(sterzoGraduale(1, 0, SECONDI_PER_RADDRIZZARE)).toBe(0)
  })

  it("invertendo usa la velocità di raddrizzamento", () => {
    const dt = 0.05
    expect(sterzoGraduale(0.5, -1, dt)).toBeCloseTo(
      0.5 - dt / SECONDI_PER_RADDRIZZARE,
    )
  })

  it("se è già dove deve essere non cambia", () => {
    expect(sterzoGraduale(0.3, 0.3, 0.016)).toBe(0.3)
  })
})
