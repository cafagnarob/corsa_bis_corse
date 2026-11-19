/*
 * modelloMezzo.ts
 * Prepara un mezzo esportato da Blender (cb_export.py) per l'instancing.
 *
 * Il .glb di un mezzo (GDD: "Export dei mezzi") ha una radice con dentro i
 * livelli di dettaglio LOD0 … LOD5, in METRI REALI, con il muso verso +X e le
 * ruote a quota 0. Qui, per ogni LOD da 1 a 5:
 * - si prendono tutte le sue mesh, nella loro posizione dentro il modello;
 * - si centrano in pianta (il centro del mezzo finisce in x = 0, z = 0) e si
 *   scalano ×5,2 (scala di gioco del GDD): così il codice lo posa al centro
 *   tra i due assi;
 * - si uniscono in UNA geometria con un gruppo per materiale (le mesh con lo
 *   stesso materiale finiscono insieme): ogni LOD diventa una InstancedMesh,
 *   con tante chiamate di disegno quanti sono i suoi materiali.
 * Con l'export v2 (GDD: bake su atlante) ogni LOD ha UN materiale con la sua
 * texture (colore + emissiva per le luci): una chiamata di disegno per LOD.
 * Per questo si tengono le UV, e il materiale si copia per regolare luci e
 * nitidezza della texture senza toccare quello caricato.
 * Il LOD0 (armatura, porte e ruote animate) servirà per la vista a bordo e a
 * piedi: per ora si usa dal LOD1 in giù.
 *
 * SNODATO (bus18.glb, GDD: "Export dello snodato"): tutti i LOD sono skinned
 * e la parte dietro segue l'osso Snodo, con pesi graduali nella fascia del
 * soffietto. Per piegarlo senza rinunciare all'instancing:
 * -  * - di ogni vertice si tiene il PESO dell'osso Snodo e delle ossa sotto di
 *   lui, come ruote e porta posteriore (attributo pesoSnodo);
 * - ogni istanza ha il suo ANGOLO di snodo (attributo angoloSnodo, uno per
 *   istanza);
 * - il materiale ha un pezzetto di shader in più: ruota il vertice attorno
 *   al giunto (asse verticale) dell'angolo, e mescola posizione dritta e
 *   ruotata secondo il peso. Il soffietto, a metà peso, si piega a metà.
 * Così tutti gli snodati di un LOD restano una sola chiamata di disegno.
 */

import {
  Box3,
  BufferAttribute,
  InstancedBufferAttribute,
  Matrix4,
  Vector3,
  type BufferGeometry,
  type Material,
  type Mesh,
  type MeshStandardMaterial,
  type Object3D,
  type SkinnedMesh,
} from "three"
import { mergeGeometries } from "three/examples/jsm/utils/BufferGeometryUtils.js"

/** Scala grafica uniforme dei mezzi (GDD: ×5,2 anche sulla lunghezza). */
export const SCALA_MEZZI = 5.2

/**
 * Intensità delle luci (fari, fanali): nel .glb vale 2; tarata a occhio con il
 * tone mapping Neutral il 18 novembre (provati 0,8, 1 e 3): con 1 si capisce
 * che sono luci senza che diventino macchie bianche. Si cambia qui, senza
 * rifare il bake. Con la luce che cambia con l'ora si potrà alzare di sera.
 */
export const INTENSITA_LUCI = 1

/** Nitidezza dell'atlante visto di sbieco (filtro anisotropo, 1-16). */
const ANISOTROPIA = 8

const ATTRIBUTI = ["position", "normal", "uv", "pesoSnodo"]

/** Copie disegnabili al massimo per LOD (dimensione delle InstancedMesh e dell'attributo angoloSnodo). */
export const ISTANZE_MASSIME = 200

/** Nome dell'osso della parte dietro dello snodato (cb_export.py). */
const OSSO_SNODO = "Snodo"

export type LodMezzo = {
  readonly geometria: BufferGeometry
  readonly materiali: Material[]
}

