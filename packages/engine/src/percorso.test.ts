/*
 * percorso.test.ts
 * Test della ricerca del percorso: continuo, il più breve, rispettoso dei
 * mezzi ammessi e dei sensi di marcia.
 */

import { describe, expect, it } from "vitest"
import { flusso } from "./casuale"
import { generaCitta } from "./citta"
import {
  generaGrafo,
  puntoSulTratto,
  posizioneVicina,
  type Arco,
  type GrafoStradale,
  type PosizioneRete,
} from "./grafo"
import { cercaPercorso, puntiPercorso } from "./percorso"
import { popolaCitta } from "./popola"
import { generaStrade } from "./strade"
import { generaStradario } from "./vie"

const CASI = Array.from({ length: 10 }, (_, i) => {
  const citta = popolaCitta(generaCitta(`seme-${i}`))
  const rete = generaStrade(citta)
  return generaGrafo(citta, rete, generaStradario(citta, rete))
})

/** Posizioni a caso sulla rete (riproducibili). */
function posizioni(
  grafo: GrafoStradale,
  n: number,
  seme: string,
): PosizioneRete[] {
  const rng = flusso(seme, "test")
  const tratti = [...grafo.tratti.values()]
  return Array.from({ length: n }, () => {
    const t = tratti[rng.intero(0, tratti.length - 1)]
    const anello =
      Math.hypot(
        t.punti[0].x - t.punti.at(-1)!.x,
        t.punti[0].z - t.punti.at(-1)!.z,
      ) < 0.01
    const verso: 1 | -1 = anello || rng.decimale() < 0.5 ? 1 : -1
    return {
      tessera: t.tessera,
      tratto: t.tratto,
      s: rng.decimale() * t.lunghezza,
      verso,
    }
  })
}

const mondo = (g: GrafoStradale, p: PosizioneRete) =>
  puntoSulTratto(
    g.tratti.get(`${p.tessera.q},${p.tessera.r}#${p.tratto}`)!,
    p.s,
  )

