/*
 * percorso.ts
 * Il percorso più breve tra due punti della rete, per un tipo di mezzo:
 * è quello che segue lo spago tra due pin consecutivi di una linea.
 *
 * Algoritmo A* sul grafo stradale (grafo.ts):
 * - il costo è la lunghezza in metri (più avanti potrà diventare il tempo);
 * - la stima che guida la ricerca è la distanza in linea d'aria fino alla
 *   meta: non supera mai la strada vera, quindi il percorso trovato è il
 *   più breve possibile;
 * - partenza e arrivo stanno in mezzo a un arco: dalla partenza si raggiunge
 *   la fine del suo arco, all'arrivo si entra dall'inizio del suo arco;
 * - si percorrono solo gli archi ammessi per il mezzo, e nel loro verso
 *   (l'anello delle rotonde solo in senso antiorario);
 * - niente inversioni a U, e si parte e arriva sulla corsia della fermata.
 *
 * Il risultato è una lista di pezzi di tratto (tratto + da dove a dove), da
 * cui la grafica disegna lo spago e la simulazione muove i mezzi.
 */

import { chiave, type Hex } from "./esagoni"
import {
  chiaveTratto,
  puntoSulTratto,
  type Arco,
  type GrafoStradale,
  type PosizioneRete,
  type TipoMezzo,
} from "./grafo"

/** Un pezzo del percorso: il tratto della tessera, percorso dall'ascissa `da` ad `a`. */
export type PezzoPercorso = {
  readonly tessera: Hex
  readonly tratto: number
  readonly da: number
  readonly a: number
}

export type Percorso = {
  readonly lunghezza: number // metri
  readonly salita: number // metri di dislivello in salita, sommati
  readonly pezzi: readonly PezzoPercorso[]
  readonly archi: readonly number[] // gli archi del grafo percorsi, in ordine (il primo e l'ultimo in parte)
}

const EPS = 0.01

/** Quanta strada c'è dall'inizio dell'arco al punto s del suo tratto (null se s non sta sull'arco). */
function distanzaSullArco(e: Arco, s: number): number | null {
  let fatta = 0
  for (const p of e.pezzi) {
    const basso = Math.min(p.da, p.a)
    const alto = Math.max(p.da, p.a)
    if (s >= basso - EPS && s <= alto + EPS) return fatta + Math.abs(s - p.da)
    fatta += Math.abs(p.a - p.da)
  }
  return null
}

/** I pezzi dell'arco tra due distanze dal suo inizio (da `o1` a `o2`). */
function tagliaArco(e: Arco, o1: number, o2: number): PezzoPercorso[] {
  const out: PezzoPercorso[] = []
  let fatta = 0
  for (const p of e.pezzi) {
    const l = Math.abs(p.a - p.da)
    const verso = Math.sign(p.a - p.da) || 1
    const ini = Math.max(o1, fatta)
    const fin = Math.min(o2, fatta + l)
    if (fin - ini > EPS / 10) {
      out.push({
        tessera: e.tessera,
        tratto: e.tratto,
        da: p.da + verso * (ini - fatta),
        a: p.da + verso * (fin - fatta),
      })
    }
    fatta += l
  }
  return out
}

/** Coda con priorità (heap binario) di coppie [priorità, nodo]. */
class Coda {
  private readonly h: [number, number][] = []
  get vuota() {
    return this.h.length === 0
  }
  metti(p: number, n: number) {
    const h = this.h
    h.push([p, n])
    let i = h.length - 1
    while (i > 0) {
      const g = (i - 1) >> 1
      if (h[g][0] <= h[i][0]) break
      ;[h[g], h[i]] = [h[i], h[g]]
      i = g
    }
  }
  prendi(): [number, number] {
    const h = this.h
    const top = h[0]
    const ultimo = h.pop()!
    if (h.length > 0) {
      h[0] = ultimo
      let i = 0
      for (;;) {
        const s = 2 * i + 1
        const d = s + 1
        let m = i
        if (s < h.length && h[s][0] < h[m][0]) m = s
        if (d < h.length && h[d][0] < h[m][0]) m = d
        if (m === i) break
        ;[h[m], h[i]] = [h[i], h[m]]
        i = m
      }
    }
    return top
  }
}

