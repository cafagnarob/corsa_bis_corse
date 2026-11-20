/*
 * treTessere.ts
 * Sceglie, in una città generata, tre tessere in fila per la prova di guida:
 * una tessera di partenza, una tessera bassa con una rampa e la tessera alta
 * a cui la rampa porta. Funzione pura: stessa città, stesse tre tessere.
 *
 * Come sceglie: scorre le rampe della rete (rete.rampe) e prende la prima
 * che ha anche una strada sul lato opposto della tessera bassa, così si
 * arriva dritti dalla tessera di partenza e si sale. Preferisce i viali
 * (più larghi) e le rampe di un solo strato.
 *
 *   partenza  →  bassa (con la rampa)  →  alta
 *
 * La direzione di partenza segue la convenzione dei lati del GDD: lato 0 =
 * est, poi in senso antiorario visto dall'alto; in Three.js la direzione del
 * lato a è (cos a, −sin a), e un mezzo che guarda +X girato di a attorno a Y
 * guarda proprio lì.
 */

import {
  APOTEMA,
  centroTessera,
  chiave,
  vicina,
  type CittaPopolata,
  type Hex,
  type Lato,
  type Rampa,
  type ReteStradale,
} from "@corsa-bis/engine"

export type TreTessere = {
  /** Partenza, bassa, alta: in quest'ordine. */
  readonly tessere: readonly [Hex, Hex, Hex]
  readonly rampa: Rampa
  /** Punto di partenza (x, z) in unità di gioco: sulla strada verso la rampa. */
  readonly puntoPartenza: { readonly x: number; readonly z: number }
  /** Angolo attorno a Y (radianti) per guardare verso la rampa. */
  readonly direzione: number
}

/** Dove nasce il mezzo, tra il centro (0) e il lato (1) della tessera di partenza. */
const FRAZIONE_PARTENZA = 1 / 3

/** Ordine di preferenza delle rampe: prima i viali, poi i salti di uno strato. */
const PESO_CLASSE = { viale: 0, urbana: 1, stretta: 2 } as const

/** Le tre tessere della prova, o null se la città non ha una rampa adatta. */
export function scegliTreTessere(
  citta: CittaPopolata,
  rete: ReteStradale,
): TreTessere | null {
  const esiste = new Set(citta.tessere.map((t) => chiave(t.hex)))
  const haStrada = (h: Hex, lato: Lato) =>
    (rete.connettori.get(chiave(h))?.[lato] ?? "nessuna") !== "nessuna"

  const candidate = [...rete.rampe].sort(
    (a, b) =>
      PESO_CLASSE[a.classe] - PESO_CLASSE[b.classe] || a.salto - b.salto,
  )

  for (const rampa of candidate) {
    const bassa = rampa.hex
    const alta = vicina(bassa, rampa.lato)
    const opposto = ((rampa.lato + 3) % 6) as Lato
    const partenza = vicina(bassa, opposto)

    if (!esiste.has(chiave(alta)) || !esiste.has(chiave(partenza))) continue
    // Strada dritta: dalla partenza nella bassa, e dalla bassa verso la partenza
    if (!haStrada(bassa, opposto) || !haStrada(partenza, rampa.lato)) continue
    // Niente rotonde: nella bassa la prova vuole un rettilineo, nella
    // partenza il mezzo nascerebbe sull'isola con il monumento
    if (rete.rotonde.has(chiave(bassa)) || rete.rotonde.has(chiave(partenza)))
      continue

    // Si parte a un terzo della strada tra il centro e il lato verso la
    // bassa: lì la strada esce dritta dal lato, anche se al centro curva
    const c = centroTessera(partenza)
    const a = (rampa.lato * Math.PI) / 3
    return {
      tessere: [partenza, bassa, alta],
      rampa,
      puntoPartenza: {
        x: c.x + Math.cos(a) * APOTEMA * FRAZIONE_PARTENZA,
        z: c.z - Math.sin(a) * APOTEMA * FRAZIONE_PARTENZA,
      },
      direzione: a,
    }
  }
  return null
}
