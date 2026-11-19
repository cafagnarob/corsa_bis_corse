/*
 * materialiKit.ts
 * I materiali dei pezzi del kit (kit_edifici.glb). Nel glb i materiali sono
 * segnaposto con un nome (GDD, "Export del kit"): qui ognuno diventa il
 * materiale vero, con le texture ripetibili del kit.
 *
 * - EDI_Intonaco: intonaco_colore/_normale, tinto PER ISTANZA (colore della
 *   casa, o lo stucco di cornici e cornicioni): instanceColor;
 * - EDI_Kraft: kraft_colore/_normale; EDI_Interno: lo stesso kraft scurito
 *   (×0,3), per le facce dentro i buchi e i tagli;
 * - EDI_Legno: legno_colore/_normale;
 * - EDI_Tenda: tenda_colore è la maschera delle strisce: bianco = colore
 *   della tenda (per istanza), nero = crema;
 * - EDI_Bordo: il taglio del cartone, la stessa texture del bordo delle
 *   tessere (textures/tessere/bordo_ondulato_*): u = lunghezza, v = spessore;
 * - tutti gli altri (vetri, coppi, insegne e scritte, spago, carta, pietra)
 *   restano come arrivano dal glb: hanno già il loro colore.
 *
 * Le UV del kit sono in metri: le texture del kit hanno un periodo di 4 m
 * (repeat 1/4); il bordo delle tessere ha un'onda ogni 32 unità di gioco,
 * cioè 32 / 5,2 m (repeat 5,2 / 32 lungo u). flipY falso, come tutte le
 * texture che arrivano su UV di glTF.
 *
 * Usa useTexture: va dentro <Suspense>.
 */

import { useTexture } from "@react-three/drei"
import { useMemo } from "react"
import {
  ClampToEdgeWrapping,
  Color,
  type Material,
  MeshStandardMaterial,
  NoColorSpace,
  RepeatWrapping,
  SRGBColorSpace,
  type Texture,
} from "three"
import { ANISOTROPIA, PERIODO_TEXTURE } from "../tessere/texture"
import { SCALA_EDIFICI } from "./progetto"

const FILE = {
  intonaco: "/textures/edifici/intonaco_colore.jpg",
  intonacoNormale: "/textures/edifici/intonaco_normale.png",
  kraft: "/textures/edifici/kraft_colore.jpg",
  kraftNormale: "/textures/edifici/kraft_normale.png",
  legno: "/textures/edifici/legno_colore.jpg",
  legnoNormale: "/textures/edifici/legno_normale.png",
  tenda: "/textures/edifici/tenda_colore.jpg",
  bordo: "/textures/tessere/bordo_ondulato_colore.jpg",
  bordoNormale: "/textures/tessere/bordo_ondulato_normale.png",
} as const
type NomeFile = keyof typeof FILE
const NOMI = Object.keys(FILE) as NomeFile[]
const COLORE = new Set<NomeFile>(["intonaco", "kraft", "legno", "bordo"])

/** Periodo delle texture del kit (m). */
const PERIODO_KIT = 4
/** Il crema delle strisce delle tende (TENDE nel JSON del kit). */
const CREMA = new Color(0.93, 0.89, 0.78)

/** Materiali che si tingono per istanza: le loro InstancedMesh hanno instanceColor. */
export const TINTI = new Set(["EDI_Intonaco", "EDI_Tenda"])

function prepara(t: Texture, nome: NomeFile) {
  t.colorSpace = COLORE.has(nome) ? SRGBColorSpace : NoColorSpace
  t.flipY = false
  t.wrapS = RepeatWrapping
  if (nome.startsWith("bordo")) {
    t.wrapT = ClampToEdgeWrapping
    t.repeat.set(SCALA_EDIFICI / PERIODO_TEXTURE, 1)
  } else {
    t.wrapT = RepeatWrapping
    t.repeat.set(1 / PERIODO_KIT, 1 / PERIODO_KIT)
  }
  t.anisotropy = ANISOTROPIA
  t.needsUpdate = true
}

/** Le tende: la maschera delle strisce sceglie tra il colore dell'istanza e il crema. */
function materialeTenda(maschera: Texture) {
  const m = new MeshStandardMaterial({ map: maschera, roughness: 0.9 })
  m.onBeforeCompile = (shader) => {
    shader.uniforms.crema = { value: CREMA }
    shader.fragmentShader = shader.fragmentShader
      .replace("#include <common>", "#include <common>\nuniform vec3 crema;")
      // la mappa non colora: è solo la maschera delle strisce
      .replace(
        "#include <map_fragment>",
        "float strisce = texture2D(map, vMapUv).r;",
      )
      .replace(
        "#include <color_fragment>",
        `#if defined( USE_INSTANCING_COLOR ) || defined( USE_COLOR )
  diffuseColor.rgb *= mix(crema, vColor.rgb, strisce);
#else
  diffuseColor.rgb *= crema;
#endif`,
      )
  }
  m.customProgramCacheKey = () => "kit-tenda"
  return m
}

/**
 * I materiali veri per nome di segnaposto; `null` = si tiene quello del glb.
 * È un hook perché carica le texture (Suspense).
 */
export function useMaterialiKit(): (segnaposto: Material) => Material {
  const lette = useTexture(
    NOMI.map((n) => FILE[n]),
    (tutte) => tutte.forEach((t, i) => prepara(t, NOMI[i])),
  )
  return useMemo(() => {
    const t = Object.fromEntries(NOMI.map((n, i) => [n, lette[i]])) as Record<
      NomeFile,
      Texture
    >
    const veri: Record<string, Material> = {
      EDI_Intonaco: new MeshStandardMaterial({
        map: t.intonaco,
        normalMap: t.intonacoNormale,
        roughness: 0.88,
      }),
      EDI_Kraft: new MeshStandardMaterial({
        map: t.kraft,
        normalMap: t.kraftNormale,
        roughness: 0.91,
      }),
      EDI_Interno: new MeshStandardMaterial({
        map: t.kraft,
        color: new Color(0.3, 0.3, 0.3),
        roughness: 0.95,
      }),
      EDI_Legno: new MeshStandardMaterial({
        map: t.legno,
        normalMap: t.legnoNormale,
        roughness: 0.8,
      }),
      EDI_Tenda: materialeTenda(t.tenda),
      EDI_Bordo: new MeshStandardMaterial({
        map: t.bordo,
        normalMap: t.bordoNormale,
        roughness: 0.94,
      }),
    }
    // i veri prendono il nome del segnaposto: KitEdifici lo usa per sapere quali tingere (TINTI)
    for (const [nome, m] of Object.entries(veri)) m.name = nome
    return (segnaposto) => veri[segnaposto.name] ?? segnaposto
    // le texture arrivano tutte insieme: basta l'elenco per sapere che sono cambiate
  }, [lette])
}
