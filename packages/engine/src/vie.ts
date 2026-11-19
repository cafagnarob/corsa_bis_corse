/*
 * vie.ts
 * Lo stradario della città: ogni strada con il suo nome (GDD: "Nomi": vie e
 * piazze con le liste tipiche italiane).
 *
 * 1. Che cos'è una via: una CATENA di tratti (i pezzi di strada dentro le
 *    tessere, da tracciati.ts) che prosegue da una tessera all'altra.
 *    - Sul lato tra due tessere, il tratto continua sempre in quello della
 *      vicina.
 *    - In un incrocio o in una rotonda la via prosegue nel ramo più dritto
 *      della stessa classe (al massimo 60° di deviazione); gli altri rami
 *      sono vie diverse che lì si incontrano.
 *    - Una via ha una sola classe: dove una urbana diventa una stretta del
 *      centro storico, comincia un'altra via.
 *    - Dove una strada si innesta su un viale, finisce lì.
 *    - L'anello di una rotonda è un luogo a sé, un piazzale; quello di una
 *      rotonda di inversione (un solo ramo) è invece la fine della via.
 * 2. Il tipo di via (e quindi il prefisso): corso (la radiale più lunga),
 *    viale (le altre arterie), viale delle Mura (la circonvallazione), via,
 *    traversa (via breve a fondo cieco), vicolo (stretta breve del centro),
 *    strada provinciale, piazzale.
 * 3. Il nome: dal TEMA del quartiere che la via attraversa di più (villette =
 *    alberi e fiori, palazzoni = Risorgimento e date, nuove costruzioni =
 *    artisti, uffici = scienziati, industrie = mestieri, centro = santi e
 *    botteghe), senza ripetizioni. Solo nomi storici e culturali.
 *
 * Restituisce anche, per ogni via, le vie collegate (che la incrociano o vi
 * sboccano): serviranno a mostrare i nomi attorno alla via selezionata.
 * Flusso casuale proprio ('vie'): non cambia niente del resto della città.
 */

import { flusso, type Casuale } from "./casuale"
import {
  chiave,
  LATI,
  latoOpposto,
  vicina,
  type Hex,
  type Lato,
} from "./esagoni"
import type { Carattere, CittaPopolata } from "./popola"
import type { ClasseStrada, Livello, ReteStradale } from "./strade"
import { puntoLato, tracciatoTessera, type Tratto } from "./tracciati"

export type TipoVia =
  | "corso"
  | "viale"
  | "circonvallazione"
  | "via"
  | "traversa"
  | "vicolo"
  | "provinciale"
  | "piazzale"

/** Un pezzo di via: il tratto numero `tratto` del tracciato della tessera. */
export type PezzoVia = { readonly tessera: Hex; readonly tratto: number }

export type Via = {
  readonly id: number
  readonly nome: string
  readonly tipo: TipoVia
  readonly classe: ClasseStrada
  readonly pezzi: readonly PezzoVia[] // in ordine lungo la via
}

export type Stradario = {
  readonly vie: readonly Via[]
  /** Via di ogni tratto: chiave "q,r#indice del tratto". */
  readonly viaDi: ReadonlyMap<string, number>
  /** Vie che si incontrano con ciascuna via (incroci, innesti, rotonde). */
  readonly collegate: ReadonlyMap<number, readonly number[]>
}

// ---------------------------------------------------------------------
// Nomi
// ---------------------------------------------------------------------

type Tema =
  | "fiori"
  | "risorgimento"
  | "artisti"
  | "scienziati"
  | "mestieri"
  | "centro"
  | "citta"

const TEMA_PER_CARATTERE: Record<Carattere, Tema> = {
  villette: "fiori",
  popolare: "risorgimento",
  nuovo: "artisti",
  misto: "scienziati",
  industriale: "mestieri",
  centro: "centro",
}

