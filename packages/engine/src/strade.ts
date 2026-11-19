/*
 * strade.ts
 * Rete stradale gerarchica della città (GDD: "Connettori sui lati",
 * "Geometria della tessera e strade", "Binari del tram").
 *
 * Tre livelli, costruiti in quest'ordine:
 * 1. ARTERIE (viali a 4 corsie), continue e decise per prime:
 *    - circonvallazione: arco di viali attorno al centro storico, sulle
 *      tessere che lo toccano (dove la città lo circonda);
 *    - radiali: da una "porta" del centro verso le zone industriali e i
 *      quartieri più grandi (3-5 in tutto), solo rettilinei o curve larghe,
 *      evitando le salite; dove vanno nella stessa direzione si fondono in un
 *      tronco comune. Un viale non entra mai nel centro storico.
 * 2. STRADE URBANE (2 corsie): ogni tessera si collega alla rete (albero
 *    casuale pesato, poi qualche anello in più nei quartieri densi).
 * 3. STRADE STRETTE: solo dentro il centro storico.
 *  4. ROTONDE (mai nel centro storico): nei fondi ciechi per fare inversione,
 *    dove finisce un'arteria, dove si incontrano più arterie, all'ingresso in
 *    città dalle strade di campagna e, a volte, negli incroci a 4 tra le case.
 *
 * Coerenza: la classe appartiene al collegamento, non alla tessera, quindi un
 * viale resta viale per tutta l'arteria. Al massimo 4 connettori per tessera;
 * un lato con strada tocca sempre un lato con strada.
 * Flusso casuale proprio ('strade'): non cambia forma, caratteri e nomi.
 */

import { flusso, type Casuale } from "./casuale"
import {
  centroTessera,
  chiave,
  distanza,
  LATI,
  latoOpposto,
  vicina,
  vicine,
  type Hex,
  type Lato,
} from "./esagoni"
import type { CittaPopolata, TesseraTipizzata, TipoTessera } from "./popola"

export type ClasseStrada = "viale" | "urbana" | "stretta"
export type Connettore = ClasseStrada | "nessuna"

/** Livello del collegamento nella gerarchia. */
export type Livello = "circonvallazione" | "radiale" | "locale"

/** Effetto dell'incontro di due classi sullo stesso lato (tabella "Abbinamento" del GDD). */
export type Abbinamento = "normale" | "restringimento" | "rallentamento"

export type Collegamento = {
  readonly a: Hex
  readonly latoA: Lato // lato di `a`; per `b` è latoOpposto(latoA)
  readonly b: Hex
  readonly classeA: ClasseStrada
  readonly classeB: ClasseStrada
  readonly abbinamento: Abbinamento
  readonly livello: Livello
}

/** Un'arteria come sequenza di tessere consecutive: servirà per tram, segnaletica e traffico. */
export type Arteria = {
  readonly livello: Exclude<Livello, "locale">
  readonly tessere: readonly Hex[]
}

/** Rotonda al centro di una tessera: compatta nei quartieri, ampia su arterie e zone industriali. */
export type TipoRotonda = "compatta" | "ampia"

export type ReteStradale = {
  /** Per ogni tessera (chiave "q,r") i connettori dei lati 0-5. */
  readonly connettori: ReadonlyMap<string, readonly Connettore[]>
  readonly collegamenti: readonly Collegamento[]
  readonly arterie: readonly Arteria[]
  /** Tessere (chiave "q,r") con una rotonda al centro. */
  readonly rotonde: ReadonlyMap<string, TipoRotonda>
  /** Le rampe tra tessere di quota diversa (dentro la tessera bassa). */
  readonly rampe: readonly Rampa[]
  /**
   * Per le tessere con almeno una rampa (chiave "q,r"): per ogni lato la
   * lunghezza del rettilineo con cui la strada parte dal lato (0 = nessuno).
   * Lì sta la rampa, che è dritta: la strada curva solo dopo.
   */
  readonly rettilinei: ReadonlyMap<string, readonly number[]>
}

/**
 * Rampa tra due tessere collegate da una strada con 1 o 2 strati di
 * differenza (GDD: "Rampe", 18 novembre). Sta dentro la tessera BASSA: parte
 * dal connettore del lato alla quota della tessera alta e scende dritta verso
 * il centro per LUNGHEZZA_RAMPA_PER_STRATO × salto.
 */
