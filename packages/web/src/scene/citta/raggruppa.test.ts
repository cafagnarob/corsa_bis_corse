import { describe, expect, it } from "vitest"
import {
  generaCitta,
  generaStrade,
  generaStradario,
  popolaCitta,
  centroTessera,
  chiave,
} from "@corsa-bis/engine"
import { raggruppa } from "./raggruppa"
import { Vector3 } from "three"
describe("raggruppa", () => {
  it("conti coerenti", () => {
    const c = popolaCitta(generaCitta("barletta"))
    const r = generaStrade(c)
    const g = raggruppa(c, r, generaStradario(c, r))
    expect(g.viaPerTriangolo.length).toBe(
      g.strade.asfalto.getAttribute("position").count / 3,
    )
    expect([...g.viaPerTriangolo].filter((v) => v >= 0).length).toBeGreaterThan(
      g.viaPerTriangolo.length * 0.8,
    )
    const n = (m: ReadonlyMap<unknown, unknown[]>) =>
      [...m.values()].reduce((s, l) => s + l.length, 0)
    expect(n(g.strati)).toBe(c.tessere.reduce((s, t) => s + t.strati, 0))
    expect(n(g.cime)).toBe(c.tessere.length)
    const disegni =
      g.strati.size + g.cime.size + g.volumi.size + g.isole.size + 3
    console.log(
      JSON.stringify({
        tessere: c.tessere.length,
        disegni,
        volumi: n(g.volumi),
        isole: n(g.isole),
        vertici:
          g.strade.asfalto.getAttribute("position").count +
          g.strade.marciapiedi.getAttribute("position").count +
          g.strade.segni.getAttribute("position").count,
      }),
    )
  })
  it("un monumento al centro di ogni rotonda dei quartieri; nessun volume dentro le rotonde", () => {
    const c = popolaCitta(generaCitta("barletta"))
    const r = generaStrade(c)
    const g = raggruppa(c, r, generaStradario(c, r))
    const centri = [...r.rotonde.keys()].map((k) =>
      centroTessera(c.tessere.find((t) => chiave(t.hex) === k)!.hex),
    )
    const voci = [...g.monumenti.values()].flat()
    expect(voci.length).toBeGreaterThan(0)
    const p = new Vector3()
    for (const v of voci) {
      p.setFromMatrixPosition(v.matrice)
      expect(centri.some((q) => Math.hypot(q.x - p.x, q.z - p.z) < 0.01)).toBe(
        true,
      )
    }
    // nessun volume segnaposto dentro l'anello di una rotonda (raggio 52 o 68)
    for (const m of [...g.volumi.values()].flat()) {
      p.setFromMatrixPosition(m)
      for (const q of centri)
        expect(Math.hypot(q.x - p.x, q.z - p.z)).toBeGreaterThan(52)
    }
  })
})
