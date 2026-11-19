/*
 * KitEdifici.tsx
 * Gli edifici montati col kit (kit_edifici.glb) attorno a chi cammina: le
 * facciate su strada con i pezzi veri (montaggio.ts) al posto di quelle
 * dipinte dei gusci. GDD, "Gusci ovunque, kit solo a piedi".
 *
 * Come funziona:
 * - il kit si carica una volta, più il FONDALE (un quadrato scuro dietro le
 *   aperture, montaggio.ts); ogni pezzo può avere più parti (una per
 *   materiale): ogni parte diventa una InstancedMesh, con i materiali veri
 *   al posto dei segnaposto (materialiKit.ts). Le parti d'intonaco e le
 *   tende hanno il colore per istanza;
 * - a ogni fotogramma (useFrame) si guarda dov'è la telecamera: si monta
 *   solo quando è vicina al suo target (camminata, o zoom molto stretto) e
 *   si ricalcola solo quando si è spostata di almeno RICALCOLO unità;
 * - sceltaKit.ts sceglie gli edifici vicini entro il tetto di triangoli, e
 *   quali montare interi: ai più lontani mancano i bordi di cartone (la
 *   parte EDI_Bordo di ogni pezzo, circa metà dei triangoli); se
 *   la scelta non cambia non si tocca niente. Se cambia, si riempiono le
 *   InstancedMesh (i pezzi di un edificio si calcolano una volta e si
 *   tengono da parte) e si dice ai gusci quali facciate nascondere
 *   (montati.ts);
 * - tutto succede fuori da React (ref e oggetti di Three.js): la scena non
 *   si ridisegna in React mentre si cammina;
 * - niente scatti mentre si corre: al primo fotogramma si creano tutte le
 *   mesh (vuote e spente), si compilano gli shader e si caricano le texture
 *   sulla scheda video; poi i pezzi degli edifici si calcolano in anticipo,
 *   IN_ANTICIPO per fotogramma. Quando si rimonta resta solo da riempire le
 *   matrici. Le mesh vuote sono spente: non costano chiamate di disegno.
 *
 * Usa useGLTF e useTexture: va dentro <Suspense>. Il glb è compresso Draco:
 * useGLTF scarica il decoder da sé.
 */

import { useGLTF } from "@react-three/drei"
import { useFrame } from "@react-three/fiber"
import { useMemo, useRef } from "react"
import {
  BufferAttribute,
  BufferGeometry,
  Color,
  type Group,
  InstancedMesh,
  type Material,
  type Mesh,
  type MeshStandardMaterial,
  type Object3D,
  Vector3,
} from "three"
import type { EdificioPosato } from "./gusci"
import { TINTI, useMaterialiKit } from "./materialiKit"
import { type Montati } from "./montati"
import { FONDALE, type Istanza, montaEdificio } from "./montaggio"
import { impronta } from "./progetto"
import { scegliEdifici, type Scelto, stessaScelta } from "./sceltaKit"

const KIT = "/models/edifici/kit_edifici.glb"
/** Oltre questa distanza tra telecamera e target non si monta niente (vista dall'alto, zoom normale). */
const VICINO = 150
/** Di quanto deve spostarsi la telecamera prima di riscegliere gli edifici. */
const RICALCOLO = 40
/** Oltre questi millisecondi un rimontaggio si segnala in console (a 75 fps un fotogramma dura 13 ms). */
const SOGLIA_LENTO = 4
/** Istanze per parte create all'inizio (poi raddoppiano se servono). */
const CAPIENZA = 64
/** Edifici di cui si calcolano i pezzi in anticipo a ogni fotogramma (circa 550 in città: un secondo). */
const IN_ANTICIPO = 10

/** Una parte di un pezzo del kit: la geometria e il materiale vero. */
type Parte = {
  readonly geometria: BufferGeometry
  readonly materiale: Material
}

/** Il fondale (montaggio.ts): un quadrato 1 × 1 nel piano x = 0 che guarda +X, da y = 0 a 1 e da z = 0 a 1. */
function geometriaFondale(): BufferGeometry {
  const g = new BufferGeometry()
  g.setAttribute(
    "position",
    new BufferAttribute(
      new Float32Array([0, 0, 0, 0, 0, 1, 0, 1, 1, 0, 1, 0]),
      3,
    ),
  )
  g.setAttribute(
    "normal",
    new BufferAttribute(
      new Float32Array([1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0]),
      3,
    ),
  )
  g.setAttribute(
    "uv",
    new BufferAttribute(new Float32Array([0, 0, 1, 0, 1, 1, 0, 1]), 2),
  )
  g.setIndex([0, 2, 1, 0, 3, 2])
  return g
}

