import { Canvas } from '@react-three/fiber';
import { OrbitControls, Float } from '@react-three/drei';
import { EffectComposer, Bloom } from '@react-three/postprocessing';
import { TestCube } from './TestCube';

export function Scene() {
  return (
    <Canvas camera={{ position: [0, 0, 5], fov: 60 }}>
      <color attach="background" args={['#050508']} />

      <ambientLight intensity={0.8} />
      <pointLight position={[2, 2, 2]} intensity={18} color="#00f0ff" />
      <pointLight position={[-2, -1, 2]} intensity={10} color="#6dffb8" />

      <Float speed={1.6} rotationIntensity={0.8} floatIntensity={1.3}>
        <TestCube />
      </Float>

      <OrbitControls
        enableDamping
        dampingFactor={0.08}
        minDistance={3}
        maxDistance={8}
        enablePan={false}
      />

      <EffectComposer>
        <Bloom luminanceThreshold={0.2} mipmapBlur intensity={1.5} />
      </EffectComposer>
    </Canvas>
  );
}