/** Misure di un mezzo preparato, in unità di gioco. */
export type MisureMezzo = {
  readonly lunghezza: number
  readonly altezza: number
  /** Posizione x del giunto dello snodo (null se il mezzo non si piega). */
  readonly giunto: number | null
}

/** Vero se l'osso è Snodo o sta sotto Snodo nel rig (ruote e porte della coda). */
function nellaCoda(osso: Object3D): boolean {
  for (let o: Object3D | null = osso; o; o = o.parent)
    if (o.name === OSSO_SNODO) return true
  return false
}

/**
 * Quanto ogni vertice di una mesh skinned segue la coda: la somma dei pesi
 * delle ossa che sono Snodo o stanno sotto Snodo. Le ruote e la porta
 * posteriore hanno le loro ossa (figlie di Snodo): contano anche loro,
 * altrimenti resterebbero dove starebbero con il mezzo dritto.
 */
function pesiSnodo(m: Mesh): Float32Array {
  const g = m.geometry
  const n = g.getAttribute("position").count
  const pesi = new Float32Array(n)
  const skinned = m as SkinnedMesh
  if (!skinned.isSkinnedMesh) return pesi
  const coda = skinned.skeleton.bones.map(nellaCoda)
  const ossa = g.getAttribute("skinIndex")
  const valori = g.getAttribute("skinWeight")
  if (!coda.some(Boolean) || !ossa || !valori) return pesi
  for (let i = 0; i < n; i++) {
    for (let c = 0; c < 4; c++)
      if (coda[ossa.getComponent(i, c)]) pesi[i] += valori.getComponent(i, c)
  }
  return pesi
}

/**
 * Aggiunge allo shader del materiale la piega dello snodo: il vertice ruota
 * attorno all'asse verticale che passa per il giunto (x = giunto), di
 * angoloSnodo radianti (positivo = coda verso +Z, come la clip Snodo del GDD:
 * il bus che curva a sinistra), in proporzione al suo pesoSnodo. Lo stesso
 * per la normale, così la luce resta giusta.
 */
function conSnodo(materiale: Material, giunto: number) {
  materiale.onBeforeCompile = (shader) => {
    shader.uniforms.giuntoSnodo = { value: giunto }
    shader.vertexShader = shader.vertexShader
      .replace(
        "#include <common>",
        `#include <common>
attribute float pesoSnodo;
attribute float angoloSnodo;
uniform float giuntoSnodo;
vec3 piegaSnodo(vec3 v, float c, float s) { return vec3(v.x * c + v.z * s, v.y, -v.x * s + v.z * c); }`,
      )
      .replace(
        "#include <beginnormal_vertex>",
        `#include <beginnormal_vertex>
objectNormal = mix(objectNormal, piegaSnodo(objectNormal, cos(angoloSnodo), sin(angoloSnodo)), pesoSnodo);`,
      )
      .replace(
        "#include <begin_vertex>",
        `#include <begin_vertex>
vec3 dalGiunto = transformed - vec3(giuntoSnodo, 0.0, 0.0);
transformed = mix(transformed, piegaSnodo(dalGiunto, cos(angoloSnodo), sin(angoloSnodo)) + vec3(giuntoSnodo, 0.0, 0.0), pesoSnodo);`,
      )
  }
  materiale.customProgramCacheKey = () => "snodo"
}

/** Il centro in pianta del mezzo e la matrice che lo porta al centro e lo scala ×5,2. */
function sistemaDi(radice: Object3D) {
  radice.updateMatrixWorld(true)
  // centro in pianta, misurato sul LOD1 (o su tutto il modello se manca)
  const riferimento = radice.getObjectByName("LOD1") ?? radice
  const box = new Box3().setFromObject(riferimento)
  const centro = box.getCenter(new Vector3())
  const sistema = new Matrix4()
    .makeScale(SCALA_MEZZI, SCALA_MEZZI, SCALA_MEZZI)
    .multiply(new Matrix4().makeTranslation(-centro.x, 0, -centro.z))
  return { box, sistema }
}

