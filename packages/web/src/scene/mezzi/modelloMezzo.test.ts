/*
 * modelloMezzo.test.ts
 * preparaMezzo con un finto mezzo: centrato in pianta, scalato ×5,2, un gruppo
 * per materiale.
 */
import { describe, expect, it } from "vitest"
import {
  Bone,
  Box3,
  BoxGeometry,
  BufferAttribute,
  Group,
  Mesh,
  MeshStandardMaterial,
  Skeleton,
  SkinnedMesh,
  Vector3,
  type InstancedBufferAttribute,
} from "three"
import { misureMezzo, preparaMezzo, SCALA_MEZZI } from "./modelloMezzo"

/** Un "bus" lungo 12 m da x = 0 a x = 12, con due pezzi dello stesso materiale e uno diverso. */
function finto() {
  const radice = new Group()
  const lod1 = new Group()
  lod1.name = "LOD1"
  const cartone = new MeshStandardMaterial()
  const vetro = new MeshStandardMaterial()
  const scocca = new Mesh(
    new BoxGeometry(12, 3, 2.5).translate(6, 1.5, 0),
    cartone,
  )
  const tetto = new Mesh(
    new BoxGeometry(11, 0.2, 2.3).translate(6, 3.1, 0),
    cartone,
  )
  const finestre = new Mesh(
    new BoxGeometry(10, 1, 2.6).translate(6, 2, 0),
    vetro,
  )
  lod1.add(scocca, tetto, finestre)
  radice.add(lod1)
  return radice
}

describe("preparaMezzo", () => {
  it("centra in pianta, scala ×5,2 e fa un gruppo per materiale", () => {
    const lod = preparaMezzo(finto())
    expect(lod[0]).not.toBeNull()
    expect(lod.slice(1).every((l) => l === null)).toBe(true) // gli altri LOD mancano nel finto
    const { geometria, materiali } = lod[0]!
    const box = new Box3().setFromBufferAttribute(
      geometria.getAttribute("position") as never,
    )
    const misure = box.getSize(new Vector3())
    expect(misure.x).toBeCloseTo(12 * SCALA_MEZZI, 3)
    expect(box.getCenter(new Vector3()).x).toBeCloseTo(0, 3)
    expect(box.min.y).toBeCloseTo(0, 3) // le ruote restano a terra
    expect(geometria.getAttribute("uv")).toBeDefined() // le UV dell'atlante restano
    expect(materiali).toHaveLength(2)
    expect(geometria.groups).toHaveLength(2)
  })
})

describe("snodato", () => {
  /** Uno "snodato" di 18 m, da x = −9 a x = 9: la metà dietro il giunto (x < −2,05) segue l'osso Snodo. */
  function snodatoFinto() {
    const radice = new Group()
    const telaio = new Bone()
    telaio.name = "Telaio"
    const snodo = new Bone()
    snodo.name = "Snodo"
    snodo.position.x = -2.05
    telaio.add(snodo)
    // la ruota posteriore ha il suo osso, figlio di Snodo
    const ruota = new Bone()
    ruota.name = "Ruota_Post_Sx"
    ruota.position.x = -4
    snodo.add(ruota)
    const g = new BoxGeometry(18, 3, 2.5, 18, 1, 1).translate(0, 1.5, 0)
    const n = g.getAttribute("position").count
    const ossa = new Uint16Array(n * 4)
    const pesi = new Float32Array(n * 4)
    for (let i = 0; i < n; i++) {
      const x = g.getAttribute("position").getX(i)
      // il fondo della coda (x < −7) è "la ruota": segue il suo osso, non Snodo direttamente
      ossa[4 * i] = x < -7 ? 2 : x < -2.05 ? 1 : 0
      pesi[4 * i] = 1
    }
    g.setAttribute("skinIndex", new BufferAttribute(ossa, 4))
    g.setAttribute("skinWeight", new BufferAttribute(pesi, 4))
    const mesh = new SkinnedMesh(g, new MeshStandardMaterial())
    mesh.add(telaio)
    mesh.bind(new Skeleton([telaio, snodo, ruota]))
    const lod1 = new Group()
    lod1.name = "LOD1"
    lod1.add(mesh)
    radice.add(lod1)
    return radice
  }

  it("misure: lunghezza, giunto in unità di gioco; un mezzo rigido non ha giunto", () => {
    const m = misureMezzo(snodatoFinto())
    expect(m.lunghezza).toBeCloseTo(18 * SCALA_MEZZI, 3)
    expect(m.giunto).toBeCloseTo(-2.05 * SCALA_MEZZI, 3)
    expect(misureMezzo(finto()).giunto).toBeNull()
  })

  it("il peso dello snodo per vertice e un angolo per istanza", () => {
    const { geometria, materiali } = preparaMezzo(snodatoFinto())[0]!
    const peso = geometria.getAttribute("pesoSnodo")
    const pos = geometria.getAttribute("position")
    for (let i = 0; i < pos.count; i++)
      expect(peso.getX(i)).toBe(pos.getX(i) < -2.05 * SCALA_MEZZI ? 1 : 0)
    expect(
      (geometria.getAttribute("angoloSnodo") as InstancedBufferAttribute)
        .isInstancedBufferAttribute,
    ).toBe(true)
    expect(materiali[0].onBeforeCompile).toBeTypeOf("function")
    // un mezzo rigido non ha né l'uno né l'altro
    expect(
      preparaMezzo(finto())[0]!.geometria.getAttribute("pesoSnodo"),
    ).toBeUndefined()
  })
})
