/*
 * montati.ts
 * Quali edifici sono montati col kit in questo momento, detto allo shader
 * delle facciate dei gusci: una piccola texture con un texel per edificio
 * (rosso 255 = montato). Le caselle del fronte che il kit sa montare hanno
 * nei vertici il numero del loro edificio (gusci.ts); lo shader legge il
 * texel e, se l'edificio è montato, butta il vertice fuori dallo schermo.
 * Così le chiamate di disegno dei gusci restano cinque, e accendere o
 * spegnere un edificio è cambiare un byte.
 *
 * La texture è larga LARGHEZZA texel e alta quanto serve; si legge con
 * texelFetch (WebGL2, quello di react-three-fiber).
 */

import { DataTexture, RedFormat, UnsignedByteType } from "three"

export const LARGHEZZA = 1024

export type Montati = {
  readonly texture: DataTexture
  /** Gli edifici montati adesso (tutti gli altri tornano guscio). */
  imposta(edifici: Iterable<number>): void
}

export function creaMontati(quanti: number): Montati {
  const altezza = Math.max(1, Math.ceil(quanti / LARGHEZZA))
  const dati = new Uint8Array(LARGHEZZA * altezza)
  const texture = new DataTexture(
    dati,
    LARGHEZZA,
    altezza,
    RedFormat,
    UnsignedByteType,
  )
  texture.needsUpdate = true
  return {
    texture,
    imposta(edifici) {
      dati.fill(0)
      for (const i of edifici) dati[i] = 255
      texture.needsUpdate = true
    },
  }
}

/** Il pezzo di shader dei vertici che nasconde le caselle degli edifici montati (va dopo <project_vertex>). */
export const NASCONDI_MONTATI = /* glsl */ `
  if (edificio >= 0.0) {
    int i = int(edificio + 0.5);
    if (texelFetch(montati, ivec2(i % ${LARGHEZZA}, i / ${LARGHEZZA}), 0).r > 0.5) gl_Position = vec4(0.0, 0.0, 2.0, 1.0);
  }`
export const DICHIARA_MONTATI = /* glsl */ `
attribute float edificio;
uniform sampler2D montati;`
