/*
 * ScenaProvaGuida.tsx
 * Scena di prova della Fase 1 del GDD: qui si renderà divertente guidare
 * l'utilitaria, prima di metterla nella città.
 *
 * Per ora contiene solo un pavimento piatto delle misure di una tessera
 * (circa 400 × 400 unità) e OrbitControls per guardarlo. Nel passo 1 qui
 * arrivano la fisica (Rapier), il veicolo e la telecamera in terza persona;
 * poi tre tessere con una rampa.
 *
 * Non importa niente da datiCitta.ts: la città non viene generata.
 */

import { OrbitControls } from "@react-three/drei"

import Palcoscenico from "../Palcoscenico"

function ScenaProvaGuida() {
  return (
    <Palcoscenico telecamera={{ posizione: [0, 120, 260], fov: 50, vicino: 1 }}>
      {/*
        Pavimento provvisorio: un piano orizzontale.
        Il piano di Three.js nasce in verticale (XY), quindi lo ruotiamo di
        -90° attorno a X per stenderlo sul tavolo (XZ).
      */}
      <mesh rotation={[-Math.PI / 2, 0, 0]}>
        <planeGeometry args={[400, 400]} />
        <meshStandardMaterial color="#8a9a7b" />
      </mesh>

      <OrbitControls makeDefault maxPolarAngle={Math.PI / 2 - 0.05} />
    </Palcoscenico>
  )
}

export default ScenaProvaGuida
