/*
 * nelMondo.test.ts
 * Le tracce smussate: continue e senza spigoli alle svolte.
 *
 * I percorsi di prova vengono dall'A* del motore (cercaPercorso) tra punti
 * di alcune strade urbane della città "barletta": nel gestionale venivano
 * dalle linee, che nel gioco di corse non ci sono più.
 */
import { describe, expect, it } from "vitest"
import {
  cercaPercorso,
  generaCitta,
  generaGrafo,
  generaStradario,
  generaStrade,
  popolaCitta,
  type PosizioneRete,
  type TrattoNelMondo,
} from "@corsa-bis/engine"
import { altezzeTessere, tracciaPercorso } from "./nelMondo"

const citta = popolaCitta(generaCitta("barletta"))
const rete = generaStrade(citta)
const grafo = generaGrafo(citta, rete, generaStradario(citta, rete))
const altezze = altezzeTessere(citta)
const urbane = [...grafo.tratti.values()].filter((t) => t.classe === "urbana")

/** Il punto a metà di un tratto, sulla corsia di andata. */
const aMeta = (t: TrattoNelMondo): PosizioneRete => ({
  tessera: t.tessera,
  tratto: t.tratto,
  s: t.lunghezza / 2,
  verso: 1,
})

// Le stesse quattro strade usate dal vecchio test, collegate in fila
const TAPPE = [0, 4, 9, 14].map((n) => aMeta(urbane[n]))

describe("tracciaPercorso", () => {
  it("le tracce dei percorsi sono continue e senza spigoli", () => {
    for (let i = 1; i < TAPPE.length; i++) {
      const percorso = cercaPercorso(grafo, TAPPE[i - 1], TAPPE[i], "bus")
      expect(percorso).not.toBeNull()
      if (!percorso) continue

      const t = tracciaPercorso(grafo, altezze, percorso)
      expect(t.punti.length).toBeGreaterThan(2)

      // Nessun salto tra due punti vicini
      // (sul lato esterno delle curve strette i punti si allargano)
      for (let j = 1; j < t.punti.length; j++) {
        const [a, b] = [t.punti[j - 1], t.punti[j]]
        expect(Math.hypot(a[0] - b[0], a[2] - b[2])).toBeLessThan(10)
      }

      // Al massimo 45° di svolta tra due segmenti vicini
      for (let j = 2; j < t.punti.length; j++) {
        const [a, b, c] = [t.punti[j - 2], t.punti[j - 1], t.punti[j]]
        const u = Math.atan2(b[2] - a[2], b[0] - a[0])
        const v = Math.atan2(c[2] - b[2], c[0] - b[0])
        const svolta = Math.abs(Math.atan2(Math.sin(v - u), Math.cos(v - u)))
        expect(svolta).toBeLessThan(Math.PI / 4)
      }
    }
  })
})
