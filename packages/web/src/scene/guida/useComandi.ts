/*
 * useComandi.ts
 * Hook che ascolta la tastiera e tiene i comandi di guida aggiornati in un
 * ref. Il veicolo lo legge a ogni passo fisico.
 *
 * Perché un ref e non lo stato React: i comandi cambiano molte volte al
 * secondo e servono dentro il ciclo della fisica, non nell'interfaccia.
 * Con useState ogni tasto farebbe ridisegnare il componente; con un ref il
 * valore cambia e basta, e chi lo legge (useFrame, passo fisico) trova sempre
 * quello più recente.
 *
 * Perché qui useEffect è giusto: la tastiera è un evento del browser fuori
 * da React (window), e va ascoltata finché il componente esiste e poi
 * staccata. È esattamente il caso per cui useEffect esiste.
 *
 * Dettagli:
 * - si tiene l'insieme dei tasti premuti e si ricalcolano i comandi a ogni
 *   pressione o rilascio (comandiDaiTasti, in comandi.ts);
 * - le frecce e la barra spaziatrice non fanno scorrere la pagina;
 * - se la finestra perde il fuoco (alt+tab) i tasti vengono rilasciati
 *   tutti: altrimenti il mezzo continuerebbe ad accelerare da solo, perché
 *   il keyup arriva a un'altra finestra.
 */

import { useEffect, useRef, type RefObject } from "react"

import {
  COMANDI_FERMI,
  TASTI_DI_GUIDA,
  comandiDaiTasti,
  type Comandi,
} from "./comandi"

export function useComandi(): RefObject<Comandi> {
  const comandi = useRef<Comandi>(COMANDI_FERMI)

  useEffect(() => {
    const premuti = new Set<string>()

    const aggiorna = () => {
      comandi.current = comandiDaiTasti(premuti)
    }

    const giu = (e: KeyboardEvent) => {
      if (!TASTI_DI_GUIDA.has(e.code)) return
      e.preventDefault() // niente scorrimento della pagina
      if (e.repeat) return // tasto tenuto premuto: già nell'insieme
      premuti.add(e.code)
      aggiorna()
    }

    const su = (e: KeyboardEvent) => {
      if (!premuti.delete(e.code)) return
      aggiorna()
    }

    const rilasciaTutto = () => {
      premuti.clear()
      aggiorna()
    }

    window.addEventListener("keydown", giu)
    window.addEventListener("keyup", su)
    window.addEventListener("blur", rilasciaTutto)

    // Pulizia: quando il componente sparisce si staccano gli ascoltatori
    return () => {
      window.removeEventListener("keydown", giu)
      window.removeEventListener("keyup", su)
      window.removeEventListener("blur", rilasciaTutto)
    }
  }, [])

  return comandi
}
