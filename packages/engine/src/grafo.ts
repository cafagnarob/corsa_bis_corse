/*
 * grafo.ts
 * Il grafo stradale della città: la rete su cui si muovono i mezzi e su cui
 * si tende lo spago delle linee (GDD: "Linee e fermate", "Note tecniche").
 *
 * Si costruisce dai tracciati delle tessere (tracciati.ts):
 * - NODI: i punti dove le strade si toccano o finiscono
 *     · il punto medio di un lato, condiviso dalle due tessere vicine;
 *     · il centro di un incrocio;
 *     · il punto dove una strada si innesta sul viale passante;
 *     · l'ingresso di una strada sull'anello di una rotonda;
 *     · la fine di una strada a fondo cieco;
 * - ARCHI: i pezzi di tratto tra due nodi, uno per senso di marcia. L'anello
 *   delle rotonde ha archi in un solo senso (antiorario).
 *
 * Ogni arco sa: lunghezza in metri (1 unità = 1 m, la tessera è in scala
 * reale), salita (differenza di quota tra i suoi nodi), classe, via e i mezzi
 * che vi possono passare:
 *   viale → tutti; urbana → minibus e bus; stretta → solo minibus;
 *   anello di una rotonda compatta → minibus e bus (lo snodato da 93,6 unità
 *   non ci sta); rotonda ampia → tutti.
 *
 * Quote: ogni tessera sta a strati × 10 m; il punto medio di un lato sta a
 * metà tra le due tessere, così la rampa tra due quote diverse si divide
 * tra le due metà strada.
 *
 * Una posizione sulla rete (dove si pianta un pin) è "tratto + distanza
 * dall'inizio del tratto" (s, in metri), come previsto dal GDD per le fermate.
 * Funzione pura: stessa città, stesso grafo.
 */

import {
  centroTessera,
  chiave,
  latoOpposto,
  LATI,
  vicina,
  type Hex,
  type Lato,
} from "./esagoni"
import type { CittaPopolata } from "./popola"
import type { ClasseStrada, ReteStradale, TipoRotonda } from "./strade"
import { puntoLato, tracciatoTessera, type Tratto } from "./tracciati"
import type { Stradario } from "./vie"

export type TipoMezzo = "minibus" | "bus" | "snodato"

/** Mezzi ammessi per classe di strada (GDD: Flotta, "Dove può andare"). */
export const MEZZI_AMMESSI: Record<ClasseStrada, readonly TipoMezzo[]> = {
  viale: ["minibus", "bus", "snodato"],
  urbana: ["minibus", "bus"],
  stretta: ["minibus"],
}

/** Mezzi ammessi sull'anello delle rotonde. */
export const AMMESSI_ROTONDA: Record<TipoRotonda, readonly TipoMezzo[]> = {
  compatta: ["minibus", "bus"],
  ampia: ["minibus", "bus", "snodato"],
}

/** Altezza reale di uno strato del plastico (GDD: "uno strato di circa 10 m reali"). */
export const METRI_PER_STRATO = 10

export type Nodo = {
  readonly id: number
  readonly chiave: string // es. "L:2,-1:0" (lato), "C:2,-1" (incrocio), "R:2,-1:3" (rotonda)
  readonly x: number // posizione nel mondo
  readonly z: number
  readonly quota: number // metri
}

/** Un pezzo di tratto percorso da `da` ad `a` (ascisse in metri; da > a = verso l'inizio del tratto). */
export type Pezzo = { readonly da: number; readonly a: number }

export type Arco = {
  readonly id: number
  readonly da: number // nodo di partenza
  readonly a: number // nodo di arrivo
  readonly tessera: Hex
  readonly tratto: number
  readonly pezzi: readonly Pezzo[] // di solito uno; due per l'arco dell'anello che passa per l'inizio
  readonly lunghezza: number
  readonly salita: number // metri, negativa in discesa
  readonly classe: ClasseStrada
  readonly via: number // id della via nello stradario (-1 se nessuna)
  readonly ammessi: readonly TipoMezzo[]
}

