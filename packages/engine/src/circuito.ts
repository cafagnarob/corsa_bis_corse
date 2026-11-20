/*
 * circuito.ts
 * Genera dal seme un circuito chiuso sulle strade della città: un giro che
 * parte da un viale e torna al traguardo senza passare due volte sulla
 * stessa strada. Stesso seme, stesso circuito.
 *
 * L'idea: un circuito è il BORDO di un gruppo di isolati vicini.
 * Un isolato è un pezzo di città chiuso da strade tutto attorno (il giro
 * più corto attorno a un punto). Se si mettono insieme due isolati che
 * confinano, la strada in comune sparisce e resta il giro attorno a tutti
 * e due, più lungo. Aggiungendo isolati uno alla volta il giro cresce,
 * finché ha la lunghezza voluta.
 *
 * I passi:
 * 1. ISOLATI (isolati): per ogni angolo delle tessere si cerca il giro più
 *    corto che lo circonda (giroAttorno). Gli angoli già dentro un isolato
 *    trovato si saltano.
 * 2. CRESCITA (generaCircuito): si parte da un isolato scelto dal seme e si
 *    aggiungono isolati confinanti. Il bordo del gruppo è fatto dalle
 *    strade che stanno in UN solo isolato del gruppo (quelle in comune a
 *    due sono "dentro"). Si accetta un isolato solo se il bordo resta un
 *    giro unico, che non tocca due volte lo stesso incrocio.
 * 3. GIRO (giroDelBordo): il bordo diventa una sequenza di archi del grafo,
 *    tutti nello stesso senso, rispettando i sensi unici (gli anelli delle
 *    rotonde si girano solo in senso antiorario).
 * 4. Quando la lunghezza sta tra il minimo e il massimo, il traguardo va
 *    sul viale più lungo del giro e il circuito è pronto.
 *
 * Come si capisce se un giro "circonda" un punto: si traccia una semiretta
 * dal punto verso l'esterno e si contano gli attraversamenti lungo il
 * giro, +1 in senso antiorario e −1 in senso orario. Somma diversa da zero
 * = il punto è dentro (attraversa, giriLungo).
 *
 * Unità: le lunghezze delle opzioni sono in metri reali (scala dei mezzi),
 * quelle del risultato in unità di gioco come il grafo (scala.ts).
 */

import { flusso } from "./casuale"
import { RAGGIO_TESSERA, centroTessera, chiave, type Hex } from "./esagoni"
import {
  chiaveTratto,
  puntoSulTratto,
  type Arco,
  type GrafoStradale,
  type PosizioneRete,
  type TipoMezzo,
} from "./grafo"
import type { PezzoPercorso } from "./percorso"
import { metriInUnita } from "./scala"

/* ------------------------------------------------------------------------
 * Opzioni e risultato
 * --------------------------------------------------------------------- */

export type OpzioniCircuito = {
  /** Lunghezza minima di un giro, in metri reali. */
  readonly lunghezzaMinima: number
  /** Lunghezza massima di un giro, in metri reali. */
  readonly lunghezzaMassima: number
  /** Da quanti isolati diversi provare a far crescere il circuito. */
  readonly tentativi: number
  /** Su quali strade si corre: "bus" = viali e urbane, niente strade strette. */
  readonly mezzo: TipoMezzo
}

/**
 * Valori predefiniti. Un giro di 1,2-2,5 km dura circa 1-2 minuti a 90 km/h
 * di media: con 3 giri la gara sta nei 3-5 minuti del GDD.
 */
export const OPZIONI_CIRCUITO: OpzioniCircuito = {
  lunghezzaMinima: 1200,
  lunghezzaMassima: 2500,
  tentativi: 40,
  mezzo: "bus",
}

