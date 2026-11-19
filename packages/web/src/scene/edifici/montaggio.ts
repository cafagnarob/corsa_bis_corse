/*
 * montaggio.ts
 * Dal progetto di un edificio ai PEZZI DEL KIT (kit_edifici.glb) che lo
 * montano da vicino, nella vista a piedi. È la parte di cb_edifici.py che
 * mette i pezzi, riscritta partendo dai progetti che usano già i gusci: la
 * casella dell'atlante dice quale modulo va lì, e cosa ci si attacca sopra.
 *
 * Cosa si monta (le decisioni del GDD, "Vincoli di peso"):
 * - solo le FACCIATE SU STRADA, cioè la parete Fronte del progetto e dei
 *   suoi corpi (anche girati: l'ala dietro del blocco a corte, le scatole
 *   del grattacielo); fianchi, retro e cortili restano guscio;
 * - le caselle che hanno un pezzo nel kit (MONTABILI). Le altre (righe
 *   d'intonaco senza riquadro, l'alzata della falda) restano guscio: in
 *   gusci.ts si nascondono solo le caselle montabili degli edifici montati;
 * - le fasce sul fronte (marcapiano, cornicioni, coronamento);
 * - i TETTI restano quelli del guscio: un modulo di tetto del kit pesa fino
 *   a 1.500 triangoli e da terra non si vede quasi.
 *
 * Il kit è già nelle coordinate dei progetti: un modulo di parete ha la
 * faccia esterna in x = 0, va da z = 0 a z = 2 (lungo la facciata, verso
 * sinistra vista dalla strada) e da y = 0 in su. Quindi la casella k della
 * riga che parte da quota y è il pezzo spostato di (0, y, 2k), senza
 * rotazioni; le aggiunte (persiane, balconi, tende) hanno la loro posizione
 * dentro il modulo, come in cb_edifici.py.
 *
 * Il risultato è un elenco di ISTANZE: nome del pezzo, matrice nel mondo e
 * colore per l'intonaco del pezzo (null = il pezzo non si tinge). Le
 * varianti (quanto sono aperte le persiane, tapparelle, insegne, colore
 * delle tende) vengono dal seme dell'edificio: rimontandolo escono uguali.
 */

import { Casuale } from "@corsa-bis/engine"
import { Matrix4 } from "three"
import { riquadro } from "./atlante"
import { STUCCO } from "./colori"
import { COPERTA, MODULO, NASCOSTA, type Progetto, type Rgb } from "./progetto"
import type { EdificioPosato } from "./gusci"

/** Un pezzo del kit messo nel mondo. */
export type Istanza = {
  readonly pezzo: string
  readonly matrice: Matrix4
  readonly colore: Rgb | null
}

/** Dove sta un pezzo dentro la casella (e quanto è stirato in y e z), e di che colore è il suo intonaco. */
type Pezzo = {
  nome: string
  x?: number
  y?: number
  z?: number
  ry?: number
  sy?: number
  sz?: number
  colore?: "casa" | Rgb | null
}

/**
 * Il FONDALE: dietro ogni casella con un'apertura, un pannello di cartone scuro a FONDO metri
 * dentro la facciata. Il guscio è vuoto e le sue facce interne non si disegnano: senza
 * fondale, da una porta o da una vetrina si vedrebbe la strada dall'altra parte. È lo
 * stesso trucco del bake dell'atlante (cb_atlante_edifici.py). Non è un pezzo del kit:
 * è un quadrato 1 × 1 (KitEdifici.tsx) stirato all'altezza e alla larghezza della casella.
 */
export const FONDALE = "Fondale"
const FONDO = 0.8
/** Le caselle senza aperture: dietro non serve il fondale. */
const CIECHE = new Set([
  "Terra_Parete",
  "Piano_Parete",
  "Pal_Testata",
  "Cap_Parete",
  "Cap_Parete_Alta",
  "Fascia_Parapetto_Pal",
  "Gr_Coronamento",
])