/** Un tratto nel mondo: la sua mezzeria con le distanze progressive. */
export type TrattoNelMondo = {
  readonly tessera: Hex
  readonly tratto: number
  readonly classe: ClasseStrada
  readonly punti: readonly { readonly x: number; readonly z: number }[]
  readonly s: readonly number[] // distanza dall'inizio di ogni punto
  readonly lunghezza: number
}

export type GrafoStradale = {
  readonly nodi: readonly Nodo[]
  readonly archi: readonly Arco[]
  /** Archi che partono da ogni nodo (indice = id del nodo). */
  readonly uscenti: readonly (readonly number[])[]
  /** Tratti nel mondo, per chiave "q,r#indice". */
  readonly tratti: ReadonlyMap<string, TrattoNelMondo>
  /** Archi che percorrono ogni tratto, per chiave "q,r#indice". */
  readonly archiSulTratto: ReadonlyMap<string, readonly number[]>
}

/**
 * Un punto della rete: il tratto e la distanza dal suo inizio. `verso` dice
 * in che senso si percorre il tratto in quel punto (1 = come il tratto,
 * -1 = al contrario), cioè su quale corsia sta la fermata; senza verso vale
 * qualsiasi senso.
 */
export type PosizioneRete = {
  readonly tessera: Hex
  readonly tratto: number
  readonly s: number
  readonly verso?: 1 | -1
}

export const chiaveTratto = (tessera: Hex, tratto: number) =>
  `${chiave(tessera)}#${tratto}`

const vicino = (a: { x: number; z: number }, b: { x: number; z: number }) =>
  Math.hypot(a.x - b.x, a.z - b.z) < 0.01

/** Il lato su cui sta un punto locale del tracciato (null se non sta su un lato). */
function latoDel(p: { x: number; z: number }): Lato | null {
  return LATI.find((l) => vicino(p, puntoLato(l))) ?? null
}

/** Distanze progressive lungo una polilinea. */
function progressive(punti: readonly { x: number; z: number }[]): number[] {
  const s = [0]
  for (let i = 1; i < punti.length; i++)
    s.push(
      s[i - 1] +
        Math.hypot(punti[i].x - punti[i - 1].x, punti[i].z - punti[i - 1].z),
    )
  return s
}

/** Taglio di un tratto: a distanza s dall'inizio c'è il nodo `nodo`. */
type Taglio = { readonly s: number; readonly nodo: number }

