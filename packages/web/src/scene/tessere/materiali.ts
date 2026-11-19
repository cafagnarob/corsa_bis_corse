/*
 * materiali.ts
 * Materiali dei pezzi della tessera, con le texture di Blender (texture.ts).
 *
 * - Faccia della cima: erba flock, asfalto o selciato, secondo il tipo.
 * - Bordo ondulato (il fianco di cartone di strati e cime):
 *   - strati: un'onda ogni 16 unità, e ogni livello un po' più chiaro del
 *     precedente (GDD: color = 0,70 + 0,08 × (k − 1), può superare 1);
 *   - cima: un'onda ogni 4 unità (è alta solo 2), colore pieno.
 * - Strade: asfalto sulle carreggiate, cemento sui marciapiedi.
 * - Rampe: carreggiata, marciapiedi e strisce come le strade; i tagli del
 *   cartone con il bordo ondulato, i due fianchi a cuneo in kraft liscio.
 * - Volumi segnaposto: un colore piatto.
 *
 * Le facce che non si vedono mai (sotto degli strati, sopra degli strati
 * coperta dalla cima, sotto della cima) non si disegnano: vedi PileTessere.
 *
 * Ogni materiale si crea una volta sola e si riusa (cache), anche con
 * centinaia di tessere: la cache è legata alle texture caricate.
 */

import {
  ClampToEdgeWrapping,
  Color,
  MeshStandardMaterial,
  RepeatWrapping,
  SRGBColorSpace,
  type Texture,
} from "three"
import type { TipoCima } from "@corsa-bis/engine"
import {
  ANISOTROPIA,
  useTextureTessere,
  type CoppiaTexture,
  type TextureTessere,
} from "./texture"

export type { TipoCima }

/** Rugosità fissa di ogni materiale, calcolata dal bake (tabelle del GDD). */
const RUGOSITA = {
  erba_flock: 0.92,
  asfalto: 0.92,
  cemento: 0.9,
  selciato: 0.81,
  bordo_ondulato: 0.94,
} as const

/** Un materiale con colore, normale e rugosità fissa. */
const conTexture = (
  { colore, normale }: CoppiaTexture,
  roughness: number,
  color = new Color(1, 1, 1),
) =>
  new MeshStandardMaterial({
    map: colore,
    normalMap: normale,
    roughness,
    color,
  })

/**
 * Una copia di una texture del bordo con un'altra ripetizione (stessa
 * immagine, caricata una volta). Le impostazioni si danno tutte qui: la copia
 * nasce al primo disegno, forse prima che texture.ts abbia preparato l'originale.
 */
function bordoRipetuto(t: Texture, u: number, colore: boolean): Texture {
  const c = t.clone()
  if (colore) c.colorSpace = SRGBColorSpace
  c.flipY = false
  c.wrapS = RepeatWrapping
  c.wrapT = ClampToEdgeWrapping
  c.repeat.set(u, 1)
  c.anisotropy = ANISOTROPIA
  c.needsUpdate = true
  return c
}

export type MaterialiTessere = {
  /** Faccia superiore della cima, per tipo. */
  readonly cime: Record<TipoCima, MeshStandardMaterial>
  /** Bordo ondulato della cima. */
  readonly bordoCima: MeshStandardMaterial
  /** Bordo ondulato dello strato al livello k (1 = il più basso). */
  readonly bordoStrato: (k: number) => MeshStandardMaterial
  /** Asfalto delle carreggiate (vince sulle superfici sotto: polygonOffset). */
  readonly asfalto: MeshStandardMaterial
  /** Cemento dei marciapiedi. */
  readonly cemento: MeshStandardMaterial
  /** Tagli del cartone della rampa (bordo ondulato, un'onda ogni 16 unità). */
  readonly bordoRampa: MeshStandardMaterial
  /** Fianchi a cuneo della rampa: kraft liscio, senza immagine. */
  readonly fiancoRampa: MeshStandardMaterial
}

/** Kraft del cartone, per le facce senza immagine. */
const KRAFT = "#b08a60"

const cache = new WeakMap<Texture, MaterialiTessere>()

function crea(t: TextureTessere): MaterialiTessere {
  const bordi = new Map<number, MeshStandardMaterial>()
  const bordo = t.bordo_ondulato
  // la cima è alta 2: un'onda ogni 4 unità invece che ogni 16
  const bordoCorto = {
    colore: bordoRipetuto(bordo.colore, 1 / 8, true),
    normale: bordoRipetuto(bordo.normale, 1 / 8, false),
  }
  const asfalto = conTexture(t.asfalto, RUGOSITA.asfalto)
  asfalto.polygonOffset = true
  asfalto.polygonOffsetFactor = -1
  asfalto.polygonOffsetUnits = -1
  return {
    cime: {
      erba: conTexture(t.erba_flock, RUGOSITA.erba_flock),
      asfalto: conTexture(t.asfalto, RUGOSITA.asfalto),
      selciato: conTexture(t.selciato, RUGOSITA.selciato),
    },
    bordoCima: conTexture(bordoCorto, RUGOSITA.bordo_ondulato),
    bordoStrato: (k) => {
      let m = bordi.get(k)
      if (!m) {
        const chiaro = 0.7 + 0.08 * (k - 1)
        m = conTexture(
          bordo,
          RUGOSITA.bordo_ondulato,
          new Color(chiaro, chiaro, chiaro),
        )
        bordi.set(k, m)
      }
      return m
    },
    asfalto,
    cemento: conTexture(t.cemento, RUGOSITA.cemento),
    bordoRampa: conTexture(bordo, RUGOSITA.bordo_ondulato),
    fiancoRampa: new MeshStandardMaterial({
      color: KRAFT,
      roughness: RUGOSITA.bordo_ondulato,
      flatShading: true,
    }),
  }
}

/** Tutti i materiali con texture delle tessere. È un hook perché carica le texture (Suspense). */
export function useMaterialiTessere(): MaterialiTessere {
  const t = useTextureTessere()
  let m = cache.get(t.erba_flock.colore)
  if (!m) {
    m = crea(t)
    cache.set(t.erba_flock.colore, m)
  }
  return m
}

// ---------- volumi segnaposto ----------

const cacheVolumi = new Map<string, MeshStandardMaterial>()

/** Materiale dei volumi segnaposto di un colore (uno per colore, condiviso). */
export function materialeVolume(colore: string): MeshStandardMaterial {
  let m = cacheVolumi.get(colore)
  if (!m) {
    m = new MeshStandardMaterial({
      color: colore,
      roughness: 0.9,
      flatShading: true,
    })
    cacheVolumi.set(colore, m)
  }
  return m
}