/** Le tende dei negozi (TENDE nel JSON del kit): il colore delle strisce; il crema lo mette il materiale. */
const TENDE: readonly Rgb[] = [
  [0.78, 0.18, 0.14],
  [0.16, 0.42, 0.26],
  [0.17, 0.27, 0.52],
]
const INSEGNE = ["Insegna_Bar", "Insegna_Farmacia", "Insegna_Tabacchi"] as const

/** FINESTRA_PIANO di cb_edifici.py: dove sono i cardini delle persiane (u0, u1) e il davanzale (z0). */
const FINESTRA = { u0: 0.55, u1: 1.45, z0: 1.0 }
/** Tapparelle dei palazzoni: in cima a 2,4 m, alte quanto l'apertura; tirate su restano nel muro (al massimo 1,45 m). */
const TAPPARELLA = {
  cima: 2.4,
  su: 1.45,
  alte: {
    Tapparella_Finestra: 1.5,
    Tapparella_Porta: 2.38,
    Tapparella_Piccola: 1.5,
  },
}

const gradi = (g: number) => (g * Math.PI) / 180

/** Le due ante delle persiane: aperte (ruotate di 100-150°, ognuna a modo suo) o chiuse sulla finestra. */
function persiane(rng: Casuale, aperte: boolean): Pezzo[] {
  const a = () => gradi(100 + rng.decimale() * 50)
  return [
    {
      nome: "Persiana",
      y: FINESTRA.z0,
      z: FINESTRA.u0,
      ry: aperte ? a() : 0,
      colore: null,
    },
    {
      nome: "Persiana",
      y: FINESTRA.z0,
      z: FINESTRA.u1,
      ry: aperte ? Math.PI - a() : Math.PI,
      colore: null,
    },
  ]
}

/** Le tapparelle dei palazzoni: `giu` da 0 (tutta su: non si vede) a 1 (tutta giù). */
function tapparella(nome: keyof typeof TAPPARELLA.alte, giu: number): Pezzo[] {
  const h = TAPPARELLA.alte[nome]
  const su = Math.min((1 - giu) * h, TAPPARELLA.su)
  if (su >= h - 0.02) return []
  return [{ nome, y: TAPPARELLA.cima + su, colore: null }]
}
const aCaso = (rng: Casuale) => rng.scegli([0, 0, 0.25, 0.5, 0.7, 1])

/**
 * Casella dell'atlante → pezzi del kit. Il primo pezzo è il modulo di parete (tinto col colore
 * della casa); gli altri sono le aggiunte. Le chiavi sono le caselle MONTABILI.
 */
