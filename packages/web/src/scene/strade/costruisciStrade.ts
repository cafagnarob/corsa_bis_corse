/*
 * costruisciStrade.ts
 * Il "motore" che disegna le strade di una tessera a partire dal tracciato del
 * motore di gioco: carreggiata, marciapiedi e segnaletica orizzontale che
 * seguono l'andamento della strada (rettilinei, curve, innesti, incroci).
 *
 * Restituisce tre geometrie (asfalto, marciapiedi, segni), una per materiale.
 * Dipendono solo dai connettori della tessera: chi le usa può metterle in
 * cache e riusarle per tutte le tessere uguali.
 *
 * Regole principali:
 * - ogni elemento è un "nastro" che segue la mezzeria a una certa distanza
 *   laterale (offset; + = destra nel senso del tracciato);
 * - marciapiedi e linee si interrompono dove entrano nella carreggiata di
 *   un'altra strada o nell'incrocio;
 * - dove una strada arriva a un incrocio, si innesta su un viale o entra in
 *   una rotonda: strisce pedonali e, entrando in rotonda o se una urbana
 *   sbocca su un viale, i denti di squalo (dare precedenza) sulla corsia che
 *   arriva;
 *  * - rotonda: anello con linee di margine, marciapiede esterno e cordolo
 *   dell'isola centrale (l'isola la decora il componente, secondo il quartiere);
 * - rampe: dove sul lato c'è una rampa verso una tessera più alta, la strada
 *   si ferma dove comincia la rampa (tagli[lato] unità prima del lato); la
 *   rampa stessa è un pezzo di tessere.glb (rampe.ts).
 */

import {
  puntoLato,
  type Lato,
  type TracciatoTessera,
  type Tratto,
} from "@corsa-bis/engine"
import { BufferAttribute, BufferGeometry } from "three"
import { PROFILO, QUOTE, SEGNI } from "./profili"

type P = { x: number; z: number; tx: number; tz: number }
type V3 = [number, number, number]

/**
 * Raccoglie triangoli (tutti rivolti verso l'alto) e li trasforma in una
 * geometria. Ogni triangolo ricorda anche un'etichetta: il numero del tratto
 * a cui appartiene (-1 = nessuno), per sapere quale via colpisce il mouse.
 */
class Accumulo {
  private pos: number[] = []
  readonly etichette: number[] = []
  etichetta = -1 // si imposta prima di disegnare un tratto

  triangolo(a: V3, b: V3, c: V3) {
    // componente verticale di (b - a) × (c - a): se è negativa il triangolo
    // guarda in basso, e si inverte l'ordine dei vertici
    const ny = (b[2] - a[2]) * (c[0] - a[0]) - (b[0] - a[0]) * (c[2] - a[2])
    if (ny >= 0) this.pos.push(...a, ...b, ...c)
    else this.pos.push(...a, ...c, ...b)
    this.etichette.push(this.etichetta)
  }

  quad(a: V3, b: V3, c: V3, d: V3) {
    this.triangolo(a, b, c)
    this.triangolo(a, c, d)
  }

  geometria(): BufferGeometry {
    const g = new BufferGeometry()
    g.setAttribute(
      "position",
      new BufferAttribute(new Float32Array(this.pos), 3),
    )
    const normali = new Float32Array(this.pos.length)
    for (let i = 1; i < normali.length; i += 3) normali[i] = 1 // tutto piatto, rivolto in alto
    g.setAttribute("normal", new BufferAttribute(normali, 3))
    return g
  }
}

/** Punto spostato lateralmente di `d` (verso destra rispetto alla direzione). */
const lato = (p: P, d: number) => ({ x: p.x - p.tz * d, z: p.z + p.tx * d })

/** Nastro tra le distanze laterali d0 e d1 lungo i punti dati, alla quota y. */
function nastro(
  acc: Accumulo,
  punti: readonly P[],
  d0: number,
  d1: number,
  y: number,
) {
  for (let i = 1; i < punti.length; i++) {
    const a0 = lato(punti[i - 1], d0)
    const a1 = lato(punti[i - 1], d1)
    const b0 = lato(punti[i], d0)
    const b1 = lato(punti[i], d1)
    acc.quad([a0.x, y, a0.z], [a1.x, y, a1.z], [b1.x, y, b1.z], [b0.x, y, b0.z])
  }
}

