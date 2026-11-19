/*
 * datiVie.ts
 * Quello che serve alla scena per mostrare le vie (funzione pura):
 * - dove scrivere il nome di ogni via: a metà della via, sdraiato sulla strada
 *   e allineato alla sua direzione (per i piazzali: al centro della rotonda);
 * - la forma di ogni via, per evidenziarla (calcolata solo quando serve,
 *   poi tenuta in memoria).
 */

import {
  centroTessera,
  chiave,
  type CittaPopolata,
  type Hex,
  type ReteStradale,
  type Stradario,
  type TipoVia,
  type Via,
} from "@corsa-bis/engine"
import { BufferAttribute, BufferGeometry } from "three"
import { tracciatoDi } from "../strade/cache"
import { PROFILO } from "../strade/profili"
import { quotaSuperiore } from "../tessere/misure"

export type DatiVia = {
  readonly id: number
  readonly nome: string
  readonly tipo: TipoVia
  readonly arteria: boolean // corso, viale, circonvallazione: nome visibile a media distanza
  readonly principale: boolean // via lunga: nome visibile a media distanza, ma meno a lungo
  /** Punto del nome (nel mondo) e direzione della strada in quel punto. */
  readonly etichetta: {
    readonly x: number
    readonly y: number
    readonly z: number
    readonly tx: number
    readonly tz: number
  }
}

/** Da quanti pezzi (tessere attraversate, circa) una via conta come principale. */
const PEZZI_PRINCIPALE = 6

const SOPRA_NOME = 3 // il nome sta appena sopra l'asfalto
const SOPRA_EVIDENZA = 1.2 // sopra asfalto e segnaletica, sotto i nomi

export type ContestoVie = {
  readonly citta: CittaPopolata
  readonly rete: ReteStradale
  readonly stradario: Stradario
}

/** Il tracciato e la posizione nel mondo della tessera di un pezzo di via. */
function luogo({ citta, rete }: ContestoVie, tessera: Hex) {
  const k = chiave(tessera)
  const t = citta.tessere.find((x) => chiave(x.hex) === k)!
  const { x, z } = centroTessera(tessera)
  const tracciato = tracciatoDi(
    rete.connettori.get(k)!,
    rete.rotonde.get(k) ?? null,
    rete.rettilinei.get(k),
  )
  return { x, z, sopra: quotaSuperiore(t.strati), tracciato }
}

export function datiVie(contesto: ContestoVie): DatiVia[] {
  return contesto.stradario.vie.map((v) => {
    // il pezzo di mezzo della via (l'anello di inversione non conta)
    const pezzi = v.pezzi.filter(
      (p) =>
        luogo(contesto, p.tessera).tracciato.tratti[p.tratto].inizio !==
          "anello" || v.tipo === "piazzale",
    )
    const pezzo = pezzi[Math.floor(pezzi.length / 2)] ?? v.pezzi[0]
    const { x, z, sopra, tracciato } = luogo(contesto, pezzo.tessera)
    const tratto = tracciato.tratti[pezzo.tratto]
    const p =
      v.tipo === "piazzale"
        ? { x: 0, z: 0, tx: 1, tz: 0 } // al centro della rotonda
        : tratto.punti[Math.floor(tratto.punti.length / 2)]
    return {
      id: v.id,
      nome: v.nome,
      tipo: v.tipo,
      arteria:
        v.tipo === "corso" ||
        v.tipo === "viale" ||
        v.tipo === "circonvallazione",
      principale:
        (v.tipo === "via" || v.tipo === "provinciale") &&
        v.pezzi.length >= PEZZI_PRINCIPALE,
      etichetta: {
        x: x + p.x,
        y: sopra + SOPRA_NOME,
        z: z + p.z,
        tx: p.tx,
        tz: p.tz,
      },
    }
  })
}

// ---------- forme delle vie, per l'evidenziazione ----------

const cacheForme = new Map<number, BufferGeometry>()

/** La forma della carreggiata di una via, nel mondo (calcolata una volta, poi riusata). */
export function formaVia(contesto: ContestoVie, via: Via): BufferGeometry {
  const gia = cacheForme.get(via.id)
  if (gia) return gia

  const pos: number[] = []
  for (const pezzo of via.pezzi) {
    const { x, z, sopra, tracciato } = luogo(contesto, pezzo.tessera)
    const tratto = tracciato.tratti[pezzo.tratto]
    const meta =
      tratto.inizio === "anello" && tracciato.rotonda
        ? tracciato.rotonda.larghezza / 2
        : PROFILO[tratto.classe].carreggiata / 2
    const y = sopra + SOPRA_EVIDENZA
    const lato = (i: number, d: number) => {
      const p = tratto.punti[i]
      return [x + p.x - p.tz * d, y, z + p.z + p.tx * d]
    }
    for (let i = 1; i < tratto.punti.length; i++) {
      const a0 = lato(i - 1, -meta)
      const a1 = lato(i - 1, meta)
      const b0 = lato(i, -meta)
      const b1 = lato(i, meta)
      // due triangoli per segmento; il materiale è a doppia faccia, l'ordine non conta
      pos.push(...a0, ...a1, ...b1, ...a0, ...b1, ...b0)
    }
  }
  const g = new BufferGeometry()
  g.setAttribute("position", new BufferAttribute(new Float32Array(pos), 3))
  g.computeBoundingSphere()
  cacheForme.set(via.id, g)
  return g
}
