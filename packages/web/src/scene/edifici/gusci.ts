/*
 * gusci.ts
 * Dai progetti degli edifici (progetto.ts) alla geometria dei GUSCI: volumi
 * semplici con le facciate dipinte (GDD: "Come arrivano nel gioco" e
 * "Vincoli di peso"). È quello che si vede in tutte le viste tranne quella a
 * piedi: circa un centinaio di triangoli per casa.
 *
 * Tutti gli edifici della città finiscono in CINQUE geometrie (cinque
 * chiamate di disegno in tutto), perché la città non si muove:
 * - facciate e industria: ogni casella di ogni parete è un rettangolo con le
 *   UV del suo riquadro nell'atlante (atlante.ts) e il colore della casa nei
 *   vertici; lo shader tinge solo dove la maschera è bianca (l'intonaco o la
 *   lamiera). Una geometria per pagina dell'atlante: facciate.json (borgo,
 *   palazzoni, villette) e facciate_industria.json (capannoni, poi
 *   grattacieli). Un riquadro largo più di un modulo (il portone del
 *   capannone) copre anche le caselle COPERTE dopo di lui;
 * - intonaco: le parti senza riquadro (righe vuote del parapetto, alzata e
 *   fianchi della falda, terrazzi, scatole sul tetto), con la texture
 *   ripetibile dell'intonaco tinta dal colore nei vertici; UV in metri / 4
 *   (periodo 4 m delle texture del kit);
 * - tetti: le falde di ondulato (borgo, denti dello shed), UV in metri / 4
 *   (u lungo la gronda, v lungo la pendenza), senza tinta;
 * - coppi: le falde a capanna delle villette, come i tetti ma con la
 *   texture dei coppi.
 * Le coordinate del progetto sono in metri; la matrice di ogni edificio lo
 * porta nel mondo (posizione, rotazione e scala ×5,2). Gli altri CORPI di un
 * progetto (progetto.ts) si disegnano con la stessa matrice più il loro
 * spostamento; il RECINTO è fatto di scatole basse d'intonaco.
 *
 * Ogni vertice porta anche l'attributo `edificio`: il numero dell'edificio
 * (la sua posizione nell'elenco) sulle caselle e fasce del fronte che il kit
 * sa montare, −1 altrove. Quando un edificio è montato col kit nella vista a
 * piedi (KitEdifici.tsx), lo shader delle facciate fa sparire quelle caselle
 * (montati.ts), così la facciata dipinta non si vede dietro i pezzi veri.
 */

import { BufferAttribute, BufferGeometry, Matrix4, Vector3 } from "three"
import { PAGINE, riquadro } from "./atlante"
import { FASCE_MONTABILI, MONTABILI } from "./montaggio"
import {
  altezzaDi,
  COPERTA,
  larghezzaDi,
  NASCOSTA,
  MODULO,
  profonditaDi,
  T,
  type Parete,
  type Progetto,
  type Recinto,
  type Rgb,
  type Scatola,
  type Tetto,
} from "./progetto"

/** Un edificio messo nel mondo. */
export type EdificioPosato = {
  readonly progetto: Progetto
  readonly matrice: Matrix4
}

/** Periodo delle texture ripetibili del kit (m). */
const PERIODO = 4
/** Di quanto le fasce stanno fuori dalla parete (m), per non sfarfallare. */
const FUORI_FASCIA = 0.03

type P = readonly [number, number, number]

/** Un contenitore di triangoli che cresce: posizioni, normali, UV e colori. */
class Fogli {
  readonly pos: number[] = []
  /** Per ogni vertice: l'indice dell'edificio se la sua casella si nasconde quando l'edificio è montato col kit, −1 se resta sempre. */
  readonly ids: number[] = []
  readonly nor: number[] = []
  readonly uv: number[] = []
  readonly col: number[] = []
  readonly idx: number[] = []
  private m = new Matrix4()
  private v = new Vector3()
  private id = -1
  /** Vero mentre si disegnano caselle che il kit sa montare (montaggio.ts, MONTABILI). */
  montabile = false

