/*
 * corte.ts
 * I palazzi a corte del residenziale vicino al centro, dal seme: le regole
 * di palazzo_corte() in cb_edifici.py, ridotte a quello che serve al guscio.
 *
 * Un BLOCCO a corte è un rettangolo di quattro ali attorno a un cortile:
 * - due ali LUNGHE, una sulla strada e una dietro (girata di 180°), lunghe
 *   n_l moduli. Ognuna è una CORTINA di palazzi accostati di 2-5 moduli,
 *   ognuno col suo colore, i suoi piani (2-4 sopra il terra), i balconi
 *   (alterni, tutti o nessuno, solo ai primi due piani), le cornici di
 *   stucco alle finestre tre volte su quattro;
 * - due ali CORTE sui fianchi (girate di ±90°, guardano le strade
 *   laterali), larghe n_s moduli, alte quanto il più basso dei due palazzi
 *   d'angolo (a volte un piano in meno);
 * - al terra botteghe (vetrine con tenda o insegna, serrande) e il portone
 *   d'ingresso al centro dell'ala sulla strada, che porta nel cortile;
 * - sul cortile (il retro delle ali lunghe) portefinestre su ogni piano:
 *   lì corrono i ballatoi della casa di ringhiera (pezzi del kit, a piedi);
 * - marcapiano e cornicione color stucco; tetti a due falde di ondulato
 *   kraft a 24° con la gronda di 35 cm.
 * I muri dove un palazzo si appoggia a un altro non si costruiscono
 * (NASCOSTA); dove il vicino è più basso, sopra di lui c'è muro cieco.
 * Il cortile resta chiuso: dalla strada non si vede (GDD, "Vincoli di peso").
 *
 * Ogni palazzo è un CORPO del progetto (progetto.ts), girato e spostato; il
 * progetto principale è il primo palazzo dell'ala sulla strada. Coordinate
 * come cb_edifici.py: l'ala sulla strada va da z = 0 a z = L, il blocco è
 * profondo B (x da −B a 0).
 *
 * Una differenza da Blender: lì le altezze delle ali corte, che decidono
 * quali muri del cortile restano nascosti, erano passate alle ali lunghe
 * scambiate tra destra e sinistra; qui ogni lato prende quella della sua ala.
 */

import type { Casuale } from "@corsa-bis/engine"
import { INTONACI_CORTE, STUCCO } from "./colori"
import {
  H_PIANO,
  H_TERRA,
  MODULO,
  NASCOSTA,
  T,
  type Corpo,
  type Fascia,
  type Progetto,
  type Rgb,
  type Tetto,
} from "./progetto"

/** TETTO_A e GRONDA di cb_edifici.py: due falde di ondulato, attaccate a quelle dei vicini. */
const TETTO: Tetto = {
  tipo: "capanna",
  pendenza: (24 * Math.PI) / 180,
  gronda: 0.35,
  materiale: "ondulato",
  fianchi: 0,
}

/** Un palazzo della cortina. */
type Segmento = {
  s0: number
  w: number
  colore: Rgb
  piani: number
  balconi: "alterni" | "tutti" | "nessuno"
  cornici: boolean
}

