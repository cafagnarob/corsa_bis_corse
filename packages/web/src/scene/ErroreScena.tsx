/*
 * ErroreScena.tsx
 * "Error boundary" attorno alla scena 3D: se qualcosa dentro si rompe (un
 * .glb che manca, uno shader che non compila, un errore nel codice di un
 * componente), invece della pagina bianca compare un messaggio con l'errore
 * e due pulsanti: "Riprova" (rimonta la scena) e "Ricarica la pagina".
 *
 * Perché una classe: in React solo un componente a classe può fare da error
 * boundary (getDerivedStateFromError e componentDidCatch non esistono per le
 * funzioni). React Three Fiber passa al genitore gli errori nati dentro il
 * Canvas, quindi basta avvolgere il Canvas.
 *
 * Non cattura gli errori negli handler degli eventi (onClick...) né nel
 * codice asincrono: quelli non rompono il disegno, si vedono in console.
 */

import {
  Component,
  type CSSProperties,
  type ErrorInfo,
  type ReactNode,
} from "react"

const stile: Record<string, CSSProperties> = {
  fondo: {
    position: "fixed",
    inset: 0,
    display: "grid",
    placeItems: "center",
    padding: 16,
    background: "#2b4442",
    color: "#f3eee4",
    font: "15px/1.5 system-ui, sans-serif",
  },
  riquadro: {
    maxWidth: 560,
    width: "100%",
    padding: 20,
    borderRadius: 10,
    background: "rgba(20, 30, 28, 0.9)",
  },
  dettaglio: {
    whiteSpace: "pre-wrap",
    wordBreak: "break-word",
    font: "12px/1.5 ui-monospace, monospace",
    color: "#ffb4a8",
  },
  pulsanti: { display: "flex", flexWrap: "wrap", gap: 8, marginTop: 12 },
  bottone: {
    minHeight: 36,
    padding: "6px 14px",
    borderRadius: 6,
    border: "none",
    cursor: "pointer",
  },
}

type ErroreScenaProps = { children: ReactNode }
type ErroreScenaStato = { errore: Error | null }

class ErroreScena extends Component<ErroreScenaProps, ErroreScenaStato> {
  state: ErroreScenaStato = { errore: null }

  /** Un figlio ha lanciato un errore: al prossimo disegno si mostra il messaggio. */
  static getDerivedStateFromError(errore: Error): ErroreScenaStato {
    return { errore }
  }

  /** Per chi sviluppa: l'errore completo e dove è nato, in console. */
  componentDidCatch(errore: Error, info: ErrorInfo) {
    console.error("La scena 3D si è interrotta:", errore, info.componentStack)
  }

  render() {
    const { errore } = this.state
    if (!errore) return this.props.children
    return (
      <div style={stile.fondo} role="alert">
        <div style={stile.riquadro}>
          <h2 style={{ margin: "0 0 8px" }}>La scena 3D si è interrotta</h2>
          <p style={{ margin: "0 0 8px" }}>
            Qualcosa non si è caricato o è andato storto. Il dettaglio:
          </p>
          <div style={stile.dettaglio}>{errore.message}</div>
          <div style={stile.pulsanti}>
            {/* rimonta la scena: va bene se l'errore era passeggero */}
            <button
              type="button"
              style={stile.bottone}
              onClick={() => this.setState({ errore: null })}
            >
              Riprova
            </button>
            {/* un .glb che non si carica resta in cache come errore: serve ricaricare */}
            <button
              type="button"
              style={stile.bottone}
              onClick={() => window.location.reload()}
            >
              Ricarica la pagina
            </button>
          </div>
        </div>
      </div>
    )
  }
}

export default ErroreScena
