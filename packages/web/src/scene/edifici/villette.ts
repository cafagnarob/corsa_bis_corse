/*
 * villette.ts
 * Le villette dei quartieri residenziali, dal seme: le regole di villetta()
 * in cb_edifici.py, ridotte a quello che serve al guscio.
 *
 * - 3-5 moduli di facciata, profonde 3-4, uno o due livelli da 3 m (niente
 *   piano terra alto 4 m: sono case, non palazzi), un colore vivace;
 * - la porta in una colonna a caso; nelle case larghe a volte il garage
 *   nell'ultima colonna a sinistra; le altre colonne finestre con le
 *   persiane (aperte nove volte su dieci);
 * - al secondo livello, una volta su tre e mezza, la portafinestra con il
 *   balcone sopra la porta (fa da portico); altrimenti la porta ha il
 *   portichetto di coppi (nell'atlante è il riquadro Villa_Porta_Portico);
 * - sui fianchi finestre al 60%, sul retro la porta in mezzo;
 * - tetto a capanna di coppi a 28° con il colmo parallelo alla strada,
 *   gronda di 35 cm, testate a triangolo nel colore della casa, cornicione
 *   bianco;
 * - il LOTTO: giardino davanti di 3-5 m, 1,5-3 m sui fianchi, 3 m dietro (un
 *   po' meno che in Blender, per farne stare di più nella tessera);
 *   tutto attorno il muretto (bianco o del colore della casa) col varco del
 *   cancello in asse con la porta.
 * Il corpo principale del progetto è la casa; il recinto sta nelle sue
 * coordinate (davanti = x positive, fianco destro = z negative).
 * La ringhiera sopra il muretto, il cancello di legno, il vialetto, il
 * comignolo e l'antenna sono pezzi del kit: arriveranno con la vista a piedi.
 */

import type { Casuale } from "@corsa-bis/engine"
import { BIANCO, INTONACI_VILLE } from "./colori"
import { H_PIANO, MODULO, T, type Parete, type Progetto } from "./progetto"

/** TETTO_V e GRONDA di cb_edifici.py. */
const TETTO = {
  pendenza: (28 * Math.PI) / 180,
  gronda: 0.35,
  materiale: "coppi",
  fianchi: 0.15,
} as const
/** Il muretto della recinzione (senza la ringhiera del kit). */
const MURETTO = { altezza: 0.5, spessore: 0.2 }
/** Giardino dietro la casa (m). */
const DIETRO = 3

export function generaVilletta(rng: Casuale): Progetto {
  const nW = rng.intero(3, 5)
  const nD = rng.scegli([3, 4])
  const livelli = rng.scegli([1, 2, 2])
  const colore = INTONACI_VILLE[rng.scegli(Object.keys(INTONACI_VILLE))]
  const garage = nW >= 4 && rng.probabilita(0.5)
  // colonna della porta (contata da destra, vista dalla strada); il garage è l'ultima a sinistra
  const kd = rng.intero(garage ? 1 : 0, garage ? nW - 2 : nW - 1)
  const balcone = livelli === 2 && rng.probabilita(0.6)
  const finestra = () =>
    rng.probabilita(0.1) ? "Piano_Finestra_Chiusa" : "Piano_Finestra_Aperta"

  const fronte: (string | null)[][] = [
    Array.from({ length: nW }, (_, k) =>
      garage && k === nW - 1
        ? "Villa_Garage"
        : k === kd
          ? balcone
            ? "Villa_Porta"
            : "Villa_Porta_Portico"
          : finestra(),
    ),
  ]
  if (livelli === 2)
    fronte.push(
      Array.from({ length: nW }, (_, k) =>
        balcone && k === kd ? "Piano_Portafinestra_Balcone" : finestra(),
      ),
    )

  const altra = (parete: Parete, n: number) =>
    Array.from({ length: livelli }, (_, li) =>
      Array.from({ length: n }, (_, k) =>
        parete === "Retro"
          ? li === 0 && k === Math.floor(n / 2)
            ? "Villa_Porta"
            : finestra()
          : rng.probabilita(0.6)
            ? finestra()
            : "Piano_Parete",
      ),
    )

  const W = nW * MODULO
  const H = H_PIANO * livelli
  // il lotto attorno alla casa: un po' più stretto che in villetta() (fianchi 2-4, davanti 4-6, dietro 4),
  // perché una tessera è larga 66 m e con i lotti di Blender ci stavano 3-5 villette
  const fianchi = rng.scegli([1.5, 2, 3])
  const davanti = rng.scegli([3, 4, 5])
  const coloreMuretto = rng.probabilita(0.5) ? colore : BIANCO

  return {
    famiglia: "villetta",
    nW,
    nD,
    righe: Array.from({ length: livelli }, () => H_PIANO),
    caselle: {
      Fronte: fronte,
      Destra: altra("Destra", nD),
      Sinistra: altra("Sinistra", nD),
      Retro: altra("Retro", nW),
    },
    colore,
    fasce: [{ cella: "Fascia_Cornicione", quota: H - 0.3, colore: BIANCO }],
    tetto: { tipo: "capanna", ...TETTO },
    scatole: [],
    recinto: {
      x0: -(nD * MODULO + 2 * T) - DIETRO,
      x1: davanti,
      z0: -fianchi,
      z1: W + fianchi,
      ...MURETTO,
      colore: coloreMuretto,
      cancello: { z: MODULO * kd + MODULO / 2, larghezza: 1.6 },
    },
  }
}