export type Circuito = {
  /** Partenza e traguardo: a metà dell'arco di partenza, nel verso di marcia. */
  readonly traguardo: PosizioneRete
  /** Tutto il giro, dal traguardo al traguardo, come pezzi di tratto. */
  readonly pezzi: readonly PezzoPercorso[]
  /** Gli archi del grafo percorsi, in ordine, a partire dall'arco del traguardo. */
  readonly archi: readonly number[]
  /** Lunghezza del giro, in unità di gioco. */
  readonly lunghezza: number
  /** Dislivello in salita di un giro, sommato. */
  readonly salita: number
  /** Le tessere attraversate, in ordine, ognuna una volta sola. */
  readonly tessere: readonly Hex[]
}

/* ------------------------------------------------------------------------
 * Geometria: attraversamenti di una semiretta
 * --------------------------------------------------------------------- */

type Punto = { readonly x: number; readonly z: number }

/**
 * Di quanto cambia il contatore dei giri percorrendo il segmento da p a q:
 * +1 se attraversa la semiretta (dal punto c in direzione d) in senso
 * antiorario visto dall'alto, −1 in senso orario, 0 se non la attraversa.
 *
 * In Three.js visto dall'alto l'asse z punta verso il basso dello schermo:
 * per lavorare con l'antiorario "da libro" si usa y = −z.
 */
export function attraversa(c: Punto, d: Punto, p: Punto, q: Punto): -1 | 0 | 1 {
  const px = p.x - c.x
  const py = -(p.z - c.z)
  const qx = q.x - c.x
  const qy = -(q.z - c.z)
  const dx = d.x
  const dy = -d.z
  // Da che parte della retta (c, d) stanno p e q: + a sinistra, − a destra
  const lp = dx * py - dy * px
  const lq = dx * qy - dy * qx
  if ((lp < 0 && lq < 0) || (lp >= 0 && lq >= 0)) return 0
  // Il punto di incrocio deve stare sulla semiretta, non dalla parte opposta
  const t = lp / (lp - lq)
  const ix = px + (qx - px) * t
  const iy = py + (qy - py) * t
  if (ix * dx + iy * dy <= 0) return 0
  return lp < 0 ? 1 : -1 // da destra a sinistra della semiretta = antiorario
}

/** Attraversamenti della semiretta lungo una linea spezzata, sommati. */
function giriLungo(linea: readonly Punto[], c: Punto, d: Punto): number {
  let giri = 0
  for (let i = 1; i < linea.length; i++)
    giri += attraversa(c, d, linea[i - 1], linea[i])
  return giri
}

/**
 * La distanza dal punto c del primo attraversamento della semiretta lungo
 * una linea spezzata (Infinity se non la attraversa).
 */
function primoAttraversamento(
  linea: readonly Punto[],
  c: Punto,
  d: Punto,
): number {
  let minima = Infinity
  for (let i = 1; i < linea.length; i++) {
    if (attraversa(c, d, linea[i - 1], linea[i]) === 0) continue
    // Punto medio del segmento proiettato sulla semiretta: basta per ordinare
    const mx = (linea[i - 1].x + linea[i].x) / 2 - c.x
    const mz = (linea[i - 1].z + linea[i].z) / 2 - c.z
    minima = Math.min(minima, mx * d.x + mz * d.z)
  }
  return minima
}

/** Ogni quante unità si prende un punto lungo un arco. */
const PASSO_LINEA = 10

/**
 * La linea vera di ogni arco (indice = id dell'arco), un punto ogni
 * PASSO_LINEA unità. Per contare gli attraversamenti non basta il segmento
 * dritto tra i due nodi, perché molti archi curvano: l'anello di una
 * rotonda è fatto di due archi tra gli stessi due nodi, e con la corda
 * dritta sembrerebbe di andare e tornare invece di girare attorno all'isola.
 */
function lineeArchi(grafo: GrafoStradale): Punto[][] {
  return grafo.archi.map((e) => {
    const t = grafo.tratti.get(chiaveTratto(e.tessera, e.tratto))
    if (!t) return [grafo.nodi[e.da], grafo.nodi[e.a]]
    const punti: Punto[] = []
    for (const p of e.pezzi) {
      const n = Math.max(1, Math.ceil(Math.abs(p.a - p.da) / PASSO_LINEA))
      for (let i = 0; i <= n; i++) {
        const q = puntoSulTratto(t, p.da + ((p.a - p.da) * i) / n)
        punti.push({ x: q.x, z: q.z })
      }
    }
    return punti
  })
}

