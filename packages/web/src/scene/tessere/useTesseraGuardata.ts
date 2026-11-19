/*
 * useTesseraGuardata.ts
 * La tessera che la telecamera sta guardando: quella sotto il punto attorno
 * a cui gira (target degli OrbitControls). Serve ai livelli di dettaglio:
 * LOD0 per lei e le sei vicine, LOD1 per le altre (lod.ts).
 *
 * useFrame la ricalcola a ogni fotogramma, ma lo stato cambia solo quando
 * il punto guardato passa su un'altra tessera: allora chi la usa si
 * ridisegna una volta, non a ogni fotogramma.
 */

import { chiave, type Hex } from "@corsa-bis/engine"
import { useFrame } from "@react-three/fiber"
import { useState } from "react"
import type { Vector3 } from "three"
import { tesseraSotto } from "./lod"

export function useTesseraGuardata(): Hex {
  const [guardata, setGuardata] = useState<Hex>({ q: 0, r: 0 })
  useFrame(({ controls }) => {
    const target = (controls as { target?: Vector3 } | null)?.target
    if (!target) return
    const h = tesseraSotto(target.x, target.z)
    if (chiave(h) !== chiave(guardata)) setGuardata(h)
  })
  return guardata
}
