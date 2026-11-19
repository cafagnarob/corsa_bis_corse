/*
 * lotti.test.ts
 * Gli edifici su tutte le tessere di una città vera: dentro la tessera,
 * fuori dalle strade e dai marciapiedi, senza toccarsi; stesso seme, stessi
 * edifici; e abbastanza veloce da farlo per tutta la città.
 */

import {
  APOTEMA,
  chiave,
  generaCitta,
  generaStrade,
  popolaCitta,
} from "@corsa-bis/engine"
import { describe, expect, it } from "vitest"
import { tracciatoDi } from "../strade/cache"
import { PROFILO } from "../strade/profili"
import { CON_EDIFICI, lottiTessera } from "./lotti"

const SEME = "barletta"
const citta = popolaCitta(generaCitta(SEME))
const rete = generaStrade(citta)
const tessere = citta.tessere.filter((t) => CON_EDIFICI.has(t.tipo))
const tracciato = (t: (typeof tessere)[number]) => {
  const k = chiave(t.hex)
  return tracciatoDi(
    rete.connettori.get(k)!,
    rete.rotonde.get(k) ?? null,
    rete.rettilinei.get(k),
  )
}

describe("lotti degli edifici", () => {
  const inizio = performance.now()
  const tutti = tessere.map((t) => ({
    t,
    lotti: lottiTessera(SEME, t.hex, t.tipo, tracciato(t)),
  }))
  const ms = performance.now() - inizio

  it("ci sono edifici, e si calcolano in fretta", () => {
    const n = tutti.reduce((s, x) => s + x.lotti.length, 0)
    console.log(
      `${tessere.length} tessere con edifici, ${n} edifici, ${ms.toFixed(0)} ms`,
      tutti
        .slice(0, 8)
        .map((x) => `${x.t.tipo}:${x.lotti.length}`)
        .join(" "),
    )
    expect(n).toBeGreaterThan(tessere.length) // in media più di uno per tessera
    expect(ms).toBeLessThan(3000)
  })

  it("ogni famiglia mette i suoi edifici: borgo, palazzoni, villette, capannoni, grattacieli", () => {
    const famiglie = new Set(
      tutti.flatMap((x) => x.lotti.map((l) => l.progetto.famiglia)),
    )
    for (const f of ["borgo", "villetta", "capannone", "grattacielo"])
      expect(famiglie.has(f), f).toBe(true)
    expect(famiglie.has("stecca") || famiglie.has("torre")).toBe(true)
  })

  it("il popolare vicino al centro ha i palazzi a corte", () => {
    const t = tessere.find((x) => x.tipo === "popolare")!
    const lotti = lottiTessera(SEME, t.hex, t.tipo, tracciato(t), true)
    expect(lotti.length).toBeGreaterThan(0)
    expect(new Set(lotti.map((l) => l.progetto.famiglia))).toEqual(
      new Set(["corte"]),
    )
  })

  it("dentro la tessera e lontano dalle mezzerie delle strade", () => {
    for (const { t, lotti } of tutti) {
      const tr = tracciato(t)
      for (const l of lotti) {
        for (const [x, z] of l.angoli)
          expect(Math.hypot(x, z)).toBeLessThan(APOTEMA * 1.16)
        const cx = (l.angoli[0][0] + l.angoli[2][0]) / 2
        const cz = (l.angoli[0][1] + l.angoli[2][1]) / 2
        for (const s of tr.tratti) {
          const limite =
            PROFILO[s.classe].carreggiata / 2 + PROFILO[s.classe].marciapiede
          for (const p of s.punti)
            expect(Math.hypot(p.x - cx, p.z - cz)).toBeGreaterThan(limite - 1)
        }
      }
    }
  })

  it("stesso seme, stessi edifici", () => {
    const t = tessere[0]
    expect(
      lottiTessera(SEME, t.hex, t.tipo, tracciato(t)).map((l) => [
        l.x,
        l.z,
        l.angolo,
      ]),
    ).toEqual(tutti[0].lotti.map((l) => [l.x, l.z, l.angolo]))
  })

  it("le tessere senza famiglia non hanno edifici", () => {
    const altra = citta.tessere.find((t) => !CON_EDIFICI.has(t.tipo))!
    expect(lottiTessera(SEME, altra.hex, altra.tipo, tracciato(altra))).toEqual(
      [],
    )
  })
})