/** La parte del nome dopo il prefisso ("Via ..."). */
const NOMI: Record<Tema | "arterie" | "corsi" | "piazzali", readonly string[]> =
  {
    fiori: [
      "delle Magnolie",
      "dei Glicini",
      "dei Tigli",
      "dei Platani",
      "degli Oleandri",
      "delle Mimose",
      "dei Gelsomini",
      "dei Ciliegi",
      "degli Ulivi",
      "dei Pini",
      "delle Querce",
      "dei Castagni",
      "dei Lillà",
      "delle Camelie",
      "delle Ortensie",
      "delle Viole",
      "delle Rose",
      "dei Gerani",
      "delle Acacie",
      "delle Betulle",
    ],
    risorgimento: [
      "Mazzini",
      "Garibaldi",
      "Cavour",
      "Cairoli",
      "Manin",
      "Pisacane",
      "Nino Bixio",
      "Goffredo Mameli",
      "XX Settembre",
      "XXV Aprile",
      "IV Novembre",
      "II Giugno",
      "Silvio Pellico",
      "Ciro Menotti",
      "Fratelli Bandiera",
      "Federico Confalonieri",
      "Anita Garibaldi",
      "Carlo Cattaneo",
    ],
    artisti: [
      "Puccini",
      "Verdi",
      "Rossini",
      "Bellini",
      "Donizetti",
      "Vivaldi",
      "Modigliani",
      "Caravaggio",
      "Giotto",
      "Tiziano",
      "Canova",
      "Raffaello",
      "Leopardi",
      "Manzoni",
      "Pascoli",
      "Carducci",
      "Boccaccio",
      "Petrarca",
    ],
    scienziati: [
      "Galilei",
      "Volta",
      "Marconi",
      "Fermi",
      "Meucci",
      "Avogadro",
      "Torricelli",
      "Spallanzani",
      "Malpighi",
      "Pacinotti",
      "Golgi",
      "Fibonacci",
      "Cardano",
      "Lagrange",
      "Archimede",
      "Maria Montessori",
    ],
    mestieri: [
      "dell'Artigianato",
      "dell'Industria",
      "del Lavoro",
      "dei Fabbri",
      "dei Tessitori",
      "dei Falegnami",
      "dei Vetrai",
      "dei Ceramisti",
      "dei Meccanici",
      "dei Fornaciai",
      "del Commercio",
      "dell'Energia",
      "delle Officine",
      "dei Cantieri",
      "dei Tipografi",
    ],
    centro: [
      "San Rocco",
      "Sant'Agata",
      "San Michele",
      "Santa Maria",
      "San Giorgio",
      "San Francesco",
      "dei Mercanti",
      "del Forno",
      "dei Calzolai",
      "dei Sarti",
      "degli Orefici",
      "della Loggia",
      "del Duomo",
      "delle Beccherie",
      "dei Cappellai",
      "del Pozzo",
    ],
    citta: [
      "Milano",
      "Napoli",
      "Torino",
      "Firenze",
      "Venezia",
      "Genova",
      "Bologna",
      "Bari",
      "Palermo",
      "Trieste",
      "Ancona",
      "Perugia",
      "Pescara",
      "Lecce",
      "Verona",
      "Padova",
      "Trento",
      "Aosta",
      "Cagliari",
      "Sassari",
      "Udine",
      "Parma",
      "Modena",
      "Ravenna",
      "Rimini",
      "Siena",
      "Pisa",
      "Lucca",
      "Livorno",
      "Arezzo",
    ],
    arterie: [
      "Europa",
      "della Repubblica",
      "della Libertà",
      "dell'Unità d'Italia",
      "della Vittoria",
      "dei Mille",
      "della Costituzione",
      "Italia",
      "Roma",
      "della Pace",
    ],
    corsi: [
      "Vittorio Emanuele",
      "Umberto I",
      "Garibaldi",
      "Cavour",
      "Italia",
      "Mazzini",
    ],
    piazzali: [
      "dei Caduti",
      "della Pace",
      "del Mercato",
      "delle Nazioni",
      "dello Sport",
      "dei Martiri",
      "della Concordia",
      "del Lavoro",
      "Europa",
      "della Fontana",
      "dei Giardini",
      "della Libertà",
      "del Popolo",
      "delle Rimembranze",
      "della Repubblica",
      "San Marco",
    ],
  }

const PREFISSO: Record<TipoVia, string> = {
  corso: "Corso",
  viale: "Viale",
  circonvallazione: "Viale",
  via: "Via",
  traversa: "Traversa",
  vicolo: "Vicolo",
  provinciale: "Strada Provinciale",
  piazzale: "Piazzale",
}