  /** La matrice e l'indice dell'edificio a cui appartengono i prossimi vertici. */
  perEdificio(m: Matrix4, id: number) {
    this.m = m
    this.id = id
  }

  private vertice(p: P, n: P, uv: readonly [number, number], c: Rgb) {
    this.v.set(p[0], p[1], p[2]).applyMatrix4(this.m)
    this.pos.push(this.v.x, this.v.y, this.v.z)
    this.v.set(n[0], n[1], n[2]).transformDirection(this.m)
    this.nor.push(this.v.x, this.v.y, this.v.z)
    this.uv.push(uv[0], uv[1])
    this.col.push(c[0], c[1], c[2])
    this.ids.push(this.montabile ? this.id : -1)
  }

  /** Un rettangolo: a basso-destra, b basso-sinistra, c alto-sinistra, d alto-destra (visto da fuori). */
  quad(
    a: P,
    b: P,
    c: P,
    d: P,
    n: P,
    uv: readonly [number, number, number, number],
    col: Rgb,
  ) {
    const i = this.pos.length / 3
    const [u0, v0, u1, v1] = uv
    this.vertice(a, n, [u1, v0], col)
    this.vertice(b, n, [u0, v0], col)
    this.vertice(c, n, [u0, v1], col)
    this.vertice(d, n, [u1, v1], col)
    // a destra-basso → sinistra-basso → sinistra-alto: antiorario visto da fuori
    this.idx.push(i, i + 2, i + 1, i, i + 3, i + 2)
  }

  /** Un triangolo con UV date per vertice. */
  tri(
    a: P,
    b: P,
    c: P,
    n: P,
    uv: readonly [number, number, number, number, number, number],
    col: Rgb,
  ) {
    const i = this.pos.length / 3
    this.vertice(a, n, [uv[0], uv[1]], col)
    this.vertice(b, n, [uv[2], uv[3]], col)
    this.vertice(c, n, [uv[4], uv[5]], col)
    this.idx.push(i, i + 1, i + 2)
  }

  /** Un triangolo girato in modo che guardi verso n (scambia b e c se serve). UV in metri / PERIODO dalle coordinate (s, y) date per vertice. */
  triVerso(
    a: P,
    b: P,
    c: P,
    n: P,
    sy: readonly [number, number, number, number, number, number],
    col: Rgb,
  ) {
    const ux = b[0] - a[0],
      uy = b[1] - a[1],
      uz = b[2] - a[2]
    const vx = c[0] - a[0],
      vy = c[1] - a[1],
      vz = c[2] - a[2]
    const verso =
      (uy * vz - uz * vy) * n[0] +
      (uz * vx - ux * vz) * n[1] +
      (ux * vy - uy * vx) * n[2]
    const [sa, ya, sb, yb, sc, yc] = sy.map((x) => x / PERIODO)
    if (verso >= 0) this.tri(a, b, c, n, [sa, ya, sb, yb, sc, yc], col)
    else this.tri(a, c, b, n, [sa, ya, sc, yc, sb, yb], col)
  }

  geometria(conColore: boolean): BufferGeometry {
    const g = new BufferGeometry()
    g.setAttribute(
      "position",
      new BufferAttribute(new Float32Array(this.pos), 3),
    )
    g.setAttribute("normal", new BufferAttribute(new Float32Array(this.nor), 3))
    g.setAttribute("uv", new BufferAttribute(new Float32Array(this.uv), 2))
    if (conColore)
      g.setAttribute(
        "color",
        new BufferAttribute(new Float32Array(this.col), 3),
      )
    g.setAttribute(
      "edificio",
      new BufferAttribute(new Float32Array(this.ids), 1),
    )
    g.setIndex(
      this.pos.length / 3 > 65535
        ? new BufferAttribute(new Uint32Array(this.idx), 1)
        : new BufferAttribute(new Uint16Array(this.idx), 1),
    )
    g.computeBoundingSphere()
    return g
  }
}

