/*
 * montaggio.test.ts
 * Il montaggio col kit: ogni pezzo esiste nel kit, ogni casella del fronte
 * di ogni famiglia sa come montarsi, i moduli di parete stanno proprio dove
 * il guscio disegna la casella, e lo stesso seme rimonta lo stesso edificio.
 */

import { Casuale } from "@corsa-bis/engine"
import { Matrix4, Vector3 } from "three"
import { describe, expect, it } from "vitest"
import { RIQUADRI } from "./atlante"
import { generaBorgo } from "./borgo"
import { generaCapannone } from "./capannoni"
import { generaCorte } from "./corte"
import { generaGrattacielo } from "./grattacieli"
import kit from "./kit_edifici.json"
import { FASCE_MONTABILI, FONDALE, MONTABILI, montaEdificio } from "./montaggio"
import { generaPalazzone } from "./palazzoni"
import { COPERTA, MODULO, NASCOSTA, type Progetto } from "./progetto"
import { generaVilletta } from "./villette"

const FAMIGLIE: Record<string, (rng: Casuale) => Progetto> = {
  borgo: generaBorgo,
  palazzoni: (rng) => generaPalazzone(rng),
  corte: generaCorte,
  villette: generaVilletta,
  capannoni: generaCapannone,
  grattacieli: generaGrattacielo,
}
const progetti = (genera: (rng: Casuale) => Progetto, n: number) =>
  Array.from({ length: n }, (_, i) => genera(new Casuale(`m-${i}`)))

/** Il progetto e i suoi corpi, con la loro matrice. */
function tuttiICorpi(
  p: Progetto,
  m = new Matrix4(),
): { p: Progetto; m: Matrix4 }[] {
  return [
    { p, m },
    ...(p.corpi ?? []).flatMap((c) =>
      tuttiICorpi(
        c.progetto,
        m
          .clone()
          .multiply(new Matrix4().makeTranslation(c.x, c.y, c.z))
          .multiply(new Matrix4().makeRotationY(c.rotazione ?? 0)),
      ),
    ),
  ]
}

describe("montaggio col kit", () => {
  it("le caselle montabili sono nell'atlante", () => {
    for (const c of MONTABILI) expect(RIQUADRI.has(c), c).toBe(true)
    for (const f of FASCE_MONTABILI) expect(RIQUADRI.has(f), f).toBe(true)
  })

  for (const [famiglia, genera] of Object.entries(FAMIGLIE))
    it(`${famiglia}: ogni casella e fascia del fronte si monta, con pezzi che esistono nel kit`, () => {
      for (const p of progetti(genera, 25)) {
        for (const { p: q } of tuttiICorpi(p)) {
          for (const riga of q.caselle.Fronte)
            for (const c of riga)
              if (c && c !== COPERTA && c !== NASCOSTA)
                expect(MONTABILI.has(c), c).toBe(true)
          for (const f of q.fasce)
            expect(FASCE_MONTABILI.has(f.cella), f.cella).toBe(true)
        }
        const istanze = montaEdificio(
          { progetto: p, matrice: new Matrix4() },
          "x",
        )
        expect(istanze.length).toBeGreaterThan(0)
        for (const i of istanze)
          if (i.pezzo !== FONDALE)
            expect(kit.pezzi, i.pezzo).toHaveProperty(i.pezzo)
      }
    })

  it("il modulo di parete di ogni casella sta dove il guscio disegna la casella", () => {
    for (const genera of Object.values(FAMIGLIE))
      for (const p of progetti(genera, 10)) {
        const posizioni = montaEdificio(
          { progetto: p, matrice: new Matrix4() },
          "s",
        ).map((i) => new Vector3().setFromMatrixPosition(i.matrice))
        for (const { p: q, m } of tuttiICorpi(p)) {
          let y = 0
          q.righe.forEach((h, r) => {
            ;(q.caselle.Fronte[r] ?? []).forEach((c, k) => {
              if (!c || c === COPERTA || c === NASCOSTA) return
              const angolo = new Vector3(0, y, MODULO * k).applyMatrix4(m)
              expect(
                posizioni.some((v) => v.distanceTo(angolo) < 1e-6),
                `${c} in ${q.famiglia}`,
              ).toBe(true)
            })
            y += h
          })
        }
      }
  })

  it("dietro porte e finestre c'è il fondale, dietro i muri ciechi no", () => {
    const p = generaBorgo(new Casuale("f"))
    const istanze = montaEdificio({ progetto: p, matrice: new Matrix4() }, "f")
    const aperture = p.caselle.Fronte.flat().filter(
      (c) => c && !["Terra_Parete", "Piano_Parete"].includes(c),
    ).length
    expect(istanze.filter((i) => i.pezzo === FONDALE)).toHaveLength(aperture)
    for (const f of istanze.filter((i) => i.pezzo === FONDALE))
      expect(new Vector3().setFromMatrixPosition(f.matrice).x).toBeCloseTo(-0.8)
  })

  it("stesso seme, stesso edificio; seme diverso, persiane diverse", () => {
    const p = generaBorgo(new Casuale("b"))
    const a = montaEdificio({ progetto: p, matrice: new Matrix4() }, "uno")
    const b = montaEdificio({ progetto: p, matrice: new Matrix4() }, "uno")
    const c = montaEdificio({ progetto: p, matrice: new Matrix4() }, "due")
    expect(b.map((i) => i.matrice.elements)).toEqual(
      a.map((i) => i.matrice.elements),
    )
    expect(c.map((i) => i.matrice.elements)).not.toEqual(
      a.map((i) => i.matrice.elements),
    )
  })

  it("triangoli: un borgo montato resta sotto i 30 mila", () => {
    const tri = (nome: string) =>
      nome === FONDALE
        ? 2
        : (kit.pezzi as Record<string, { triangoli: number }>)[nome].triangoli
    for (const p of progetti(generaBorgo, 10))
      expect(
        montaEdificio({ progetto: p, matrice: new Matrix4() }, "t").reduce(
          (s, i) => s + tri(i.pezzo),
          0,
        ),
      ).toBeLessThan(30000)
  })
})