export function generaGrafo(
  citta: CittaPopolata,
  rete: ReteStradale,
  stradario: Stradario,
): GrafoStradale {
  const strati = new Map(citta.tessere.map((t) => [chiave(t.hex), t.strati]))

  // ---------- nodi (senza doppioni) ----------
  const nodi: Nodo[] = []
  const perChiave = new Map<string, number>()
  const nodo = (k: string, x: number, z: number, quota: number): number => {
    const gia = perChiave.get(k)
    if (gia !== undefined) return gia
    const id = nodi.length
    nodi.push({ id, chiave: k, x, z, quota })
    perChiave.set(k, id)
    return id
  }

  /** Nodo del punto medio di un lato, lo stesso per le due tessere che lo condividono. */
  const nodoLato = (h: Hex, lato: Lato): number => {
    const altra = vicina(h, lato)
    const k = [
      `${chiave(h)}:${lato}`,
      `${chiave(altra)}:${latoOpposto(lato)}`,
    ].sort()[0]
    const c = centroTessera(h)
    const p = puntoLato(lato)
    const qui = strati.get(chiave(h))!
    const la = strati.get(chiave(altra)) ?? qui
    return nodo(
      `L:${k}`,
      c.x + p.x,
      c.z + p.z,
      ((qui + la) / 2) * METRI_PER_STRATO,
    )
  }

  // ---------- tratti nel mondo e tagli ----------
  const tratti = new Map<string, TrattoNelMondo>()
  const tagli = new Map<string, Taglio[]>()
  const locali = new Map<
    string,
    { tratto: Tratto; rotonda: TipoRotonda | null; anello: boolean }
  >()

  for (const t of citta.tessere) {
    const k = chiave(t.hex)
    const conn = rete.connettori.get(k)
    if (!conn) continue
    const tipoRotonda = rete.rotonde.get(k) ?? null
    const tracciato = tracciatoTessera(
      conn,
      tipoRotonda,
      rete.rettilinei.get(k),
    )
    const c = centroTessera(t.hex)
    const quota = t.strati * METRI_PER_STRATO
    const mondo = (p: { x: number; z: number }) => ({
      x: c.x + p.x,
      z: c.z + p.z,
    })

    tracciato.tratti.forEach((tr, i) => {
      const kt = chiaveTratto(t.hex, i)
      const punti = tr.punti.map(mondo)
      const s = progressive(tr.punti)
      tratti.set(kt, {
        tessera: t.hex,
        tratto: i,
        classe: tr.classe,
        punti,
        s,
        lunghezza: s[s.length - 1],
      })
      locali.set(kt, {
        tratto: tr,
        rotonda: tipoRotonda,
        anello: tr.inizio === "anello",
      })
      tagli.set(kt, [])
    })

    tracciato.tratti.forEach((tr, i) => {
      if (tr.inizio === "anello") return
      const kt = chiaveTratto(t.hex, i)
      const L = tratti.get(kt)!.lunghezza
      const fine = tr.punti[tr.punti.length - 1]
      const taglia = (kTratto: string, s: number, n: number) =>
        tagli.get(kTratto)!.push({ s, nodo: n })

      // inizio: sempre su un lato
      taglia(kt, 0, nodoLato(t.hex, tr.lato!))

      // fine
      let nFine: number
      if (tr.fine === "lato") nFine = nodoLato(t.hex, latoDel(fine)!)
      else if (tr.fine === "incrocio") nFine = nodo(`C:${k}`, c.x, c.z, quota)
      else if (tr.fine === "cieco")
        nFine = nodo(`E:${k}#${i}`, c.x + fine.x, c.z + fine.z, quota)
      else if (tr.fine === "innesto") {
        // l'innesto finisce su un punto del viale passante (il tratto 0): lì il viale si divide.
        // Due innesti da lati opposti possono arrivare nello stesso punto (un incrocio
        // vero e proprio): il nodo dipende dal punto, così è uno solo.
        const passante = tracciato.tratti[0]
        const j = passante.punti.findIndex((p) => vicino(p, fine))
        nFine = nodo(`I:${k}@${j}`, c.x + fine.x, c.z + fine.z, quota)
        taglia(
          chiaveTratto(t.hex, 0),
          tratti.get(chiaveTratto(t.hex, 0))!.s[j],
          nFine,
        )
      } else {
        // 'rotonda': l'ingresso sta sull'anello, all'angolo del lato da cui arriva la strada
        const iAnello = tracciato.tratti.findIndex((x) => x.inizio === "anello")
        const kAnello = chiaveTratto(t.hex, iAnello)
        const anello = tracciato.tratti[iAnello].punti
        const n = anello.length - 1 // l'ultimo punto coincide con il primo
        const j = Math.round((tr.lato! / 6) * n) % n
        nFine = nodo(
          `R:${k}:${tr.lato}`,
          c.x + anello[j].x,
          c.z + anello[j].z,
          quota,
        )
        taglia(kAnello, tratti.get(kAnello)!.s[j], nFine)
      }
      taglia(kt, L, nFine)
    })
  }

  // ---------- archi ----------
  const archi: Arco[] = []
  const archiSulTratto = new Map<string, number[]>()
  const aggiungi = (
    kt: string,
    da: number,
    a: number,
    pezzi: Pezzo[],
    ammessi: readonly TipoMezzo[],
  ) => {
    const tr = tratti.get(kt)!
    const id = archi.length
    archi.push({
      id,
      da,
      a,
      tessera: tr.tessera,
      tratto: tr.tratto,
      pezzi,
      lunghezza: pezzi.reduce((m, p) => m + Math.abs(p.a - p.da), 0),
      salita: nodi[a].quota - nodi[da].quota,
      classe: tr.classe,
      via: stradario.viaDi.get(kt) ?? -1,
      ammessi,
    })
    archiSulTratto.get(kt)!.push(id)
  }

  for (const [kt, lista] of tagli) {
    archiSulTratto.set(kt, [])
    const { tratto, rotonda, anello } = locali.get(kt)!
    const ordinati = [...lista].sort((x, y) => x.s - y.s)
    if (anello) {
      // anello: un solo senso (quello dei punti, antiorario), da un ingresso al successivo
      const L = tratti.get(kt)!.lunghezza
      const ammessi = AMMESSI_ROTONDA[rotonda!]
      ordinati.forEach((t, j) => {
        const dopo = ordinati[(j + 1) % ordinati.length]
        const pezzi =
          dopo.s > t.s
            ? [{ da: t.s, a: dopo.s }]
            : [
                { da: t.s, a: L },
                { da: 0, a: dopo.s },
              ]
        aggiungi(
          kt,
          t.nodo,
          dopo.nodo,
          pezzi.filter((p) => p.a > p.da),
          ammessi,
        )
      })
    } else {
      // strade a doppio senso: un arco per verso tra due tagli consecutivi
      const ammessi = MEZZI_AMMESSI[tratto.classe]
      for (let j = 1; j < ordinati.length; j++) {
        const x = ordinati[j - 1]
        const y = ordinati[j]
        if (y.s - x.s < 0.01) continue
        aggiungi(kt, x.nodo, y.nodo, [{ da: x.s, a: y.s }], ammessi)
        aggiungi(kt, y.nodo, x.nodo, [{ da: y.s, a: x.s }], ammessi)
      }
    }
  }

  const uscenti: number[][] = nodi.map(() => [])
  for (const e of archi) uscenti[e.da].push(e.id)

  return { nodi, archi, uscenti, tratti, archiSulTratto }
}