/** Una parete: dove comincia (bordo destro visto da fuori), verso la sinistra, normale verso fuori, colonne. */
type Lato = {
  readonly o: P
  readonly sx: P
  readonly n: P
  readonly colonne: number
}

/** Le quattro pareti di un progetto, nelle sue coordinate (vedi progetto.ts). */
function lati(p: Progetto): Record<Parete, Lato> {
  const W = larghezzaDi(p)
  const D = profonditaDi(p)
  return {
    Fronte: { o: [0, 0, 0], sx: [0, 0, 1], n: [1, 0, 0], colonne: p.nW },
    Retro: { o: [-D, 0, W], sx: [0, 0, -1], n: [-1, 0, 0], colonne: p.nW },
    Destra: { o: [-D, 0, 0], sx: [1, 0, 0], n: [0, 0, -1], colonne: p.nD },
    Sinistra: { o: [0, 0, W], sx: [-1, 0, 0], n: [0, 0, 1], colonne: p.nD },
  }
}

const lungo = (
  o: P,
  d: P,
  t: number,
  y: number,
  fuori: P = [0, 0, 0],
  f = 0,
): P => [o[0] + d[0] * t + fuori[0] * f, y, o[2] + d[2] * t + fuori[2] * f]

/** UV in metri / PERIODO di un rettangolo largo w e alto h, a partire da (s, y). */
const uvMetri = (
  s: number,
  y: number,
  w: number,
  h: number,
): [number, number, number, number] => [
  s / PERIODO,
  y / PERIODO,
  (s + w) / PERIODO,
  (y + h) / PERIODO,
]

/** Le pareti con le caselle dell'atlante (o intonaco dove la casella è vuota) e le fasce. */
function pareti(p: Progetto, facciate: readonly Fogli[], intonaco: Fogli) {
  const L = lati(p)
  for (const parete of Object.keys(L) as Parete[]) {
    const { o, sx, n, colonne } = L[parete]
    // i fianchi sono lunghi D = nD moduli + 2 spessori di muro: senza stirare la prima e l'ultima
    // colonna di T, agli angoli resterebbe una fessura di 16 cm tra il fianco e il fronte o il retro
    const fianco = parete === "Destra" || parete === "Sinistra"
    const da = (k: number) => (fianco && k > 0 ? T + MODULO * k : MODULO * k)
    const a_ = (k: number, largo: number) =>
      fianco && k === colonne - 1
        ? MODULO * colonne + 2 * T
        : da(k) + largo + (fianco && k === 0 ? T : 0)
    let y = 0
    p.righe.forEach((h, r) => {
      for (let k = 0; k < colonne; k++) {
        const nome = p.caselle[parete][r]?.[k] ?? null
        if (nome === COPERTA || nome === NASCOSTA) continue // la copre il riquadro largo della colonna prima, o il corpo accanto
        const q = nome ? riquadro(nome) : null
        const largo = q ? Math.max(MODULO, q.larghezza) : MODULO
        const t0 = da(k)
        const t1 = a_(k, largo)
        const a = lungo(o, sx, t0, y)
        const b = lungo(o, sx, t1, y)
        const c = lungo(o, sx, t1, y + h)
        const d = lungo(o, sx, t0, y + h)
        if (q) {
          // sul fronte, le caselle che il kit sa montare spariscono quando l'edificio è montato
          facciate[q.pagina].montabile =
            parete === "Fronte" && MONTABILI.has(nome!)
          facciate[q.pagina].quad(a, b, c, d, n, q.uv, p.colore)
          facciate[q.pagina].montabile = false
        } else
          intonaco.quad(a, b, c, d, n, uvMetri(t0, y, t1 - t0, h), p.colore)
      }
      y += h
    })
    // fasce: un rettangolo lungo tutta la parete, appena fuori
    for (const f of p.fasce) {
      const q = riquadro(f.cella)
      facciate[q.pagina].montabile =
        parete === "Fronte" && FASCE_MONTABILI.has(f.cella)
      for (let k = 0; k < colonne; k++) {
        const t0 = da(k)
        const t1 = a_(k, MODULO)
        facciate[q.pagina].quad(
          lungo(o, sx, t0, f.quota, n, FUORI_FASCIA),
          lungo(o, sx, t1, f.quota, n, FUORI_FASCIA),
          lungo(o, sx, t1, f.quota + q.altezza, n, FUORI_FASCIA),
          lungo(o, sx, t0, f.quota + q.altezza, n, FUORI_FASCIA),
          n,
          q.uv,
          f.colore,
        )
      }
      facciate[q.pagina].montabile = false
    }
  }
}

