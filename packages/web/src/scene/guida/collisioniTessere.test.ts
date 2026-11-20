/*
 * collisioniTessere.test.ts
 * Le forme della fisica stanno dove sta la strada disegnata: cima delle
 * tessere alla quota dell'asfalto, cuneo delle rampe che va dalla quota
 * della tessera bassa a quella della tessera alta.
 */
import { describe, expect, it } from "vitest"
import {
  RAGGIO_TESSERA,
  centroTessera,
  puntoLato,
  type Rampa,
} from "@corsa-bis/engine"
import {
  puntiRampa,
  quotaGuida,
  trimeshTessere,
  QUOTA_TAVOLO,
} from "./collisioniTessere"
import { lunghezzaRampa } from "../strade/rampe"
import { PASSO_STRATO } from "../tessere/misure"

describe("trimeshTessere", () => {
  const t = trimeshTessere([
    { hex: { q: 0, r: 0 }, strati: 1 },
    { hex: { q: 1, r: 0 }, strati: 3 },
  ])

  it("13 vertici e 18 triangoli per tessera", () => {
    expect(t.vertici.length / 3).toBe(26)
    expect(t.indici.length / 3).toBe(36)
  })

  it("la cima sta alla quota dell'asfalto, il fondo sul tavolo", () => {
    const y = (i: number) => t.vertici[3 * i + 1]
    expect(y(0)).toBeCloseTo(quotaGuida(1)) // centro della prima
    expect(y(13)).toBeCloseTo(quotaGuida(3)) // centro della seconda
    expect(y(7)).toBeCloseTo(QUOTA_TAVOLO) // un angolo in basso
  })

  it("gli angoli stanno a un raggio dal centro", () => {
    const [x, , z] = [t.vertici[3], t.vertici[4], t.vertici[5]]
    expect(Math.hypot(x, z)).toBeCloseTo(RAGGIO_TESSERA)
  })

  /** Normale (non normalizzata) del triangolo n: prodotto vettoriale (b − a) × (c − a). */
  const normale = (n: number) => {
    const p = (i: number) => [
      t.vertici[3 * i],
      t.vertici[3 * i + 1],
      t.vertici[3 * i + 2],
    ]
    const [a, b, c] = [0, 1, 2].map((k) => p(t.indici[3 * n + k]))
    const u = [b[0] - a[0], b[1] - a[1], b[2] - a[2]]
    const v = [c[0] - a[0], c[1] - a[1], c[2] - a[2]]
    return {
      x: u[1] * v[2] - u[2] * v[1],
      y: u[2] * v[0] - u[0] * v[2],
      z: u[0] * v[1] - u[1] * v[0],
    }
  }

  it("la cima guarda in su", () => {
    expect(normale(0).y).toBeGreaterThan(0)
  })

  it("i fianchi guardano verso fuori", () => {
    // Triangolo 1: primo fianco, tra gli angoli a 30° e 90° (verso nord-est)
    const n = normale(1)
    const fuori = { x: Math.cos(Math.PI / 3), z: -Math.sin(Math.PI / 3) }
    expect(n.x * fuori.x + n.z * fuori.z).toBeGreaterThan(0)
    expect(normale(2).x * fuori.x + normale(2).z * fuori.z).toBeGreaterThan(0)
  })
})

describe("puntiRampa", () => {
  const rampa: Rampa = {
    hex: { q: 0, r: 0 },
    lato: 0,
    classe: "viale",
    salto: 1,
  }
  const p = puntiRampa(rampa, 2)
  const punto = (i: number) => ({
    x: p[3 * i],
    y: p[3 * i + 1],
    z: p[3 * i + 2],
  })

  it("sul connettore arriva alla quota della tessera alta", () => {
    const lato = puntoLato(0)
    const c = centroTessera(rampa.hex)
    expect(punto(0).y).toBeCloseTo(quotaGuida(2) + PASSO_STRATO)
    expect(punto(0).x).toBeCloseTo(c.x + lato.x)
  })

  it("in fondo è al livello della tessera bassa, 61 unità più dentro", () => {
    expect(punto(2).y).toBeCloseTo(quotaGuida(2))
    expect(punto(0).x - punto(2).x).toBeCloseTo(lunghezzaRampa(1))
  })
})