export type Rampa = {
  /** La tessera bassa, che contiene la rampa. */
  readonly hex: Hex
  /** Il lato della tessera bassa verso la tessera alta. */
  readonly lato: Lato
  readonly classe: ClasseStrada
  /** Strati di differenza: 1 o 2. */
  readonly salto: 1 | 2
}

/**
 * Lunghezza di una rampa per ogni strato di dislivello: 5 × 12,2 (il passo di
 * uno strato in scena) = 61 unità, come i pezzi Rampa_* di tessere.glb.
 */
export const LUNGHEZZA_RAMPA_PER_STRATO = 61

export const REGOLE_STRADE = {
  maxConnettori: 4,
  radiali: [3, 5],
  probabilitaRotondaResidenziale: 0.5,
} as const

/** Probabilità di un collegamento in più (anello) secondo il tipo: denso = più incroci. */
const PROBABILITA_ANELLO: Record<TipoTessera, number> = {
  centro_storico: 0.6,
  uffici_commercio: 0.5,
  popolare: 0.4,
  nuove_costruzioni: 0.35,
  industriale: 0.3,
  villette: 0.25,
  parco: 0.15,
  strada: 0.05,
}

/** Risultato dell'incontro di due classi sullo stesso lato. */
export function abbinamento(x: ClasseStrada, y: ClasseStrada): Abbinamento {
  if (x === y) return "normale"
  if (x === "stretta" || y === "stretta") return "rallentamento" // urbana ↔ stretta
  return "restringimento" // viale ↔ urbana
}

/**
 * Curve ammesse per un viale: entrando da `ingresso`, si esce dal lato opposto
 * (dritto) o da uno dei due lati accanto all'opposto (curva larga, 120°).
 * La curva stretta (uscire dal lato accanto all'ingresso) non è ammessa.
 */
export function curvaAmmessa(ingresso: Lato, uscita: Lato): boolean {
  const d = (uscita - ingresso + 6) % 6
  return d === 2 || d === 3 || d === 4
}

const k2 = (h: Hex, lato: Lato) => `${chiave(h)}:${lato}`

