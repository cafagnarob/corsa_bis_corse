/*
 * grafo.test.ts
 * Test del grafo stradale: copre tutte le strade, è tutto collegato, rispetta
 * i sensi delle rotonde, i mezzi ammessi e le quote.
 */

import { describe, expect, it } from "vitest"
import { generaCitta } from "./citta"
import { generaGrafo, type GrafoStradale, type TipoMezzo } from "./grafo"
import { popolaCitta } from "./popola"
import { generaStrade } from "./strade"
import { generaStradario } from "./vie"

const CASI = Array.from({ length: 20 }, (_, i) => {
  const citta = popolaCitta(generaCitta(`seme-${i}`))
  const rete = generaStrade(citta)
  const stradario = generaStradario(citta, rete)
  return { citta, rete, stradario, grafo: generaGrafo(citta, rete, stradario) }
})

/** Nodi raggiungibili da un nodo, seguendo gli archi ammessi per il mezzo. */
function raggiungibili(
  grafo: GrafoStradale,
  da: number,
  mezzo: TipoMezzo,
): Set<number> {
  const visti = new Set([da])
  const pila = [da]
  while (pila.length > 0) {
    const n = pila.pop()!
    for (const id of grafo.uscenti[n]) {
      const e = grafo.archi[id]
      if (e.ammessi.includes(mezzo) && !visti.has(e.a)) {
        visti.add(e.a)
        pila.push(e.a)
      }
    }
  }
  return visti
}

describe("generaGrafo", () => {
  it("stessa città, stesso grafo", () => {
    const { citta, rete, stradario, grafo } = CASI[0]
    expect(generaGrafo(citta, rete, stradario).archi).toEqual(grafo.archi)
  })

  it("ogni tratto è coperto per intero dagli archi, in ogni senso ammesso", () => {
    for (const { grafo } of CASI) {
      for (const [k, t] of grafo.tratti) {
        const archi = grafo.archiSulTratto.get(k)!.map((id) => grafo.archi[id])
        const avanti = archi
          .filter((e) => e.pezzi[0].a > e.pezzi[0].da)
          .reduce((m, e) => m + e.lunghezza, 0)
        expect(avanti, k).toBeCloseTo(t.lunghezza, 3)
      }
    }
  })

  it("con il minibus da ogni nodo si raggiunge ogni altro nodo (niente isole, niente vicoli senza uscita)", () => {
    for (const { grafo } of CASI) {
      for (const da of [
        0,
        Math.floor(grafo.nodi.length / 2),
        grafo.nodi.length - 1,
      ]) {
        expect(raggiungibili(grafo, da, "minibus").size).toBe(grafo.nodi.length)
      }
    }
  })

  it("l'anello delle rotonde ha un solo senso, antiorario, e copre tutto il cerchio", () => {
    let anelli = 0
    for (const { grafo } of CASI) {
      for (const [k, t] of grafo.tratti) {
        const archi = grafo.archiSulTratto.get(k)!.map((id) => grafo.archi[id])
        // l'anello è l'unico tratto chiuso (primo e ultimo punto coincidono)
        const p = t.punti
        if (
          Math.hypot(p[0].x - p[p.length - 1].x, p[0].z - p[p.length - 1].z) >
          0.01
        )
          continue
        anelli++
        for (const e of archi)
          for (const q of e.pezzi) expect(q.a).toBeGreaterThan(q.da)
        expect(archi.reduce((m, e) => m + e.lunghezza, 0)).toBeCloseTo(
          t.lunghezza,
          3,
        )
        // antiorario visto dall'alto (nord = -z): l'area con segno su (x, -z) è positiva
        let area = 0
        for (let i = 1; i < p.length; i++)
          area += p[i - 1].x * -p[i].z - p[i].x * -p[i - 1].z
        expect(area).toBeGreaterThan(0)
      }
    }
    expect(anelli).toBeGreaterThan(20)
  })

  it("mezzi ammessi: strette solo minibus, niente snodati sulle urbane e nelle rotonde compatte", () => {
    for (const { grafo, rete } of CASI) {
      for (const e of grafo.archi) {
        if (e.classe === "stretta") expect(e.ammessi).toEqual(["minibus"])
        if (e.classe === "viale") expect(e.ammessi).toContain("snodato")
        const k = `${e.tessera.q},${e.tessera.r}`
        const anello = grafo.archi
          .filter((x) => x.tessera === e.tessera && x.tratto === e.tratto)
          .every((x) => x.pezzi.every((q) => q.a > q.da))
        if (anello && rete.rotonde.get(k) === "compatta")
          expect(e.ammessi).not.toContain("snodato")
      }
    }
  })

  it("quote: salita = differenza di quota tra i nodi; andata e ritorno si compensano", () => {
    for (const { grafo } of CASI) {
      for (const e of grafo.archi)
        expect(e.salita).toBeCloseTo(
          grafo.nodi[e.a].quota - grafo.nodi[e.da].quota,
          6,
        )
      const pendenze = grafo.archi.map((e) => Math.abs(e.salita) / e.lunghezza)
      // al massimo 2 strati (20 m) tra tessere vicine, su almeno metà tessera di strada
      expect(Math.max(...pendenze)).toBeLessThan(0.15)
    }
  })

  it("ogni arco appartiene a una via dello stradario", () => {
    for (const { grafo } of CASI) {
      expect(grafo.archi.filter((e) => e.via < 0)).toHaveLength(0)
    }
  })
})
