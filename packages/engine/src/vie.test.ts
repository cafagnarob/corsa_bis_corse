/*
 * vie.test.ts
 * Test dello stradario: ogni tratto in una via, vie continue, nomi unici e
 * coerenti con il tipo di strada.
 */

import { describe, expect, it } from "vitest"
import { generaCitta } from "./citta"
import { chiave, distanza } from "./esagoni"
import { popolaCitta } from "./popola"
import { generaStrade } from "./strade"
import { tracciatoTessera } from "./tracciati"
import { generaStradario } from "./vie"

const CASI = Array.from({ length: 30 }, (_, i) => {
  const citta = popolaCitta(generaCitta(`seme-${i}`))
  const rete = generaStrade(citta)
  return { citta, rete, stradario: generaStradario(citta, rete) }
})

const PREFISSI = {
  corso: "Corso ",
  viale: "Viale ",
  circonvallazione: "Viale delle Mura",
  via: "Via ",
  traversa: "Traversa ",
  vicolo: "Vicolo ",
  provinciale: "Strada Provinciale ",
  piazzale: "Piazzale ",
}

describe("generaStradario", () => {
  it("stessa città, stesso stradario", () => {
    const { citta, rete } = CASI[0]
    expect(generaStradario(citta, rete)).toEqual(generaStradario(citta, rete))
  })

  it("ogni tratto di ogni tessera appartiene a una e una sola via", () => {
    for (const { citta, rete, stradario } of CASI) {
      let tratti = 0
      for (const t of citta.tessere) {
        const k = chiave(t.hex)
        const n = tracciatoTessera(
          rete.connettori.get(k)!,
          rete.rotonde.get(k) ?? null,
        ).tratti.length
        for (let i = 0; i < n; i++)
          expect(stradario.viaDi.has(`${k}#${i}`)).toBe(true)
        tratti += n
      }
      expect(stradario.vie.reduce((s, v) => s + v.pezzi.length, 0)).toBe(tratti)
    }
  })

  it("le vie sono continue: pezzi consecutivi nella stessa tessera o in tessere vicine", () => {
    for (const { stradario } of CASI) {
      for (const v of stradario.vie) {
        for (let i = 1; i < v.pezzi.length; i++) {
          expect(
            distanza(v.pezzi[i].tessera, v.pezzi[i - 1].tessera),
          ).toBeLessThanOrEqual(1)
        }
      }
    }
  })

  it("nomi e dediche unici, con il prefisso del loro tipo; ogni via ha una sola classe", () => {
    for (const { rete, stradario } of CASI) {
      const nomi = stradario.vie.map((v) => v.nome)
      expect(new Set(nomi).size).toBe(nomi.length)
      // nemmeno la stessa dedica con prefissi diversi (Corso Garibaldi e Via Garibaldi)
      const dediche = stradario.vie
        .filter(
          (v) => v.tipo !== "circonvallazione" && v.tipo !== "provinciale",
        )
        .map((v) => v.nome.slice(PREFISSI[v.tipo].length).trim())
      expect(new Set(dediche).size, "dedica ripetuta").toBe(dediche.length)
      for (const v of stradario.vie) {
        if (v.tipo !== "circonvallazione")
          expect(v.nome.startsWith(PREFISSI[v.tipo])).toBe(true)
        // l'anello di una rotonda di inversione fa parte della via ma non conta per la classe
        const classi = new Set(
          v.pezzi
            .map((p) => {
              const k = chiave(p.tessera)
              return tracciatoTessera(
                rete.connettori.get(k)!,
                rete.rotonde.get(k) ?? null,
              ).tratti[p.tratto]
            })
            .filter((t) => t.inizio !== "anello")
            .map((t) => t.classe),
        )
        if (v.tipo !== "piazzale") expect(classi.size).toBe(1)
      }
    }
  })

  it("i viali sono solo arterie, e dove ci sono radiali c'è un corso", () => {
    for (const { rete, stradario } of CASI) {
      for (const v of stradario.vie) {
        if (["corso", "viale", "circonvallazione"].includes(v.tipo))
          expect(v.classe).toBe("viale")
      }
      if (rete.arterie.some((a) => a.livello === "radiale")) {
        expect(stradario.vie.filter((v) => v.tipo === "corso")).toHaveLength(1)
      }
    }
  })

  it("le vie collegate sono reciproche, e ogni piazzale è collegato alle vie che vi arrivano", () => {
    for (const { stradario } of CASI) {
      for (const [a, lista] of stradario.collegate) {
        for (const b of lista) expect(stradario.collegate.get(b)).toContain(a)
      }
      for (const v of stradario.vie.filter((v) => v.tipo === "piazzale")) {
        expect(stradario.collegate.get(v.id)!.length).toBeGreaterThan(0)
      }
    }
  })
})