export function generaStrade(citta: CittaPopolata): ReteStradale {
  const rng = flusso(citta.seme, "strade")
  const tessere = new Map(citta.tessere.map((t) => [chiave(t.hex), t]))
  const grado = new Map<string, number>([...tessere.keys()].map((k) => [k, 0]))
  const presi = new Map<string, Livello>() // lato "q,r:lato" → livello del collegamento
  const archi: {
    a: TesseraTipizzata
    lato: Lato
    b: TesseraTipizzata
    livello: Livello
  }[] = []

  const tessera = (h: Hex) => tessere.get(chiave(h))
  const ePreso = (h: Hex, lato: Lato) => presi.has(k2(h, lato))
  const pieno = (h: Hex) => grado.get(chiave(h))! >= REGOLE_STRADE.maxConnettori
  const isCentro = (h: Hex) => tessera(h)?.tipo === "centro_storico"

  function collega(a: TesseraTipizzata, lato: Lato, livello: Livello) {
    const b = tessera(vicina(a.hex, lato))!
    if (ePreso(a.hex, lato)) return
    archi.push({ a, lato, b, livello })
    presi.set(k2(a.hex, lato), livello)
    presi.set(k2(b.hex, latoOpposto(lato)), livello)
    grado.set(chiave(a.hex), grado.get(chiave(a.hex))! + 1)
    grado.set(chiave(b.hex), grado.get(chiave(b.hex))! + 1)
  }

  // ---------- 1a. circonvallazione ----------
  const arterie: Arteria[] = []
  const anello = circonvallazione(citta, tessere)
  if (anello.length > 0)
    arterie.push({ livello: "circonvallazione", tessere: anello })
  for (let i = 0; i + 1 < anello.length; i++) {
    const lato = LATI.find(
      (l) => chiave(vicina(anello[i], l)) === chiave(anello[i + 1]),
    )!
    collega(tessera(anello[i])!, lato, "circonvallazione")
  }

  // ---------- 1b. radiali ----------
  // le radiali partono dalla circonvallazione o, dove manca, da una "porta" del centro
  const partenze = bordoCentro(citta, tessere)
  for (const meta of metteRadiali(citta, rng)) {
    const percorso = cercaRadiale(partenze, meta, tessere, presi, grado)
    if (!percorso) continue
    for (const { da, lato } of percorso) collega(tessera(da)!, lato, "radiale")
    arterie.push({
      livello: "radiale",
      tessere: [percorso[0].da, ...percorso.map((p) => vicina(p.da, p.lato))],
    })
  }

  // ---------- 2. albero urbano (Kruskal casuale pesato) ----------
  // Ogni coppia di vicine è un candidato; le arterie sono già "collegate".
  const padre = new Map<string, string>([...tessere.keys()].map((k) => [k, k]))
  const radice = (k: string): string =>
    padre.get(k) === k ? k : radice(padre.get(k)!)
  const unisci = (x: string, y: string) => padre.set(radice(x), radice(y))
  for (const { a, b } of archi) unisci(chiave(a.hex), chiave(b.hex))

  const candidati = citta.tessere.flatMap((a) =>
    ([0, 1, 2] as const).flatMap((lato) => {
      const b = tessera(vicina(a.hex, lato))
      if (!b || ePreso(a.hex, lato)) return []
      const salto = Math.abs(a.strati - b.strati)
      // chiave d'ordine casuale pesata (metodo di Efraimidis-Spirakis): peso alto = prima
      const peso = [1, 0.5, 0.2][salto]
      return [{ a, lato, b, ordine: rng.decimale() ** (1 / peso) }]
    }),
  )
  candidati.sort((x, y) => y.ordine - x.ordine)
  // due passate: prima rispettando il limite di connettori, poi (solo se serve) senza
  for (const rispettaLimite of [true, false]) {
    for (const { a, lato, b } of candidati) {
      if (
        ePreso(a.hex, lato) ||
        radice(chiave(a.hex)) === radice(chiave(b.hex))
      )
        continue
      if (rispettaLimite && (pieno(a.hex) || pieno(b.hex))) continue
      collega(a, lato, "locale")
      unisci(chiave(a.hex), chiave(b.hex))
    }
  }

  // ---------- 2b. anelli locali ----------
  for (const { a, lato, b } of candidati) {
    if (ePreso(a.hex, lato) || pieno(a.hex) || pieno(b.hex)) continue
    const p = (PROBABILITA_ANELLO[a.tipo] + PROBABILITA_ANELLO[b.tipo]) / 2
    if (rng.probabilita(p)) collega(a, lato, "locale")
  }

  // ---------- 3. classi e connettori ----------
  const connettori = new Map<string, Connettore[]>(
    [...tessere.keys()].map((k) => [k, Array<Connettore>(6).fill("nessuna")]),
  )
  const classeLocale = (h: Hex): ClasseStrada =>
    isCentro(h) ? "stretta" : "urbana"
  const collegamenti: Collegamento[] = archi.map(({ a, lato, b, livello }) => {
    const arteria = livello !== "locale"
    const classeA = arteria ? "viale" : classeLocale(a.hex)
    const classeB = arteria ? "viale" : classeLocale(b.hex)
    connettori.get(chiave(a.hex))![lato] = classeA
    connettori.get(chiave(b.hex))![latoOpposto(lato)] = classeB
    return {
      a: a.hex,
      latoA: lato,
      b: b.hex,
      classeA,
      classeB,
      abbinamento: abbinamento(classeA, classeB),
      livello,
    }
  })

  // ---------- 4. rotonde ----------
  const rotonde = new Map<string, TipoRotonda>()
  for (const t of citta.tessere) {
    if (t.tipo === "centro_storico") continue // nel centro storico: piazze, non rotonde
    const lati = connettori.get(chiave(t.hex))!
    const strade = LATI.filter((l) => lati[l] !== "nessuna")
    const viali = strade.filter((l) => lati[l] === "viale").length
    const daCampagna =
      t.tipo !== "strada" &&
      strade.some((l) => tessera(vicina(t.hex, l))?.tipo === "strada")

    let serve = false
    if (strade.length === 1)
      serve = true // fondo cieco: rotonda di inversione
    else if (viali === 1)
      serve = true // dove finisce un'arteria
    else if (viali >= 3)
      serve = true // dove si incontrano più arterie
    else if (viali === 0 && strade.length >= 3 && daCampagna)
      serve = true // ingresso in città
    else if (viali === 0 && strade.length === 4 && RESIDENZIALI.has(t.tipo)) {
      serve = rng.probabilita(REGOLE_STRADE.probabilitaRotondaResidenziale) // incrocio a 4 tra le case
    }
    if (serve)
      rotonde.set(
        chiave(t.hex),
        t.tipo === "industriale" || viali > 0 ? "ampia" : "compatta",
      )
  }

  // ---------- 5. rampe ----------
  const rampe = trovaRampe(citta, connettori)
  const rettilinei = new Map<string, number[]>()
  for (const r of rampe) {
    const k = chiave(r.hex)
    const lunghezze = rettilinei.get(k) ?? [0, 0, 0, 0, 0, 0]
    lunghezze[r.lato] = LUNGHEZZA_RAMPA_PER_STRATO * r.salto
    rettilinei.set(k, lunghezze)
  }

  return { connettori, collegamenti, arterie, rotonde, rampe, rettilinei }
}