/** Il verso in cui un arco percorre il suo tratto (1 = come il tratto). */
const versoArco = (e: Arco) => (e.pezzi[0].a >= e.pezzi[0].da ? 1 : -1)

/** f è l'inversione a U di e: lo stesso pezzo di strada, ripercorso all'indietro. */
const eInversione = (e: Arco, f: Arco) =>
  f.da === e.a &&
  f.a === e.da &&
  f.tratto === e.tratto &&
  f.tessera === e.tessera &&
  versoArco(f) !== versoArco(e)

/**
 * Il percorso più breve da `da` ad `a` per il mezzo indicato, oppure null se
 * non esiste. Regole di guida:
 * - si parte e si arriva nel verso della fermata (la sua corsia), se indicato;
 * - niente inversioni a U: né in mezzo alla strada né agli incroci. Si torna
 *   indietro solo girando in una rotonda, facendo il giro dell'isolato o in
 *   fondo a una strada senza uscita (dove non c'è altra scelta).
 * Per questo la ricerca non avanza di nodo in nodo ma di ARCO in arco: per
 * sapere quali svolte sono ammesse serve sapere da dove si arriva.
 */
export function cercaPercorso(
  grafo: GrafoStradale,
  da: PosizioneRete,
  a: PosizioneRete,
  mezzo: TipoMezzo,
): Percorso | null {
  const ammesso = (e: Arco) => e.ammessi.includes(mezzo)
  const sulTratto = (p: PosizioneRete) =>
    (grafo.archiSulTratto.get(chiaveTratto(p.tessera, p.tratto)) ?? [])
      .map((id) => grafo.archi[id])
      .filter(
        (e) =>
          ammesso(e) && (p.verso === undefined || versoArco(e) === p.verso),
      )
      .map((e) => ({ e, o: distanzaSullArco(e, p.s) }))
      .filter((x): x is { e: Arco; o: number } => x.o !== null)

  const partenze = sulTratto(da)
  const arrivi = sulTratto(a)
  if (partenze.length === 0 || arrivi.length === 0) return null

  /** Archi che si possono prendere arrivando con l'arco e (senza inversione a U, salvo vicoli ciechi). */
  const prossimi = (e: Arco): Arco[] => {
    const tutti = grafo.uscenti[e.a]
      .map((id) => grafo.archi[id])
      .filter(ammesso)
    const senzaU = tutti.filter((f) => !eInversione(e, f))
    return senzaU.length > 0 ? senzaU : tutti
  }

  const meta = puntoSulTratto(
    grafo.tratti.get(chiaveTratto(a.tessera, a.tratto))!,
    a.s,
  )
  const stima = (e: Arco) =>
    Math.hypot(grafo.nodi[e.a].x - meta.x, grafo.nodi[e.a].z - meta.z)

  let migliore = Infinity
  let finale:
    | { tipo: "diretto"; e: Arco; o1: number; o2: number }
    | { tipo: "grafo"; ultimo: Arco; e: Arco; o: number }
    | null = null

  // partenza e arrivo sullo stesso arco, con l'arrivo più avanti
  for (const p of partenze) {
    for (const q of arrivi) {
      if (p.e.id === q.e.id && q.o >= p.o - EPS && q.o - p.o < migliore) {
        migliore = Math.max(0, q.o - p.o)
        finale = { tipo: "diretto", e: p.e, o1: p.o, o2: Math.max(p.o, q.o) }
      }
    }
  }

  // A* sugli archi: g = strada fatta fino alla FINE dell'arco
  const g = new Map<number, number>()
  const venuto = new Map<number, { prima: Arco | null; inizio: number }>() // prima = null: arco di partenza
  const coda = new Coda()
  for (const p of partenze) {
    const costo = p.e.lunghezza - p.o
    if (costo < (g.get(p.e.id) ?? Infinity)) {
      g.set(p.e.id, costo)
      venuto.set(p.e.id, { prima: null, inizio: p.o })
      coda.metti(costo + stima(p.e), p.e.id)
    }
  }
  while (!coda.vuota) {
    const [f, id] = coda.prendi()
    if (f >= migliore) break
    const e = grafo.archi[id]
    const ge = g.get(id)!
    if (f - stima(e) > ge + EPS) continue // voce superata
    const uscite = prossimi(e)
    for (const q of arrivi) {
      if (uscite.includes(q.e) && ge + q.o < migliore) {
        migliore = ge + q.o
        finale = { tipo: "grafo", ultimo: e, e: q.e, o: q.o }
      }
    }
    for (const n of uscite) {
      const costo = ge + n.lunghezza
      if (costo < (g.get(n.id) ?? Infinity) - EPS) {
        g.set(n.id, costo)
        venuto.set(n.id, { prima: e, inizio: 0 })
        coda.metti(costo + stima(n), n.id)
      }
    }
  }
  if (!finale) return null

  // ---------- ricostruzione ----------
  const usati: { arco: Arco; o1: number; o2: number }[] = []
  if (finale.tipo === "diretto")
    usati.push({ arco: finale.e, o1: finale.o1, o2: finale.o2 })
  else {
    let e: Arco | null = finale.ultimo
    for (let passi = 0; e && passi <= grafo.archi.length; passi++) {
      const v: { prima: Arco | null; inizio: number } = venuto.get(e.id)!
      usati.unshift({ arco: e, o1: v.inizio, o2: e.lunghezza })
      e = v.prima
    }
    usati.push({ arco: finale.e, o1: 0, o2: finale.o })
  }

  return {
    lunghezza: migliore,
    salita: usati.reduce(
      (m, u) =>
        m +
        Math.max(0, u.arco.salita) * ((u.o2 - u.o1) / (u.arco.lunghezza || 1)),
      0,
    ),
    pezzi: unisci(usati.flatMap((u) => tagliaArco(u.arco, u.o1, u.o2))),
    archi: usati.map((u) => u.arco.id),
  }
}

