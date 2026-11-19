/*
 * geometrie.test.ts
 * leggiPezzi riconosce pezzo, LOD e parte dai nomi del .glb, sia per i nodi
 * con più parti (gruppo di mesh) sia per quelli con una parte sola (mesh).
 */

import { BoxGeometry, Group, Mesh, MeshStandardMaterial } from "three"
import { describe, expect, it } from "vitest"
import { leggiPezzi } from "./geometrie"

const parte = (nome: string) =>
  new Mesh(new BoxGeometry(), new MeshStandardMaterial({ name: nome }))

describe("geometrie delle tessere", () => {
  it("pezzo, LOD e parte dai nomi", () => {
    const scena = new Group()
    const strato0 = new Group()
    strato0.name = "Strato_LOD0"
    strato0.add(parte("GLB_Faccia"), parte("GLB_Bordo"))
    const cima1 = parte("GLB_Faccia")
    cima1.name = "Cima_LOD1"
    const altro = new Group()
    altro.name = "Luce"
    scena.add(strato0, cima1, altro)
    const pezzi = leggiPezzi(scena)
    expect([...pezzi.keys()]).toEqual(["Strato", "Cima"])
    expect(Object.keys(pezzi.get("Strato")![0])).toEqual(["Faccia", "Bordo"])
    expect(pezzi.get("Cima")![1].Faccia).toBe(cima1.geometry)
  })
})
