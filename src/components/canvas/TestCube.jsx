import { useRef } from 'react';
import { useFrame } from '@react-three/fiber';

export function TestCube() {
  const meshRef = useRef();

  useFrame((state, delta) => {
    if (!meshRef.current) return;

    meshRef.current.rotation.x += delta * 0.65;
    meshRef.current.rotation.y += delta * 0.8;
    meshRef.current.rotation.z += delta * 0.45;
  });

  return (
    <mesh ref={meshRef} position={[0, 0, 0]}>
      <boxGeometry args={[1.5, 1.5, 1.5]} />
      <meshStandardMaterial
        color="#00f0ff"
        emissive="#00f0ff"
        emissiveIntensity={1.6}
        metalness={0.4}
        roughness={0.25}
      />
    </mesh>
  );
}
