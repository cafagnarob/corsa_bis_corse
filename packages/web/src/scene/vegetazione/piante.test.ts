/*
 * piante.test.ts
 * Dove vanno alberi, cespugli e siepi: sempre gli stessi per la stessa
 * tessera, mai su strade, rotonde o fuori dalla tessera; la siepe solo lungo
 * i viali dei quartieri residenziali; nelle isole tra monumento e cordolo.
 */

import {
  APOTEMA,
  chiave,
  generaCitta,
  generaStrade,
  LATI,
  MISURE_ROTONDA,
  popolaCitta,
  puntoLato,
  type Rotonda,
} from "@corsa-bis/engine"
import { describe, expect, it } from "vitest"
import { tracciatoDi } from "../strade/cache"
import { PROFILO } from "../strade/profili"
import { MODULO_SIEPE, pianteIsola, pianteTessera } from "./piante"

const citta = popolaCitta(generaCitta("barletta"))
const rete = generaStrade(citta)
const tessere = citta.tessere.map((t) => {
  const k = chiave(t.hex)
  const tracciato = tracciatoDi(
    rete.connettori.get(k)!,
    rete.rotonde.get(k) ?? null,
    rete.rettilinei.get(k),
  )
  return {
    t,
    tracciato,
    piante: pianteTessera(citta.seme, t.hex, t.tipo, tracciato, []),
  }
})

describe("piante delle tessere", () => {
  it("sempre le stesse per la stessa tessera", () => {
    const { t, tracciato, piante } = tessere[5]
    expect(pianteTessera(citta.seme, t.hex, t.tipo, tracciato, [])).toEqual(
      piante,
    )
  })

  it("mai su strade e marciapiedi, nella rotonda o fuori dalla tessera", () => {
    for (const { tracciato, piante } of tessere) {
      for (const p of piante.filter((x) => x.pianta !== "Siepe")) {
        for (const l of LATI) {
          const q = puntoLato(l)
          expect((p.x * q.x + p.z * q.z) / APOTEMA).toBeLessThan(APOTEMA)
        }
        for (const tr of tracciato.tratti.filter(
          (x) => x.inizio !== "anello",
        )) {
          const d = Math.min(
            ...tr.punti.map((q) => Math.hypot(p.x - q.x, p.z - q.z)),
          )
          expect(d).toBeGreaterThan(
            PROFILO[tr.classe].carreggiata / 2 + PROFILO[tr.classe].marciapiede,
          )
        }
        if (tracciato.rotonda)
          expect(Math.hypot(p.x, p.z)).toBeGreaterThan(
            tracciato.rotonda.raggio + tracciato.rotonda.larghezza / 2,
          )
      }
    }
  })

  it("i parchi sono boschi; la siepe solo nei quartieri residenziali (non nelle villette), lungo viali e strade urbane", () => {
    const parchi = tessere.filter((x) => x.t.tipo === "parco")
    if (parchi.length > 0)
      expect(Math.max(...parchi.map((x) => x.piante.length))).toBeGreaterThan(
        20,
      )
    let siepi = 0
    for (const { t, tracciato, piante } of tessere) {
      const moduli = piante.filter((p) => p.pianta === "Siepe")
      siepi += moduli.length
      if (moduli.length === 0) continue
      expect(["popolare", "nuove_costruzioni"]).toContain(t.tipo) // le villette hanno il muretto
      expect(
        tracciato.tratti.some(
          (x) => x.classe === "viale" || x.classe === "urbana",
        ),
      ).toBe(true)
    }
    expect(siepi).toBeGreaterThan(0)
    expect(MODULO_SIEPE).toBeCloseTo(20.8, 6)
  })

  it("i volumi restano liberi, anche dalla siepe", () => {
    const { t, tracciato } = tessere.find((x) => x.t.tipo === "popolare")!
    // senza volumi, dove va la siepe; poi un edificio proprio sopra un modulo
    const modulo = pianteTessera(citta.seme, t.hex, t.tipo, tracciato, []).find(
      (x) => x.pianta === "Siepe",
    )!
    const volume = { x: modulo.x, z: modulo.z, larghezza: 60, profondita: 40 }
    for (const p of pianteTessera(citta.seme, t.hex, t.tipo, tracciato, [
      volume,
    ])) {
      const dentro =
        Math.abs(p.x - volume.x) < volume.larghezza / 2 &&
        Math.abs(p.z - volume.z) < volume.profondita / 2
      expect(dentro).toBe(false)
    }
  })
})

describe("piante delle isole", () => {
  const rotonda = (tipo: "compatta" | "ampia"): Rotonda => {
    const { raggio, larghezza } = MISURE_ROTONDA[tipo]
    return { tipo, raggio, larghezza, isola: raggio - larghezza / 2 }
  }

  it("compatta: solo cespugli tra il basamento e il cordolo; ampia: anche pioppi", () => {
    const compatta = pianteIsola(
      "s",
      { q: 0, r: 0 },
      rotonda("compatta"),
      36,
      24,
    )
    expect(compatta.every((p) => p.pianta.startsWith("Cespuglio"))).toBe(true)
    for (const p of compatta) {
      const d = Math.hypot(p.x, p.z)
      expect(d).toBeGreaterThan(24)
      expect(d).toBeLessThan(36)
    }
    const ampia = pianteIsola("s", { q: 0, r: 0 }, rotonda("ampia"), 48, 30)
    expect(ampia.some((p) => p.pianta === "Albero_Goccia")).toBe(true)
  })
})
