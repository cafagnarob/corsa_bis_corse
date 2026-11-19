/*
 * strade.test.ts
 * Test della rete stradale gerarchica su molte città.
 */

import { describe, expect, it } from "vitest"
import { generaCitta } from "./citta"
import { chiave, LATI, latoOpposto, vicina, type Hex } from "./esagoni"
import { popolaCitta } from "./popola"
import {
  REGOLE_STRADE,
  abbinamento,
  curvaAmmessa,
  generaStrade,
} from "./strade"

const CASI = Array.from({ length: 40 }, (_, i) => {
  const citta = popolaCitta(generaCitta(`seme-${i}`))
  return { citta, rete: generaStrade(citta) }
})

/** Lati con una data classe. */
const latiCon = (lati: readonly string[], classe: string) =>
  LATI.filter((l) => lati[l] === classe)

describe("generaStrade", () => {
  it("stessa città, stessa rete", () => {
    const c = popolaCitta(generaCitta("castelfiume"))
    expect(generaStrade(c)).toEqual(generaStrade(c))
  })

  it("ogni lato con strada tocca un lato con strada della vicina, della stessa classe se è un viale", () => {
    for (const { rete } of CASI) {
      for (const [k, lati] of rete.connettori) {
        const [q, r] = k.split(",").map(Number)
        for (const lato of LATI) {
          if (lati[lato] === "nessuna") continue
          const altro =
            rete.connettori.get(chiave(vicina({ q, r }, lato)))?.[
              latoOpposto(lato)
            ] ?? "nessuna"
          expect(altro).not.toBe("nessuna")
          if (lati[lato] === "viale") expect(altro).toBe("viale") // il viale non cambia a metà
        }
      }
    }
  })

  it("ogni tessera ha da 1 a 4 connettori", () => {
    for (const { rete } of CASI) {
      for (const lati of rete.connettori.values()) {
        const n = lati.filter((c) => c !== "nessuna").length
        expect(n).toBeGreaterThanOrEqual(1)
        expect(n).toBeLessThanOrEqual(REGOLE_STRADE.maxConnettori)
      }
    }
  })

  it("niente isole: dal centro storico si raggiunge in strada ogni tessera", () => {
    for (const { citta, rete } of CASI) {
      const viste = new Set(["0,0"])
      const coda = [{ q: 0, r: 0 }]
      while (coda.length > 0) {
        const h = coda.pop()!
        const lati = rete.connettori.get(chiave(h))!
        for (const lato of LATI) {
          if (lati[lato] === "nessuna") continue
          const v = vicina(h, lato)
          if (!viste.has(chiave(v))) {
            viste.add(chiave(v))
            coda.push(v)
          }
        }
      }
      expect(viste.size).toBe(citta.tessere.length)
    }
  })

  it("gerarchia: viali solo sulle arterie, strade strette solo nel centro, nessun viale nel centro", () => {
    for (const { citta, rete } of CASI) {
      for (const c of rete.collegamenti) {
        if (c.livello === "locale")
          expect([c.classeA, c.classeB]).not.toContain("viale")
        else expect([c.classeA, c.classeB]).toEqual(["viale", "viale"])
        expect(c.abbinamento).toBe(abbinamento(c.classeA, c.classeB))
      }
      for (const t of citta.tessere) {
        const lati = rete.connettori.get(chiave(t.hex))!
        if (t.tipo === "centro_storico")
          expect(latiCon(lati, "viale")).toEqual([])
        else expect(latiCon(lati, "stretta")).toEqual([])
      }
    }
  })

  it("lungo ogni radiale solo rettilinei e curve larghe", () => {
    /** Il lato di `a` che guarda verso `b` (tessere vicine). */
    const latoVerso = (a: Hex, b: Hex) =>
      LATI.find((l) => chiave(vicina(a, l)) === chiave(b))!
    for (const { rete } of CASI) {
      for (const arteria of rete.arterie.filter(
        (a) => a.livello === "radiale",
      )) {
        const t = arteria.tessere
        for (let i = 1; i + 1 < t.length; i++) {
          const ingresso = latoVerso(t[i], t[i - 1])
          const uscita = latoVerso(t[i], t[i + 1])
          expect(curvaAmmessa(ingresso, uscita)).toBe(true)
        }
      }
    }
  })

  it("quasi ogni città ha arterie, e le zone industriali sono raggiunte da un viale", () => {
    const conViali = CASI.filter(({ rete }) =>
      rete.collegamenti.some((c) => c.classeA === "viale"),
    )
    expect(conViali.length).toBeGreaterThanOrEqual(36)
    for (const { citta, rete } of CASI) {
      for (const q of citta.quartieri.filter(
        (q) => q.carattere === "industriale",
      )) {
        const servito = q.tessere.some((h) =>
          rete.connettori.get(chiave(h))!.includes("viale"),
        )
        expect(servito).toBe(true)
      }
    }
  })

  it("rotonde: mai nel centro storico, sempre nei fondi ciechi e dove finisce un viale", () => {
    let conRotonde = 0
    for (const { citta, rete } of CASI) {
      for (const t of citta.tessere) {
        const k = chiave(t.hex)
        const lati = rete.connettori.get(k)!
        const strade = lati.filter((c) => c !== "nessuna").length
        const viali = lati.filter((c) => c === "viale").length
        if (t.tipo === "centro_storico") expect(rete.rotonde.has(k)).toBe(false)
        else if (strade === 1 || viali === 1 || viali >= 3)
          expect(rete.rotonde.has(k)).toBe(true)
        if (rete.rotonde.get(k) === "compatta") expect(viali).toBe(0)
      }
      if (rete.rotonde.size > 0) conRotonde++
    }
    expect(conRotonde).toBe(CASI.length)
  })

  it("curvaAmmessa: dritto e curve larghe sì, curve strette no", () => {
    expect(curvaAmmessa(3, 0)).toBe(true) // dritto
    expect(curvaAmmessa(3, 1)).toBe(true) // curva larga
    expect(curvaAmmessa(3, 5)).toBe(true) // curva larga
    expect(curvaAmmessa(3, 2)).toBe(false) // curva stretta
    expect(curvaAmmessa(3, 4)).toBe(false) // curva stretta
  })
})
