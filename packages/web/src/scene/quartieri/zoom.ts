/*
 * zoom.ts
 * "Quanto siamo lontani": la distanza tra la telecamera e il punto che guarda
 * (il target degli OrbitControls), e i livelli di dettaglio che ne derivano:
 * - vicino (sotto 2.200-2.600): la via sotto il mouse e le sue collegate;
 * - medio (circa da 1.200 a 2.800): i nomi delle arterie, e fino a ~2.600
 *   anche quelli delle vie principali;
 * - lontano (oltre 2.600-3.400): la vista mappa dei quartieri.
 * fattoreZoom è 0 da vicino e 1 da lontano (vista mappa).
 */

import { MathUtils, Vector3, type Camera } from "three"

/** Distanze della telecamera: da qui la "vista mappa" inizia a comparire, da qui è piena. */
export const ZOOM = { comparsa: 2600, pieno: 3400 }

const ORIGINE = new Vector3()

/** Distanza della telecamera dal punto che guarda. */
export function distanzaVista(camera: Camera, controls: unknown): number {
  const target = (controls as { target?: Vector3 } | null)?.target ?? ORIGINE
  return camera.position.distanceTo(target)
}

/** Da 0 a 1 mentre `d` passa da `da` ad `a` (dissolvenza lineare). */
export const sfuma = (d: number, da: number, a: number) =>
  MathUtils.clamp((d - da) / (a - da), 0, 1)

/** 0 da vicino, 1 nella vista mappa. */
export function fattoreZoom(camera: Camera, controls: unknown): number {
  return sfuma(distanzaVista(camera, controls), ZOOM.comparsa, ZOOM.pieno)
}

/** Visibilità dei nomi delle arterie: compaiono a media distanza, spariscono nella vista mappa. */
export const fattoreMedio = (d: number) =>
  sfuma(d, 1000, 1400) * (1 - sfuma(d, 2600, 3000))

/** Visibilità dei nomi delle vie principali: come le arterie, ma spariscono prima. */
export const fattorePrincipali = (d: number) =>
  sfuma(d, 1000, 1400) * (1 - sfuma(d, 2200, 2600))

/** Visibilità della via selezionata e delle collegate: solo da vicino. */
export const fattoreVicino = (d: number) => 1 - sfuma(d, 2200, 2600)