// ---------------------------------------------------------------------
// Posizioni sulla rete
// ---------------------------------------------------------------------

/** Il punto (e la direzione) di un tratto a distanza s dal suo inizio. */
export function puntoSulTratto(
  t: TrattoNelMondo,
  s: number,
): { x: number; z: number; tx: number; tz: number } {
  const v = Math.min(Math.max(s, 0), t.lunghezza)
  let i = 1
  while (i < t.s.length - 1 && t.s[i] < v) i++
  const a = t.punti[i - 1]
  const b = t.punti[i]
  const l = t.s[i] - t.s[i - 1] || 1
  const k = (v - t.s[i - 1]) / l
  return {
    x: a.x + (b.x - a.x) * k,
    z: a.z + (b.z - a.z) * k,
    tx: (b.x - a.x) / l,
    tz: (b.z - a.z) / l,
  }
}

/**
 * La posizione della rete più vicina a un punto del mondo (per piantare un
 * pin dove si clicca). Restituisce anche la distanza dal punto cliccato.
 * Il verso viene dal lato della strada su cui si è cliccato: in Italia si
 * guida a destra, quindi un clic a destra della mezzeria (guardando nel senso
 * del tratto) vuol dire percorrerlo nel suo senso, un clic a sinistra al
 * contrario. L'anello delle rotonde ha un senso solo.
 */
export function posizioneVicina(
  grafo: GrafoStradale,
  x: number,
  z: number,
): (PosizioneRete & { distanza: number }) | null {
  let migliore: (PosizioneRete & { distanza: number }) | null = null
  for (const t of grafo.tratti.values()) {
    for (let i = 1; i < t.punti.length; i++) {
      const a = t.punti[i - 1]
      const b = t.punti[i]
      const dx = b.x - a.x
      const dz = b.z - a.z
      const l2 = dx * dx + dz * dz || 1
      const k = Math.min(1, Math.max(0, ((x - a.x) * dx + (z - a.z) * dz) / l2))
      const d = Math.hypot(a.x + dx * k - x, a.z + dz * k - z)
      if (!migliore || d < migliore.distanza) {
        // lato del clic: prodotto scalare con la destra del tratto (-dz, dx)
        const destra = (x - a.x) * -dz + (z - a.z) * dx
        const anello =
          Math.hypot(
            t.punti[0].x - t.punti[t.punti.length - 1].x,
            t.punti[0].z - t.punti[t.punti.length - 1].z,
          ) < 0.01
        const verso: 1 | -1 = anello || destra >= 0 ? 1 : -1
        migliore = {
          tessera: t.tessera,
          tratto: t.tratto,
          s: t.s[i - 1] + (t.s[i] - t.s[i - 1]) * k,
          verso,
          distanza: d,
        }
      }
    }
  }
  return migliore
}
