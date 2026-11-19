/*
 * modelliMonumenti.test.ts
 * leggiMonumenti riconosce nome e LOD dai nodi Monumento_<nome>_LOD<n>.
 */

import { BoxGeometry, Group, Mesh, MeshStandardMaterial } from "three"
import { describe, expect, it } from "vitest"
import { leggiMonumenti } from "./modelliMonumenti"

describe("monumenti.glb", () => {
  it("nome e LOD dai nodi; un nodo può essere la mesh o un gruppo con la mesh", () => {
    const scena = new Group()
    const materiale = new MeshStandardMaterial({ name: "Monumento_Poeta" })
    const lod0 = new Mesh(new BoxGeometry(), materiale)
    lod0.name = "Monumento_Poeta_LOD0"
    const lod1 = new Group()
    lod1.name = "Monumento_Poeta_LOD1"
    lod1.add(new Mesh(new BoxGeometry(), materiale))
    scena.add(lod0, lod1)
    const m = leggiMonumenti(scena).get("Poeta")!
    expect(m[0]!.geometria).toBe(lod0.geometry)
    expect(m[1]!.materiale).toBe(materiale)
  })
})