const CASELLE: Record<string, (rng: Casuale) => Pezzo[]> = {
  // piano terra (borgo, corte, palazzoni)
  Terra_Parete: () => [{ nome: "Terra_Parete" }],
  Terra_Porta: () => [{ nome: "Terra_Porta" }],
  Terra_Porta_Pensilina: () => [
    { nome: "Terra_Porta" },
    { nome: "Pensilina", colore: null },
  ],
  Terra_Vetrina: () => [{ nome: "Terra_Vetrina" }],
  Terra_Vetrina_Tenda: (rng) => [
    { nome: "Terra_Vetrina" },
    { nome: "Tenda", colore: rng.scegli(TENDE) },
  ],
  Terra_Vetrina_Insegna: (rng) => [
    { nome: "Terra_Vetrina" },
    { nome: rng.scegli(INSEGNE), colore: null },
  ],
  Terra_Serranda: () => [{ nome: "Terra_Serranda" }],
  Terra_Portone: () => [{ nome: "Terra_Portone" }],
  // piani del borgo e delle corti
  Piano_Parete: () => [{ nome: "Modulo_Parete" }],
  Piano_Finestra_Aperta: (rng) => [
    { nome: "Modulo_Finestra" },
    ...persiane(rng, true),
  ],
  Piano_Finestra_Chiusa: (rng) => [
    { nome: "Modulo_Finestra" },
    ...persiane(rng, false),
  ],
  Piano_Portafinestra: () => [{ nome: "Modulo_Portafinestra" }],
  Piano_Portafinestra_Balcone: () => [
    { nome: "Modulo_Portafinestra" },
    { nome: "Balcone", colore: null },
  ],
  Corte_Finestra_Aperta: (rng) => [
    { nome: "Modulo_Finestra" },
    { nome: "Cornice_Finestra", colore: STUCCO },
    ...persiane(rng, true),
  ],
  Corte_Finestra_Chiusa: (rng) => [
    { nome: "Modulo_Finestra" },
    { nome: "Cornice_Finestra", colore: STUCCO },
    ...persiane(rng, false),
  ],
  Corte_Portafinestra_Balcone: () => [
    { nome: "Modulo_Portafinestra" },
    { nome: "Cornice_Portafinestra", colore: STUCCO },
    { nome: "Balcone", colore: null },
  ],
  // palazzoni (i balconi a nastro li mette balconiPalazzoni, che guarda le caselle accanto)
  Pal_Finestra_Su: () => [{ nome: "Pal_Finestra" }],
  Pal_Finestra_Meta: () => [
    { nome: "Pal_Finestra" },
    ...tapparella("Tapparella_Finestra", 0.5),
  ],
  Pal_Finestra_Giu: () => [
    { nome: "Pal_Finestra" },
    ...tapparella("Tapparella_Finestra", 1),
  ],
  Pal_Finestra_Balcone: (rng) => [
    { nome: "Pal_Finestra" },
    ...tapparella("Tapparella_Finestra", aCaso(rng)),
  ],
  Pal_Portafinestra_Balcone: (rng) => [
    { nome: "Pal_Portafinestra" },
    ...tapparella("Tapparella_Porta", aCaso(rng)),
    ...tapparella("Tapparella_Piccola", aCaso(rng)),
  ],
  Pal_Portafinestra_Balcone_Chiusa: () => [
    { nome: "Pal_Portafinestra" },
    ...tapparella("Tapparella_Porta", 1),
    ...tapparella("Tapparella_Piccola", 1),
  ],
  Pal_Vano_Scala: () => [{ nome: "Pal_Vano_Scala" }],
  Pal_Testata: () => [{ nome: "Modulo_Parete" }],
  Pal_Terra_Androne: () => [{ nome: "Pal_Terra_Androne" }],
  Fascia_Parapetto_Pal: () => [{ nome: "Pal_Parapetto" }],
  // villette
  Villa_Porta: () => [{ nome: "Villa_Porta" }],
  Villa_Porta_Portico: () => [
    { nome: "Villa_Porta" },
    { nome: "Villa_Portico", colore: null },
  ],
  Villa_Garage: () => [{ nome: "Villa_Garage" }],
  // capannoni (il portone ha la tettoia sopra)
  Cap_Parete: () => [{ nome: "Cap_Parete" }],
  Cap_Parete_Alta: () => [{ nome: "Cap_Parete_Alta" }],
  Cap_Finestrata: () => [{ nome: "Cap_Finestrata" }],
  Cap_Porta: () => [{ nome: "Cap_Porta" }],
  Cap_Portone: () => [
    { nome: "Cap_Portone" },
    { nome: "Cap_Tettoia", colore: null },
  ],
  // grattacieli
  Gr_Nastro: () => [{ nome: "Gr_Nastro" }],
  Gr_Vetrata: () => [{ nome: "Gr_Vetrata" }],
  Gr_Terra_Vetrata: () => [{ nome: "Gr_Terra_Vetrata" }],
  Gr_Coronamento: () => [{ nome: "Gr_Coronamento" }],
}

/** Le fasce che hanno un pezzo nel kit. */
const FASCE: Record<string, string> = {
  Fascia_Marcapiano: "Marcapiano",
  Fascia_Cornicione: "Cornicione",
  Fascia_Cornicione_Corte: "Cornicione_Corte",
  Gr_Coronamento: "Gr_Coronamento",
}

/** Le caselle che il kit sa montare: in gusci.ts sono quelle che si nascondono quando l'edificio è montato. */
export const MONTABILI: ReadonlySet<string> = new Set(Object.keys(CASELLE))
/** Le fasce che il kit sa montare (si nascondono come le caselle). */
export const FASCE_MONTABILI: ReadonlySet<string> = new Set(Object.keys(FASCE))

