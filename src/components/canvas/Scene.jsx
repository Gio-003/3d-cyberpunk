import { Suspense } from 'react';
import { Canvas } from '@react-three/fiber';
import { ScrollControls } from '@react-three/drei';
import { EffectComposer, Bloom } from '@react-three/postprocessing';
import { Street } from './Street';
import { Rain } from './Rain';
import { CameraRig } from './CameraRig';
import { CanvasLoader } from '../ui/Loader';

export function Scene() {
  return (
    <Canvas camera={{ position: [0, 4, 6], fov: 60 }} style={{ width: '100%', height: '100%' }}>
      <color attach="background" args={['#010204']} />
      <fog attach="fog" args={['#010204', 10, 80]} />

      <ambientLight intensity={0.25} color="#1a2a48" />
      <directionalLight position={[14, 28, 10]} intensity={1.2} color="#b7c9e6" />

      <ScrollControls pages={5} damping={0.2}>
        <Suspense fallback={<CanvasLoader />}>
          <Street />
        </Suspense>
        <Rain />
        <CameraRig />
      </ScrollControls>

      <EffectComposer>
        <Bloom luminanceThreshold={1} mipmapBlur intensity={2.0} />
      </EffectComposer>
    </Canvas>
  );
}