/** Il tetto: falda di ondulato con alzata e fianchi, terrazzo con il parapetto dentro, capanna di coppi o shed. */
function tetto(p: Progetto, f: FogliCitta) {
  const { intonaco, tetti } = f
  const W = larghezzaDi(p)
  const D = profonditaDi(p)
  const H = altezzaDi(p)
  if (p.tetto.tipo === "falda") {
    const { pendenza, sporto } = p.tetto
    const tg = Math.tan(pendenza)
    const h = tg * D // il fronte è più alto del retro di tanto
    // alzata del fronte e fianchi a triangolo, nel colore della casa
    intonaco.quad(
      [0, H, 0],
      [0, H, W],
      [0, H + h, W],
      [0, H + h, 0],
      [1, 0, 0],
      uvMetri(0, H, W, h),
      p.colore,
    )
    intonaco.tri(
      [0, H, 0],
      [-D, H, 0],
      [0, H + h, 0],
      [0, 0, -1],
      [0, H / PERIODO, D / PERIODO, H / PERIODO, 0, (H + h) / PERIODO],
      p.colore,
    )
    intonaco.tri(
      [-D, H, W],
      [0, H, W],
      [0, H + h, W],
      [0, 0, 1],
      [
        0,
        H / PERIODO,
        D / PERIODO,
        H / PERIODO,
        D / PERIODO,
        (H + h) / PERIODO,
      ],
      p.colore,
    )
    // la falda: dal davanti (con lo sporto) al retro, poco sopra i muri
    const y = (x: number) => H + h + tg * x + 0.05
    const lunga = (D + 2 * sporto) / Math.cos(pendenza)
    const cz = Math.cos(pendenza)
    const sy = Math.sin(pendenza)
    tetti.quad(
      [sporto, y(sporto), -sporto],
      [sporto, y(sporto), W + sporto],
      [-D - sporto, y(-D - sporto), W + sporto],
      [-D - sporto, y(-D - sporto), -sporto],
      [-sy, cz, 0], // scende verso il retro: la normale guarda in su e un po' indietro
      [0, 0, (W + 2 * sporto) / PERIODO, lunga / PERIODO],
      [1, 1, 1],
    )
  } else if (p.tetto.tipo === "solaio") {
    // un coperchio a filo dei muri (un pelo sopra), sotto la scatola che ci sta sopra
    intonaco.quad(
      [0, H + 0.01, 0],
      [0, H + 0.01, W],
      [-D, H + 0.01, W],
      [-D, H + 0.01, 0],
      [0, 1, 0],
      [0, 0, W / PERIODO, D / PERIODO],
      p.tetto.copertura,
    )
  } else if (p.tetto.tipo === "capanna") {
    capanna(p, p.tetto, f)
  } else if (p.tetto.tipo === "shed") {
    shed(p, p.tetto.dente, p.tetto.canale, p.tetto.pendenza, f)
  } else {
    // terrazzo: la copertura alla quota sotto il parapetto (l'ultima riga) e il parapetto visto da dentro
    const parapetto = p.righe[p.righe.length - 1]
    const yc = H - parapetto
    intonaco.quad(
      [0, yc + 0.02, 0],
      [0, yc + 0.02, W],
      [-D, yc + 0.02, W],
      [-D, yc + 0.02, 0],
      [0, 1, 0],
      [0, 0, W / PERIODO, D / PERIODO],
      p.tetto.copertura,
    )
    const L = lati(p)
    for (const parete of Object.keys(L) as Parete[]) {
      const { o, sx, n, colonne } = L[parete]
      const lato = colonne * MODULO
      const dentro: P = [-n[0], 0, -n[2]]
      // stesso rettangolo della parete, girato verso l'interno (un pelo dentro, per non toccarla)
      intonaco.quad(
        lungo(o, sx, lato, yc, dentro, 0.06),
        lungo(o, sx, 0, yc, dentro, 0.06),
        lungo(o, sx, 0, H, dentro, 0.06),
        lungo(o, sx, lato, H, dentro, 0.06),
        dentro,
        uvMetri(0, yc, lato, parapetto),
        p.colore,
      )
    }
  }
}