/** Le caselle dei palazzoni con il balcone a nastro davanti. */
const CON_PAL_BALCONE = new Set([
  "Pal_Finestra_Balcone",
  "Pal_Portafinestra_Balcone",
  "Pal_Portafinestra_Balcone_Chiusa",
])

/**
 * I balconi a nastro dei palazzoni su una riga: un Pal_Balcone per casella, le due testate
 * alle estremità di ogni tratto e, a caso, i divisori fra gli appartamenti (come in cb_edifici.py).
 */
function balconiPalazzoni(
  riga: readonly (string | null)[],
  rng: Casuale,
): Pezzo[] {
  const pezzi: Pezzo[] = []
  let k = 0
  while (k < riga.length) {
    if (!CON_PAL_BALCONE.has(riga[k] ?? "")) {
      k++
      continue
    }
    const inizio = k
    while (k < riga.length && CON_PAL_BALCONE.has(riga[k] ?? "")) {
      pezzi.push({ nome: "Pal_Balcone", z: MODULO * k, colore: "casa" })
      if (k > inizio && rng.probabilita(0.5))
        pezzi.push({ nome: "Pal_Divisorio", z: MODULO * k, colore: "casa" })
      k++
    }
    pezzi.push({
      nome: "Pal_Balcone_Testa",
      z: MODULO * inizio,
      colore: "casa",
    })
    pezzi.push({
      nome: "Pal_Balcone_Testa",
      z: MODULO * k - 0.06,
      colore: "casa",
    })
  }
  return pezzi
}

const tmp = new Matrix4()

/** I pezzi della facciata su strada di un progetto (e dei suoi corpi), con la matrice `m` che lo porta nel mondo. */
function facciata(p: Progetto, m: Matrix4, rng: Casuale, out: Istanza[]) {
  const metti = (q: Pezzo, x: number, y: number, z: number) => {
    const mat = m
      .clone()
      .multiply(
        tmp.makeTranslation(x + (q.x ?? 0), y + (q.y ?? 0), z + (q.z ?? 0)),
      )
    if (q.ry) mat.multiply(tmp.makeRotationY(q.ry))
    if (q.sy || q.sz) mat.multiply(tmp.makeScale(1, q.sy ?? 1, q.sz ?? 1))
    const colore =
      q.colore === undefined || q.colore === "casa" ? p.colore : q.colore
    out.push({ pezzo: q.nome, matrice: mat, colore })
  }

  let y = 0
  p.righe.forEach((h, r) => {
    const riga = p.caselle.Fronte[r] ?? []
    riga.forEach((nome, k) => {
      if (!nome || nome === COPERTA || nome === NASCOSTA) return
      const pezzi = CASELLE[nome]?.(rng)
      if (!pezzi) return
      for (const q of pezzi) metti(q, 0, y, MODULO * k)
      if (!CIECHE.has(nome))
        metti(
          {
            nome: FONDALE,
            x: -FONDO,
            sy: h,
            sz: riquadro(nome).larghezza,
            colore: null,
          },
          0,
          y,
          MODULO * k,
        )
    })
    for (const q of balconiPalazzoni(riga, rng)) metti(q, 0, y, 0)
    y += h
  })
  for (const f of p.fasce) {
    const pezzo = FASCE[f.cella]
    if (!pezzo) continue
    for (let k = 0; k < p.nW; k++)
      metti({ nome: pezzo, colore: f.colore }, 0, f.quota, MODULO * k)
  }
  for (const c of p.corpi ?? [])
    facciata(
      c.progetto,
      m
        .clone()
        .multiply(new Matrix4().makeTranslation(c.x, c.y, c.z))
        .multiply(new Matrix4().makeRotationY(c.rotazione ?? 0)),
      rng,
      out,
    )
}

/** I pezzi del kit di un edificio posato; `seme` lo distingue dagli altri (stesse persiane a ogni rimontaggio). */
export function montaEdificio(
  { progetto, matrice }: EdificioPosato,
  seme: string,
): Istanza[] {
  const out: Istanza[] = []
  facciata(progetto, matrice, new Casuale(seme), out)
  return out
}
