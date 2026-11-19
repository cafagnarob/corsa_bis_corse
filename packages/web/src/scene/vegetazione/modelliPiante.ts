/*
 * modelliPiante.ts
 * Le piante di cartone, lette da vegetazione.glb (GDD: "Vegetazione
 * esportata", 18 novembre): Abete, Abete_Festoni, Albero_Tondo,
 * Albero_Goccia, Cespuglio_Cupola, Cespuglio_Nuvola, Siepe.
 *
 * Nel .glb ogni pianta ha due nodi, <Pianta>_LOD0 e _LOD1, tutti
 * nell'origine (il piede della pianta), in metri reali, ognuno con il suo
 * materiale (tempera, decoro, tronco e bordo cotti in un'immagine). Qui si
 * tengono geometria e materiale di ogni pianta per LOD; dove e quanto grandi
 * lo decidono piante.ts e raggruppa.ts.
 */

import { useGLTF } from "@react-three/drei"
import type { BufferGeometry, Material, Mesh, Object3D } from "three"

const PERCORSO = "/models/arredo/vegetazione.glb"
const DRACO = "/draco/"

export type LodPianta = {
  readonly geometria: BufferGeometry
  readonly materiale: Material
}
/** Pianta (Abete, Siepe, ...) → [LOD0, LOD1]. */
export type ModelliPiante = ReadonlyMap<
  string,
  readonly [LodPianta | null, LodPianta | null]
>

const cache = new WeakMap<Object3D, ModelliPiante>()

/** Legge dalla scena del .glb geometria e materiale di ogni pianta, per LOD. */
export function leggiPiante(scena: Object3D): ModelliPiante {
  const modelli = new Map<string, [LodPianta | null, LodPianta | null]>()
  for (const nodo of scena.children) {
    const nome = /^(.+)_LOD([01])$/.exec(nodo.name)
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

/** Le piante di vegetazione.glb. È un hook perché carica il file (Suspense). */
export function usePiante(): ModelliPiante {
  const { scene } = useGLTF(PERCORSO, DRACO)
  let m = cache.get(scene)
  if (!m) {
    m = leggiPiante(scene)
    cache.set(scene, m)
  }
  return m
}

useGLTF.preload(PERCORSO, DRACO)
