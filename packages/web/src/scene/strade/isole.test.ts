/*
 * isole.test.ts
 * Monumenti delle rotonde: quale monumento e dove guarda.
 */

import {
  MISURE_ROTONDA,
  puntoLato,
  type Connettore,
  type Rotonda,
} from "@corsa-bis/engine"
import { describe, expect, it } from "vitest"
import { latoPrincipale, monumentoIsola, SCALA_MONUMENTI } from "./isole"

const rotonda = (tipo: "compatta" | "ampia"): Rotonda => {
  const { raggio, larghezza } = MISURE_ROTONDA[tipo]
  return { tipo, raggio, larghezza, isola: raggio - larghezza / 2 }
}
const connettori: Connettore[] = [
  "urbana",
  "nessuna",
  "viale",
  "nessuna",
  "urbana",
  "nessuna",
]

describe("monumenti delle rotonde", () => {
  it("statue nelle compatte dei quartieri, equestre nelle ampie, niente in industria", () => {
    const casa = monumentoIsola(
      rotonda("compatta"),
      "villette",
      { q: 1, r: 2 },
      connettori,
    )!
    expect(["Oratore", "Pensatore", "Fiaccola", "Poeta"]).toContain(casa.nome)
    expect(casa.scala).toBeCloseTo(SCALA_MONUMENTI.compatta, 6)
    // sempre la stessa statua per la stessa tessera
    expect(
      monumentoIsola(
        rotonda("compatta"),
        "villette",
        { q: 1, r: 2 },
        connettori,
      )!.nome,
    ).toBe(casa.nome)
    const arteria = monumentoIsola(
      rotonda("ampia"),
      "popolare",
      { q: 0, r: 0 },
      connettori,
    )!
    expect(arteria.nome).toBe("Equestre")
    expect(arteria.scala).toBeCloseTo(6.5, 6)
    expect(
      monumentoIsola(
        rotonda("ampia"),
        "industriale",
        { q: 0, r: 0 },
        connettori,
      ),
    ).toBeNull()
    expect(
      monumentoIsola(
        rotonda("compatta"),
        "uffici_commercio",
        { q: 0, r: 0 },
        connettori,
      ),
    ).toBeNull() // fontana
  })

  it("il monumento guarda il viale principale", () => {
    expect(latoPrincipale(connettori)).toBe(2)
    const m = monumentoIsola(
      rotonda("compatta"),
      "parco",
      { q: 0, r: 0 },
      connettori,
    )!
    const l = puntoLato(2)
    expect(m.dx * l.x + m.dz * l.z).toBeCloseTo(Math.hypot(l.x, l.z), 6)
  })
})