/**
 * Tetto a capanna: colmo a metà profondità, parallelo alla facciata; una
 * falda scende verso il fronte e una verso il retro, con la gronda che
 * sporge; i fianchi chiusi da due triangoli nel colore della casa. Le falde
 * vanno nei coppi (villette) o nell'ondulato (palazzi a corte).
 */
function capanna(
  p: Progetto,
  t: Extract<Tetto, { tipo: "capanna" }>,
  { intonaco, coppi, tetti }: FogliCitta,
) {
  const { pendenza, gronda } = t
  const falde = t.materiale === "coppi" ? coppi : tetti
  const W = larghezzaDi(p)
  const D = profonditaDi(p)
  const H = altezzaDi(p)
  const tg = Math.tan(pendenza)
  const hr = (tg * D) / 2 // altezza del colmo sopra i muri
  const o = t.fianchi
  const su = 0.05 // un pelo sopra i muri e le testate
  const yG = H - tg * gronda + su
  const yC = H + hr + su
  const lunga = (D / 2 + gronda) / Math.cos(pendenza)
  const uv: [number, number, number, number] = [
    0,
    0,
    (W + 2 * o) / PERIODO,
    lunga / PERIODO,
  ]
  const s = Math.sin(pendenza)
  const c = Math.cos(pendenza)
  // falda davanti (vista dalla strada) e falda dietro (vista dal retro)
  falde.quad(
    [gronda, yG, -o],
    [gronda, yG, W + o],
    [-D / 2, yC, W + o],
    [-D / 2, yC, -o],
    [s, c, 0],
    uv,
    [1, 1, 1],
  )
  falde.quad(
    [-D - gronda, yG, W + o],
    [-D - gronda, yG, -o],
    [-D / 2, yC, -o],
    [-D / 2, yC, W + o],
    [-s, c, 0],
    uv,
    [1, 1, 1],
  )
  // testate, solo sui fianchi che si vedono: dove l'ultima riga del fianco è NASCOSTA c'è un palazzo
  // accanto alto almeno quanto questo, e il triangolo starebbe sul suo muro (sfarfallerebbe)
  const siVede = (parete: "Destra" | "Sinistra") =>
    p.caselle[parete].at(-1)?.[0] !== NASCOSTA
  if (siVede("Destra"))
    intonaco.triVerso(
      [0, H, 0],
      [-D, H, 0],
      [-D / 2, H + hr, 0],
      [0, 0, -1],
      [0, H, D, H, D / 2, H + hr],
      p.colore,
    )
  if (siVede("Sinistra"))
    intonaco.triVerso(
      [-D, H, W],
      [0, H, W],
      [-D / 2, H + hr, W],
      [0, 0, 1],
      [0, H, D, H, D / 2, H + hr],
      p.colore,
    )
}

