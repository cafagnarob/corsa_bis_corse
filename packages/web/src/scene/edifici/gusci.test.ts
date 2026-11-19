/*
 * gusci.test.ts
 * I generatori danno progetti coerenti (ogni casella ha un riquadro
 * dell'atlante, righe e colonne giuste) e i gusci pesano poco.
 */

import { Casuale } from "@corsa-bis/engine"
import { type BufferGeometry, Matrix4, Vector3 } from "three"
import { describe, expect, it } from "vitest"
import { RIQUADRI } from "./atlante"
import { generaBorgo } from "./borgo"
import { generaCapannone } from "./capannoni"
import { generaCorte } from "./corte"
import { generaGrattacielo } from "./grattacieli"
import { costruisciGusci } from "./gusci"
import { generaPalazzone } from "./palazzoni"
import {
  COPERTA,
  impronta,
  NASCOSTA,
  larghezzaDi,
  PARETI,
  profonditaDi,
  type Progetto,
} from "./progetto"
import { generaVilletta } from "./villette"

const progetti = (genera: (r: Casuale) => Progetto, n: number) =>
  Array.from({ length: n }, (_, i) => genera(new Casuale(`prova-${i}`)))

function coerente(p: Progetto) {
  for (const parete of PARETI) {
    const righe = p.caselle[parete]
    expect(righe).toHaveLength(p.righe.length)
    const colonne = parete === "Fronte" || parete === "Retro" ? p.nW : p.nD
    for (const riga of righe) {
      expect(riga).toHaveLength(colonne)
      riga.forEach((nome, k) => {
        // una casella COPERTA viene solo dopo un riquadro largo due moduli
        if (nome === COPERTA)
          expect(RIQUADRI.get(riga[k - 1]!)?.larghezza).toBe(4)
        else if (nome && nome !== NASCOSTA)
          expect(RIQUADRI.has(nome), nome).toBe(true)
      })
    }
  }
  for (const f of p.fasce) expect(RIQUADRI.has(f.cella)).toBe(true)
  for (const c of p.corpi ?? []) coerente(c.progetto)
}

/** Ogni triangolo guarda dalla parte della sua normale (giro antiorario visto da fuori). */
function giriGiusti(g: BufferGeometry) {
  const pos = g.getAttribute("position")
  const nor = g.getAttribute("normal")
  const idx = g.index!
  const [a, b, c, n] = [
    new Vector3(),
    new Vector3(),
    new Vector3(),
    new Vector3(),
  ]
  let sbagliati = 0
  for (let i = 0; i < idx.count; i += 3) {
    a.fromBufferAttribute(pos, idx.getX(i))
    b.fromBufferAttribute(pos, idx.getX(i + 1))
    c.fromBufferAttribute(pos, idx.getX(i + 2))
    n.fromBufferAttribute(nor, idx.getX(i))
    if (b.sub(a).cross(c.sub(a)).dot(n) <= 0) sbagliati++
  }
  return sbagliati
}