/** Le parti di ogni pezzo del kit, per nome; un pezzo con un solo materiale è una Mesh, con più materiali un gruppo di Mesh. */
function partiDelKit(
  scena: Object3D,
  vero: (m: Material) => Material,
): Map<string, Parte[]> {
  const parti = new Map<string, Parte[]>()
  // il fondale dietro le aperture: cartone scuro, lo stesso dell'interno dei buchi
  parti.set(FONDALE, [
    {
      geometria: geometriaFondale(),
      materiale: vero({ name: "EDI_Interno" } as Material),
    },
  ])
  for (const pezzo of scena.children) {
    const mesh = ((pezzo as Mesh).isMesh ? [pezzo] : pezzo.children) as Mesh[]
    parti.set(
      pezzo.name,
      mesh.map((m) => ({
        geometria: m.geometry,
        materiale: vero(m.material as Material),
      })),
    )
  }
  return parti
}

/** La parte dei bordi di cartone (il taglio): circa metà dei triangoli, solo sugli edifici vicini. */
const eBordo = (p: Parte) => p.materiale.name === "EDI_Bordo"

type KitEdificiProps = {
  edifici: readonly EdificioPosato[]
  /** Dove dire ai gusci quali facciate nascondere. */
  montati: Montati
}

function KitEdifici({ edifici, montati }: KitEdificiProps) {
  const { scene } = useGLTF(KIT)
  const vero = useMaterialiKit()
  const parti = useMemo(() => partiDelKit(scene, vero), [scene, vero])
  /** Triangoli di ogni pezzo, intero e senza i bordi di cartone, per il tetto della scelta. */
  const triangoliPezzo = useMemo(() => {
    const t = new Map<string, { intero: number; senzaBordi: number }>()
    const tri = (p: Parte) =>
      (p.geometria.index
        ? p.geometria.index.count
        : p.geometria.getAttribute("position").count) / 3
    for (const [nome, ps] of parti)
      t.set(nome, {
        intero: ps.reduce((s, p) => s + tri(p), 0),
        senzaBordi: ps
          .filter((p) => !eBordo(p))
          .reduce((s, p) => s + tri(p), 0),
      })
    return t
  }, [parti])
  /** Il centro di ogni edificio nel mondo (x, z): il centro della sua impronta. */
  const centri = useMemo(() => {
    const c = new Float32Array(edifici.length * 2)
    const v = new Vector3()
    edifici.forEach(({ progetto, matrice }, i) => {
      const imp = impronta(progetto)
      v.set((imp.x0 + imp.x1) / 2, 0, (imp.z0 + imp.z1) / 2).applyMatrix4(
        matrice,
      )
      c[2 * i] = v.x
      c[2 * i + 1] = v.z
    })
    return c
  }, [edifici])

  const gruppo = useRef<Group>(null)
  // stato che cambia mentre si cammina: fuori da React
  const stato = useRef({
    scelti: [] as Scelto[],
    ultima: new Vector3(Infinity, 0, 0),
    pezzi: new Map<number, Istanza[]>(), // i pezzi di ogni edificio già calcolati
    mesh: new Map<string, InstancedMesh[]>(), // per pezzo, una InstancedMesh per parte
    pronto: false, // mesh create e shader compilati (preparazione al primo fotogramma)
    prossimo: 0, // il prossimo edificio di cui calcolare i pezzi in anticipo
  })

  /** Le InstancedMesh di un pezzo, una per parte, capaci di `capienza` istanze. */
  const creaMesh = (nome: string, capienza: number): InstancedMesh[] => {
    const g = gruppo.current!
    const colore = new Color(1, 1, 1)
    return (parti.get(nome) ?? []).map((p) => {
      const m = new InstancedMesh(p.geometria, p.materiale, capienza)
      m.frustumCulled = false // le istanze sono sparse: il volume della geometria di partenza non vale
      m.name = nome
      m.count = 0
      m.visible = false
      // il colore per istanza va creato subito: cambia lo shader, e lo shader si compila una volta sola
      if (TINTI.has(p.materiale.name)) m.setColorAt(0, colore)
      g.add(m)
      return m
    })
  }

  const pezziDi = (i: number) => {
    const s = stato.current
    let p = s.pezzi.get(i)
    if (!p) s.pezzi.set(i, (p = montaEdificio(edifici[i], `edificio-${i}`)))
    return p
  }
  const peso = (i: number, vicino: boolean) => {
    let t = 0
    for (const x of pezziDi(i)) {
      const p = triangoliPezzo.get(x.pezzo)
      if (p) t += vicino ? p.intero : p.senzaBordi
    }
    return t
  }

  /**
   * Riempie le InstancedMesh con i pezzi degli edifici scelti. Per ogni pezzo le istanze degli
   * edifici vicini vengono prima: così la parte dei bordi di cartone ne disegna solo le prime
   * (count = quante sono vicine) e le altre parti tutte.
   */
  const monta = (scelti: readonly Scelto[]) => {
    const s = stato.current
    const g = gruppo.current
    if (!g) return
    // i pezzi raccolti per nome, prima i vicini
    const perPezzo = new Map<string, { istanze: Istanza[]; vicine: number }>()
    for (const vicino of [true, false])
      for (const sc of scelti) {
        if (sc.vicino !== vicino) continue
        for (const x of pezziDi(sc.i)) {
          const q =
            perPezzo.get(x.pezzo) ??
            perPezzo.set(x.pezzo, { istanze: [], vicine: 0 }).get(x.pezzo)!
          q.istanze.push(x)
          if (vicino) q.vicine++
        }
      }
    // le mesh dei pezzi che non servono più restano vuote (e spente: non costano una chiamata)
    for (const [nome, ms] of s.mesh)
      if (!perPezzo.has(nome))
        for (const m of ms) {
          m.count = 0
          m.visible = false
        }
    const colore = new Color()
    for (const [nome, { istanze, vicine }] of perPezzo) {
      const ps = parti.get(nome)
      if (!ps) continue
      let ms = s.mesh.get(nome)
      // capienza: si rifanno solo se non bastano (il doppio, così succede di rado)
      if (!ms || ms[0].instanceMatrix.count < istanze.length) {
        for (const m of ms ?? []) {
          g.remove(m)
          m.dispose()
        }
        ms = creaMesh(nome, istanze.length * 2)
        s.mesh.set(nome, ms)
      }
      ms.forEach((m, j) => {
        const tinto = TINTI.has(ps[j].materiale.name)
        // i bordi di cartone solo sugli edifici vicini
        const quante = eBordo(ps[j]) ? vicine : istanze.length
        for (let k = 0; k < quante; k++) {
          const x = istanze[k]
          m.setMatrixAt(k, x.matrice)
          if (tinto)
            m.setColorAt(
              k,
              x.colore
                ? colore.setRGB(x.colore[0], x.colore[1], x.colore[2])
                : colore.setRGB(1, 1, 1),
            )
        }
        m.count = quante
        m.visible = quante > 0
        m.instanceMatrix.needsUpdate = true
        if (m.instanceColor) m.instanceColor.needsUpdate = true
      })
    }
    montati.imposta(scelti.map((x) => x.i))
  }

  useFrame(({ camera, controls, gl, scene: tutta }) => {
    const s = stato.current
    // al primo fotogramma: tutte le mesh (vuote) e gli shader compilati subito, con le texture già
    // sulla scheda video. Senza, la prima volta che un pezzo compare il gioco si ferma un attimo
    if (!s.pronto && gruppo.current) {
      for (const nome of parti.keys())
        s.mesh.set(nome, creaMesh(nome, CAPIENZA))
      gruppo.current.traverse((o) => (o.visible = true))
      gl.compile(tutta, camera)
      for (const p of new Set(
        [...parti.values()].flat().map((x) => x.materiale),
      ))
        for (const t of [
          (p as MeshStandardMaterial).map,
          (p as MeshStandardMaterial).normalMap,
        ])
          if (t) gl.initTexture(t)
      gruppo.current.traverse((o) => (o.visible = o === gruppo.current))
      s.pronto = true
      return
    }
    // i pezzi degli edifici si calcolano in anticipo, pochi per fotogramma, così montarli dopo non pesa
    for (let n = 0; n < IN_ANTICIPO && s.prossimo < edifici.length; n++)
      pezziDi(s.prossimo++)
    const target = (controls as unknown as { target?: Vector3 } | null)?.target
    const vicino = !!target && camera.position.distanceTo(target) < VICINO
    if (!vicino) {
      if (s.scelti.length > 0) {
        s.scelti = []
        s.ultima.set(Infinity, 0, 0)
        monta([])
      }
      return
    }
    if (camera.position.distanceTo(s.ultima) < RICALCOLO) return
    s.ultima.copy(camera.position)
    const scelti = scegliEdifici(
      centri,
      camera.position.x,
      camera.position.z,
      peso,
    )
    if (stessaScelta(scelti, s.scelti)) return
    s.scelti = scelti
    const t0 = performance.now()
    monta(scelti)
    // per le prove: se rimontare costa più di qualche millisecondo lo dice in console
    const ms = performance.now() - t0
    if (ms > SOGLIA_LENTO)
      console.warn(
        `[kit] rimontati ${scelti.length} edifici in ${ms.toFixed(1)} ms`,
      )
  })

  return <group ref={gruppo} />
}

useGLTF.preload(KIT)

export default KitEdifici
