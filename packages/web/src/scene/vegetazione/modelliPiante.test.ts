/*
 * modelliPiante.test.ts
 * leggiPiante riconosce pianta e LOD dai nodi <Pianta>_LOD<n>.
 */

import { BoxGeometry, Group, Mesh, MeshStandardMaterial } from "three"
import { describe, expect, it } from "vitest"
import { leggiPiante } from "./modelliPiante"

describe("vegetazione.glb", () => {
  it("pianta e LOD dai nodi, anche con il trattino basso nel nome", () => {
    const scena = new Group()
    const lod0 = new Mesh(new BoxGeometry(), new MeshStandardMaterial())
    lod0.name = "Albero_Tondo_LOD0"
    const lod1 = new Group()
    lod1.name = "Albero_Tondo_LOD1"
    lod1.add(new Mesh(new BoxGeometry(), new MeshStandardMaterial()))
    scena.add(lod0, lod1)
    const m = leggiPiante(scena).get("Albero_Tondo")!
    expect(m[0]!.geometria).toBe(lod0.geometry)
    expect(m[1]).not.toBeNull()
  })
})
