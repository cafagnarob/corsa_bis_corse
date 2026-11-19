/*
 * atlante.ts
 * I riquadri degli atlanti di facciata dei gusci, esportati da
 * cb_atlante_edifici.py: per ogni modulo del kit visto di fronte, il
 * rettangolo UV [u0, v0, u1, v1] (v dal basso, come in Blender), le misure
 * in metri e la PAGINA dell'atlante in cui sta:
 * - pagina 0 = facciate.json (+ facciate_colore.jpg / facciate_maschera.jpg):
 *   borgo, palazzoni, villette;
 * - pagina 1 = facciate_industria.json (+ facciate_industria_colore.jpg /
 *   _maschera.jpg): capannoni e grattacieli.
 * Ogni pagina è una texture diversa, quindi una geometria (e una chiamata
 * di disegno) a sé in gusci.ts. I nomi non si ripetono tra le pagine.
 */

import borgo from "./facciate.json"
import industria from "./facciate_industria.json"

export type Pagina = 0 | 1
export const PAGINE: readonly Pagina[] = [0, 1]

export type Riquadro = {
  readonly uv: readonly [number, number, number, number]
  readonly larghezza: number
  readonly altezza: number
  readonly pagina: Pagina
}

type Celle = Record<
  string,
  { uv: number[]; larghezza_m: number; altezza_m: number }
>

const leggi = (celle: Celle, pagina: Pagina) =>
  Object.entries(celle).map(
    ([nome, c]) =>
      [
        nome,
        {
          uv: [c.uv[0], c.uv[1], c.uv[2], c.uv[3]] as const,
          larghezza: c.larghezza_m,
          altezza: c.altezza_m,
          pagina,
        },
      ] as const,
  )

export const RIQUADRI: ReadonlyMap<string, Riquadro> = new Map([
  ...leggi(borgo.celle as Celle, 0),
  ...leggi(industria.celle as Celle, 1),
])

/** Il riquadro di un modulo; un nome che manca è un errore del generatore. */
export function riquadro(nome: string): Riquadro {
  const r = RIQUADRI.get(nome)
  if (!r)
    throw new Error(
      `riquadro ${nome} non trovato negli atlanti (facciate.json, facciate_industria.json)`,
    )
  return r
}
