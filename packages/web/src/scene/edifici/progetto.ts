/*
 * progetto.ts
 * Il "progetto" di un edificio: la descrizione astratta che i generatori
 * (borgo.ts, palazzoni.ts, poi le altre famiglie) producono dal seme e che
 * gusci.ts trasforma in geometria. È la stessa idea di cb_edifici.py in
 * Blender (stesse misure e stesse regole), ma invece dei pezzi 3D del kit
 * dice quale RIQUADRO dell'atlante di facciata (facciate.json) va in ogni
 * casella di ogni parete: è il guscio, quello che si vede in tutte le viste
 * tranne quella a piedi (GDD: "Vincoli di peso").
 *
 * Coordinate del progetto: metri reali (il gioco scala ×5,2), assi di
 * Three.js. La facciata principale guarda +X (la strada), l'edificio occupa
 * x da −profondità a 0 e z da 0 a larghezza; l'origine è l'angolo in basso a
 * destra della facciata vista dalla strada (come nel kit: chi guarda la
 * facciata ha la destra verso −Z, quindi z = 0 è il bordo destro).
 * Le colonne di ogni parete si contano dal suo bordo destro (visto da fuori),
 * come in cb_edifici.py: k = 0 è la colonna più a destra.
 *
 * Le costanti vengono da kit_edifici.json (sezione "costanti"): se in
 * Blender cambiano, vanno cambiate anche qui.
 *
 * Oltre al corpo principale un progetto può avere:
 * - altri CORPI, ognuno un progetto completo spostato di (x, y, z) rispetto
 *   all'origine: la palazzina degli uffici davanti al capannone, le scatole
 *   impilate dei grattacieli;
 * - un RECINTO: il muretto attorno al lotto della villetta, col varco del
 *   cancello.
 * L'IMPRONTA (impronta()) è il rettangolo che contiene tutto: lotti.ts mette
 * a filo del marciapiede il suo lato davanti, non la facciata.
 */

/** Modulo di facciata, altezza del piano terra e dei piani (m). */
export const MODULO = 2
export const H_TERRA = 4
export const H_PIANO = 3
/** Spessore del cartone delle pareti (m): la profondità ha due spessori in più. */
export const T = 0.08
/** Scala grafica: metri reali → unità di gioco. */
export const SCALA_EDIFICI = 5.2

export type Rgb = readonly [number, number, number]

/** Casella occupata dal riquadro largo della colonna prima (il portone del capannone è largo 2 moduli). */
export const COPERTA = "←"
/** Casella che non si costruisce: muro appoggiato a un altro corpo (i palazzi accostati del blocco a corte). */
export const NASCOSTA = "∅"

/** Le pareti, con il nome che hanno in cb_edifici.py. */
export type Parete = "Fronte" | "Destra" | "Sinistra" | "Retro"
export const PARETI: readonly Parete[] = [
  "Fronte",
  "Destra",
  "Sinistra",
  "Retro",
]

/** Una fascia orizzontale (marcapiano, cornicione) lungo tutte le pareti. */
export type Fascia = {
  readonly cella: string
  readonly quota: number
  readonly colore: Rgb
}

/** Il tetto del guscio. */
export type Tetto =
  /** Falda unica di ondulato che scende verso il retro (borgo): alza il fronte e i fianchi di `alzata`. */
  | {
      readonly tipo: "falda"
      readonly pendenza: number
      readonly sporto: number
    }
  /** Tetto piano (terrazzo) con il parapetto tutto attorno: un'altra riga di caselle in cima. */
  | { readonly tipo: "piano"; readonly copertura: Rgb }
  /** Solo il solaio piatto in cima ai muri, senza parapetto: le scatole di sotto dei grattacieli (la cornice è una fascia). */
  | { readonly tipo: "solaio"; readonly copertura: Rgb }
  /**
   * Due falde con il colmo parallelo alla facciata; i fianchi chiusi dalle testate a triangolo.
   * Coppi per le villette, ondulato kraft per i palazzi a corte; `fianchi` = di quanto le falde
   * sporgono oltre i fianchi (0 dove il palazzo accanto è attaccato).
   */
  | {
      readonly tipo: "capanna"
      readonly pendenza: number
      readonly gronda: number
      readonly materiale: "coppi" | "ondulato"
      readonly fianchi: number
    }
  /**
   * Shed (capannoni): denti larghi `dente` m lungo la strada, ognuno con il
   * canale piatto, la falda di ondulato che sale di `pendenza` e la vetrata
   * verticale; le teste dei denti, a triangolo, sul fronte e sul retro.
   */
  | {
      readonly tipo: "shed"
      readonly dente: number
      readonly canale: number
      readonly pendenza: number
    }