export function generaCorte(rng: Casuale): Progetto {
  const nD = rng.scegli([2, 2, 3])
  const Dw = nD * MODULO + 2 * T
  // colonne del lato cortile coperte dalle ali corte
  const nc = Math.ceil(Dw / MODULO - 0.1)
  const nL = rng.intero(2 * nc + 3, 2 * nc + 5)
  const nS = rng.intero(2, 4)
  const base = rng.scegli([2, 3, 3, 4])
  const L = nL * MODULO
  const B = 2 * Dw + nS * MODULO
  const cAndrone = Math.floor((nL - 1) / 2)

  /** Divide nL colonne in palazzi di 2-5 moduli, ognuno col suo carattere. */
  const cortina = (): Segmento[] => {
    const segs: Segmento[] = []
    let k = 0
    let prima: string | null = null
    while (k < nL) {
      let w = rng.intero(2, 4)
      if (nL - (k + w) === 1) w += 1
      w = Math.min(w, nL - k)
      const nome: string = rng.scegli(
        Object.keys(INTONACI_CORTE).filter((c) => c !== prima),
      )
      prima = nome
      segs.push({
        s0: k,
        w,
        colore: INTONACI_CORTE[nome],
        piani: Math.max(2, Math.min(4, base + rng.scegli([-1, 0, 0, 1]))),
        balconi: rng.scegli([
          "alterni",
          "alterni",
          "tutti",
          "nessuno",
        ] as const),
        cornici: rng.probabilita(0.75),
      })
      k += w
    }
    return segs
  }

  // le ali corte sono alte quanto il più basso dei palazzi d'angolo: prima si decidono le cortine
  const fronte = cortina() // colonna 0 a z = 0 (destra, vista dalla strada)
  const retro = cortina() // girata: colonna 0 a z = L
  const pcDx = Math.max(
    2,
    Math.min(fronte[0].piani, retro[retro.length - 1].piani) -
      rng.scegli([0, 0, 1]),
  )
  const pcSx = Math.max(
    2,
    Math.min(fronte[fronte.length - 1].piani, retro[0].piani) -
      rng.scegli([0, 0, 1]),
  )

  const corpi: Corpo[] = [
    // ala sulla strada: i palazzi uno dopo l'altro lungo z
    ...alaLunga(fronte, [pcDx, pcSx]).map((progetto, i) => ({
      progetto,
      x: 0,
      y: 0,
      z: MODULO * fronte[i].s0,
    })),
    // ala dietro, girata di 180°: la sua colonna 0 è a z = L
    ...alaLunga(retro, [pcSx, pcDx]).map((progetto, i) => ({
      progetto,
      x: -B,
      y: 0,
      z: L - MODULO * retro[i].s0,
      rotazione: Math.PI,
    })),
    // ali corte sui fianchi: la destra guarda −Z, la sinistra +Z
    {
      progetto: alaCorta(
        pcDx,
        rng.scegli([fronte[0].colore, retro[retro.length - 1].colore]),
      ),
      x: -B + Dw,
      y: 0,
      z: 0,
      rotazione: Math.PI / 2,
    },
    {
      progetto: alaCorta(
        pcSx,
        rng.scegli([fronte[fronte.length - 1].colore, retro[0].colore]),
      ),
      x: -Dw,
      y: 0,
      z: L,
      rotazione: -Math.PI / 2,
    },
  ]
  const [primo, ...altri] = corpi
  return { ...primo.progetto, famiglia: "corte", corpi: altri }

  /** Un'ala lunga: un progetto per palazzo della cortina. `pc` = piani delle ali corte vicino alla colonna 0 e all'ultima. */
  function alaLunga(
    segs: readonly Segmento[],
    pc: readonly [number, number],
  ): Progetto[] {
    return segs.map((g, i) => {
      const { s0, w, piani } = g
      const vicinoDx = i > 0 ? segs[i - 1].piani : null // verso la colonna 0
      const vicinoSx = i < segs.length - 1 ? segs[i + 1].piani : null
      const ka = s0 <= cAndrone && cAndrone < s0 + w ? cAndrone - s0 : null
      const balconi = new Set(
        {
          alterni: Array.from({ length: w }, (_, k) => k).filter(
            (k) => (s0 + k) % 2 === 1,
          ),
          tutti: Array.from({ length: w }, (_, k) => k),
          nessuno: [],
        }[g.balconi].filter((k) => k !== ka),
      )
      const finestra = () =>
        g.cornici
          ? rng.probabilita(0.15)
            ? "Corte_Finestra_Chiusa"
            : "Corte_Finestra_Aperta"
          : rng.probabilita(0.15)
            ? "Piano_Finestra_Chiusa"
            : "Piano_Finestra_Aperta"
      const balcone = g.cornici
        ? "Corte_Portafinestra_Balcone"
        : "Piano_Portafinestra_Balcone"

      const strada: string[][] = [
        Array.from({ length: w }, (_, k) =>
          k === ka ? "Terra_Portone" : bottega(rng),
        ),
      ]
      for (let p = 1; p <= piani; p++)
        strada.push(
          Array.from({ length: w }, (_, k) =>
            balconi.has(k) && p <= 2 ? balcone : finestra(),
          ),
        )

      // il cortile: le colonne dietro un'ala corta restano nascoste fin dove arriva lei
      const cortile: string[][] = []
      for (let li = 0; li <= piani; li++)
        cortile.push(
          Array.from({ length: w }, (_, k) => {
            const gc = s0 + (w - 1 - k) // colonna dell'ala (le colonne del retro si contano dall'altra parte)
            if (gc < nc || gc >= nL - nc)
              return li <= pc[gc < nc ? 0 : 1] ? NASCOSTA : "Piano_Parete"
            if (li === 0)
              return gc === cAndrone
                ? "Terra_Portone"
                : gc % 3 === 0
                  ? "Terra_Porta"
                  : "Terra_Parete"
            return "Piano_Portafinestra"
          }),
        )
      // i fianchi: contro il palazzo accanto non si costruiscono; alle teste dell'ala finestre sulla strada laterale
      const fianco = (vicino: number | null) => {
        const r: string[][] = []
        for (let li = 0; li <= piani; li++)
          r.push(
            Array.from({ length: nD }, () =>
              vicino !== null
                ? li <= vicino
                  ? NASCOSTA
                  : "Piano_Parete"
                : li === 0
                  ? "Terra_Parete"
                  : rng.probabilita(0.8)
                    ? finestra()
                    : "Piano_Parete",
            ),
          )
        return r
      }
      return palazzo(w, nD, piani, g.colore, g.cornici, {
        Fronte: strada,
        Retro: cortile,
        Destra: fianco(vicinoDx),
        Sinistra: fianco(vicinoSx),
      })
    })
  }

  /** Un'ala corta: botteghe e finestre con le cornici sulla strada laterale, porta sul cortile, fianchi contro le ali lunghe. */
  function alaCorta(piani: number, colore: Rgb): Progetto {
    const finestra = () =>
      rng.probabilita(0.2) ? "Corte_Finestra_Chiusa" : "Corte_Finestra_Aperta"
    const strada: string[][] = [
      Array.from({ length: nS }, () =>
        rng.scegli(["Terra_Parete", "Terra_Vetrina", "Terra_Serranda"]),
      ),
    ]
    const cortile: string[][] = [
      Array.from({ length: nS }, (_, k) =>
        k === Math.floor(nS / 2) ? "Terra_Porta" : "Terra_Parete",
      ),
    ]
    for (let p = 1; p <= piani; p++) {
      strada.push(Array.from({ length: nS }, finestra))
      cortile.push(Array.from({ length: nS }, () => "Piano_Finestra_Aperta"))
    }
    const contro = Array.from({ length: piani + 1 }, () =>
      Array.from({ length: nD }, () => NASCOSTA),
    )
    return palazzo(nS, nD, piani, colore, true, {
      Fronte: strada,
      Retro: cortile,
      Destra: contro,
      Sinistra: contro,
    })
  }
}

