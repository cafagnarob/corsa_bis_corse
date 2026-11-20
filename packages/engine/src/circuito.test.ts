/*
 * circuito.test.ts
 * Il generatore di circuiti: giri chiusi e continui, della lunghezza
 * chiesta, su strade ammesse, senza ripassare sulla stessa strada; stesso
 * seme, stesso circuito.
 */
import { describe, expect, it } from "vitest"
import {
  OPZIONI_CIRCUITO,
  attraversa,
  generaCircuito,
  isolati,
  type Circuito,
} from "./circuito"
import { generaCitta } from "./citta"
import {
  chiaveTratto,
  generaGrafo,
  puntoSulTratto,
  type GrafoStradale,
} from "./grafo"
import { popolaCitta } from "./popola"
import { metriInUnita } from "./scala"
import { generaStrade } from "./strade"
import { generaStradario } from "./vie"

const grafoDi = (seme: string): GrafoStradale => {
  const citta = popolaCitta(generaCitta(seme))
  const rete = generaStrade(citta)
  return generaGrafo(citta, rete, generaStradario(citta, rete))
}

// Semi per cui il generatore trova un circuito (provato su 20 semi: 18 sì)
const SEMI = ["castelfiume", "barletta", "prova", "milano", "roma"]
const CASI = SEMI.map((seme) => {
  const grafo = grafoDi(seme)
  return { seme, grafo, circuito: generaCircuito(grafo, seme) }
})

/** Il punto del mondo all'inizio (o alla fine) di un pezzo. */
const estremo = (g: GrafoStradale, p: Circuito["pezzi"][number], s: number) =>
  puntoSulTratto(g.tratti.get(chiaveTratto(p.tessera, p.tratto))!, s)

describe("attraversa", () => {
  const c = { x: 0, z: 0 }
  const d = { x: 1, z: 0 } // semiretta verso +x
  it("conta +1 o −1 secondo il senso, 0 dalla parte opposta", () => {
    // Da z = +1 a z = −1 a x = 5: antiorario visto dall'alto (z verso il basso)
    expect(attraversa(c, d, { x: 5, z: 1 }, { x: 5, z: -1 })).toBe(1)
    expect(attraversa(c, d, { x: 5, z: -1 }, { x: 5, z: 1 })).toBe(-1)
    expect(attraversa(c, d, { x: -5, z: 1 }, { x: -5, z: -1 })).toBe(0)
  })

  it("un quadrato attorno al centro fa un giro", () => {
    const q = [
      { x: 1, z: 1 },
      { x: 1, z: -1 },
      { x: -1, z: -1 },
      { x: -1, z: 1 },
      { x: 1, z: 1 },
    ]
    let giri = 0
    for (let i = 1; i < q.length; i++) giri += attraversa(c, d, q[i - 1], q[i])
    expect(Math.abs(giri)).toBe(1)
  })
})

describe("isolati", () => {
  it("trova gli isolati della città, ognuno senza strade ripetute", () => {
    const tutti = isolati(CASI[0].grafo, "bus")
    expect(tutti.length).toBeGreaterThan(10)
    for (const i of tutti) expect(i.lati.size).toBeGreaterThanOrEqual(3)
  })
})

describe("generaCircuito", () => {
  for (const { seme, grafo, circuito } of CASI) {
    describe(seme, () => {
      it("trova un circuito della lunghezza chiesta", () => {
        expect(circuito).not.toBeNull()
        if (!circuito) return
        expect(circuito.lunghezza).toBeGreaterThanOrEqual(
          metriInUnita(OPZIONI_CIRCUITO.lunghezzaMinima),
        )
        expect(circuito.lunghezza).toBeLessThanOrEqual(
          metriInUnita(OPZIONI_CIRCUITO.lunghezzaMassima),
        )
      })

      it("è chiuso e continuo: ogni pezzo riparte dove finisce il precedente", () => {
        if (!circuito) return
        const n = circuito.pezzi.length
        for (let i = 0; i < n; i++) {
          const p = circuito.pezzi[i]
          const q = circuito.pezzi[(i + 1) % n] // l'ultimo torna al primo
          const fine = estremo(grafo, p, p.a)
          const inizio = estremo(grafo, q, q.da)
          // Tolleranza 2 unità (circa 40 cm): dove una strada entra in una
          // rotonda la fine del tratto e l'anello distano poco più di 1 unità
          expect(Math.hypot(fine.x - inizio.x, fine.z - inizio.z)).toBeLessThan(
            2,
          )
        }
      })

      it("non passa due volte sullo stesso arco, e mai su strade strette", () => {
        if (!circuito) return
        expect(new Set(circuito.archi).size).toBe(circuito.archi.length)
        for (const id of circuito.archi)
          expect(grafo.archi[id].classe).not.toBe("stretta")
      })

      it("il traguardo sta sul primo arco, a metà", () => {
        if (!circuito) return
        const primo = grafo.archi[circuito.archi[0]]
        expect(circuito.traguardo.tratto).toBe(primo.tratto)
        expect(circuito.pezzi[0].da).toBeCloseTo(circuito.traguardo.s)
      })
    })
  }

  it("il traguardo è su un viale quando il giro ne ha uno", () => {
    const { grafo, circuito } = CASI[0]
    const haViale = circuito!.archi.some(
      (id) => grafo.archi[id].classe === "viale",
    )
    if (haViale) expect(grafo.archi[circuito!.archi[0]].classe).toBe("viale")
  })

  it("stesso seme, stesso circuito; semi diversi, circuiti diversi", () => {
    const { seme, grafo, circuito } = CASI[0]
    expect(generaCircuito(grafo, seme)).toEqual(circuito)
    expect(CASI[1].circuito!.lunghezza).not.toBe(circuito!.lunghezza)
  })
})
