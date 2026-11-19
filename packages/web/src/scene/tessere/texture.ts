/*
 * texture.ts
 * Carica tutte le texture delle tessere in una volta sola (una Suspense):
 * erba flock, asfalto, cemento, selciato e bordo ondulato, ognuna con il
 * colore (JPG) e la normale (PNG). GDD: "Immagini per il gioco" e
 * "Asfalto e bordo ondulato".
 *
 * Come si preparano (una volta, quando le immagini sono caricate):
 * - colore in sRGB (è un colore); la normale resta lineare (è un dato);
 * - flipY = false: le UV arrivano da Blender attraverso il glTF, che conta la
 *   v dall'alto dell'immagine. Con flipY vero il bordo ondulato sarebbe
 *   capovolto (la copertina di sopra finirebbe sotto);
 * - suoli (erba, asfalto, cemento, selciato): ripetuti nelle due direzioni,
 *   un'immagine ogni 32 unità (le UV sono in unità di gioco);
 * - bordo: ripetuto lungo il bordo (u, un'immagine ogni 32 unità = due onde)
 *   e bloccato sullo spessore (v da 0 a 1 copre tutto il fianco);
 * - anisotropia 8: le texture restano nitide viste di sbieco.
 */

import { useTexture } from "@react-three/drei"
import {
  ClampToEdgeWrapping,
  RepeatWrapping,
  SRGBColorSpace,
  type Texture,
} from "three"

/** Unità di gioco coperte da una ripetizione delle texture (suoli e bordo). */
export const PERIODO_TEXTURE = 32
export const ANISOTROPIA = 8

export const SUOLI = ["erba_flock", "asfalto", "cemento", "selciato"] as const
export type Suolo = (typeof SUOLI)[number]

/** Colore e normale di un materiale. */
export type CoppiaTexture = {
  readonly colore: Texture
  readonly normale: Texture
}

export type TextureTessere = Record<Suolo | "bordo_ondulato", CoppiaTexture>

const NOMI = [...SUOLI, "bordo_ondulato"] as const
const PERCORSI = NOMI.flatMap((n) => [
  `/textures/tessere/${n}_colore.jpg`,
  `/textures/tessere/${n}_normale.png`,
])

/** Prepara una texture appena caricata (vedi il commento in alto). */
function prepara(t: Texture, colore: boolean, bordo: boolean) {
  if (colore) t.colorSpace = SRGBColorSpace
  t.flipY = false
  t.wrapS = RepeatWrapping
  t.wrapT = bordo ? ClampToEdgeWrapping : RepeatWrapping
  t.repeat.set(1 / PERIODO_TEXTURE, bordo ? 1 : 1 / PERIODO_TEXTURE)
  t.anisotropy = ANISOTROPIA
  t.needsUpdate = true
}

/** Tutte le texture delle tessere. È un hook perché carica le immagini (Suspense). */
export function useTextureTessere(): TextureTessere {
  const lette = useTexture(PERCORSI, (tutte) =>
    tutte.forEach((t, i) =>
      prepara(t, i % 2 === 0, NOMI[Math.floor(i / 2)] === "bordo_ondulato"),
    ),
  )
  const coppia = (i: number): CoppiaTexture => ({
    colore: lette[2 * i],
    normale: lette[2 * i + 1],
  })
  return Object.fromEntries(
    NOMI.map((n, i) => [n, coppia(i)]),
  ) as TextureTessere
}
