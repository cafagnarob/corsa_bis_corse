/*
 * esagoni.test.ts
 * Test della geometria esagonale: controllano che le funzioni rispettino
 * le convenzioni del GDD. Si lanciano con `npm test`.
 */

import { describe, expect, it } from "vitest"
import {
  APOTEMA,
  LATI,
  areaEsagonale,
  centroTessera,
  chiave,
  distanza,
  latoOpposto,
  vicina,
  vicine,
} from "./esagoni"

const ORIGINE = { q: 0, r: 0 }

describe("lati", () => {
  it("il lato opposto è (i + 3) mod 6", () => {
    expect(LATI.map(latoOpposto)).toEqual([3, 4, 5, 0, 1, 2])
  })

  it("andando su un lato e tornando dal lato opposto si torna al punto di partenza", () => {
    for (const lato of LATI) {
      expect(vicina(vicina(ORIGINE, lato), latoOpposto(lato))).toEqual(ORIGINE)
    }
  })
})

describe("posizioni nel mondo", () => {
  it("i centri seguono la formula del GDD", () => {
    expect(centroTessera({ q: 1, r: 0 }).x).toBeCloseTo(346.41, 2)
    expect(centroTessera({ q: 0, r: 1 }).x).toBeCloseTo(173.21, 2)
    expect(centroTessera({ q: 0, r: 1 }).z).toBeCloseTo(300, 6)
  })

  it("ogni vicina sta a due apotemi, nella direzione del suo lato", () => {
    for (const lato of LATI) {
      const c = centroTessera(vicina(ORIGINE, lato))
      expect(Math.hypot(c.x, c.z)).toBeCloseTo(2 * APOTEMA, 6)
      // angolo misurato da est in senso antiorario (nord = -z, quindi -c.z)
      const gradi = (Math.atan2(-c.z, c.x) * 180) / Math.PI
      expect((gradi + 360) % 360).toBeCloseTo(lato * 60, 6)
    }
  })
})

describe("distanze", () => {
  it("le sei vicine stanno a un passo", () => {
    for (const v of vicine(ORIGINE)) expect(distanza(ORIGINE, v)).toBe(1)
  })

  it("una tessera dista zero da se stessa", () => {
    expect(distanza({ q: 3, r: -2 }, { q: 3, r: -2 })).toBe(0)
  })

  it("tre passi verso est sono distanza 3", () => {
    expect(distanza(ORIGINE, { q: 3, r: 0 })).toBe(3)
  })
})

describe("chiave", () => {
  it("è uguale per tessere uguali e diversa per tessere diverse", () => {
    expect(chiave({ q: 2, r: -1 })).toBe(chiave({ q: 2, r: -1 }))
    expect(chiave({ q: 2, r: -1 })).not.toBe(chiave({ q: -1, r: 2 }))
  })
})

describe("areaEsagonale", () => {
  it("contiene 1, 7, 19, 37, 61 tessere per raggio 0-4", () => {
    expect(
      [0, 1, 2, 3, 4].map((n) => areaEsagonale(ORIGINE, n).length),
    ).toEqual([1, 7, 19, 37, 61])
  })

  it("tutte le tessere sono entro il raggio e nessuna è ripetuta", () => {
    const area = areaEsagonale(ORIGINE, 4)
    expect(area.every((h) => distanza(h, ORIGINE) <= 4)).toBe(true)
    expect(new Set(area.map(chiave)).size).toBe(area.length)
  })
})
