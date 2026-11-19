/*
 * clipVeicolo.test.ts
 * Dai valori di Rapier ai fotogrammi delle clip Ruota e Sterzo.
 */
import { describe, expect, it } from "vitest"
import { FPS_CLIP, tempoRuota, tempoSterzo } from "./clipVeicolo"

const fotogramma = (tempo: number) => tempo * FPS_CLIP
const gradi = (g: number) => (g * Math.PI) / 180

describe("tempoRuota", () => {
  it("ruota ferma = fotogramma 1, mezzo giro = 13", () => {
    expect(fotogramma(tempoRuota(0))).toBeCloseTo(1)
    expect(fotogramma(tempoRuota(Math.PI))).toBeCloseTo(13)
  })

  it("dopo un giro intero ricomincia", () => {
    expect(tempoRuota(2 * Math.PI + 0.5)).toBeCloseTo(tempoRuota(0.5))
  })

  it("anche girando all'indietro resta dentro la clip", () => {
    const f = fotogramma(tempoRuota(-0.5))
    expect(f).toBeGreaterThanOrEqual(1)
    expect(f).toBeLessThanOrEqual(25)
  })
})

describe("tempoSterzo", () => {
  it("dritto = fotogramma 2, ±35° = fotogrammi 3 e 1", () => {
    expect(fotogramma(tempoSterzo(0))).toBeCloseTo(2)
    expect(fotogramma(tempoSterzo(gradi(35)))).toBeCloseTo(3)
    expect(fotogramma(tempoSterzo(gradi(-35)))).toBeCloseTo(1)
  })

  it("oltre i 35° si ferma a fine clip", () => {
    expect(fotogramma(tempoSterzo(gradi(60)))).toBeCloseTo(3)
  })
})
