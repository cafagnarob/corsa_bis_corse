/*
 * clipVeicolo.ts
 * Dai valori del controller di Rapier al tempo delle clip "slider" dei mezzi
 * (GDD, "Formato dell'export"). Funzioni pure, separate dal componente
 * ModelloVeicolo così si testano da sole (e il file del componente esporta
 * solo il componente, come chiede il Fast Refresh di Vite).
 *
 * Le clip esportate da Blender vanno a 24 fotogrammi al secondo e partono
 * dal fotogramma 1:
 * - Ruota: fotogrammi 1-25 = un giro completo;
 * - Sterzo: fotogramma 1 = −35°, 2 = dritto, 3 = +35° (positivo = sinistra,
 *   la stessa convenzione di Rapier).
 */

/** Fotogrammi al secondo delle clip esportate da Blender. */
export const FPS_CLIP = 24

/** Angolo di sterzo ai fotogrammi 1 e 3 della clip Sterzo, in gradi. */
export const STERZO_CLIP = 35

/** Tempo della clip Ruota per una rotazione in radianti (un giro = fotogrammi 1-25). */
export function tempoRuota(rotazione: number): number {
  const giri = rotazione / (2 * Math.PI)
  const frazione = giri - Math.floor(giri) // 0..1, anche per rotazioni negative
  return (1 + frazione * 24) / FPS_CLIP
}

/** Tempo della clip Sterzo per un angolo in radianti (+ = sinistra), limitato a ±35°. */
export function tempoSterzo(angolo: number): number {
  const gradi = Math.max(
    -STERZO_CLIP,
    Math.min(STERZO_CLIP, (angolo * 180) / Math.PI),
  )
  return (2 + gradi / STERZO_CLIP) / FPS_CLIP // fotogramma 2 = dritto, 1 e 3 ai lati
}