/* ------------------------------------------------------------------------
 * Strade come "lati" senza verso
 * --------------------------------------------------------------------- */

/** Il verso in cui un arco percorre il suo tratto (1 = come il tratto). */
const versoArco = (e: Arco) => (e.pezzi[0].a >= e.pezzi[0].da ? 1 : -1)

/**
 * La strada di un arco senza il verso: stesso tratto e stesso pezzo, in
 * qualunque senso lo si percorra. L'andata e il ritorno su una strada
 * hanno lo stesso lato; le due metà dell'anello di una rotonda no.
 */
function lato(e: Arco): string {
  const da = Math.min(...e.pezzi.map((p) => Math.min(p.da, p.a)))
  const a = Math.max(...e.pezzi.map((p) => Math.max(p.da, p.a)))
  return `${chiaveTratto(e.tessera, e.tratto)}|${da.toFixed(1)}-${a.toFixed(1)}`
}

/** f è l'inversione a U di e: lo stesso pezzo di strada, ripercorso all'indietro. */
const eInversione = (e: Arco, f: Arco) =>
  f.da === e.a &&
  f.a === e.da &&
  lato(f) === lato(e) &&
  versoArco(f) !== versoArco(e)

/* ------------------------------------------------------------------------
 * Il giro più corto attorno a un punto (Dijkstra su archi e giri)
 * --------------------------------------------------------------------- */

/** Coda con priorità (heap binario): estrae sempre la distanza più piccola. */
class Coda {
  #voci: { d: number; s: number }[] = []
  get vuota() {
    return this.#voci.length === 0
  }
  metti(d: number, s: number) {
    const v = this.#voci
    v.push({ d, s })
    for (let i = v.length - 1; i > 0; ) {
      const p = (i - 1) >> 1
      if (v[p].d <= v[i].d) break
      ;[v[p], v[i]] = [v[i], v[p]]
      i = p
    }
  }
  togli(): { d: number; s: number } {
    const v = this.#voci
    const cima = v[0]
    const ultima = v.pop()!
    if (v.length > 0) {
      v[0] = ultima
      for (let i = 0; ; ) {
        const a = 2 * i + 1
        const b = a + 1
        let m = i
        if (a < v.length && v[a].d < v[m].d) m = a
        if (b < v.length && v[b].d < v[m].d) m = b
        if (m === i) break
        ;[v[m], v[i]] = [v[i], v[m]]
        i = m
      }
    }
    return cima
  }
}

/** Oltre ±2 giri la ricerca non serve: il giro buono ne fa uno solo. */
const GIRI_MASSIMI = 2
const STATI_PER_ARCO = 2 * GIRI_MASSIMI + 1

/**
 * Il giro più corto che parte dall'arco `inizio` e ci torna dopo aver fatto
 * un giro attorno a `centro` (in un senso o nell'altro), senza inversioni a
 * U e usando solo gli archi `ammesso`. Restituisce gli archi in ordine (il
 * primo è `inizio`) o null. Lo stato della ricerca è (arco, giri fatti):
 * come in percorso.ts si avanza di arco in arco per vietare le inversioni.
 */
