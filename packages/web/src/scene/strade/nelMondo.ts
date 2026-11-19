/*
 * nelMondo.ts
 * Dalle posizioni del motore (tratto + distanza) ai punti 3D della scena:
 * x e z vengono dal grafo, l'altezza dalla pila di strati della tessera.
 *
 * Il motore ragiona sulla mezzeria; per far capire il verso di marcia lo
 * spago si sposta sulla CORSIA DI DESTRA (in Italia si guida a destra):
 * - strada urbana e stretta: metà della propria metà di carreggiata;
 * - viale: la corsia esterna (quella delle fermate);
 * - anello delle rotonde: resta al centro (è a senso unico).
 * "Destra" dipende dal verso: se un pezzo percorre il tratto all'indietro
 * (da > a) la destra si inverte.
 * Funzioni pure, usate da pin, spago e frecce.
 *
 *  * Dalle posizioni del motore (tratto + distanza) ai punti 3D della scena:
 * x e z vengono dal grafo, l'altezza dalla pila di strati della tessera, più
 * la rampa se il punto ci sta sopra (rampe.ts): così mezzi, spago e pin
 * salgono lungo la rampa invece di saltare sul lato.
 */

import {
  centroTessera,
  chiave,
  chiaveTratto,
  puntoSulTratto,
  type CittaPopolata,
  type ClasseStrada,
  type GrafoStradale,
  type Percorso,
  type PosizioneRete,
  type Rampa,
  type ReteStradale,
  type TrattoNelMondo,
} from "@corsa-bis/engine"
import { PROFILO } from "../strade/profili"
import { quotaSuperiore } from "../tessere/misure"
import { quotaRampa, rampePerTessera } from "../strade/rampe"

const CORSIA = 18.2

/** Distanza dalla mezzeria del centro della corsia di destra. */
const SCOSTAMENTO: Record<ClasseStrada, number> = {
  viale: PROFILO.viale.carreggiata / 2 - CORSIA / 2, // corsia esterna
  urbana: PROFILO.urbana.carreggiata / 4,
  stretta: PROFILO.stretta.carreggiata / 4,
}

/** Distanza dalla mezzeria del centro del marciapiede (dove si pianta la palina). */
export const marciapiede = (classe: ClasseStrada) =>
  PROFILO[classe].carreggiata / 2 + Math.max(PROFILO[classe].marciapiede / 2, 3)

/** L'anello di una rotonda è l'unico tratto chiuso (primo e ultimo punto coincidono). */
const eAnello = (t: TrattoNelMondo) => {
  const a = t.punti[0]
  const b = t.punti[t.punti.length - 1]
  return Math.hypot(a.x - b.x, a.z - b.z) < 0.01
}

/**
 * Altezza della faccia superiore di ogni tessera, per chiave "q,r"; con la
 * rete stradale anche le rampe di ogni tessera (rampe), per le quote lungo
 * la rampa. Resta una Map: chi la usa solo per la tessera non cambia.
 */
export type Altezze = ReadonlyMap<string, number> & {
  readonly rampe?: ReadonlyMap<string, readonly Rampa[]>
}

export function altezzeTessere(
  citta: CittaPopolata,
  rete?: ReteStradale,
): Altezze {
  const altezze = new Map(
    citta.tessere.map((t) => [chiave(t.hex), quotaSuperiore(t.strati)]),
  )
  return Object.assign(altezze, {
    rampe: rete ? rampePerTessera(rete.rampe) : undefined,
  })
}

/** La quota del punto (x, z) della tessera: la sua faccia superiore, più la rampa se ci sta sopra. */
export const quotaNelPunto = (
  altezze: Altezze,
  k: string,
  x: number,
  z: number,
) => (altezze.get(k) ?? 0) + quotaRampa(altezze.rampe?.get(k), x, z)

export type Campione = {
  readonly p: [number, number, number] // punto 3D
  readonly dx: number // direzione di marcia (versore)
  readonly dz: number
}

/**
 * Il punto 3D di una posizione della rete per chi viaggia nel `verso`
 * indicato (+1 = come il tratto, -1 = al contrario), scostato di `laterale`
 * unità verso destra e alzato di `sopra` unità.
 */
export function campione(
  grafo: GrafoStradale,
  altezze: Altezze,
  p: PosizioneRete,
  verso: number,
  laterale: number,
  sopra = 0,
): Campione {
  const q = puntoSulTratto(
    grafo.tratti.get(chiaveTratto(p.tessera, p.tratto))!,
    p.s,
  )
  const dx = q.tx * verso
  const dz = q.tz * verso
  // destra rispetto al verso di marcia: (-dz, dx) con x = est e z = sud
  const x = q.x - dz * laterale
  const z = q.z + dx * laterale
  return {
    p: [x, quotaNelPunto(altezze, chiave(p.tessera), x, z) + sopra, z],
    dx,
    dz,
  }
}