describe("progetti e gusci", () => {
  it("borgo: 1-3 moduli, 1-3 piani, almeno un ingresso al terra", () => {
    for (const p of progetti(generaBorgo, 40)) {
      coerente(p)
      expect(p.nW).toBeGreaterThanOrEqual(1)
      expect(p.nW).toBeLessThanOrEqual(3)
      expect(
        p.caselle.Fronte[0].some(
          (c) => c?.startsWith("Terra_Porta") || c === "Terra_Portone",
        ),
      ).toBe(true)
    }
  })

  it("palazzoni: stecche e torri, un androne per ogni vano scala", () => {
    const tutti = progetti(generaPalazzone, 30)
    expect(new Set(tutti.map((p) => p.famiglia))).toEqual(
      new Set(["stecca", "torre"]),
    )
    for (const p of tutti) {
      coerente(p)
      const androni = p.caselle.Fronte[0].filter(
        (c) => c === "Pal_Terra_Androne",
      ).length
      expect(androni).toBe(p.scatole.length) // un torrino per vano
    }
  })

  it("villette: porta sul fronte, tetto a capanna, recinto attorno alla casa col cancello davanti alla porta", () => {
    for (const p of progetti(generaVilletta, 40)) {
      coerente(p)
      expect(p.tetto.tipo).toBe("capanna")
      const kd = p.caselle.Fronte[0].findIndex((c) =>
        c?.startsWith("Villa_Porta"),
      )
      expect(kd).toBeGreaterThanOrEqual(0)
      const r = p.recinto!
      expect(r.x1).toBeGreaterThan(0)
      expect(r.x0).toBeLessThan(-profonditaDi(p))
      expect(r.z0).toBeLessThan(0)
      expect(r.z1).toBeGreaterThan(larghezzaDi(p))
      expect(r.cancello.z).toBeCloseTo(2 * kd + 1)
      expect(impronta(p)).toEqual({ x0: r.x0, x1: r.x1, z0: r.z0, z1: r.z1 })
    }
  })

  it("capannoni: lunghezza pari (denti dello shed), portoni da due moduli, uffici davanti", () => {
    const tutti = progetti(generaCapannone, 40)
    expect(tutti.some((p) => p.tetto.tipo === "shed")).toBe(true)
    expect(tutti.some((p) => p.tetto.tipo === "piano")).toBe(true)
    expect(tutti.some((p) => p.caselle.Fronte[0].includes("Cap_Portone"))).toBe(
      true,
    )
    for (const p of tutti) {
      coerente(p)
      expect(p.nW % 2).toBe(0)
      for (const c of p.corpi ?? []) expect(impronta(p).x1).toBeCloseTo(c.x)
    }
  })

  it("grattacieli: 2-3 scatole impilate, sempre più strette, 8-10 piani, coronamento in cima", () => {
    for (const p of progetti(generaGrattacielo, 40)) {
      coerente(p)
      const corpi = p.corpi ?? []
      expect(corpi.length).toBeGreaterThanOrEqual(1)
      expect(corpi.length).toBeLessThanOrEqual(2)
      const piani = [p, ...corpi.map((c) => c.progetto)].reduce(
        (s, q) => s + q.righe.filter((h) => h >= 3).length,
        0,
      )
      expect(piani).toBeGreaterThanOrEqual(8)
      expect(piani).toBeLessThanOrEqual(10)
      // ogni scatola sta dentro l'impronta della base
      const base = impronta({ ...p, corpi: [] })
      for (const c of corpi) {
        expect(c.x - profonditaDi(c.progetto)).toBeGreaterThanOrEqual(
          base.x0 - 0.01,
        )
        expect(c.z + larghezzaDi(c.progetto)).toBeLessThanOrEqual(
          base.z1 + 0.01,
        )
      }
      const ultima = corpi[corpi.length - 1].progetto
      expect(
        ultima.caselle.Fronte.at(-1)!.every((c) => c === "Gr_Coronamento"),
      ).toBe(true)
      expect(ultima.scatole).toHaveLength(1) // locale macchine
    }
  })

  it("palazzi a corte: quattro ali chiuse attorno al cortile, portone sulla strada, ali corte non più alte degli angoli", () => {
    for (const p of progetti(generaCorte, 30)) {
      coerente(p)
      expect(p.famiglia).toBe("corte")
      const tuttiCorpi = [
        { progetto: p, x: 0, z: 0, rotazione: 0 },
        ...(p.corpi ?? []),
      ]
      const strada = tuttiCorpi.filter((c) => !c.rotazione)
      const corte = tuttiCorpi.filter(
        (c) => Math.abs(Math.abs(c.rotazione ?? 0) - Math.PI / 2) < 1e-9,
      )
      expect(corte).toHaveLength(2)
      // il portone d'ingresso, una sola volta sull'ala sulla strada
      expect(
        strada
          .flatMap((c) => c.progetto.caselle.Fronte[0])
          .filter((x) => x === "Terra_Portone"),
      ).toHaveLength(1)
      // l'ala sulla strada copre tutta la lunghezza del blocco, senza buchi
      const lunghezza = strada.reduce((s, c) => s + larghezzaDi(c.progetto), 0)
      const imp = impronta(p)
      expect(imp.z1 - imp.z0).toBeCloseTo(lunghezza)
      expect(imp.x1).toBeCloseTo(0)
      // ali corte alte al massimo come il palazzo d'angolo più basso
      const angoli = Math.min(...strada.map((c) => c.progetto.righe.length))
      for (const c of corte)
        expect(c.progetto.righe.length).toBeLessThanOrEqual(
          Math.max(...strada.map((x) => x.progetto.righe.length)),
        )
      expect(angoli).toBeGreaterThanOrEqual(3)
    }
  })

  const tutte = [
    ...progetti(generaCorte, 10),
    ...progetti(generaGrattacielo, 20),
    ...progetti(generaBorgo, 20),
    ...progetti(generaPalazzone, 10),
    ...progetti(generaVilletta, 20),
    ...progetti(generaCapannone, 20),
  ]

  it("ogni faccia guarda fuori", () => {
    const g = costruisciGusci(
      tutte.map((progetto) => ({
        progetto,
        matrice: new Matrix4()
          .makeRotationY(0.7)
          .scale(new Vector3(5.2, 5.2, 5.2)),
      })),
    )
    for (const geo of [...g.facciate, g.intonaco, g.tetti, g.coppi])
      expect(giriGiusti(geo)).toBe(0)
    expect(g.coppi.index!.count).toBeGreaterThan(0)
    expect(g.facciate[1].index!.count).toBeGreaterThan(0)
  })

  it("UV dentro i riquadri, e pochi triangoli per casa", () => {
    const lista = tutte.map((progetto) => ({
      progetto,
      matrice: new Matrix4(),
    }))
    const g = costruisciGusci(lista)
    for (const pagina of g.facciate) {
      const uv = pagina.getAttribute("uv")
      for (let i = 0; i < uv.count; i++) {
        expect(uv.getX(i)).toBeGreaterThanOrEqual(0)
        expect(uv.getX(i)).toBeLessThanOrEqual(1)
      }
    }
    const triangoli = [...g.facciate, g.intonaco, g.tetti, g.coppi].reduce(
      (s, x) => s + x.index!.count / 3,
      0,
    )
    console.log(
      "triangoli per edificio in media:",
      Math.round(triangoli / lista.length),
    )
    expect(triangoli / lista.length).toBeLessThan(600)
  })

  it("le caselle montabili del fronte portano il numero del loro edificio, il resto −1", () => {
    const lista = [
      generaBorgo(new Casuale("n0")),
      generaPalazzone(new Casuale("n1")),
      generaCorte(new Casuale("n2")),
    ].map((progetto) => ({ progetto, matrice: new Matrix4() }))
    const g = costruisciGusci(lista)
    const ids = new Set<number>()
    for (const pagina of g.facciate) {
      const a = pagina.getAttribute("edificio")
      for (let i = 0; i < a.count; i++) ids.add(a.getX(i))
    }
    expect([...ids].sort()).toEqual([-1, 0, 1, 2])
    // intonaco e tetti non si nascondono mai
    const into = g.intonaco.getAttribute("edificio")
    for (let i = 0; i < into.count; i++) expect(into.getX(i)).toBe(-1)
  })

  it("agli angoli il fianco tocca il fronte e il retro (niente fessure)", () => {
    for (const progetto of [
      generaPalazzone(new Casuale("a1")),
      generaBorgo(new Casuale("a2")),
    ]) {
      const g = costruisciGusci([{ progetto, matrice: new Matrix4() }])
      const D = profonditaDi(progetto)
      // i vertici di ognuno dei due fianchi (normale −Z e +Z) vanno da x = −D a x = 0
      for (const verso of [-1, 1]) {
        const xs: number[] = []
        for (const geo of [...g.facciate, g.intonaco]) {
          const pos = geo.getAttribute("position")
          const nor = geo.getAttribute("normal")
          for (let i = 0; i < pos.count; i++)
            if (nor.getZ(i) * verso > 0.99 && pos.getY(i) < 3)
              xs.push(pos.getX(i)) // il piano terra: sopra ci sono parapetti e falde
        }
        expect(Math.min(...xs)).toBeCloseTo(-D)
        expect(Math.max(...xs)).toBeCloseTo(0)
      }
    }
  })
})
