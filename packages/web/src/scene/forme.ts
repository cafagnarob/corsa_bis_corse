/*
 * forme.ts
 * Forme unitarie condivise da tutta la scena: si scalano per ottenere le
 * misure volute (anche come istanze di una InstancedMesh). Base a y = 0.
 */

import { BoxGeometry, CylinderGeometry } from "three"

/** Cubo 1 × 1 × 1 con la base all'origine. */
export const cubo = new BoxGeometry(1, 1, 1).translate(0, 0.5, 0)

/** Cilindro di raggio 1 e altezza 1 con la base all'origine. */
export const cilindro = new CylinderGeometry(1, 1, 1, 32).translate(0, 0.5, 0)