/**
 * Distributore di nomi: liste mescolate dal seed, nessuna dedica ripetuta.
 * Il controllo è sulla dedica, non sul nome completo: se c'è già Corso
 * Garibaldi non ci sarà anche Via Garibaldi (in gioco creerebbe confusione).
 */
function creaNomi(rng: Casuale) {
  const mazzi = new Map(
    Object.entries(NOMI).map(([k, l]) => [k, rng.mescola(l)]),
  )
  const usati = new Set<string>() // dediche già usate ("Garibaldi") e nomi fissi
  const prova = (dedica: string) =>
    usati.has(dedica) ? null : (usati.add(dedica), dedica)
  return (tipo: TipoVia, lista: keyof typeof NOMI): string => {
    if (tipo === "circonvallazione")
      return prova("Viale delle Mura") ?? prova("Circonvallazione")!
    if (tipo === "provinciale") {
      for (;;) {
        const n = prova(`Strada Provinciale ${rng.intero(10, 99)}`)
        if (n) return n
      }
    }
    // prima la lista del tema, poi le città, poi un numero
    for (const l of [lista, "citta"] as const) {
      const mazzo = mazzi.get(l)!
      while (mazzo.length > 0) {
        const d = prova(mazzo.pop()!)
        if (d) return `${PREFISSO[tipo]} ${d}`
      }
    }
    for (let i = 2; ; i++) {
      const d = prova(`${NOMI[lista][0]} ${i}`)
      if (d) return `${PREFISSO[tipo]} ${d}`
    }
  }
}

// ---------------------------------------------------------------------
// Catene di tratti
// ---------------------------------------------------------------------

/** Un estremo di un tratto: "q,r#i:0" (inizio) o "q,r#i:1" (fine). */
type Estremo = string
const id = (h: Hex, i: number) => `${chiave(h)}#${i}`

/** Il lato su cui sta un punto del tracciato (null se non sta su un lato). */
function latoDel(p: { x: number; z: number }): Lato | null {
  return (
    LATI.find(
      (l) => Math.hypot(p.x - puntoLato(l).x, p.z - puntoLato(l).z) < 0.01,
    ) ?? null
  )
}