/** Una bottega al terra: vetrina (a volte con la tenda o l'insegna), serranda, o muro. */
function bottega(rng: Casuale): string {
  const t = rng.scegli([
    "Terra_Vetrina",
    "Terra_Vetrina",
    "Terra_Serranda",
    "Terra_Parete",
  ])
  if (t !== "Terra_Vetrina") return t
  return rng.probabilita(0.5)
    ? "Terra_Vetrina_Tenda"
    : rng.probabilita(0.3)
      ? "Terra_Vetrina_Insegna"
      : t
}

/** Un palazzo della corte: terra + piani, marcapiano e cornicione di stucco, tetto a due falde. */
function palazzo(
  nW: number,
  nD: number,
  piani: number,
  colore: Rgb,
  cornici: boolean,
  caselle: Progetto["caselle"],
): Progetto {
  const H = H_TERRA + H_PIANO * piani
  const fasce: Fascia[] = [
    { cella: "Fascia_Marcapiano", quota: H_TERRA - 0.08, colore: STUCCO },
    cornici
      ? { cella: "Fascia_Cornicione_Corte", quota: H - 0.4, colore: STUCCO }
      : { cella: "Fascia_Cornicione", quota: H - 0.3, colore: STUCCO },
  ]
  return {
    famiglia: "palazzo_corte",
    nW,
    nD,
    righe: [H_TERRA, ...Array.from({ length: piani }, () => H_PIANO)],
    caselle,
    colore,
    fasce,
    tetto: TETTO,
    scatole: [],
  }
}