/** Unisce i pezzi consecutivi dello stesso tratto che proseguono l'uno nell'altro. */
function unisci(pezzi: PezzoPercorso[]): PezzoPercorso[] {
  const out: PezzoPercorso[] = []
  for (const p of pezzi) {
    const u = out[out.length - 1]
    const stessoVerso = u && Math.sign(u.a - u.da) === Math.sign(p.a - p.da)
    if (
      u &&
      stessoVerso &&
      chiave(u.tessera) === chiave(p.tessera) &&
      u.tratto === p.tratto &&
      Math.abs(u.a - p.da) < EPS
    ) {
      out[out.length - 1] = { ...u, a: p.a }
    } else out.push(p)
  }
  return out
}

/** I punti del mondo lungo un percorso (per disegnare lo spago), circa ogni `passo` metri. */
export function puntiPercorso(
  grafo: GrafoStradale,
  percorso: Percorso,
  passo = 4,
): { x: number; z: number }[] {
  const out: { x: number; z: number }[] = []
  for (const p of percorso.pezzi) {
    const t = grafo.tratti.get(chiaveTratto(p.tessera, p.tratto))!
    const l = Math.abs(p.a - p.da)
    const n = Math.max(1, Math.ceil(l / passo))
    for (let i = 0; i <= n; i++) {
      const q = puntoSulTratto(t, p.da + ((p.a - p.da) * i) / n)
      out.push({ x: q.x, z: q.z })
    }
  }
  return out
}