describe("cercaPercorso", () => {
  it("il minibus trova sempre un percorso continuo, che parte e arriva dove deve", () => {
    for (const [i, g] of CASI.entries()) {
      const pos = posizioni(g, 12, `continuo-${i}`)
      for (let j = 1; j < pos.length; j++) {
        const p = cercaPercorso(g, pos[j - 1], pos[j], "minibus")
        expect(p).not.toBeNull()
        const punti = puntiPercorso(g, p!)
        const a = mondo(g, pos[j - 1])
        const b = mondo(g, pos[j])
        expect(Math.hypot(punti[0].x - a.x, punti[0].z - a.z)).toBeLessThan(0.1)
        expect(
          Math.hypot(punti.at(-1)!.x - b.x, punti.at(-1)!.z - b.z),
        ).toBeLessThan(0.1)
        // nessun salto: l'unico scarto ammesso è il raccordo dei rami sull'anello delle rotonde
        for (let k = 1; k < punti.length; k++) {
          expect(
            Math.hypot(
              punti[k].x - punti[k - 1].x,
              punti[k].z - punti[k - 1].z,
            ),
          ).toBeLessThan(6)
        }
        // la lunghezza dichiarata è quella dei pezzi, e mai meno della linea d'aria
        const somma = p!.pezzi.reduce((m, q) => m + Math.abs(q.a - q.da), 0)
        expect(p!.lunghezza).toBeCloseTo(somma, 3)
        expect(p!.lunghezza).toBeGreaterThanOrEqual(
          Math.hypot(a.x - b.x, a.z - b.z) - 0.5,
        )
      }
    }
  })

  it("è il più breve: andare da A a B non costa mai più che passare da C", () => {
    for (const [i, g] of CASI.entries()) {
      const [a, b, c] = posizioni(g, 3, `breve-${i}`)
      const ab = cercaPercorso(g, a, b, "minibus")!.lunghezza
      const ac = cercaPercorso(g, a, c, "minibus")!.lunghezza
      const cb = cercaPercorso(g, c, b, "minibus")!.lunghezza
      expect(ab).toBeLessThanOrEqual(ac + cb + 0.01)
    }
  })

  it("dallo stesso punto allo stesso punto: lunghezza zero", () => {
    const g = CASI[0]
    const [a] = posizioni(g, 1, "zero")
    expect(cercaPercorso(g, a, a, "minibus")!.lunghezza).toBeCloseTo(0, 6)
  })

  it("lo snodato passa solo sui viali e nelle rotonde ampie; se la meta non è su un viale non parte", () => {
    for (const g of CASI) {
      const viali = [...g.tratti.values()].filter((t) => t.classe === "viale")
      const urbana = [...g.tratti.values()].find((t) => t.classe === "urbana")!
      if (viali.length < 2) continue
      const a = {
        tessera: viali[0].tessera,
        tratto: viali[0].tratto,
        s: viali[0].lunghezza / 2,
      }
      const b = {
        tessera: viali.at(-1)!.tessera,
        tratto: viali.at(-1)!.tratto,
        s: viali.at(-1)!.lunghezza / 2,
      }
      const p = cercaPercorso(g, a, b, "snodato")
      if (p) {
        for (const q of p.pezzi) {
          const archi = g.archiSulTratto
            .get(`${q.tessera.q},${q.tessera.r}#${q.tratto}`)!
            .map((id) => g.archi[id])
          expect(archi.every((e) => e.ammessi.includes("snodato"))).toBe(true)
        }
      }
      expect(
        cercaPercorso(
          g,
          a,
          { tessera: urbana.tessera, tratto: urbana.tratto, s: 1 },
          "snodato",
        ),
      ).toBeNull()
    }
  })

  it("posizioneVicina ritrova il punto della rete da cui si parte", () => {
    const g = CASI[1]
    for (const p of posizioni(g, 20, "vicina")) {
      const m = mondo(g, p)
      const v = posizioneVicina(g, m.x + 0.5, m.z - 0.5)!
      expect(v.distanza).toBeLessThan(1)
      const w = mondo(g, v)
      expect(Math.hypot(w.x - m.x, w.z - m.z)).toBeLessThan(1)
    }
  })

  it("niente inversioni a U (salvo nei vicoli ciechi); si parte e si arriva sulla corsia della fermata", () => {
    const verso = (e: Arco) => (e.pezzi[0].a >= e.pezzi[0].da ? 1 : -1)
    for (const [i, g] of CASI.entries()) {
      const pos = posizioni(g, 15, `inversioni-${i}`)
      for (let j = 1; j < pos.length; j++) {
        const p = cercaPercorso(g, pos[j - 1], pos[j], "minibus")
        expect(p).not.toBeNull()
        const archi = p!.archi.map((id) => g.archi[id])
        expect(verso(archi[0])).toBe(pos[j - 1].verso)
        expect(verso(archi.at(-1)!)).toBe(pos[j].verso)
        for (let k = 1; k < archi.length; k++) {
          const [e, f] = [archi[k - 1], archi[k]]
          expect(f.da).toBe(e.a)
          const inversione =
            f.a === e.da &&
            f.tratto === e.tratto &&
            f.tessera === e.tessera &&
            verso(f) !== verso(e)
          if (inversione) {
            // ammessa solo se non c'era nessun'altra strada da prendere
            const altre = g.uscenti[e.a]
              .map((id) => g.archi[id])
              .filter((x) => x.id !== f.id && x.ammessi.includes("minibus"))
            expect(altre).toHaveLength(0)
          }
        }
      }
    }
  })

  it("il verso del pin viene dal lato della strada su cui si clicca", () => {
    const g = CASI[2]
    for (const t of [...g.tratti.values()].slice(0, 30)) {
      if (
        Math.hypot(
          t.punti[0].x - t.punti.at(-1)!.x,
          t.punti[0].z - t.punti.at(-1)!.z,
        ) < 0.01
      )
        continue // anello
      const q = puntoSulTratto(t, t.lunghezza / 2)
      const destra = posizioneVicina(g, q.x - q.tz * 3, q.z + q.tx * 3)! // 3 unità a destra della mezzeria
      const sinistra = posizioneVicina(g, q.x + q.tz * 3, q.z - q.tx * 3)!
      if (destra.tratto === t.tratto && destra.tessera === t.tessera)
        expect(destra.verso).toBe(1)
      if (sinistra.tratto === t.tratto && sinistra.tessera === t.tessera)
        expect(sinistra.verso).toBe(-1)
    }
  })
})