/**
 * Tetto a shed: lungo la larghezza, un dente ogni `dente` m. Ogni dente ha
 * il canale piatto, la falda di ondulato che sale verso la sinistra (vista
 * dalla strada) e la vetrata verticale in cima (la banda di vetro del
 * riquadro Cap_Finestrata, una per modulo di profondità); le teste a
 * triangolo, nel colore della lamiera, chiudono i denti sul fronte e sul
 * retro.
 */
function shed(
  p: Progetto,
  dente: number,
  canale: number,
  pendenza: number,
  { intonaco, tetti, facciate }: FogliCitta,
) {
  const W = larghezzaDi(p)
  const D = profonditaDi(p)
  const H = altezzaDi(p)
  const L = dente - canale
  const hs = Math.tan(pendenza) * L
  const lunga = L / Math.cos(pendenza)
  const sn = Math.sin(pendenza)
  const cs = Math.cos(pendenza)
  const y = H + 0.02
  // la banda di vetro del nastro di finestre (da 0,8 a 2,5 m del riquadro alto 3 m)
  const f = riquadro("Cap_Finestrata")
  const [u0, v0, u1, v1] = f.uv
  const vetro: [number, number, number, number] = [
    u0,
    v0 + ((v1 - v0) * 0.8) / f.altezza,
    u1,
    v0 + ((v1 - v0) * 2.5) / f.altezza,
  ]
  for (let z0 = 0; z0 + dente <= W + 0.01; z0 += dente) {
    const za = z0 + canale
    const zb = z0 + dente
    tetti.quad(
      [0, y, z0],
      [0, y, za],
      [-D, y, za],
      [-D, y, z0],
      [0, 1, 0],
      [0, 0, canale / PERIODO, D / PERIODO],
      [1, 1, 1],
    )
    tetti.quad(
      [-D, y, za],
      [0, y, za],
      [0, y + hs, zb],
      [-D, y + hs, zb],
      [0, cs, -sn],
      [0, 0, D / PERIODO, lunga / PERIODO],
      [1, 1, 1],
    )
    for (let j = 0; j < p.nD; j++) {
      const xd = -T - MODULO * j // bordo destro (visto da +Z) del modulo di vetrata
      facciate[f.pagina].quad(
        [xd, y, zb],
        [xd - MODULO, y, zb],
        [xd - MODULO, y + hs, zb],
        [xd, y + hs, zb],
        [0, 0, 1],
        vetro,
        p.colore,
      )
    }
    for (const [x, n] of [
      [0, 1],
      [-D, -1],
    ] as const)
      intonaco.triVerso(
        [x, H, za],
        [x, H, zb],
        [x, H + hs, zb],
        [n, 0, 0],
        [za, H, zb, H, zb, H + hs],
        p.colore,
      )
  }
}

/** Il muretto del recinto: quattro lati di scatole basse, con il varco del cancello sul davanti. */
function recinto(r: Recinto, intonaco: Fogli) {
  const { x0, x1, z0, z1, altezza, spessore: s, colore, cancello } = r
  const muro = (xa: number, xb: number, za: number, zb: number) =>
    scatola(
      {
        x: xb,
        z: za,
        quota: 0,
        larghezza: zb - za,
        profondita: xb - xa,
        altezza,
        colore,
      },
      intonaco,
    )
  muro(x1 - s, x1, z0, cancello.z - cancello.larghezza / 2)
  muro(x1 - s, x1, cancello.z + cancello.larghezza / 2, z1)
  muro(x0, x0 + s, z0, z1)
  muro(x0 + s, x1 - s, z0, z0 + s)
  muro(x0 + s, x1 - s, z1 - s, z1)
}