export function generaStradario(
  citta: CittaPopolata,
  rete: ReteStradale,
): Stradario {
  const rng = flusso(citta.seme, "vie")
  const nomi = creaNomi(rng)

  // ---------- i tratti di ogni tessera ----------
  const tracciati = new Map<string, readonly Tratto[]>()
  for (const t of citta.tessere) {
    const k = chiave(t.hex)
    tracciati.set(
      k,
      tracciatoTessera(
        rete.connettori.get(k)!,
        rete.rotonde.get(k) ?? null,
        rete.rettilinei.get(k),
      ).tratti,
    )
  }
  const tessera = new Map(citta.tessere.map((t) => [chiave(t.hex), t]))
  const livelloSul = new Map<string, Livello>() // "q,r:lato" → livello del collegamento
  for (const c of rete.collegamenti) {
    livelloSul.set(`${chiave(c.a)}:${c.latoA}`, c.livello)
    livelloSul.set(`${chiave(c.b)}:${latoOpposto(c.latoA)}`, c.livello)
  }

  // ---------- 1. legami tra estremi ----------
  const legame = new Map<Estremo, Estremo>()
  const lega = (a: Estremo, b: Estremo) => {
    legame.set(a, b)
    legame.set(b, a)
  }
  /** Tratto della tessera h che tocca il lato l, con l'estremo che lo tocca. */
  const sulLato = new Map<string, Estremo>()
  const classeDi = new Map<Estremo, ClasseStrada>()
  for (const [k, tratti] of tracciati) {
    tratti.forEach((t, i) => {
      if (t.inizio === "anello") return
      const [q, r] = k.split(",").map(Number)
      const h = { q, r }
      for (const [e, p] of [
        [0, t.punti[0]],
        [1, t.punti[t.punti.length - 1]],
      ] as const) {
        const l = latoDel(p)
        if (l !== null) {
          sulLato.set(`${k}:${l}`, `${id(h, i)}:${e}`)
          classeDi.set(`${id(h, i)}:${e}`, t.classe)
        }
      }
    })
  }
  // a) da una tessera alla vicina, attraverso il lato (solo tra strade della
  //    stessa classe: dove una urbana diventa una stretta del centro, cambia via)
  for (const [kl, estremo] of sulLato) {
    const [k, l] = kl.split(":")
    const [q, r] = k.split(",").map(Number)
    const lato = Number(l) as Lato
    const altro = sulLato.get(
      `${chiave(vicina({ q, r }, lato))}:${latoOpposto(lato)}`,
    )
    if (
      altro &&
      !legame.has(estremo) &&
      classeDi.get(altro) === classeDi.get(estremo)
    )
      lega(estremo, altro)
  }
  // b) dentro la tessera, negli incroci e nelle rotonde: si prosegue nel ramo più dritto
  const incontri = new Map<string, Estremo[]>() // nodo → estremi che vi arrivano (per le vie collegate)
  for (const [k, tratti] of tracciati) {
    const [q, r] = k.split(",").map(Number)
    const h = { q, r }
    const rami: {
      estremo: Estremo
      tx: number
      tz: number
      classe: ClasseStrada
    }[] = []
    let anello: Estremo | null = null
    tratti.forEach((t, i) => {
      if (t.fine === "incrocio" || t.fine === "rotonda") {
        const p = t.punti[t.punti.length - 1]
        rami.push({
          estremo: `${id(h, i)}:1`,
          tx: p.tx,
          tz: p.tz,
          classe: t.classe,
        })
      }
      if (t.fine === "innesto") {
        // il ramo incontra il viale passante della tessera (il tratto 0)
        incontri.set(`${k}|innesto${i}`, [`${id(h, i)}:1`, `${id(h, 0)}:0`])
      }
      if (t.inizio === "anello") {
        anello = `${id(h, i)}:0`
        incontri.set(`${k}|anello`, [anello])
      }
    })
    // rotonda di inversione (un solo ramo): l'anello è la fine della via, non un piazzale
    if (anello && rami.length === 1) {
      lega(rami[0].estremo, anello)
      incontri.delete(`${k}|anello`)
      continue
    }
    if (rami.length > 0) {
      const nodo = `${k}|nodo`
      incontri.set(nodo, [
        ...(incontri.get(`${k}|anello`) ?? []),
        ...rami.map((r) => r.estremo),
      ])
      // coppie della stessa classe, ordinate dalla più dritta
      const coppie: { a: number; b: number; dritto: number }[] = []
      for (let a = 0; a < rami.length; a++) {
        for (let b = a + 1; b < rami.length; b++) {
          if (rami[a].classe !== rami[b].classe) continue // un viale non diventa una via
          // arrivando con la direzione di a, si prosegue nel verso opposto all'arrivo di b
          const dritto = -(rami[a].tx * rami[b].tx + rami[a].tz * rami[b].tz)
          coppie.push({ a, b, dritto })
        }
      }
      coppie.sort((x, y) => y.dritto - x.dritto)
      const presi = new Set<number>()
      for (const { a, b, dritto } of coppie) {
        if (dritto < 0.49 || presi.has(a) || presi.has(b)) continue // oltre 60° di deviazione: vie diverse
        presi.add(a).add(b)
        lega(rami[a].estremo, rami[b].estremo)
      }
    }
  }

  // ---------- 2. catene: si percorrono i legami da un capo all'altro ----------
  const catene: PezzoVia[][] = []
  const visti = new Set<string>()
  const tuttiTratti = [...tracciati].flatMap(([k, tratti]) =>
    tratti.map((_, i) => `${k}#${i}`),
  )
  const pezzo = (t: string): PezzoVia => {
    const [k, i] = t.split("#")
    const [q, r] = k.split(",").map(Number)
    return { tessera: { q, r }, tratto: Number(i) }
  }
  const percorri = (inizio: string, daEstremo: 0 | 1) => {
    const catena: PezzoVia[] = []
    let t = inizio
    let entrata = daEstremo
    while (!visti.has(t)) {
      visti.add(t)
      catena.push(pezzo(t))
      const uscita = `${t}:${1 - entrata}`
      const prossimo = legame.get(uscita)
      if (!prossimo) break
      const [pt, pe] = prossimo.split(":")
      t = pt
      entrata = Number(pe) as 0 | 1
    }
    catene.push(catena)
  }
  // prima le catene che hanno un capo libero (si parte da lì), poi gli anelli chiusi
  for (const t of tuttiTratti) {
    if (visti.has(t)) continue
    if (!legame.has(`${t}:0`)) percorri(t, 0)
    else if (!legame.has(`${t}:1`)) percorri(t, 1)
  }
  for (const t of tuttiTratti) if (!visti.has(t)) percorri(t, 0)

  // ---------- 3. tipo e nome di ogni via ----------
  const trattoDi = (p: PezzoVia) => tracciati.get(chiave(p.tessera))![p.tratto]
  const lunghezza = (c: PezzoVia[]) => c.length
  const radiali = catene.filter(
    (c) =>
      c.some((p) => trattoDi(p).classe === "viale") && !eCirconvallazione(c),
  )
  const corso =
    radiali.length > 0
      ? radiali.reduce((m, c) => (lunghezza(c) > lunghezza(m) ? c : m))
      : null

  /** Circonvallazione se la maggior parte dei suoi pezzi parte da un lato di circonvallazione. */
  function eCirconvallazione(c: PezzoVia[]): boolean {
    const sullAnello = c.filter((p) => {
      const l = latoDel(trattoDi(p).punti[0])
      return (
        l !== null &&
        livelloSul.get(`${chiave(p.tessera)}:${l}`) === "circonvallazione"
      )
    }).length
    return sullAnello > c.length / 2
  }

  const vie: Via[] = []
  const viaDi = new Map<string, number>()
  catene.forEach((c, i) => {
    const primo = trattoDi(c[0])
    const classe = trattoDi(
      c.find((p) => trattoDi(p).inizio !== "anello") ?? c[0],
    ).classe
    const tessere = c.map((p) => tessera.get(chiave(p.tessera))!)
    const inCampagna =
      tessere.filter((t) => t.tipo === "strada").length > tessere.length / 2
    // a fondo cieco: finisce nel vuoto o in una rotonda di inversione
    const cieca = c.some(
      (p) => trattoDi(p).fine === "cieco" || trattoDi(p).inizio === "anello",
    )
    const tratti = c.filter((p) => trattoDi(p).inizio !== "anello").length

    let tipo: TipoVia
    if (primo.inizio === "anello" && c.length === 1) tipo = "piazzale"
    else if (classe === "viale")
      tipo =
        c === corso
          ? "corso"
          : eCirconvallazione(c)
            ? "circonvallazione"
            : "viale"
    else if (inCampagna) tipo = "provinciale"
    else if (classe === "stretta" && tratti <= 2) tipo = "vicolo"
    else if (cieca && tratti <= 2) tipo = "traversa"
    else tipo = "via"

    // tema: il carattere del quartiere più presente lungo la via
    const conta = new Map<Carattere, number>()
    for (const t of tessere) {
      const q =
        t.quartiere === null
          ? undefined
          : citta.quartieri.find((x) => x.id === t.quartiere)
      if (q) conta.set(q.carattere, (conta.get(q.carattere) ?? 0) + 1)
    }
    const carattere = [...conta].sort((a, b) => b[1] - a[1])[0]?.[0] ?? "misto"
    const lista: keyof typeof NOMI =
      tipo === "corso"
        ? "corsi"
        : tipo === "viale" || tipo === "circonvallazione"
          ? "arterie"
          : tipo === "piazzale"
            ? "piazzali"
            : TEMA_PER_CARATTERE[carattere]

    vie.push({ id: i, nome: nomi(tipo, lista), tipo, classe, pezzi: c })
    for (const p of c) viaDi.set(`${chiave(p.tessera)}#${p.tratto}`, i)
  })

  // ---------- 4. vie collegate ----------
  const collegate = new Map<number, Set<number>>(
    vie.map((v) => [v.id, new Set()]),
  )
  for (const estremi of incontri.values()) {
    const ids = [...new Set(estremi.map((e) => viaDi.get(e.split(":")[0])!))]
    for (const a of ids)
      for (const b of ids) if (a !== b) collegate.get(a)!.add(b)
  }

  return {
    vie,
    viaDi,
    collegate: new Map(
      [...collegate].map(([k, s]) => [k, [...s].sort((a, b) => a - b)]),
    ),
  }
}
