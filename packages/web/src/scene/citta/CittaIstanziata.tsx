/*
 * CittaIstanziata.tsx
 * Disegna tutta la città con poche chiamate di disegno, a partire dai gruppi
 * preparati da raggruppa.ts:
 * - le pile delle tessere (strati e cime) con i pezzi di tessere.glb, in due
 *   livelli di dettaglio: PileTessere;
 * - i gusci degli edifici in cinque chiamate di disegno: Edifici, in un suo
 *   <Suspense> (le texture arrivano a parte);
 * - da vicino (camminata) le facciate su strada montate col kit: KitEdifici,
 *   in un altro <Suspense>; i due si parlano con `montati` (quali gusci
 *   nascondere);
 * - una InstancedMesh per ogni colore di volume (le tessere ancora senza
 *   edifici) e per ogni materiale delle isole;
 * - i monumenti al centro delle rotonde (monumenti.glb): Monumenti;
 * - alberi, cespugli e siepi (vegetazione.glb): Vegetazione;
 * - tre mesh per tutte le strade della città: asfalto (texture asfalto),
 *   marciapiedi (texture cemento) e segni.
 *
 * Qui si scelgono solo geometrie e materiali: posizioni e misure sono già
 * nei gruppi.
 */

import { cilindro, cubo } from "../forme"
import { MATERIALI_ISOLA, MATERIALI_STRADA } from "../strade/materiali"
import { materialeVolume, useMaterialiTessere } from "../tessere/materiali"
import { Suspense, useMemo } from "react"
import Edifici from "../edifici/Edifici"
import KitEdifici from "../edifici/KitEdifici"
import { creaMontati } from "../edifici/montati"
import Istanze from "./Istanze"
import Monumenti from "./Monumenti"
import Vegetazione from "../vegetazione/Vegetazione"
import PileTessere from "./PileTessere"
import type { GruppiCitta } from "./raggruppa"

/** Per le prove: con ?kit=0 nell'indirizzo il kit a piedi non si monta (si vede se gli scatti sono suoi). */
const KIT_ACCESO =
  new URLSearchParams(window.location.search).get("kit") !== "0"

type CittaIstanziataProps = {
  gruppi: GruppiCitta
  /** Il kit a piedi: false alla guida, dove a ogni spostamento costerebbe un rimontaggio (GDD, "kit solo a piedi"). */
  kit?: boolean
}

function CittaIstanziata({ gruppi, kit = true }: CittaIstanziataProps) {
  const materiali = useMaterialiTessere()
  // quali edifici sono montati col kit: lo decide KitEdifici, lo usano i gusci per nascondere le facciate
  const montati = useMemo(() => creaMontati(gruppi.edifici.length), [gruppi])

  return (
    // dispose={null}: geometrie e materiali sono condivisi e restano in memoria
    <group dispose={null}>
      <PileTessere gruppi={gruppi} />
      <Monumenti gruppi={gruppi} />
      <Vegetazione gruppi={gruppi} />
      <Suspense fallback={null}>
        <Edifici gruppi={gruppi} montati={montati} />
      </Suspense>
      {/* a parte: il kit (glb e texture) arriva dopo i gusci e non li fa aspettare */}
      {KIT_ACCESO && kit && (
        <Suspense fallback={null}>
          <KitEdifici edifici={gruppi.edifici} montati={montati} />
        </Suspense>
      )}
      {[...gruppi.volumi].map(([colore, matrici]) => (
        <Istanze
          key={`volume-${colore}`}
          geometria={cubo}
          materiale={materialeVolume(colore)}
          matrici={matrici}
        />
      ))}
      {[...gruppi.isole].map(([materiale, matrici]) => (
        <Istanze
          key={`isola-${materiale}`}
          geometria={cilindro}
          materiale={MATERIALI_ISOLA[materiale]}
          matrici={matrici}
        />
      ))}
      <mesh geometry={gruppi.strade.asfalto} material={materiali.asfalto} />
      <mesh geometry={gruppi.strade.marciapiedi} material={materiali.cemento} />
      <mesh geometry={gruppi.strade.segni} material={MATERIALI_STRADA.segni} />
    </group>
  )
}

export default CittaIstanziata