function giroAttorno(
  grafo: GrafoStradale,
  inizio: Arco,
  centro: Punto,
  semiretta: Punto,
  ammesso: (e: Arco) => boolean,
  linee: readonly (readonly Punto[])[],
): Arco[] | null {
  const giriArco = (e: Arco) => giriLungo(linee[e.id], centro, semiretta)
  const stato = (arco: number, giri: number) =>
    arco * STATI_PER_ARCO + (giri + GIRI_MASSIMI)
  const arcoDi = (s: number) => Math.floor(s / STATI_PER_ARCO)
  const giriDi = (s: number) => (s % STATI_PER_ARCO) - GIRI_MASSIMI

  const distanza = new Map<number, number>()
  const precedente = new Map<number, number>()
  const coda = new Coda()
  const s0 = stato(inizio.id, giriArco(inizio))
  distanza.set(s0, inizio.lunghezza)
  coda.metti(inizio.lunghezza, s0)

  while (!coda.vuota) {
    const { d, s } = coda.togli()
    if (d > (distanza.get(s) ?? Infinity)) continue
    const e = grafo.archi[arcoDi(s)]
    const giri = giriDi(s)

    for (const id of grafo.uscenti[e.a]) {
      const f = grafo.archi[id]
      if (!ammesso(f) || eInversione(e, f)) continue

      // Arrivo: di nuovo sull'arco di partenza, con un giro fatto
      if (f.id === inizio.id) {
        if (Math.abs(giri) !== 1) continue
        const archi: Arco[] = []
        for (
          let k: number | undefined = s;
          k !== undefined;
          k = precedente.get(k)
        )
          archi.push(grafo.archi[arcoDi(k)])
        return archi.reverse()
      }

      const g = giri + giriArco(f)
      if (Math.abs(g) > GIRI_MASSIMI) continue
      const t = stato(f.id, g)
      const nd = d + f.lunghezza
      if (nd < (distanza.get(t) ?? Infinity)) {
        distanza.set(t, nd)
        precedente.set(t, s)
        coda.metti(nd, t)
      }
    }
  }
  return null
}

/* ------------------------------------------------------------------------
 * 1. Isolati
 * --------------------------------------------------------------------- */

export type Isolato = {
  /** Le strade attorno all'isolato (lati senza verso). */
  readonly lati: ReadonlySet<string>
}

/** Quante strade tra le più vicine provare per trovare il bordo di un isolato. */
const STRADE_DA_PROVARE = 3

/** Una direzione qualunque per le semirette: basta che sia sempre la stessa. */
const DIREZIONE = { x: Math.cos(0.3), z: -Math.sin(0.3) }

/**
 * Gli isolati della città: per ogni angolo delle tessere, il giro più
 * corto che lo circonda. Gli angoli dentro un isolato già trovato si
 * saltano, così ogni isolato si cerca una volta sola.
 */
export function isolati(
  grafo: GrafoStradale,
  mezzo: TipoMezzo,
  linee: readonly (readonly Punto[])[] = lineeArchi(grafo),
): Isolato[] {
  const ammesso = (e: Arco) => e.ammessi.includes(mezzo)

  // Gli angoli delle tessere che hanno strade, una volta sola ciascuno
  const angoli = new Map<string, Punto>()
  for (const t of grafo.tratti.values()) {
    const c = centroTessera(t.tessera)
    for (let k = 0; k < 6; k++) {
      const a = ((30 + 60 * k) * Math.PI) / 180
      const p = {
        x: c.x + RAGGIO_TESSERA * Math.cos(a),
        z: c.z - RAGGIO_TESSERA * Math.sin(a),
      }
      angoli.set(`${Math.round(p.x)},${Math.round(p.z)}`, p)
    }
  }

  const trovati: { lati: Set<string>; archi: Arco[] }[] = []
  for (const p of angoli.values()) {
    // Già dentro un isolato trovato?
    const dentro = trovati.some(
      (i) =>
        i.archi.reduce(
          (g, e) => g + giriLungo(linee[e.id], p, DIREZIONE),
          0,
        ) !== 0,
    )
    if (dentro) continue

    // La prima strada che la semiretta incontra uscendo da p sta sul bordo
    // dell'isolato di p: si cerca il giro partendo dalle strade più vicine
    // (se la più vicina è un vicolo cieco il giro non ci passa: si prova la
    // successiva, fino a STRADE_DA_PROVARE strade)
    const vicine = grafo.archi
      .filter(ammesso)
      .map((e) => ({ e, d: primoAttraversamento(linee[e.id], p, DIREZIONE) }))
      .filter((x) => x.d < Infinity)
      .sort((a, b) => a.d - b.d)
      .slice(0, 2 * STRADE_DA_PROVARE) // due archi per strada: andata e ritorno
    let migliore: Arco[] | null = null
    let corto = Infinity
    for (const { e } of vicine) {
      const g = giroAttorno(grafo, e, p, DIREZIONE, ammesso, linee)
      const l = g ? lunghezzaDi(g) : Infinity
      if (g && l < corto) {
        migliore = g
        corto = l
      }
    }
    if (!migliore) continue
    const lati = new Set(migliore.map(lato))
    if (lati.size !== migliore.length) continue // ripassa su una strada: non è un isolato
    trovati.push({ lati, archi: migliore })
  }
  return trovati.map((i) => ({ lati: i.lati }))
}

