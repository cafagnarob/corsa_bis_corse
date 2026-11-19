/*
 * geometrieQuartieri.ts
 * Le forme che servono alla "vista mappa" dei quartieri (GDD, lente
 * Quartieri: "un contorno sottile colorato e il nome al centro"):
 * - CONTORNI: una linea colorata lungo il confine di ogni quartiere, appena
 *   dentro il quartiere (così due quartieri vicini mostrano due linee
 *   affiancate, ognuna del suo colore). Tutti i contorni in UNA geometria,
 *   con il colore nei vertici: una sola chiamata di disegno.
 * - AREE: per ogni quartiere le facce superiori delle sue tessere unite in
 *   una geometria: servono per il passaggio del mouse e per illuminarlo.
 *
 * Il confine si trova così: un lato di una tessera è di confine se la vicina
 * da quel lato non appartiene allo stesso quartiere (o non esiste).
 * Funzione pura: città in ingresso, geometrie in uscita.
 */

import {
  centroTessera,
  chiave,
  LATI,
  RAGGIO_TESSERA,
  vicina,
  type CittaPopolata,
} from "@corsa-bis/engine"
import { BufferAttribute, BufferGeometry, Color } from "three"
import { quotaSuperiore } from "../tessere/misure"

/** Colori dei quartieri, ben distinti tra loro (si ripetono dopo l'ultimo). */
export const COLORI_QUARTIERI = [
  "#e07a5f",
  "#3d85c6",
  "#81b29a",
  "#e6a23c",
  "#9b72cf",
  "#d65a8a",
  "#5aa9a0",
  "#c9b23f",
  "#7a9e3f",
]
export const coloreQuartiere = (id: number) =>
  COLORI_QUARTIERI[id % COLORI_QUARTIERI.length]

const RIENTRO = 4 // distanza della linea dal bordo della tessera
const SPESSORE = 14 // spessore della linea (lungo i raggi dei vertici)
const SOPRA_CONTORNI = 1.8 // sopra strade e segnaletica
const SOPRA_AREE = 1.5

/** Vertice k dell'esagono (punta in alto): angoli 30°, 90°, 150°... a distanza `r` dal centro. */
const vertice = (x: number, z: number, k: number, r: number) => {
  const a = Math.PI / 6 + (k * Math.PI) / 3
  return { x: x + r * Math.cos(a), z: z - r * Math.sin(a) }
}

/** Raccoglie triangoli rivolti verso l'alto, con un colore per vertice. */
class Triangoli {
  pos: number[] = []
  col: number[] = []

  aggiungi(a: number[], b: number[], c: number[], colore?: Color) {
    // se il triangolo guarda in basso si scambiano due vertici
    const ny = (b[2] - a[2]) * (c[0] - a[0]) - (b[0] - a[0]) * (c[2] - a[2])
    const [p, q] = ny >= 0 ? [b, c] : [c, b]
    this.pos.push(...a, ...p, ...q)
    if (colore)
      for (let i = 0; i < 3; i++) this.col.push(colore.r, colore.g, colore.b)
  }

  geometria(): BufferGeometry {
    const g = new BufferGeometry()
    g.setAttribute(
      "position",
      new BufferAttribute(new Float32Array(this.pos), 3),
    )
    if (this.col.length > 0)
      g.setAttribute(
        "color",
        new BufferAttribute(new Float32Array(this.col), 3),
      )
    g.computeBoundingSphere()
    return g
  }
}

export type GeometrieQuartieri = {
  readonly contorni: BufferGeometry
  readonly aree: ReadonlyMap<number, BufferGeometry> // id del quartiere → area
}

export function geometrieQuartieri(citta: CittaPopolata): GeometrieQuartieri {
  const quartiereDi = new Map(
    citta.tessere.map((t) => [chiave(t.hex), t.quartiere]),
  )
  const strati = new Map(citta.tessere.map((t) => [chiave(t.hex), t.strati]))
  const contorni = new Triangoli()
  const aree = new Map<number, BufferGeometry>()

  for (const q of citta.quartieri) {
    const colore = new Color(coloreQuartiere(q.id))
    const area = new Triangoli()

    for (const h of q.tessere) {
      const { x, z } = centroTessera(h)
      const sopra = quotaSuperiore(strati.get(chiave(h)) ?? 1)

      // area: la faccia superiore della tessera (6 triangoli a ventaglio)
      const ya = sopra + SOPRA_AREE
      for (let k = 0; k < 6; k++) {
        const v1 = vertice(x, z, k, RAGGIO_TESSERA)
        const v2 = vertice(x, z, k + 1, RAGGIO_TESSERA)
        area.aggiungi([x, ya, z], [v1.x, ya, v1.z], [v2.x, ya, v2.z])
      }

      // contorno: i lati che danno su un altro quartiere o sul vuoto
      const yc = sopra + SOPRA_CONTORNI
      for (const lato of LATI) {
        if (quartiereDi.get(chiave(vicina(h, lato))) === q.id) continue
        // il lato `lato` va dal vertice (lato - 1) al vertice `lato`
        const esterno = RAGGIO_TESSERA - RIENTRO
        const interno = esterno - SPESSORE
        const a1 = vertice(x, z, lato - 1, esterno)
        const a2 = vertice(x, z, lato, esterno)
        const b1 = vertice(x, z, lato - 1, interno)
        const b2 = vertice(x, z, lato, interno)
        contorni.aggiungi(
          [a1.x, yc, a1.z],
          [a2.x, yc, a2.z],
          [b2.x, yc, b2.z],
          colore,
        )
        contorni.aggiungi(
          [a1.x, yc, a1.z],
          [b2.x, yc, b2.z],
          [b1.x, yc, b1.z],
          colore,
        )
      }
    }
    aree.set(q.id, area.geometria())
  }

  return { contorni: contorni.geometria(), aree }
}
