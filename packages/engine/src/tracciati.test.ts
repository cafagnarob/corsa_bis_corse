/*
 * tracciati.test.ts
 * Test del tracciato delle strade dentro la tessera.
 */

import { describe, expect, it } from "vitest"
import { generaCitta } from "./citta"
import { LATI } from "./esagoni"
import { popolaCitta } from "./popola"
import { generaStrade, type Connettore } from "./strade"
import {
  puntoLato,
  tracciatoTessera,
  versoInterno,
  type PuntoTracciato,
} from "./tracciati"

const N = "nessuna" as const
/** Connettori da una stringa di 6 lettere: v = viale, u = urbana, s = stretta, - = nessuna. */
const conn = (s: string): Connettore[] =>
  [...s].map(
    (c) => ({ v: "viale", u: "urbana", s: "stretta", "-": N })[c] as Connettore,
  )

// tutti i connettori che compaiono davvero in 20 città
const TUTTI = new Map<string, Connettore[]>()
for (let i = 0; i < 20; i++) {
  const rete = generaStrade(popolaCitta(generaCitta(`seme-${i}`)))
  for (const c of rete.connettori.values()) TUTTI.set(c.join(), [...c])
}

const dist = (a: { x: number; z: number }, b: { x: number; z: number }) =>
  Math.hypot(a.x - b.x, a.z - b.z)

describe("tracciatoTessera", () => {
  it("ogni lato con strada ha esattamente un tratto che parte da lì, perpendicolare al lato", () => {
    for (const c of TUTTI.values()) {
      const { tratti } = tracciatoTessera(c)
      for (const l of LATI) {
        // un tratto "tocca" il lato se una delle sue estremità sta sul punto medio del lato
        const tocchi = tratti.filter((t) =>
          [t.punti[0], t.punti.at(-1)!].some(
            (p) => dist(p, puntoLato(l)) < 0.01,
          ),
        )
        expect(tocchi.length).toBe(c[l] === N ? 0 : 1)
        for (const t of tocchi) {
          const p =
            dist(t.punti[0], puntoLato(l)) < 0.01 ? t.punti[0] : t.punti.at(-1)!
          const d = versoInterno(l)
          expect(Math.abs(p.tx * d.x + p.tz * d.z)).toBeCloseTo(1, 6) // tangente perpendicolare al lato
        }
      }
    }
  })

  it("un viale che attraversa la tessera è un unico tratto da lato a lato", () => {
    const { tratti, incrocio } = tracciatoTessera(conn("v--v--"))
    expect(tratti).toHaveLength(1)
    expect(tratti[0]).toMatchObject({
      classe: "viale",
      inizio: "lato",
      fine: "lato",
    })
    expect(incrocio).toBeNull()
  })

  it("le strade che si innestano finiscono sopra la mezzeria del viale, perpendicolari", () => {
    const { tratti } = tracciatoTessera(conn("vu-v--"))
    const viale = tratti.find((t) => t.classe === "viale")!
    const ramo = tratti.find((t) => t.fine === "innesto")!
    const fine = ramo.punti.at(-1)!
    const vicino: PuntoTracciato = viale.punti.reduce((m, p) =>
      dist(p, fine) < dist(m, fine) ? p : m,
    )
    expect(dist(vicino, fine)).toBeLessThan(0.01)
    expect(Math.abs(fine.tx * vicino.tx + fine.tz * vicino.tz)).toBeLessThan(
      0.01,
    ) // perpendicolari
  })

  it("tre o più strade senza viale passante fanno un incrocio al centro", () => {
    const { tratti, incrocio } = tracciatoTessera(conn("u-u-u-"))
    expect(incrocio).toEqual({ x: 0, z: 0 })
    expect(
      tratti.every(
        (t) =>
          t.fine === "incrocio" && dist(t.punti.at(-1)!, { x: 0, z: 0 }) < 0.01,
      ),
    ).toBe(true)
  })

  it("un solo connettore è un fondo cieco", () => {
    expect(tracciatoTessera(conn("---u--")).tratti[0].fine).toBe("cieco")
  })

  it("i punti sono fitti e le tangenti sono versori", () => {
    for (const c of TUTTI.values()) {
      for (const t of tracciatoTessera(c).tratti) {
        for (let i = 1; i < t.punti.length; i++)
          expect(dist(t.punti[i], t.punti[i - 1])).toBeLessThan(8)
        for (const p of t.punti)
          expect(Math.hypot(p.tx, p.tz)).toBeCloseTo(1, 6)
      }
    }
  })
})

describe("rotonde nel tracciato", () => {
  it("con la rotonda ogni ramo finisce sulla mezzeria dell'anello, e l'anello è chiuso", () => {
    for (const tipo of ["compatta", "ampia"] as const) {
      const { tratti, rotonda } = tracciatoTessera(conn("v-u-u-"), tipo)
      expect(rotonda).not.toBeNull()
      const rami = tratti.filter((t) => t.fine === "rotonda")
      expect(rami).toHaveLength(3)
      for (const r of rami)
        expect(Math.hypot(r.punti.at(-1)!.x, r.punti.at(-1)!.z)).toBeCloseTo(
          rotonda!.raggio,
          6,
        )
      const anello = tratti.find((t) => t.inizio === "anello")!
      expect(dist(anello.punti[0], anello.punti.at(-1)!)).toBeLessThan(0.01)
      expect(rotonda!.isola).toBeGreaterThan(0)
    }
  })

  it("l'anello gira in senso antiorario visto dall'alto (si dà la destra al centro)", () => {
    const anello = tracciatoTessera(conn("---u--"), "compatta").tratti.find(
      (t) => t.inizio === "anello",
    )!
    // a est del centro (x > 0, z = 0) si va verso nord (z che diminuisce)
    expect(anello.punti[0].x).toBeGreaterThan(0)
    expect(anello.punti[0].tz).toBeLessThan(0)
  })
})
