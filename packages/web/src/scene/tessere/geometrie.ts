/*
 * geometrie.ts
 * Le forme dei pezzi delle tessere, lette da tessere.glb (GDD: "Pezzi delle
 * tessere esportati", 18 novembre): Strato, Cima e le rampe, ognuno in due
 * LOD (LOD0 da vicino, LOD1 da lontano).
 *
 * Nel .glb ogni pezzo ha una parte per materiale (GLB_Faccia, GLB_Bordo,
 * GLB_Interno, GLB_Strada, ...): il loader di three ne fa una mesh figlia
 * per ciascuna. Qui si tengono solo le geometrie, indicizzate per pezzo,
 * LOD e parte; i materiali veri li sceglie il codice (materiali.ts).
 *
 * Convenzioni dei pezzi (uguali ai vecchi segnaposto):
 * - origine al centro della faccia INFERIORE (il pezzo sale da y = 0);
 * - punte dell'esagono lungo l'asse Z;
 * - UV della faccia in unità di gioco; UV del bordo con u lungo il bordo
 *   (in unità) e v sullo spessore.
 *
 * Il file si carica con Draco (decoder locale in public/draco/).
 */

import { useGLTF } from "@react-three/drei"
import type { BufferGeometry, Mesh, Object3D } from "three"

const PERCORSO = "/models/tessere/tessere.glb"
const DRACO = "/draco/"

export type Lod = 0 | 1
/** Nome del materiale nel .glb senza "GLB_". */
export type ParteTessera =
  | "Faccia"
  | "Bordo"
  | "Interno"
  | "Strada"
  | "Marciapiede"
  | "Striscia"
  | "Fianco"
/** Le parti di un pezzo in un LOD (solo quelle che ha). */
export type PartiPezzo = Partial<Record<ParteTessera, BufferGeometry>>
/** Pezzo (Strato, Cima, Rampa_urbana_1, ...) → parti del LOD0 e del LOD1. */
export type GeometrieTessere = ReadonlyMap<
  string,
  readonly [PartiPezzo, PartiPezzo]
>

const cache = new WeakMap<Object3D, GeometrieTessere>()

/** Legge dalla scena del .glb le geometrie di ogni pezzo, per LOD e parte. */
export function leggiPezzi(scena: Object3D): GeometrieTessere {
  const pezzi = new Map<string, [PartiPezzo, PartiPezzo]>()
  for (const nodo of scena.children) {
    const nome = /^(.+)_LOD([01])$/.exec(nodo.name)
    if (!nome) continue
    const [, pezzo, lod] = nome
    const voce = pezzi.get(pezzo) ?? [{}, {}]
    // un nodo con una sola parte è già la mesh; con più parti è un gruppo di mesh
    const mesh = (nodo as Mesh).isMesh
      ? [nodo as Mesh]
      : (nodo.children.filter((c) => (c as Mesh).isMesh) as Mesh[])
    for (const m of mesh) {
      const materiale = Array.isArray(m.material) ? m.material[0] : m.material
      const parte = materiale.name.replace(/^GLB_/, "") as ParteTessera
      voce[Number(lod) as Lod][parte] = m.geometry
    }
    pezzi.set(pezzo, voce)
  }
  return pezzi
}

/** Le geometrie di tessere.glb. È un hook perché carica il file (Suspense). */
export function useGeometrieTessere(): GeometrieTessere {
  const { scene } = useGLTF(PERCORSO, DRACO)
  let g = cache.get(scene)
  if (!g) {
    g = leggiPezzi(scene)
    cache.set(scene, g)
  }
  return g
}

useGLTF.preload(PERCORSO, DRACO)