/** Una scatola sul tetto (torrino della scala, sopraelevazione): solo intonaco tinto. */
export type Scatola = {
  readonly x: number // angolo verso +X e verso z = 0 (come l'origine dell'edificio)
  readonly z: number
  readonly quota: number // dove appoggia
  readonly larghezza: number
  readonly profondita: number
  readonly altezza: number
  readonly colore: Rgb
}

/** Il muretto attorno al lotto, nelle coordinate del progetto, con il varco del cancello sul davanti. */
export type Recinto = {
  readonly x0: number // retro
  readonly x1: number // davanti (sulla strada)
  readonly z0: number // destra
  readonly z1: number // sinistra
  readonly altezza: number
  readonly spessore: number
  readonly colore: Rgb
  /** Centro e larghezza del varco del cancello, lungo z. */
  readonly cancello: { readonly z: number; readonly larghezza: number }
}

/**
 * Un altro volume dell'edificio, spostato rispetto all'origine del progetto principale e
 * girato attorno a Y di `rotazione` (radianti, come rotation.y di Three.js: π/2 porta la
 * facciata a guardare −Z). Prima si gira, poi si sposta.
 */
export type Corpo = {
  readonly progetto: Progetto
  readonly x: number
  readonly y: number
  readonly z: number
  readonly rotazione?: number
}

export type Progetto = {
  readonly famiglia: string
  /** Moduli in larghezza (lungo la strada) e in profondità. */
  readonly nW: number
  readonly nD: number
  /** Altezza di ogni riga di caselle, dal basso (4 = terra, 3 = piano, 0,72 = parapetto...). */
  readonly righe: readonly number[]
  /** Per ogni parete, riga e colonna: il nome del riquadro dell'atlante (null = niente, la parete resta intonaco). */
  readonly caselle: Readonly<
    Record<Parete, readonly (readonly (string | null)[])[]>
  >
  readonly colore: Rgb
  readonly fasce: readonly Fascia[]
  readonly tetto: Tetto
  readonly scatole: readonly Scatola[]
  readonly corpi?: readonly Corpo[]
  readonly recinto?: Recinto
}

/** Larghezza e profondità in metri (la profondità comprende lo spessore delle due pareti, come nel kit). */
export const larghezzaDi = (p: Progetto) => p.nW * MODULO
export const profonditaDi = (p: Progetto) => p.nD * MODULO + 2 * T
/** Altezza delle pareti, senza il tetto. */
export const altezzaDi = (p: Progetto) => p.righe.reduce((a, b) => a + b, 0)

/** Il rettangolo (m, coordinate del progetto) che contiene corpo principale, altri corpi e recinto. */
export type Impronta = {
  readonly x0: number
  readonly x1: number
  readonly z0: number
  readonly z1: number
}

export function impronta(p: Progetto): Impronta {
  let x0 = -profonditaDi(p)
  let x1 = 0
  let z0 = 0
  let z1 = larghezzaDi(p)
  for (const c of p.corpi ?? []) {
    const i = impronta(c.progetto)
    const cs = Math.cos(c.rotazione ?? 0)
    const sn = Math.sin(c.rotazione ?? 0)
    // i quattro angoli dell'impronta del corpo, girati come rotation.y e poi spostati
    for (const [px, pz] of [
      [i.x0, i.z0],
      [i.x0, i.z1],
      [i.x1, i.z0],
      [i.x1, i.z1],
    ]) {
      const x = c.x + cs * px + sn * pz
      const z = c.z - sn * px + cs * pz
      x0 = Math.min(x0, x)
      x1 = Math.max(x1, x)
      z0 = Math.min(z0, z)
      z1 = Math.max(z1, z)
    }
  }
  if (p.recinto) {
    x0 = Math.min(x0, p.recinto.x0)
    x1 = Math.max(x1, p.recinto.x1)
    z0 = Math.min(z0, p.recinto.z0)
    z1 = Math.max(z1, p.recinto.z1)
  }
  return { x0, x1, z0, z1 }
}