/** Disco (poligono a 24 lati) per incroci e fondi ciechi. */
function disco(acc: Accumulo, x: number, z: number, raggio: number, y: number) {
  const n = 24
  for (let i = 0; i < n; i++) {
    const a = (i / n) * Math.PI * 2
    const b = ((i + 1) / n) * Math.PI * 2
    acc.triangolo(
      [x, y, z],
      [x + raggio * Math.cos(a), y, z + raggio * Math.sin(a)],
      [x + raggio * Math.cos(b), y, z + raggio * Math.sin(b)],
    )
  }
}

/** Distanze progressive dall'inizio del tratto (ascissa curvilinea). */
function ascisse(punti: readonly P[]): number[] {
  const s = [0]
  for (let i = 1; i < punti.length; i++)
    s.push(
      s[i - 1] +
        Math.hypot(punti[i].x - punti[i - 1].x, punti[i].z - punti[i - 1].z),
    )
  return s
}

/** Distanza di un punto da una mezzeria (i punti sono fitti: basta il più vicino). */
function distanzaDa(q: { x: number; z: number }, punti: readonly P[]): number {
  let min = Infinity
  for (const p of punti) min = Math.min(min, Math.hypot(q.x - p.x, q.z - p.z))
  return min
}

/** Spezza una sequenza di punti nei tratti consecutivi in cui `tieni` è vero. */
function spezza(punti: readonly P[], tieni: (i: number) => boolean): P[][] {
  const pezzi: P[][] = []
  let corrente: P[] = []
  punti.forEach((p, i) => {
    if (tieni(i)) corrente.push(p)
    else {
      if (corrente.length >= 2) pezzi.push(corrente)
      corrente = []
    }
  })
  if (corrente.length >= 2) pezzi.push(corrente)
  return pezzi
}

/** Punti del tratto tra le ascisse s0 e s1 (misurate dall'inizio), con gli estremi interpolati. */
function porzione(
  punti: readonly P[],
  s: readonly number[],
  s0: number,
  s1: number,
): P[] {
  const interpola = (sv: number): P => {
    let i = 1
    while (i < s.length - 1 && s[i] < sv) i++
    const t = (sv - s[i - 1]) / (s[i] - s[i - 1] || 1)
    const a = punti[i - 1]
    const b = punti[i]
    return {
      x: a.x + (b.x - a.x) * t,
      z: a.z + (b.z - a.z) * t,
      tx: a.tx,
      tz: a.tz,
    }
  }
  const dentro = punti.filter((_, i) => s[i] > s0 && s[i] < s1)
  return [interpola(s0), ...dentro, interpola(s1)]
}

/** Nessun taglio: nessuna rampa sui sei lati. */
export const SENZA_TAGLI: readonly number[] = [0, 0, 0, 0, 0, 0]

/** Il lato su cui sta un punto (il punto medio di un lato), oppure null. */
function latoDelPunto(p: { x: number; z: number }): Lato | null {
  for (const l of [0, 1, 2, 3, 4, 5] as const) {
    const q = puntoLato(l)
    if (Math.hypot(p.x - q.x, p.z - q.z) < 0.5) return l
  }
  return null
}

/**
 * Il tratto accorciato alle estremità che toccano un lato con rampa, oppure
 * null se non ne resta niente (rampa più lunga del tratto).
 */
function accorcia(t: Tratto, tagli: readonly number[]): Tratto | null {
  if (t.inizio === "anello") return t
  const latoFine =
    t.fine === "lato" ? latoDelPunto(t.punti[t.punti.length - 1]) : null
  const daInizio = t.inizio === "lato" && t.lato !== null ? tagli[t.lato] : 0
  const daFine = latoFine !== null ? tagli[latoFine] : 0
  if (daInizio === 0 && daFine === 0) return t
  const s = ascisse(t.punti)
  const L = s[s.length - 1]
  if (L - daInizio - daFine < 1) return null
  return { ...t, punti: porzione(t.punti, s, daInizio, L - daFine) }
}

