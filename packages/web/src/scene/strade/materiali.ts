/*
 * materiali.ts (strade)
 * Materiali di strade e isole delle rotonde, creati una volta sola.
 * polygonOffset: asfalto e segni "vincono" sulle superfici sotto di loro,
 * anche da lontano dove la precisione di profondità è scarsa.
 */

import { MeshStandardMaterial } from "three"
import { COLORI_ISOLA, type MaterialeIsola } from "./isole"

export const MATERIALI_STRADA = {
  asfalto: new MeshStandardMaterial({
    color: "#3a3a3d",
    roughness: 0.9,
    polygonOffset: true,
    polygonOffsetFactor: -1,
    polygonOffsetUnits: -1,
  }),
  marciapiede: new MeshStandardMaterial({ color: "#b9b2a6", roughness: 0.95 }),
  segni: new MeshStandardMaterial({
    color: "#efece4",
    roughness: 0.8,
    polygonOffset: true,
    polygonOffsetFactor: -3,
    polygonOffsetUnits: -3,
  }),
}

export const MATERIALI_ISOLA = Object.fromEntries(
  Object.entries(COLORI_ISOLA).map(([nome, colore]) => [
    nome,
    new MeshStandardMaterial({
      color: colore,
      roughness: nome === "acqua" ? 0.3 : 0.9,
      flatShading: nome !== "acqua",
    }),
  ]),
) as Record<MaterialeIsola, MeshStandardMaterial>
