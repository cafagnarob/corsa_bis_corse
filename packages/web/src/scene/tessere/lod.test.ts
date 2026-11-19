/*
 * lod.test.ts
 * La tessera sotto un punto è l'inverso di centroTessera; le vicine (LOD0)
 * sono la tessera guardata e le sei attorno.
 */

import { centroTessera, vicine, type Hex } from "@corsa-bis/engine"
import { Matrix4 } from "three"
import { describe, expect, it } from "vitest"
import { dividiPerLod, tesseraSotto } from "./lod"

describe("lod", () => {
  it("tesseraSotto ritrova la tessera dal suo centro e da punti vicini al centro", () => {
    for (const h of [
      { q: 0, r: 0 },
      { q: 3, r: -2 },
      { q: -4, r: 1 },
    ]) {
      const c = centroTessera(h)
      expect(tesseraSotto(c.x, c.z)).toEqual(h)
      expect(tesseraSotto(c.x + 120, c.z - 60)).toEqual(h)
    }
  })

  it("dividiPerLod: la tessera guardata e le sei vicine da una parte, le altre dall’altra", () => {
    const guardata: Hex = { q: 2, r: 1 }
    const tutte = [
      guardata,
      ...vicine(guardata),
      { q: 5, r: 1 },
      { q: 2, r: 4 },
    ]
    const matrici = tutte.map((h) => {
      const c = centroTessera(h)
      return new Matrix4().setPosition(c.x, 3, c.z)
    })
    const [v, l] = dividiPerLod(matrici, guardata)
    expect(v).toHaveLength(7)
    expect(l).toHaveLength(2)
  })
})
