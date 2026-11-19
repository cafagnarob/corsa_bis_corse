/*
 * casuale.test.ts
 * Test del generatore con seed: soprattutto "stesso seme, stessa sequenza".
 */

import { describe, expect, it } from "vitest"
import { Casuale, flusso, hashTesto } from "./casuale"

/** I primi n decimali di un generatore. */
const sequenza = (c: Casuale, n: number) =>
  Array.from({ length: n }, () => c.decimale())

describe("determinismo", () => {
  it("stesso seme, stessa sequenza", () => {
    expect(sequenza(new Casuale("castelfiume"), 20)).toEqual(
      sequenza(new Casuale("castelfiume"), 20),
    )
  })

  it("semi diversi, sequenze diverse", () => {
    expect(sequenza(new Casuale("castelfiume"), 5)).not.toEqual(
      sequenza(new Casuale("castelfiume2"), 5),
    )
  })

  it("valori di riferimento: se cambiano, città e salvataggi non sono più compatibili", () => {
    expect(hashTesto("castelfiume")).toBe(1463716179)
    expect(sequenza(new Casuale("castelfiume"), 3)).toEqual([
      0.9896109031978995, 0.34226162801496685, 0.7713614345993847,
    ])
  })

  it("ripartendo dallo stato salvato la sequenza continua identica", () => {
    const a = new Casuale("partita")
    sequenza(a, 7) // si gioca un po'
    const b = new Casuale(a.stato) // "caricamento del salvataggio"
    expect(sequenza(b, 10)).toEqual(sequenza(a, 10))
  })

  it("i flussi sono indipendenti: pescare dagli eventi non cambia la città", () => {
    const citta1 = sequenza(flusso("castelfiume", "citta"), 5)

    const eventi = flusso("castelfiume", "eventi")
    sequenza(eventi, 100)
    const citta2 = sequenza(flusso("castelfiume", "citta"), 5)

    expect(citta2).toEqual(citta1)
  })
})

describe("valori", () => {
  it("decimale sta tra 0 (compreso) e 1 (escluso) e ha media circa 0,5", () => {
    const v = sequenza(new Casuale(1), 10000)
    expect(v.every((x) => x >= 0 && x < 1)).toBe(true)
    const media = v.reduce((s, x) => s + x, 0) / v.length
    expect(media).toBeGreaterThan(0.48)
    expect(media).toBeLessThan(0.52)
  })

  it("intero esce solo nell'intervallo e prima o poi esce ogni valore", () => {
    const c = new Casuale("dado")
    const usciti = new Set(Array.from({ length: 1000 }, () => c.intero(1, 6)))
    expect([...usciti].sort()).toEqual([1, 2, 3, 4, 5, 6])
  })

  it("intervalli non validi danno errore", () => {
    expect(() => new Casuale(1).intero(5, 1)).toThrow(RangeError)
    expect(() => new Casuale(1).scegli([])).toThrow(RangeError)
  })
})

describe("liste", () => {
  it("mescola tiene gli stessi elementi e non tocca l'originale", () => {
    const mazzo = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    const mescolato = new Casuale("contratti").mescola(mazzo)
    expect([...mescolato].sort((a, b) => a - b)).toEqual(mazzo)
    expect(mazzo).toEqual([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
  })

  it("mescola è deterministico", () => {
    const mazzo = ["A", "B", "C", "D", "E"]
    expect(new Casuale("x").mescola(mazzo)).toEqual(
      new Casuale("x").mescola(mazzo),
    )
  })

  it("scegliPesato rispetta i pesi", () => {
    const c = new Casuale("pesi")
    const voci = [
      { valore: "mai", peso: 0 },
      { valore: "raro", peso: 1 },
      { valore: "comune", peso: 9 },
    ]
    const conti = { mai: 0, raro: 0, comune: 0 }
    for (let i = 0; i < 10000; i++)
      conti[c.scegliPesato(voci) as keyof typeof conti]++
    expect(conti.mai).toBe(0)
    expect(conti.raro).toBeGreaterThan(800) // circa 1000 attesi
    expect(conti.raro).toBeLessThan(1200)
  })
})