/** Una scatola sul tetto: quattro pareti e il coperchio, d'intonaco tinto. */
function scatola(s: Scatola, intonaco: Fogli) {
  const x0 = s.x - s.profondita
  const x1 = s.x
  const z0 = s.z
  const z1 = s.z + s.larghezza
  const y0 = s.quota
  const y1 = s.quota + s.altezza
  const h = s.altezza
  intonaco.quad(
    [x1, y0, z0],
    [x1, y0, z1],
    [x1, y1, z1],
    [x1, y1, z0],
    [1, 0, 0],
    uvMetri(0, y0, s.larghezza, h),
    s.colore,
  )
  intonaco.quad(
    [x0, y0, z1],
    [x0, y0, z0],
    [x0, y1, z0],
    [x0, y1, z1],
    [-1, 0, 0],
    uvMetri(0, y0, s.larghezza, h),
    s.colore,
  )
  intonaco.quad(
    [x0, y0, z0],
    [x1, y0, z0],
    [x1, y1, z0],
    [x0, y1, z0],
    [0, 0, -1],
    uvMetri(0, y0, s.profondita, h),
    s.colore,
  )
  intonaco.quad(
    [x1, y0, z1],
    [x0, y0, z1],
    [x0, y1, z1],
    [x1, y1, z1],
    [0, 0, 1],
    uvMetri(0, y0, s.profondita, h),
    s.colore,
  )
  intonaco.quad(
    [x1, y1, z0],
    [x1, y1, z1],
    [x0, y1, z1],
    [x0, y1, z0],
    [0, 1, 0],
    [0, 0, s.larghezza / PERIODO, s.profondita / PERIODO],
    s.colore,
  )
}

/** I fogli in cui finiscono tutti gli edifici: uno per pagina dell'atlante, intonaco, ondulato, coppi. */
type FogliCitta = {
  readonly facciate: readonly Fogli[]
  readonly intonaco: Fogli
  readonly tetti: Fogli
  readonly coppi: Fogli
}

export type GeometrieGusci = {
  /** Una geometria per pagina dell'atlante: [facciate.json, facciate_industria.json]. */
  readonly facciate: readonly BufferGeometry[]
  readonly intonaco: BufferGeometry
  readonly tetti: BufferGeometry
  readonly coppi: BufferGeometry
}

/** Un progetto con la sua matrice, poi i suoi altri corpi spostati. */
function edificio(p: Progetto, m: Matrix4, id: number, f: FogliCitta) {
  for (const fogli of [...f.facciate, f.intonaco, f.tetti, f.coppi])
    fogli.perEdificio(m, id)
  pareti(p, f.facciate, f.intonaco)
  tetto(p, f)
  for (const s of p.scatole) scatola(s, f.intonaco)
  if (p.recinto) recinto(p.recinto, f.intonaco)
  // prima si gira il corpo attorno a Y, poi lo si sposta (come rotation.y e position di Three.js)
  for (const c of p.corpi ?? [])
    edificio(
      c.progetto,
      m
        .clone()
        .multiply(new Matrix4().makeTranslation(c.x, c.y, c.z))
        .multiply(new Matrix4().makeRotationY(c.rotazione ?? 0)),
      id,
      f,
    )
}

/** Le geometrie dei gusci di tutti gli edifici dati. */
export function costruisciGusci(
  edifici: readonly EdificioPosato[],
): GeometrieGusci {
  const f: FogliCitta = {
    facciate: PAGINE.map(() => new Fogli()),
    intonaco: new Fogli(),
    tetti: new Fogli(),
    coppi: new Fogli(),
  }
  // l'indice nell'elenco è il numero dell'edificio: lo shader delle facciate lo usa per nascondere i montati
  edifici.forEach(({ progetto, matrice }, i) =>
    edificio(progetto, matrice, i, f),
  )
  return {
    facciate: f.facciate.map((x) => x.geometria(true)),
    intonaco: f.intonaco.geometria(true),
    tetti: f.tetti.geometria(false),
    coppi: f.coppi.geometria(false),
  }
}