/**
 * Dove sta una cosa rispetto alla mezzeria, a destra del verso di marcia:
 * - 'corsia': il centro della corsia (ci viaggiano i mezzi);
 * - 'marciapiede': il centro del marciapiede (ci stanno i pin e lo spago,
 *   annodato ai pin). Sull'anello delle rotonde, a senso unico, la corsia è
 *   al centro e il "marciapiede" è appena fuori dal bordo esterno
 *   (larghezza dell'anello = raggio / 2, come in MISURE_ROTONDA).
 */
export type Lato = "corsia" | "marciapiede"

export function scostamento(t: TrattoNelMondo, lato: Lato): number {
  if (!eAnello(t))
    return lato === "corsia" ? SCOSTAMENTO[t.classe] : marciapiede(t.classe)
  if (lato === "corsia") return 0
  const c = centroTessera(t.tessera)
  const raggio = Math.hypot(t.punti[0].x - c.x, t.punti[0].z - c.z)
  return raggio / 4 + 4
}

/** Il punto 3D sul lato indicato (corsia o marciapiede), per chi viaggia nel verso della posizione. */
export function campioneLato(
  grafo: GrafoStradale,
  altezze: ReadonlyMap<string, number>,
  p: PosizioneRete,
  lato: Lato,
  sopra = 0,
): Campione {
  const t = grafo.tratti.get(chiaveTratto(p.tessera, p.tratto))!
  return campione(grafo, altezze, p, p.verso ?? 1, scostamento(t, lato), sopra)
}

/** Il punto 3D al centro della corsia di destra, per chi viaggia nel verso della posizione. */
export const campioneCorsia = (
  grafo: GrafoStradale,
  altezze: ReadonlyMap<string, number>,
  p: PosizioneRete,
  sopra = 0,
) => campioneLato(grafo, altezze, p, "corsia", sopra)

/** I campioni di uno spago sulla corsia di destra, ogni `passo` unità circa, sospesi `sopra` unità. */
export function campioniSpago(
  grafo: GrafoStradale,
  altezze: ReadonlyMap<string, number>,
  percorso: Percorso,
  sopra: number,
  passo = 6,
  lato: Lato = "corsia",
): Campione[] {
  const out: Campione[] = []
  for (const pezzo of percorso.pezzi) {
    const verso: 1 | -1 = pezzo.a >= pezzo.da ? 1 : -1
    const l = Math.abs(pezzo.a - pezzo.da)
    const n = Math.max(1, Math.ceil(l / passo))
    for (let i = 0; i <= n; i++) {
      const s = pezzo.da + ((pezzo.a - pezzo.da) * i) / n
      out.push(
        campioneLato(
          grafo,
          altezze,
          { tessera: pezzo.tessera, tratto: pezzo.tratto, s, verso },
          lato,
          sopra,
        ),
      )
    }
  }
  return out
}

/**
 * Classe e verso di marcia in una fermata: il verso scelto con il clic (la
 * corsia), oppure, se manca, quello dello spago che parte o che arriva.
 */
export function versoInFermata(
  grafo: GrafoStradale,
  partenza: Percorso | undefined,
  arrivo: Percorso | undefined,
  p: PosizioneRete,
) {
  const classe = grafo.tratti.get(chiaveTratto(p.tessera, p.tratto))!.classe
  const pezzo = partenza?.pezzi[0] ?? arrivo?.pezzi.at(-1)
  const verso = p.verso ?? (pezzo ? Math.sign(pezzo.a - pezzo.da) || 1 : 1)
  return { classe, verso }
}

// ---------------------------------------------------------------------
// Tracce smussate: la linea che seguono spago e mezzi
// ---------------------------------------------------------------------

/**
 * Una traccia è il percorso sulla corsia di destra come polilinea 3D, con le
 * distanze progressive. Agli incroci, agli innesti e agli ingressi in rotonda
 * due pezzi di strada si incontrano ad angolo (e con la corsia spostata):
 * lì la traccia si "smussa" come la curva di un autista. Si accorciano i due
 * pezzi di RAGGIO_SVOLTA unità ciascuno e si uniscono con una curva di Bézier
 * cubica, tangente a entrambi. Dove la strada prosegue dritta non cambia niente.
 */
export type Traccia = {
  readonly punti: [number, number, number][]
  readonly s: number[]
  readonly lunghezza: number
}

const RAGGIO_SVOLTA = 30
const cacheTracce: Record<Lato, WeakMap<Percorso, Traccia>> = {
  corsia: new WeakMap(),
  marciapiede: new WeakMap(),
}

type P3 = [number, number, number]
const dist = (a: P3, b: P3) => Math.hypot(a[0] - b[0], a[2] - b[2])
const progressive3 = (punti: P3[]) => {
  const s = [0]
  for (let i = 1; i < punti.length; i++)
    s.push(s[i - 1] + dist(punti[i - 1], punti[i]))
  return s
}