export type GeometrieStrade = {
  readonly asfalto: BufferGeometry
  readonly marciapiedi: BufferGeometry
  readonly segni: BufferGeometry
  /** Per ogni triangolo dell'asfalto, il numero del tratto del tracciato (-1 = incrocio). */
  readonly trattoPerTriangolo: readonly number[]
}

export function costruisciStrade(
  { tratti: interi, incrocio, rotonda }: TracciatoTessera,
  tagli: readonly number[] = SENZA_TAGLI,
): GeometrieStrade {
  // i tratti accorciati dove comincia una rampa; l'indice resta quello del
  // tracciato (serve a trattoPerTriangolo), null = tratto tutto sulla rampa
  const accorciati = interi.map((t) => accorcia(t, tagli))
  const tratti = accorciati.filter((t): t is Tratto => t !== null)
  const asfalto = new Accumulo()
  const marciapiedi = new Accumulo()
  const segni = new Accumulo()

  // raggio dell'incrocio centrale: la metà della carreggiata più larga che ci arriva
  const raggioIncrocio = incrocio
    ? Math.max(...tratti.map((t) => PROFILO[t.classe].carreggiata / 2))
    : 0
  const haViale = tratti.some((t) => t.classe === "viale")

  /** Metà carreggiata di un tratto (l'anello della rotonda ha la sua larghezza). */
  const metaDi = (t: Tratto) =>
    t.inizio === "anello" && rotonda
      ? rotonda.larghezza / 2
      : PROFILO[t.classe].carreggiata / 2

  /** Vero se il punto q sta dentro la carreggiata di un altro tratto o dentro l'incrocio. */
  const occupato = (q: { x: number; z: number }, io: Tratto, margine = 0) =>
    tratti.some(
      (t) => t !== io && distanzaDa(q, t.punti) < metaDi(t) + margine,
    ) ||
    (incrocio !== null &&
      Math.hypot(q.x - incrocio.x, q.z - incrocio.z) < raggioIncrocio + margine)

  for (const [indice, t] of accorciati.entries()) {
    if (!t) continue
    asfalto.etichetta = indice // i triangoli di asfalto che seguono sono di questo tratto
    if (t.inizio === "anello") {
      anelloRotonda(t)
      continue
    }
    const { carreggiata, marciapiede, linee, attraversamenti } =
      PROFILO[t.classe]
    const meta = carreggiata / 2
    const s = ascisse(t.punti)
    const L = s[s.length - 1]

    // ---------- carreggiata ----------
    nastro(asfalto, t.punti, -meta, meta, QUOTE.carreggiata)
    if (t.fine === "cieco") {
      const f = t.punti[t.punti.length - 1]
      disco(asfalto, f.x, f.z, meta * 1.3, QUOTE.carreggiata) // slargo per girare
    }

    // ---------- zona dell'incrocio (alla fine del tratto) ----------
    // da dove inizia la strada "libera", risalendo dalla fine del tratto
    let liberaDa = 0 // distanza dalla fine
    const versoNodo =
      t.fine === "incrocio" || t.fine === "innesto" || t.fine === "rotonda"
    if (versoNodo) {
      for (let i = t.punti.length - 1; i >= 0; i--) {
        if (!occupato(t.punti[i], t, marciapiede)) {
          liberaDa = L - s[i]
          break
        }
      }
    }
    const conStrisce = attraversamenti && versoNodo
    // dare precedenza: entrando in una rotonda, o da una urbana che sbocca su un viale
    const conDenti =
      conStrisce && (t.fine === "rotonda" || (t.classe === "urbana" && haViale))
    const zona = conStrisce
      ? liberaDa +
        SEGNI.zebra.lunghezza +
        SEGNI.distacco +
        (conDenti ? SEGNI.dente.altezza + SEGNI.distacco : 0)
      : t.fine === "cieco"
        ? meta * 1.5
        : 0

    // ---------- marciapiedi ----------
    for (const verso of [-1, 1]) {
      const centro = verso * (meta + marciapiede / 2)
      for (const pezzo of spezza(
        t.punti,
        (i) => !occupato(lato(t.punti[i], centro), t),
      )) {
        nastro(
          marciapiedi,
          pezzo,
          verso * meta,
          verso * (meta + marciapiede),
          QUOTE.marciapiede,
        )
      }
    }

    // ---------- linee longitudinali ----------
    for (const { offset, tratteggiata } of linee) {
      const tieni = (i: number) =>
        L - s[i] > zona && // fuori dalla zona dell'incrocio
        !occupato(lato(t.punti[i], offset), t) &&
        (!tratteggiata || s[i] % (2 * SEGNI.tratto) < SEGNI.tratto)
      for (const pezzo of spezza(t.punti, tieni)) {
        nastro(
          segni,
          pezzo,
          offset - SEGNI.spessore / 2,
          offset + SEGNI.spessore / 2,
          QUOTE.segni,
        )
      }
    }

    // ---------- strisce pedonali ----------
    if (conStrisce && L - liberaDa > SEGNI.zebra.lunghezza) {
      const s1 = L - liberaDa
      const s0 = s1 - SEGNI.zebra.lunghezza
      const tratto = porzione(t.punti, s, s0, s1)
      const { striscia, passo } = SEGNI.zebra
      for (let d = -meta + passo / 2; d + striscia < meta; d += passo) {
        nastro(segni, tratto, d, d + striscia, QUOTE.segni)
      }

      // ---------- denti di squalo sulla corsia che arriva (a destra) ----------
      if (conDenti) {
        const sBase = s0 - SEGNI.distacco
        const sPunta = sBase - SEGNI.dente.altezza
        if (sPunta > 0) {
          const [base] = porzione(t.punti, s, sBase, sBase + 0.01)
          const [punta] = porzione(t.punti, s, sPunta, sPunta + 0.01)
          const { base: b, passo } = SEGNI.dente
          for (let d = 1; d + b < meta; d += passo) {
            const p1 = lato(base, d)
            const p2 = lato(base, d + b)
            const p3 = lato(punta, d + b / 2)
            segni.triangolo(
              [p1.x, QUOTE.segni, p1.z],
              [p2.x, QUOTE.segni, p2.z],
              [p3.x, QUOTE.segni, p3.z],
            )
          }
        }
      }
    }
  }

  /** L'anello della rotonda: carreggiata, marciapiede esterno, cordolo dell'isola, linee di margine. */
  function anelloRotonda(t: Tratto) {
    if (!rotonda) return
    const meta = rotonda.larghezza / 2
    const marciapiede = PROFILO.urbana.marciapiede
    nastro(asfalto, t.punti, -meta, meta, QUOTE.carreggiata)
    // + = verso l'esterno (l'anello gira in senso antiorario): marciapiede esterno interrotto dai rami
    for (const pezzo of spezza(
      t.punti,
      (i) => !occupato(lato(t.punti[i], meta + marciapiede / 2), t),
    )) {
      nastro(marciapiedi, pezzo, meta, meta + marciapiede, QUOTE.marciapiede)
    }
    // cordolo dell'isola centrale
    nastro(
      marciapiedi,
      t.punti,
      -meta - SEGNI.cordolo,
      -meta,
      QUOTE.marciapiede,
    )
    // linee di margine: quella esterna si interrompe dove entrano i rami
    for (const offset of [-meta + 1.6, meta - 1.6]) {
      for (const pezzo of spezza(
        t.punti,
        (i) => !occupato(lato(t.punti[i], offset), t),
      )) {
        nastro(
          segni,
          pezzo,
          offset - SEGNI.spessore / 2,
          offset + SEGNI.spessore / 2,
          QUOTE.segni,
        )
      }
    }
  }

  asfalto.etichetta = -1 // il disco dell'incrocio non appartiene a una via sola
  if (incrocio)
    disco(asfalto, incrocio.x, incrocio.z, raggioIncrocio, QUOTE.carreggiata)

  return {
    asfalto: asfalto.geometria(),
    marciapiedi: marciapiedi.geometria(),
    segni: segni.geometria(),
    trattoPerTriangolo: asfalto.etichette,
  }
}
