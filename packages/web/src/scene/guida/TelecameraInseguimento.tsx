/*
 * TelecameraInseguimento.tsx
 * Telecamera in terza persona: sta dietro e sopra il mezzo, lo segue con un
 * leggero ritardo e si allontana un po' quando va forte.
 *
 * Come funziona, a ogni fotogramma:
 * 1. legge posizione e direzione del gruppo seguito (quello disegnato, già
 *    interpolato dalla fisica, così telecamera e mezzo non tremano);
 * 2. calcola dove dovrebbe stare la telecamera: dietro il mezzo lungo la sua
 *    direzione orizzontale (se il mezzo salta o si inclina la telecamera non
 *    si capovolge), alla distanza e all'altezza scelte;
 * 3. ci si avvicina con uno smorzamento esponenziale: ogni fotogramma copre
 *    una parte della distanza che manca. Con 1 − e^(−rapidità × dt) il
 *    risultato è lo stesso a 30, 60 o 144 fotogrammi al secondo;
 * 4. guarda un punto un po' davanti al mezzo, smorzato allo stesso modo;
 * 5. allarga il campo visivo con la velocità: dà la sensazione di correre.
 *
 * Va messo DENTRO <Physics>: così gira dopo che la fisica ha aggiornato le
 * posizioni disegnate, e insegue il fotogramma giusto.
 *
 * Nessuno stato React: i vettori di lavoro sono creati una volta sola e
 * riusati, per non creare oggetti nuovi 60 volte al secondo.
 *
 * Nota sul linter (React Compiler): la telecamera si prende dallo stato che
 * useFrame passa alla funzione, non da useThree. Un valore restituito da un
 * hook è considerato "di React" e non si può modificare; l'oggetto ricevuto
 * da useFrame invece è fatto apposta per essere mosso a ogni fotogramma.
 */

import { useRef, type RefObject } from "react"
import { useFrame } from "@react-three/fiber"
import { PerspectiveCamera, Quaternion, Vector3, type Group } from "three"

import { SCALA, kmhInUnita } from "./parametri"

/* ------------------------------------------------------------------------
 * Regolazioni (metri reali e gradi; valori da tarare guidando)
 * --------------------------------------------------------------------- */

const DIETRO = 6.5 // distanza dietro il mezzo, da fermo
const DIETRO_IN_PIU = 2.5 // distanza aggiunta alla velocità di riferimento
const SOPRA = 2.4 // altezza sopra il mezzo
const GUARDA_AVANTI = 4 // il punto guardato sta davanti al mezzo
const GUARDA_SOPRA = 1 // e un po' sopra
const RAPIDITA_POSIZIONE = 6 // più alto = segue più stretto
const RAPIDITA_SGUARDO = 10
const FOV_FERMO = 55 // gradi
const FOV_IN_PIU = 12 // gradi aggiunti alla velocità di riferimento
const VELOCITA_RIFERIMENTO = kmhInUnita(140) // dove distanza e FOV arrivano al massimo

type TelecameraInseguimentoProps = {
  /** Il gruppo da seguire: il mezzo disegnato. */
  readonly seguitoRef: RefObject<Group | null>
}

function TelecameraInseguimento({ seguitoRef }: TelecameraInseguimentoProps) {
  // Vettori di lavoro, creati una volta
  const lavoro = useRef({
    posizione: new Vector3(),
    rotazione: new Quaternion(),
    avanti: new Vector3(),
    voluta: new Vector3(),
    sguardo: new Vector3(),
    sguardoVoluto: new Vector3(),
    precedente: new Vector3(),
    velocita: 0, // unità al secondo, smorzata
    primo: true,
  })

  // La telecamera si prende dallo stato di useFrame: è l'oggetto di Three.js
  // da muovere a ogni fotogramma, non un valore di React
  useFrame(({ camera }, delta) => {
    const g = seguitoRef.current
    if (!g || delta <= 0) return
    const w = lavoro.current

    // 1. Posizione e direzione del mezzo
    g.getWorldPosition(w.posizione)
    g.getWorldQuaternion(w.rotazione)
    w.avanti.set(1, 0, 0).applyQuaternion(w.rotazione) // il davanti dei modelli è +X
    w.avanti.y = 0
    if (w.avanti.lengthSq() < 1e-6) w.avanti.set(1, 0, 0) // mezzo in verticale: si tiene X
    w.avanti.normalize()

    // Velocità stimata dallo spostamento tra due fotogrammi, smorzata
    const istantanea = w.primo
      ? 0
      : w.posizione.distanceTo(w.precedente) / delta
    w.velocita += (istantanea - w.velocita) * (1 - Math.exp(-5 * delta))
    w.precedente.copy(w.posizione)
    const quota = Math.min(1, w.velocita / VELOCITA_RIFERIMENTO)

    // 2. Dove dovrebbe stare la telecamera, e quale punto dovrebbe guardare
    const dietro = (DIETRO + DIETRO_IN_PIU * quota) * SCALA
    w.voluta
      .copy(w.posizione)
      .addScaledVector(w.avanti, -dietro)
      .setY(w.posizione.y + SOPRA * SCALA)

    //    (il punto guardato)
    w.sguardoVoluto
      .copy(w.posizione)
      .addScaledVector(w.avanti, GUARDA_AVANTI * SCALA)
      .setY(w.posizione.y + GUARDA_SOPRA * SCALA)

    // 3 e 4. Avvicinamento smorzato (al primo fotogramma si salta direttamente lì)
    if (w.primo) {
      camera.position.copy(w.voluta)
      w.sguardo.copy(w.sguardoVoluto)
      w.primo = false
    } else {
      camera.position.lerp(w.voluta, 1 - Math.exp(-RAPIDITA_POSIZIONE * delta))
      w.sguardo.lerp(w.sguardoVoluto, 1 - Math.exp(-RAPIDITA_SGUARDO * delta))
    }
    camera.lookAt(w.sguardo)

    // 5. Campo visivo che si allarga con la velocità
    if (camera instanceof PerspectiveCamera) {
      camera.fov = FOV_FERMO + FOV_IN_PIU * quota
      camera.updateProjectionMatrix()
    }
  })

  return null // non disegna niente: muove la telecamera della scena
}

export default TelecameraInseguimento