/** Il punto (e la direzione) di una polilinea a distanza d dall'inizio. */
function lungo(
  punti: P3[],
  s: number[],
  d: number,
): { p: P3; dx: number; dz: number } {
  const v = Math.min(Math.max(d, 0), s[s.length - 1])
  let i = 1
  while (i < s.length - 1 && s[i] < v) i++
  const a = punti[i - 1]
  const b = punti[i]
  const l = s[i] - s[i - 1] || 1
  const k = (v - s[i - 1]) / l
  return {
    p: [
      a[0] + (b[0] - a[0]) * k,
      a[1] + (b[1] - a[1]) * k,
      a[2] + (b[2] - a[2]) * k,
    ],
    dx: (b[0] - a[0]) / l,
    dz: (b[2] - a[2]) / l,
  }
}

/** Taglia una polilinea tra le distanze da e a (punti inclusi agli estremi). */
function taglia(punti: P3[], s: number[], da: number, a: number): P3[] {
  const out: P3[] = [lungo(punti, s, da).p]
  for (let i = 0; i < punti.length; i++)
    if (s[i] > da && s[i] < a) out.push(punti[i])
  out.push(lungo(punti, s, a).p)
  return out
}

export function tracciaPercorso(
  grafo: GrafoStradale,
  altezze: ReadonlyMap<string, number>,
  percorso: Percorso,
  lato: Lato = "corsia",
): Traccia {
  const gia = cacheTracce[lato].get(percorso)
  if (gia) return gia

  // un tratto di polilinea per ogni pezzo del percorso, sulla corsia di destra
  const pezzi = percorso.pezzi.map((pz) => {
    const punti = campioniSpago(
      grafo,
      altezze,
      { ...percorso, pezzi: [pz] },
      0,
      4,
      lato,
    ).map((c) => c.p)
    return { punti, s: progressive3(punti) }
  })

  const out: P3[] = []
  let inizio = 0 // da dove prendere il pezzo corrente (accorciato dalla svolta precedente)
  pezzi.forEach((pz, i) => {
    const L = pz.s[pz.s.length - 1]
    const dopo = pezzi[i + 1]
    let fine = L
    const curva: P3[] = [] // i punti della svolta (vuota se non si svolta)
    if (dopo) {
      const a = lungo(pz.punti, pz.s, L)
      const b = lungo(dopo.punti, dopo.s, 0)
      const angolo = Math.abs(
        Math.atan2(a.dx * b.dz - a.dz * b.dx, a.dx * b.dx + a.dz * b.dz),
      )
      // svolta vera: cambia direzione o la corsia salta di lato
      if (angolo > 0.17 || dist(a.p, b.p) > 1) {
        const Ldopo = dopo.s[dopo.s.length - 1]
        const r = Math.min(RAGGIO_SVOLTA, 0.45 * (L - inizio), 0.45 * Ldopo)
        fine = L - r
        const p0 = lungo(pz.punti, pz.s, fine)
        const p3 = lungo(dopo.punti, dopo.s, r)
        const k = dist(p0.p, p3.p) * 0.45 // lunghezza delle maniglie della Bézier
        const c1: P3 = [p0.p[0] + p0.dx * k, p0.p[1], p0.p[2] + p0.dz * k]
        const c2: P3 = [p3.p[0] - p3.dx * k, p3.p[1], p3.p[2] - p3.dz * k]
        for (let j = 1; j < 12; j++) {
          const t = j / 12
          const u = 1 - t
          const w = [u * u * u, 3 * u * u * t, 3 * u * t * t, t * t * t]
          curva.push(
            [0, 1, 2].map(
              (c) =>
                w[0] * p0.p[c] + w[1] * c1[c] + w[2] * c2[c] + w[3] * p3.p[c],
            ) as P3,
          )
        }
        out.push(...taglia(pz.punti, pz.s, inizio, fine), ...curva)
        inizio = r
        return
      }
    }
    out.push(...taglia(pz.punti, pz.s, inizio, fine))
    inizio = 0
  })

  // via i punti troppo vicini al precedente: dove due pezzi si toccano senza svolta
  // le corsie combaciano a meno di qualche decimo e lascerebbero un piccolo zig-zag
  const punti: P3[] = []
  for (const p of out)
    if (punti.length === 0 || dist(p, punti[punti.length - 1]) > 1)
      punti.push(p)
  if (punti.length === 1) punti.push([...punti[0]] as P3)
  const s = progressive3(punti)
  const traccia: Traccia = { punti, s, lunghezza: s[s.length - 1] }
  cacheTracce[lato].set(percorso, traccia)
  return traccia
}

/** Il punto di una traccia a distanza d dall'inizio, con la direzione di marcia. */
export const puntoTraccia = (t: Traccia, d: number) => lungo(t.punti, t.s, d)

/** La parte di una traccia tra le distanze da e a (estremi interpolati); vuota se da >= a. */
export const porzioneTraccia = (
  t: Traccia,
  da: number,
  a: number,
): [number, number, number][] => (da < a ? taglia(t.punti, t.s, da, a) : [])