const lunghezzaDi = (archi: readonly Arco[]) =>
  archi.reduce((s, e) => s + e.lunghezza, 0)

/* ------------------------------------------------------------------------
 * 3. Dal bordo al giro
 * --------------------------------------------------------------------- */

/**
 * Il bordo (un insieme di lati) come giro di archi tutti nello stesso
 * senso, oppure null se il bordo non è un giro unico: ogni incrocio del
 * bordo deve toccare esattamente due lati, e tutti i lati devono essere
 * collegati. Si prova un senso e, se un senso unico lo impedisce, l'altro.
 */
function giroDelBordo(
  bordo: ReadonlySet<string>,
  archiDelLato: ReadonlyMap<string, readonly Arco[]>,
  ammesso: (e: Arco) => boolean,
): Arco[] | null {
  // I due estremi (nodi) di ogni lato, e i lati che toccano ogni nodo
  const estremi = new Map<string, [number, number]>()
  const latiDelNodo = new Map<number, string[]>()
  for (const l of bordo) {
    const e = archiDelLato.get(l)?.[0]
    if (!e) return null
    estremi.set(l, [e.da, e.a])
    for (const n of [e.da, e.a])
      latiDelNodo.set(n, [...(latiDelNodo.get(n) ?? []), l])
  }
  for (const lati of latiDelNodo.values()) if (lati.length !== 2) return null

  const primo = bordo.values().next().value as string
  for (const verso of [0, 1]) {
    const archi: Arco[] = []
    let l = primo
    let nodo = estremi.get(l)![verso] // il nodo da cui si parte
    let ok = true
    do {
      const [u, v] = estremi.get(l)!
      const arrivo = nodo === u ? v : u // il nodo a cui si arriva
      const arco = archiDelLato
        .get(l)!
        .find((e) => e.da === nodo && e.a === arrivo && ammesso(e))
      if (!arco) {
        ok = false
        break
      }
      archi.push(arco)
      nodo = arrivo
      l = latiDelNodo.get(nodo)!.find((x) => x !== l)!
    } while (l !== primo)
    // Un giro unico passa per tutti i lati del bordo
    if (ok && archi.length === bordo.size) return archi
  }
  return null
}

/* ------------------------------------------------------------------------
 * 2 e 4. Generatore
 * --------------------------------------------------------------------- */

/**
 * Il circuito della città per questo seme, oppure null se nessun gruppo di
 * isolati dà un giro della lunghezza voluta.
 */
