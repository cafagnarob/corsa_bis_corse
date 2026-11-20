/*
 * collisioniTessere.ts
 * Le forme che la fisica usa al posto delle tessere disegnate.
 *
 * Perché servono: la città è disegnata con InstancedMesh e geometrie fuse
 * (raggruppa.ts), che Rapier non vede. Diamo alla fisica forme più semplici
 * che stanno esattamente dove sta la superficie di guida:
 * - per ogni tessera, la faccia superiore (un esagono piatto) e i suoi sei
 *   fianchi fino al tavolo: tutto in una sola mesh di triangoli (trimesh);
 * - per ogni rampa, un cuneo (6 punti) da usare come forma convessa: sul
 *   lato verso la tessera alta arriva alla sua quota, dopo 61 unità per
 *   strato è al livello della tessera bassa (come quotaRampa in rampe.ts).
 *
 * Le quote sono quelle dell'asfalto: faccia superiore della tessera più lo
 * spessore della carreggiata (QUOTE.carreggiata), così le ruote poggiano
 * sulla strada disegnata e non 3 mm sotto. I marciapiedi (mezza unità più
 * alti) per ora non hanno collisione: sono circa 10 cm reali, la ruota non
 * li sentirebbe.
 *
 * Orientamento della tessera (GDD): vertice in alto, lati verticali a destra
 * e sinistra; lato 0 = est. In Three.js i vertici stanno a 30° + 60° × k, con
 * x = R cos(a) e z = −R sin(a).
 */

import {
  RAGGIO_TESSERA,
  centroTessera,
  puntoLato,
  type Hex,
  type Rampa,
} from "@corsa-bis/engine"

import { QUOTE } from "../strade/profili"
import { lunghezzaRampa, mezzaLarghezzaRampa } from "../strade/rampe"
import { PASSO_STRATO, quotaStrato, quotaSuperiore } from "../tessere/misure"

/** Una mesh di triangoli per Rapier: vertici (x, y, z in fila) e indici. */
export type Trimesh = {
  readonly vertici: Float32Array
  readonly indici: Uint32Array
}

/** Quota della superficie di guida di una tessera con n strati. */
export const quotaGuida = (strati: number) =>
  quotaSuperiore(strati) + QUOTE.carreggiata

/** Quota del tavolo: la faccia inferiore della pila di tessere. */
export const QUOTA_TAVOLO = quotaStrato(1)

/** Il vertice k (0-5) di una tessera, rispetto al suo centro. */
function vertice(k: number): { x: number; z: number } {
  const a = ((30 + 60 * k) * Math.PI) / 180
  return { x: RAGGIO_TESSERA * Math.cos(a), z: -RAGGIO_TESSERA * Math.sin(a) }
}

/**
 * Faccia superiore e fianchi delle tessere date, in un'unica trimesh.
 * Per ogni tessera: 7 vertici in cima (centro + 6 angoli), 6 in basso;
 * 6 triangoli a ventaglio per la cima, 2 per ogni fianco.
 */
export function trimeshTessere(
  tessere: readonly { readonly hex: Hex; readonly strati: number }[],
): Trimesh {
  const vertici: number[] = []
  const indici: number[] = []

  for (const t of tessere) {
    const c = centroTessera(t.hex)
    const cima = quotaGuida(t.strati)
    const base = vertici.length / 3

    vertici.push(c.x, cima, c.z) // 0: centro della cima
    for (let k = 0; k < 6; k++) {
      const v = vertice(k)
      vertici.push(c.x + v.x, cima, c.z + v.z) // 1-6: angoli in cima
    }
    for (let k = 0; k < 6; k++) {
      const v = vertice(k)
      vertici.push(c.x + v.x, QUOTA_TAVOLO, c.z + v.z) // 7-12: angoli in basso
    }

    for (let k = 0; k < 6; k++) {
      const a = 1 + k
      const b = 1 + ((k + 1) % 6)
      // Cima: ventaglio dal centro. Gli angoli vanno in senso antiorario
      // visto dall'alto, quindi (centro, a, b) ha la normale verso l'alto
      indici.push(base, base + a, base + b)
      // Fianco tra gli angoli a e b: due triangoli con la normale verso fuori
      indici.push(base + a, base + 6 + a, base + b)
      indici.push(base + b, base + 6 + a, base + 6 + b)
    }
  }
  return { vertici: new Float32Array(vertici), indici: new Uint32Array(indici) }
}

/**
 * I 6 punti del cuneo di una rampa, per una forma convessa.
 * `strati` sono quelli della tessera BASSA (quella che contiene la rampa).
 * Due punti in alto sul connettore, due in basso sul connettore, due in
 * basso in fondo alla rampa: la faccia inclinata è quella su cui si guida.
 */
export function puntiRampa(rampa: Rampa, strati: number): Float32Array {
  const c = centroTessera(rampa.hex)
  const a = (rampa.lato * Math.PI) / 3
  const fuori = { x: Math.cos(a), z: -Math.sin(a) } // verso il lato, fuori dalla tessera
  const traverso = { x: -fuori.z, z: fuori.x } // lungo il lato
  const lato = puntoLato(rampa.lato)
  const connettore = { x: c.x + lato.x, z: c.z + lato.z }
  const fondo = {
    x: connettore.x - fuori.x * lunghezzaRampa(rampa.salto),
    z: connettore.z - fuori.z * lunghezzaRampa(rampa.salto),
  }
  const w = mezzaLarghezzaRampa(rampa.classe)
  const basso = quotaGuida(strati)
  const alto = basso + rampa.salto * PASSO_STRATO

  const p: number[] = []
  for (const s of [-1, 1]) {
    const tx = traverso.x * w * s
    const tz = traverso.z * w * s
    p.push(connettore.x + tx, alto, connettore.z + tz)
    p.push(connettore.x + tx, basso, connettore.z + tz)
    p.push(fondo.x + tx, basso, fondo.z + tz)
  }
  return new Float32Array(p)
}
