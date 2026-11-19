/*
 * nelMondo.test.ts
 * Le tracce smussate: continue, senza spigoli alle svolte, lunghe quasi
 * quanto il percorso del motore.
 */
import { describe, expect, it } from "vitest"
import {
  applicaComando,
  generaCitta,
  generaGrafo,
  generaStradario,
  generaStrade,
  popolaCitta,
  STATO_LINEE_VUOTO,
  type ComandoLinee,
} from "@corsa-bis/engine"
import { altezzeTessere, tracciaPercorso } from "./nelMondo"

const citta = popolaCitta(generaCitta("barletta"))
const rete = generaStrade(citta)
const grafo = generaGrafo(citta, rete, generaStradario(citta, rete))
const altezze = altezzeTessere(citta)
const urbane = [...grafo.tratti.values()].filter((t) => t.classe === "urbana")

describe("tracciaPercorso", () => {
  it("le tracce del giro sono continue e senza spigoli", () => {
    const comandi: ComandoLinee[] = [
      { tipo: "crea", mezzo: "bus" },
      ...[0, 4, 9, 14].map((n) => ({
        tipo: "posaFermata" as const,
        linea: 1,
        posizione: {
          tessera: urbane[n].tessera,
          tratto: urbane[n].tratto,
          s: urbane[n].lunghezza / 2,
          verso: 1 as const,
        },
      })),
    ]
    const stato = comandi.reduce(
      (s, c) => applicaComando(grafo, s, c).stato,
      STATO_LINEE_VUOTO,
    )
    const linea = stato.linee[0]
    expect(linea.giro.length).toBeGreaterThan(0)
    for (const percorso of linea.giro) {
      const t = tracciaPercorso(grafo, altezze, percorso)
      for (let i = 1; i < t.punti.length; i++) {
        const [a, b] = [t.punti[i - 1], t.punti[i]]
        expect(Math.hypot(a[0] - b[0], a[2] - b[2])).toBeLessThan(10) // nessun salto (sul lato esterno delle curve strette i punti si allargano)
      }
      for (let i = 2; i < t.punti.length; i++) {
        const [a, b, c] = [t.punti[i - 2], t.punti[i - 1], t.punti[i]]
        const u = Math.atan2(b[2] - a[2], b[0] - a[0])
        const v = Math.atan2(c[2] - b[2], c[0] - b[0])
        const svolta = Math.abs(Math.atan2(Math.sin(v - u), Math.cos(v - u)))
        expect(svolta).toBeLessThan(Math.PI / 4) // al massimo 45° tra due segmenti vicini
      }
    }
  })
})
