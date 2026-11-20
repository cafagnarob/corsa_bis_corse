/*
 * Istanze.tsx
 * Disegna la stessa geometria in molte posizioni con UNA sola chiamata di
 * disegno (InstancedMesh). Riceve geometria, materiale e l'elenco delle
 * matrici (posizione, rotazione e scala di ogni copia).
 *
 * Le matrici cambiano spesso: a ogni cambio di tessera guardata i livelli di
 * dettaglio (PileTessere, Vegetazione, Monumenti) si passano le copie tra
 * LOD0 e LOD1. Ricreare la mesh ogni volta costava uno scatto (e lasciava
 * in memoria della scheda video le matrici vecchie). Perciò:
 * - la mesh si crea con una CAPIENZA (la potenza di 2 che basta) e si
 *   ricrea solo se le copie non ci stanno più o cambiano geometria o
 *   materiale;
 * - quando cambiano le matrici si riscrivono nella mesh che c'è già e si
 *   aggiorna `count` (quante copie disegnare);
 * - la mesh vecchia si libera (dispose) quando viene sostituita o il
 *   componente sparisce.
 *
 * Scrivere nella mesh di Three.js è sincronizzarsi con un sistema esterno a
 * React: è il caso giusto per gli effetti.
 */

import { useEffect, useLayoutEffect, useMemo } from "react"
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

/** La potenza di 2 che contiene n copie (almeno 16): la mesh si ricrea di rado. */
const capienzaPer = (n: number) => Math.max(16, 2 ** Math.ceil(Math.log2(n)))

/** Scrive le matrici nella mesh e dice a Three.js quante copie disegnare. */
function riempi(mesh: InstancedMesh, matrici: readonly Matrix4[]) {
  matrici.forEach((matrice, i) => mesh.setMatrixAt(i, matrice))
  mesh.count = matrici.length
  mesh.instanceMatrix.needsUpdate = true
  // sfera che contiene tutte le copie: serve a Three.js per non disegnare
  // ciò che è fuori dall'inquadratura (frustum culling)
  mesh.computeBoundingSphere()
}

function Istanze({ geometria, materiale, matrici }: IstanzeProps) {
  const capienza = capienzaPer(matrici.length)

  const mesh = useMemo(() => {
    const m = new InstancedMesh(geometria, materiale, capienza)
    m.count = 0
    return m
  }, [geometria, materiale, capienza])

  // la mesh sostituita o smontata libera il suo buffer delle matrici (geometria e materiale sono condivisi)
  useEffect(() => () => mesh.dispose(), [mesh])

  // prima del disegno: le matrici nuove nella mesh che c'è già
  useLayoutEffect(() => riempi(mesh, matrici), [mesh, matrici])

  return <primitive object={mesh} />
}

export default Istanze