export function generaCircuito(
  grafo: GrafoStradale,
  seme: string,
  opzioni: OpzioniCircuito = OPZIONI_CIRCUITO,
): Circuito | null {
  const ammesso = (e: Arco) => e.ammessi.includes(opzioni.mezzo)
  const archiDelLato = new Map<string, Arco[]>()
  for (const e of grafo.archi)
    archiDelLato.set(lato(e), [...(archiDelLato.get(lato(e)) ?? []), e])

  const tutti = isolati(grafo, opzioni.mezzo)
  if (tutti.length === 0) return null

  const caso = flusso(seme, "circuito")
  const minimo = metriInUnita(opzioni.lunghezzaMinima)
  const massimo = metriInUnita(opzioni.lunghezzaMassima)

  for (const primo of caso.mescola(tutti).slice(0, opzioni.tentativi)) {
    // Lunghezza voluta per questo tentativo: così i circuiti non sono tutti
    // lunghi quanto il minimo
    const voluta = minimo + caso.decimale() * (massimo - minimo)

    // Il gruppo parte da un isolato; il bordo è l'insieme dei suoi lati
    const gruppo = new Set<Isolato>([primo])
    let bordo = new Set(primo.lati)
    let giro = giroDelBordo(bordo, archiDelLato, ammesso)

    while (giro) {
      const lunghezza = lunghezzaDi(giro)
      if (lunghezza > massimo) break
      if (lunghezza >= voluta) return costruisci(conTraguardo(giro), lunghezza)

      // Isolati confinanti: hanno almeno una strada sul bordo
      const vicini = caso.mescola(
        tutti.filter(
          (i) => !gruppo.has(i) && [...i.lati].some((l) => bordo.has(l)),
        ),
      )
      let cresciuto = false
      for (const v of vicini) {
        // Bordo nuovo: le strade in comune spariscono, le altre si aggiungono
        const nuovo = new Set(bordo)
        for (const l of v.lati) {
          if (nuovo.has(l)) nuovo.delete(l)
          else nuovo.add(l)
        }
        const g = giroDelBordo(nuovo, archiDelLato, ammesso)
        if (!g) continue // il bordo non sarebbe più un giro unico
        gruppo.add(v)
        bordo = nuovo
        giro = g
        cresciuto = true
        break
      }
      if (!cresciuto) break
    }
    // Non è cresciuto fino alla lunghezza voluta, ma il minimo c'è: va bene
    if (giro && lunghezzaDi(giro) >= minimo && lunghezzaDi(giro) <= massimo)
      return costruisci(conTraguardo(giro), lunghezzaDi(giro))
  }
  return null
}

/**
 * Lo stesso giro, fatto partire dall'arco migliore per il traguardo: il
 * viale più lungo (se non ci sono viali, la strada più lunga).
 */
function conTraguardo(giro: readonly Arco[]): Arco[] {
  const viale = (x: Arco) => (x.classe === "viale" ? 1 : 0)
  let i = 0
  giro.forEach((e, k) => {
    const m = giro[i]
    if (
      viale(e) > viale(m) ||
      (viale(e) === viale(m) && e.lunghezza > m.lunghezza)
    )
      i = k
  })
  return [...giro.slice(i), ...giro.slice(0, i)]
}

/**
 * Dal giro come archi al Circuito: il traguardo a metà del primo arco, i
 * pezzi di tratto dal traguardo al traguardo, le tessere attraversate.
 */
function costruisci(archi: readonly Arco[], lunghezza: number): Circuito {
  const primo = archi[0]
  const pezziDi = (e: Arco): PezzoPercorso[] =>
    e.pezzi.map((p) => ({
      tessera: e.tessera,
      tratto: e.tratto,
      da: p.da,
      a: p.a,
    }))

  // Metà del primo arco: si divide il suo primo pezzo (di solito è l'unico)
  const p0 = primo.pezzi[0]
  const meta = (p0.da + p0.a) / 2
  const sulPrimo = { tessera: primo.tessera, tratto: primo.tratto }
  const pezzi: PezzoPercorso[] = [
    { ...sulPrimo, da: meta, a: p0.a },
    ...pezziDi(primo).slice(1),
    ...archi.slice(1).flatMap(pezziDi),
    { ...sulPrimo, da: p0.da, a: meta },
  ]

  const tessere: Hex[] = []
  const viste = new Set<string>()
  for (const p of pezzi) {
    const k = chiave(p.tessera)
    if (!viste.has(k)) {
      viste.add(k)
      tessere.push(p.tessera)
    }
  }

  return {
    traguardo: { ...sulPrimo, s: meta, verso: versoArco(primo) },
    pezzi,
    archi: archi.map((e) => e.id),
    lunghezza,
    salita: archi.reduce((s, e) => s + Math.max(0, e.salita), 0),
    tessere,
  }
}
