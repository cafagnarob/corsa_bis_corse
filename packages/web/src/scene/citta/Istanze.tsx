/*
 * Istanze.tsx
 * Disegna la stessa geometria in molte posizioni con UNA sola chiamata di
 * disegno (InstancedMesh). Riceve geometria, materiale e l'elenco delle
 * matrici (posizione, rotazione e scala di ogni copia).
 *
 * La mesh si crea in useMemo: si ricrea solo se cambiano i dati in ingresso.
 */

import { useMemo } from "react"
import {
  InstancedMesh,
  type BufferGeometry,
  type Material,
  type Matrix4,
} from "three"

type IstanzeProps = {
  geometria: BufferGeometry
  materiale: Material
  matrici: readonly Matrix4[]
}

function Istanze({ geometria, materiale, matrici }: IstanzeProps) {
  const mesh = useMemo(() => {
    const m = new InstancedMesh(geometria, materiale, matrici.length)
    matrici.forEach((matrice, i) => m.setMatrixAt(i, matrice))
    m.instanceMatrix.needsUpdate = true
    // sfera che contiene tutte le copie: serve a Three.js per non disegnare
    // ciò che è fuori dall'inquadratura (frustum culling)
    m.computeBoundingSphere()
    return m
  }, [geometria, materiale, matrici])

  return <primitive object={mesh} />
}

export default Istanze
