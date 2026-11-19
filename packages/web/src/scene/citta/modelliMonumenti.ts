/*
 * modelliMonumenti.ts
 * I monumenti delle rotonde, letti da monumenti.glb (GDD: "Monumenti
 * esportati", 18 novembre): Oratore, Pensatore, Fiaccola, Poeta, Equestre.
 *
 * Nel .glb ogni monumento ha due nodi, Monumento_<nome>_LOD0 e _LOD1, tutti
 * nell'origine (centro della base del basamento, a terra), davanti +X, in
 * metri reali. Un materiale per monumento, con il cartone cotto in una
 * texture, condiviso dai due LOD. Qui si tengono geometria e materiale di
 * ogni monumento per LOD; scala e posizione le decide raggruppa.ts.
 */

import { useGLTF } from "@react-three/drei"
import type { BufferGeometry, Material, Mesh, Object3D } from "three"

const PERCORSO = "/models/arredo/monumenti.glb"
const DRACO = "/draco/"

export type LodMonumento = {
  readonly geometria: BufferGeometry
  readonly materiale: Material
}
/** Monumento (Oratore, ...) → [LOD0, LOD1]. */
export type ModelliMonumenti = ReadonlyMap<
  string,
  readonly [LodMonumento | null, LodMonumento | null]
>

const cache = new WeakMap<Object3D, ModelliMonumenti>()

/** Legge dalla scena del .glb geometria e materiale di ogni monumento, per LOD. */
export function leggiMonumenti(scena: Object3D): ModelliMonumenti {
  const modelli = new Map<string, [LodMonumento | null, LodMonumento | null]>()
  for (const nodo of scena.children) {
    const nome = /^Monumento_(.+)_LOD([01])$/.exec(nodo.name)
    if (!nome) continue
    // una sola parte: il nodo è la mesh (o un gruppo con la mesh dentro)
    const mesh = (
      (nodo as Mesh).isMesh
        ? nodo
        : nodo.children.find((c) => (c as Mesh).isMesh)
    ) as Mesh | undefined
    if (!mesh) continue
    const voce = modelli.get(nome[1]) ?? [null, null]
    const materiale = Array.isArray(mesh.material)
      ? mesh.material[0]
      : mesh.material
    voce[Number(nome[2])] = { geometria: mesh.geometry, materiale }
    modelli.set(nome[1], voce)
  }
  return modelli
}

/** I monumenti di monumenti.glb. È un hook perché carica il file (Suspense). */
export function useMonumenti(): ModelliMonumenti {
  const { scene } = useGLTF(PERCORSO, DRACO)
  let m = cache.get(scene)
  if (!m) {
    m = leggiMonumenti(scene)
    cache.set(scene, m)
  }
  return m
}

useGLTF.preload(PERCORSO, DRACO)
