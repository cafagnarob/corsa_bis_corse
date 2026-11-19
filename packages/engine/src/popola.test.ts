/*
 * popola.test.ts
 * Test di caratteri, tipi di tessera e nomi dei quartieri.
 */

import { describe, expect, it } from "vitest"
import { generaCitta } from "./citta"
import { chiave } from "./esagoni"

import {
  MAX_INDUSTRIALI,
  TIPI_PER_CARATTERE,
  popolaCitta,
  type TipoTessera,
} from "./popola"

const POPOLATE = Array.from({ length: 40 }, (_, i) =>
  popolaCitta(generaCitta(`seme-${i}`)),
)

const PREFISSI_NOME = [
  "Centro Storico",
  "Porta ",
  "Borgo ",
  "San ",
  "Santa ",
  "Sant'",
  "Villaggio ",
  "Quartiere ",
  "Poggio ",
  "Colle ",
  "Monte ",
  "Zona Industriale ",
  "Zona Artigianale ",
  "Le ",
  "Parco ",
  "Residenza ",
  "I ",
  "Corte ",
]

describe("popolaCitta", () => {
  it("stessa città, stesso popolamento", () => {
    const c = generaCitta("castelfiume")
    expect(popolaCitta(c)).toEqual(popolaCitta(c))
  })

  it("non cambia la forma: posizioni, quote e ruoli restano quelli della città", () => {
    const c = generaCitta("castelfiume")
    const p = popolaCitta(c)
    expect(
      p.tessere.map(({ hex, strati, ruolo, quartiere }) => ({
        hex,
        strati,
        ruolo,
        quartiere,
      })),
    ).toEqual(c.tessere)
  })

  it("il centro è centro storico e le strade sono strade", () => {
    for (const p of POPOLATE) {
      for (const t of p.tessere) {
        if (t.ruolo === "centro") expect(t.tipo).toBe("centro_storico")
        if (t.ruolo === "strada") expect(t.tipo).toBe("strada")
      }
    }
  })

  it("ogni tessera di quartiere ha un tipo ammesso dal carattere del suo quartiere", () => {
    for (const p of POPOLATE) {
      const tipo = new Map(p.tessere.map((t) => [chiave(t.hex), t.tipo]))
      for (const q of p.quartieri) {
        if (q.carattere === "centro") continue
        const { interno, bordo } = TIPI_PER_CARATTERE[q.carattere]
        const ammessi = new Set([
          ...Object.keys(interno),
          ...Object.keys(bordo),
        ] as TipoTessera[])
        for (const h of q.tessere)
          expect(ammessi.has(tipo.get(chiave(h))!)).toBe(true)
      }
    }
  })

  it("nomi unici, del tipo previsto dal GDD, e il centro si chiama Centro Storico", () => {
    for (const p of POPOLATE) {
      const nomi = p.quartieri.map((q) => q.nome)
      expect(new Set(nomi).size).toBe(nomi.length)
      expect(p.quartieri[0].nome).toBe("Centro Storico")
      for (const n of nomi) {
        expect(
          PREFISSI_NOME.some((pre) => n.startsWith(pre)),
          `nome inatteso: "${n}"`,
        ).toBe(true)
      }
    }
  })

  it("le zone industriali si chiamano Zona Industriale (o Artigianale) + direzione", () => {
    const industriali = POPOLATE.flatMap((p) =>
      p.quartieri.filter((q) => q.carattere === "industriale"),
    )
    expect(industriali.length).toBeGreaterThan(0)
    for (const q of industriali)
      expect(q.nome).toMatch(
        /^Zona (Industriale|Artigianale) (Nord|Sud|Est|Ovest)( \d+)?$/,
      )
  })
  it("al massimo 2 zone industriali per città", () => {
    for (const p of POPOLATE) {
      expect(
        p.quartieri.filter((q) => q.carattere === "industriale").length,
      ).toBeLessThanOrEqual(MAX_INDUSTRIALI)
    }
  })

  it("su molte città compaiono tutti i caratteri", () => {
    const caratteri = new Set(
      POPOLATE.flatMap((p) => p.quartieri.map((q) => q.carattere)),
    )
    expect([...caratteri].sort()).toEqual([
      "centro",
      "industriale",
      "misto",
      "nuovo",
      "popolare",
      "villette",
    ])
  })
})