/** Le rampe della città: ogni lato con strada verso una tessera più alta di 1 o 2 strati. */
function trovaRampe(
  citta: CittaPopolata,
  connettori: ReadonlyMap<string, readonly Connettore[]>,
): Rampa[] {
  const strati = new Map(citta.tessere.map((t) => [chiave(t.hex), t.strati]))
  const rampe: Rampa[] = []
  for (const t of citta.tessere) {
    const lati = connettori.get(chiave(t.hex))
    if (!lati) continue
    for (const lato of LATI) {
      const classe = lati[lato]
      if (classe === "nessuna") continue
      const altra = strati.get(chiave(vicina(t.hex, lato)))
      const salto = altra === undefined ? 0 : altra - t.strati
      // solo dalla tessera bassa: quella alta non ha niente da fare
      if (salto === 1 || salto === 2)
        rampe.push({ hex: t.hex, lato, classe, salto })
    }
  }
  return rampe
}

const RESIDENZIALI = new Set<TipoTessera>([
  "popolare",
  "villette",
  "nuove_costruzioni",
])

// =====================================================================
// Arterie
// =====================================================================

/** Tessere non di centro che toccano il centro storico. */
function bordoCentro(
  citta: CittaPopolata,
  tessere: Map<string, TesseraTipizzata>,
): Hex[] {
  const bordo = new Map<string, Hex>()
  for (const t of citta.tessere) {
    if (t.tipo !== "centro_storico") continue
    for (const v of vicine(t.hex)) {
      const tv = tessere.get(chiave(v))
      if (tv && tv.tipo !== "centro_storico") bordo.set(chiave(v), v)
    }
  }
  return [...bordo.values()]
}

/**
 * Circonvallazione: le tessere attorno al centro, in ordine di angolo, unite
 * dove sono vicine. Restituisce una sequenza di tessere consecutive (vicine a
 * due a due); se la città non circonda tutto il centro, è un arco e non un anello.
 */
function circonvallazione(
  citta: CittaPopolata,
  tessere: Map<string, TesseraTipizzata>,
): Hex[] {
  const bordo = bordoCentro(citta, tessere)
  if (bordo.length < 3) return []
  const centro = citta.tessere
    .filter((t) => t.tipo === "centro_storico")
    .map((t) => centroTessera(t.hex))
  const cx = centro.reduce((s, p) => s + p.x, 0) / centro.length
  const cz = centro.reduce((s, p) => s + p.z, 0) / centro.length
  const angolo = (h: Hex) => {
    const p = centroTessera(h)
    return Math.atan2(cz - p.z, p.x - cx)
  }
  const ordinate = [...bordo].sort((x, y) => angolo(x) - angolo(y))

  // il tratto continuo più lungo di tessere vicine a due a due (anche "girando" dall'ultima alla prima)
  const n = ordinate.length
  const vicineTra = (i: number) =>
    distanza(ordinate[i % n], ordinate[(i + 1) % n]) === 1
  if (ordinate.every((_, i) => vicineTra(i))) return [...ordinate, ordinate[0]] // anello chiuso
  let migliore: Hex[] = []
  for (let inizio = 0; inizio < n; inizio++) {
    if (vicineTra(inizio - 1 + n)) continue // si parte solo dopo un'interruzione
    const tratto = [ordinate[inizio]]
    for (let i = inizio; vicineTra(i) && tratto.length < n; i++)
      tratto.push(ordinate[(i + 1) % n])
    if (tratto.length > migliore.length) migliore = tratto
  }
  return migliore.length >= 3 ? migliore : []
}