/** Lunghezza, altezza e giunto dello snodo del mezzo, in unità di gioco. */
export function misureMezzo(radice: Object3D): MisureMezzo {
  const { box, sistema } = sistemaDi(radice)
  const misure = box.getSize(new Vector3())
  const osso = radice.getObjectByName(OSSO_SNODO)
  const giunto = osso
    ? osso.getWorldPosition(new Vector3()).applyMatrix4(sistema).x
    : null
  return {
    lunghezza: misure.x * SCALA_MEZZI,
    altezza: box.max.y * SCALA_MEZZI,
    giunto,
  }
}

/** Le mesh dentro un nodo, con la geometria portata nelle coordinate del modello. */
function meshDi(
  nodo: Object3D,
  snodo: boolean,
): { geometria: BufferGeometry; materiale: Material }[] {
  const out: { geometria: BufferGeometry; materiale: Material }[] = []
  nodo.traverse((o) => {
    const m = o as Mesh
    if (!m.isMesh) return
    const materiale = Array.isArray(m.material) ? m.material[0] : m.material
    // per le mesh skinned (LOD0-2) la geometria è nella posa di riposo: con lo skin
    // rigido è il mezzo fermo, ruote dritte e porte chiuse, giusto per l'instancing
    let g = m.geometry.clone()
    // il peso dell'osso Snodo si legge prima di togliere gli attributi dello skin
    if (snodo) g.setAttribute("pesoSnodo", new BufferAttribute(pesiSnodo(m), 1))
    g = g.applyMatrix4(m.matrixWorld)
    if (g.index) g = g.toNonIndexed() // tutte uguali, altrimenti mergeGeometries rifiuta
    // si tengono posizione, normali e UV (servono all'atlante del bake); via skinIndex e skinWeight
    for (const nome of Object.keys(g.attributes))
      if (!ATTRIBUTI.includes(nome)) g.deleteAttribute(nome)
    if (!g.getAttribute("uv"))
      g.setAttribute(
        "uv",
        new BufferAttribute(
          new Float32Array(g.getAttribute("position").count * 2),
          2,
        ),
      )
    out.push({ geometria: g, materiale })
  })
  return out
}

/**
 * I LOD da 1 a 5 di un mezzo, pronti per l'instancing (indice 0 = LOD1).
 * Un LOD mancante nel file resta null.
 */
export function preparaMezzo(radice: Object3D): (LodMezzo | null)[] {
  const { sistema } = sistemaDi(radice)
  const { giunto } = misureMezzo(radice)

  return [1, 2, 3, 4, 5].map((n) => {
    const nodo = radice.getObjectByName(`LOD${n}`)
    if (!nodo) return null
    // raggruppa per materiale: un gruppo (una chiamata di disegno) per materiale
    const perMateriale = new Map<Material, BufferGeometry[]>()
    for (const { geometria, materiale } of meshDi(nodo, giunto !== null)) {
      perMateriale.set(materiale, [
        ...(perMateriale.get(materiale) ?? []),
        geometria.applyMatrix4(sistema),
      ])
    }
    // copia del materiale (quello del file resta com'è) con le luci ricalibrate
    const materiali = [...perMateriale.keys()].map((m) => {
      const copia = m.clone() as MeshStandardMaterial
      if ("emissiveIntensity" in copia) copia.emissiveIntensity = INTENSITA_LUCI
      if (copia.map) copia.map.anisotropy = ANISOTROPIA
      if (giunto !== null) conSnodo(copia, giunto)
      return copia as Material
    })
    const parti = [...perMateriale.values()].map((g) => mergeGeometries(g)!)
    const geometria = mergeGeometries(parti, true)! // true = un gruppo per parte, nell'ordine dei materiali
    geometria.computeBoundingSphere()
    // snodato: un angolo per istanza, che MezziLinee scrive a ogni fotogramma
    if (giunto !== null)
      geometria.setAttribute(
        "angoloSnodo",
        new InstancedBufferAttribute(new Float32Array(ISTANZE_MASSIME), 1),
      )
    return { geometria, materiali }
  })
}
