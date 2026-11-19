/*
 * Edifici.tsx
 * Disegna i gusci di tutti gli edifici della città (gusci.ts) con cinque
 * sole chiamate di disegno: facciate (due pagine dell'atlante), intonaco,
 * tetti di ondulato, tetti di coppi. Posizioni e progetti
 * arrivano da raggruppa.ts (gruppi.edifici), che li ha messi lungo le
 * strade (lotti.ts).
 *
 * Texture del kit in public/textures/edifici/ (cb_atlante_edifici.py e
 * cb_materiali_edifici.py):
 * - facciate_colore.jpg + facciate_maschera.jpg: l'atlante dei moduli visti
 *   di fronte. Lo shader fa colore = texel × mix(1, coloreCasa, maschera): il
 *   colore della casa (nei vertici) tinge solo l'intonaco (maschera bianca);
 *   vetri, kraft, stucco, tende e insegne restano come sono;
 * - facciate_industria_colore.jpg + _maschera.jpg: la seconda pagina
 *   (capannoni, grattacieli), stesso shader; qui la maschera bianca è la
 *   lamiera;
 * - intonaco_colore/_normale: le parti d'intonaco senza riquadro, tinte dal
 *   colore nei vertici (parapetti, alzate, terrazzi, torrini);
 * - tetto_ondulato_colore/_normale: le falde di kraft ondulato (borgo, shed);
 * - tetto_coppi_colore/_normale: le falde a capanna delle villette.
 * Le UV di intonaco e tetti sono già in metri / 4 (periodo delle texture del
 * kit): la ripetizione resta 1. L'atlante usa le UV di facciate.json, con la
 * v dal basso come in Blender: flipY resta vero (quello di Three.js).
 *
 * Gli edifici montati col kit nella vista a piedi (montati.ts) perdono le
 * caselle del fronte che il kit sa montare: lo fa lo shader delle facciate,
 * senza ricostruire le geometrie.
 *
 * Usa useTexture: va dentro <Suspense>.
 */

import { useTexture } from "@react-three/drei"
import { useMemo } from "react"
import {
  DoubleSide,
  MeshStandardMaterial,
  NoColorSpace,
  RepeatWrapping,
  SRGBColorSpace,
  type Texture,
} from "three"
import type { GruppiCitta } from "../citta/raggruppa"
import { ANISOTROPIA } from "../tessere/texture"
import { costruisciGusci } from "./gusci"
import { DICHIARA_MONTATI, NASCONDI_MONTATI, type Montati } from "./montati"

const CARTELLA = "/textures/edifici/"
const FILE = {
  facciate: "facciate_colore.jpg",
  maschera: "facciate_maschera.jpg",
  industria: "facciate_industria_colore.jpg",
  industriaMaschera: "facciate_industria_maschera.jpg",
  intonaco: "intonaco_colore.jpg",
  intonacoNormale: "intonaco_normale.png",
  tetto: "tetto_ondulato_colore.jpg",
  tettoNormale: "tetto_ondulato_normale.png",
  coppi: "tetto_coppi_colore.jpg",
  coppiNormale: "tetto_coppi_normale.png",
} as const
/** Le texture di colore (sRGB); le altre sono dati (lineari). */
const COLORE = new Set<keyof typeof FILE>([
  "facciate",
  "industria",
  "intonaco",
  "tetto",
  "coppi",
])
/** Gli atlanti non si ripetono; le altre sì. */
const ATLANTI = new Set<keyof typeof FILE>([
  "facciate",
  "maschera",
  "industria",
  "industriaMaschera",
])
const NOMI = Object.keys(FILE) as (keyof typeof FILE)[]

/** Colore in sRGB, dati (maschera, normali) lineari; le ripetibili si ripetono. */
function prepara(t: Texture, nome: keyof typeof FILE) {
  t.colorSpace = COLORE.has(nome) ? SRGBColorSpace : NoColorSpace
  if (!ATLANTI.has(nome)) t.wrapS = t.wrapT = RepeatWrapping
  t.anisotropy = ANISOTROPIA
  t.needsUpdate = true
}

/**
 * Il materiale delle facciate: l'atlante tinto dove la maschera è bianca; in più, nei vertici,
 * le caselle degli edifici montati col kit spariscono (montati.ts).
 */
function materialeFacciate(
  colore: Texture,
  maschera: Texture,
  montati: Montati,
) {
  const m = new MeshStandardMaterial({
    map: colore,
    vertexColors: true,
    roughness: 0.88,
  })
  m.onBeforeCompile = (shader) => {
    shader.uniforms.mascheraFacciate = { value: maschera }
    shader.uniforms.montati = { value: montati.texture }
    shader.vertexShader = shader.vertexShader
      .replace("#include <common>", `#include <common>${DICHIARA_MONTATI}`)
      .replace(
        "#include <project_vertex>",
        `#include <project_vertex>${NASCONDI_MONTATI}`,
      )
    shader.fragmentShader = shader.fragmentShader
      .replace(
        "#include <common>",
        "#include <common>\nuniform sampler2D mascheraFacciate;",
      )
      .replace(
        "#include <color_fragment>",
        `#if defined( USE_COLOR ) && defined( USE_MAP )
  diffuseColor.rgb *= mix(vec3(1.0), vColor.rgb, texture2D(mascheraFacciate, vMapUv).r);
#endif`,
      )
  }
  m.customProgramCacheKey = () => "facciate-maschera"
  return m
}

type EdificiProps = {
  gruppi: GruppiCitta
  /** Gli edifici montati col kit adesso (li sceglie KitEdifici): le loro caselle del fronte spariscono. */
  montati: Montati
}

function Edifici({ gruppi, montati }: EdificiProps) {
  const lette = useTexture(
    NOMI.map((n) => CARTELLA + FILE[n]),
    (tutte) => tutte.forEach((t, i) => prepara(t, NOMI[i])),
  )
  const tex = Object.fromEntries(NOMI.map((n, i) => [n, lette[i]])) as Record<
    keyof typeof FILE,
    Texture
  >
  const geometrie = useMemo(() => costruisciGusci(gruppi.edifici), [gruppi])
  const materiali = useMemo(
    () => ({
      // una per pagina dell'atlante, nello stesso ordine di gusci.facciate
      facciate: [
        materialeFacciate(tex.facciate, tex.maschera, montati),
        materialeFacciate(tex.industria, tex.industriaMaschera, montati),
      ],
      intonaco: new MeshStandardMaterial({
        map: tex.intonaco,
        normalMap: tex.intonacoNormale,
        vertexColors: true,
        roughness: 0.88,
      }),
      tetti: new MeshStandardMaterial({
        map: tex.tetto,
        normalMap: tex.tettoNormale,
        roughness: 0.9,
        side: DoubleSide,
      }),
      coppi: new MeshStandardMaterial({
        map: tex.coppi,
        normalMap: tex.coppiNormale,
        roughness: 0.85,
        side: DoubleSide,
      }),
    }),
    // le texture arrivano tutte insieme: basta la prima per sapere che sono cambiate
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [lette, montati],
  )

  return (
    <group>
      {geometrie.facciate.map((g, i) => (
        <mesh key={i} geometry={g} material={materiali.facciate[i]} />
      ))}
      <mesh geometry={geometrie.intonaco} material={materiali.intonaco} />
      <mesh geometry={geometrie.tetti} material={materiali.tetti} />
      <mesh geometry={geometrie.coppi} material={materiali.coppi} />
    </group>
  )
}

export default Edifici