/** Le mete delle radiali: zone industriali, poi i quartieri più grandi, fino a 3-5. */
function metteRadiali(citta: CittaPopolata, rng: Casuale): Hex[][] {
  const quartieri = citta.quartieri.filter((q) => q.id !== 0)
  const industriali = quartieri.filter((q) => q.carattere === "industriale")
  const altri = quartieri
    .filter((q) => q.carattere !== "industriale" && !q.frazione)
    .sort((x, y) => y.tessere.length - x.tessere.length)
  const numero = rng.intero(...REGOLE_STRADE.radiali)
  return [...industriali, ...altri].slice(0, numero).map((q) => [...q.tessere])
}

type Passo = { da: Hex; lato: Lato }

/**
 * Percorso di una radiale (ricerca a costo minimo, Dijkstra) dalle tessere di
 * partenza a una qualsiasi tessera della meta. Lo stato è "tessera + lato da cui
 * si è entrati", per rispettare le curve ammesse. Riusare un'arteria già
 * esistente costa poco: così le radiali si fondono in tronchi comuni.
 */
function cercaRadiale(
  partenze: Hex[],
  meta: Hex[],
  tessere: Map<string, TesseraTipizzata>,
  presi: Map<string, Livello>,
  grado: Map<string, number>,
): Passo[] | null {
  const mete = new Set(meta.map(chiave))
  const statoK = (h: Hex, ingresso: Lato | -1) => `${chiave(h)}|${ingresso}`
  const costi = new Map<string, number>()
  const da = new Map<string, { stato: string; passo: Passo } | null>()
  const aperti: { h: Hex; ingresso: Lato | -1; costo: number }[] = []

  for (const p of partenze) {
    const s = statoK(p, -1)
    costi.set(s, 0)
    da.set(s, null)
    aperti.push({ h: p, ingresso: -1, costo: 0 })
  }

  while (aperti.length > 0) {
    // il più economico (la città è piccola: una ricerca lineare basta)
    let iMin = 0
    for (let i = 1; i < aperti.length; i++)
      if (aperti[i].costo < aperti[iMin].costo) iMin = i
    const { h, ingresso, costo } = aperti.splice(iMin, 1)[0]
    const s = statoK(h, ingresso)
    if (costo > costi.get(s)!) continue

    if (mete.has(chiave(h)) && ingresso !== -1) {
      // ricostruzione del percorso all'indietro
      const passi: Passo[] = []
      for (let cur = da.get(s); cur; cur = da.get(cur.stato))
        passi.unshift(cur.passo)
      return passi
    }

    const t = tessere.get(chiave(h))!
    for (const uscita of LATI) {
      if (ingresso !== -1 && !curvaAmmessa(ingresso, uscita)) continue
      const v = vicina(h, uscita)
      const tv = tessere.get(chiave(v))
      if (!tv || tv.tipo === "centro_storico") continue
      const gia = presi.get(k2(h, uscita))
      if (gia === "locale") continue
      const esistente = gia !== undefined // tratto di arteria già costruito
      if (
        !esistente &&
        ((grado.get(chiave(h)) ?? 0) >= 4 || (grado.get(chiave(v)) ?? 0) >= 4)
      )
        continue
      const salto = Math.abs(t.strati - tv.strati)
      const passo = esistente ? 0.3 : 1 + [0, 0.5, 2][salto]
      const ns = statoK(v, latoOpposto(uscita))
      const nc = costo + passo
      if (nc < (costi.get(ns) ?? Infinity)) {
        costi.set(ns, nc)
        da.set(ns, { stato: s, passo: { da: h, lato: uscita } })
        aperti.push({ h: v, ingresso: latoOpposto(uscita), costo: nc })
      }
    }
  }
  return null
}
