/*
 * tracciatoGara.test.ts
 * Linea, traiettoria e checkpoint di un circuito; passaggio delle porte e
 * avanzamento sul giro.
 */
import { describe, expect, it } from "vitest"
import { generaCircuito } from "./circuito"
import { generaCitta } from "./citta"
import { generaGrafo } from "./grafo"
import { popolaCitta } from "./popola"
import { generaStrade } from "./strade"
import {
  OPZIONI_TRACCIATO,
  attraversaCheckpoint,
  progressoSulGiro,
  tracciatoGara,
  type Checkpoint,
} from "./tracciatoGara"
import { generaStradario } from "./vie"

const citta = popolaCitta(generaCitta("castelfiume"))
const rete = generaStrade(citta)
const grafo = generaGrafo(citta, rete, generaStradario(citta, rete))
const circuito = generaCircuito(grafo, "castelfiume")!
const t = tracciatoGara(grafo, circuito)

describe("tracciatoGara", () => {
  it("la linea è lunga quanto il circuito e torna al traguardo", () => {
    expect(t.lunghezza / circuito.lunghezza).toBeGreaterThan(0.98)
    expect(t.lunghezza / circuito.lunghezza).toBeLessThan(1.02)
    const [primo, ultimo] = [t.linea[0], t.linea.at(-1)!]
    expect(Math.hypot(primo.x - ultimo.x, primo.z - ultimo.z)).toBeLessThan(
      2 * OPZIONI_TRACCIATO.passo,
    )
  })

  it("le distanze crescono e le direzioni sono unitarie", () => {
    for (let i = 1; i < t.linea.length; i++)
      expect(t.linea[i].s).toBeGreaterThan(t.linea[i - 1].s)
    for (const p of t.linea) expect(Math.hypot(p.tx, p.tz)).toBeCloseTo(1, 1)
  })

  it("la traiettoria resta dentro la carreggiata, meno il margine", () => {
    t.traiettoria.forEach((q, i) => {
      const p = t.linea[i]
      const scarto = Math.hypot(q.x - p.x, q.z - p.z)
      expect(scarto).toBeLessThanOrEqual(
        p.mezzaLarghezza - OPZIONI_TRACCIATO.margine + 0.01,
      )
    })
  })

  it("la traiettoria è più corta della mezzeria: taglia le curve", () => {
    const giro = (punti: readonly { x: number; z: number }[]) =>
      punti.reduce(
        (l, p, i) =>
          l +
          Math.hypot(
            p.x - punti[(i + 1) % punti.length].x,
            p.z - punti[(i + 1) % punti.length].z,
          ),
        0,
      )
    expect(giro(t.traiettoria)).toBeLessThan(giro(t.linea))
  })

  it("checkpoint in ordine, il primo sul traguardo, a distanze simili", () => {
    expect(t.checkpoint.length).toBeGreaterThanOrEqual(3)
    expect(t.checkpoint[0].s).toBe(0)
    const passo = t.lunghezza / t.checkpoint.length
    t.checkpoint.forEach((c, i) => {
      expect(c.indice).toBe(i)
      expect(c.s).toBeCloseTo(i * passo, -1)
    })
  })
})

describe("attraversaCheckpoint", () => {
  const porta: Checkpoint = {
    indice: 0,
    x: 0,
    z: 0,
    tx: 1,
    tz: 0,
    mezzaLarghezza: 20,
    s: 0,
  }
  it("conta solo nel verso di marcia e dentro la porta", () => {
    expect(attraversaCheckpoint(porta, { x: -5, z: 3 }, { x: 5, z: 3 })).toBe(
      true,
    )
    expect(attraversaCheckpoint(porta, { x: 5, z: 3 }, { x: -5, z: 3 })).toBe(
      false,
    )
    expect(attraversaCheckpoint(porta, { x: -5, z: 60 }, { x: 5, z: 60 })).toBe(
      false,
    )
    expect(attraversaCheckpoint(porta, { x: 1, z: 0 }, { x: 5, z: 0 })).toBe(
      false,
    )
  })
})

describe("progressoSulGiro", () => {
  it("segue un mezzo che percorre la linea, fino in fondo al giro", () => {
    let s = 0
    for (let i = 0; i < t.linea.length; i += 3) {
      const p = t.linea[i]
      s = progressoSulGiro(t, p.x + 3, p.z, s)
      expect(Math.abs(s - p.s)).toBeLessThan(3 * OPZIONI_TRACCIATO.passo)
    }
  })
})
