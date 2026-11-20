/*
 * LineaGara.tsx
 * La mezzeria del giro disegnata sulla strada: una linea sottile appena
 * sopra l'asfalto, chiusa, così si vede dove va il circuito. Provvisoria:
 * arriveranno transenne, frecce e cartelli di cartone.
 *
 * Line di drei disegna linee con uno spessore in pixel (lineWidth), che
 * resta uguale a ogni distanza: le linee normali di WebGL sono larghe 1 px.
 */

import { Line } from "@react-three/drei"

type LineaGaraProps = {
  readonly punti: readonly [number, number, number][]
}

function LineaGara({ punti }: LineaGaraProps) {
  // Si ripete il primo punto in fondo per chiudere il giro
  return <Line points={[...punti, punti[0]]} color="#ffd34d" lineWidth={3} />
}

export default LineaGara
