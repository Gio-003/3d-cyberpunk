import { useMemo, useRef } from 'react';
import { useFrame } from '@react-three/fiber';

const COUNT = 1500;
const HEIGHT = 30;
// Horizontal drift per meter of fall, so streaks lean slightly with the wind.
const WIND = 0.12;

function randomDrop() {
  const speed = 14 + Math.random() * 20;
  return {
    x: Math.random() * 20 - 10,
    y: Math.random() * HEIGHT,
    z: -80 + Math.random() * 95,
    speed,
    // Faster drops read as longer streaks, like motion blur.
    length: 0.25 + (speed / 34) * 0.55,
  };
}

export function Rain() {
  const lines = useRef(null);
  const drops = useRef(null);

  const positions = useMemo(() => {
    // Each drop is one line segment: a head vertex and a tail vertex.
    const array = new Float32Array(COUNT * 6);
    const state = [];
    for (let i = 0; i < COUNT; i += 1) {
      const drop = randomDrop();
      state.push(drop);
      // Three.js is Y-up. The alley runs toward -Z, so drops are spread
      // across the street (X), along its length (Z), and fall on Y.
      array[i * 6] = drop.x;
      array[i * 6 + 1] = drop.y;
      array[i * 6 + 2] = drop.z;
      array[i * 6 + 3] = drop.x - drop.length * WIND;
      array[i * 6 + 4] = drop.y + drop.length;
      array[i * 6 + 5] = drop.z;
    }
    drops.current = state;
    return array;
  }, []);

  useFrame((_, delta) => {
    const attribute = lines.current?.geometry?.attributes?.position;
    const state = drops.current;
    if (!attribute || !state) return;

    const array = attribute.array;
    for (let i = 0; i < COUNT; i += 1) {
      const drop = state[i];
      const fall = delta * drop.speed;
      drop.y -= fall;
      drop.x += fall * WIND;

      if (drop.y < 0) {
        const fresh = randomDrop();
        fresh.y = HEIGHT + Math.random() * 6;
        state[i] = fresh;
      }

      const current = state[i];
      array[i * 6] = current.x;
      array[i * 6 + 1] = current.y;
      array[i * 6 + 2] = current.z;
      array[i * 6 + 3] = current.x - current.length * WIND;
      array[i * 6 + 4] = current.y + current.length;
      array[i * 6 + 5] = current.z;
    }
    attribute.needsUpdate = true;
  });

  return (
    <lineSegments ref={lines} frustumCulled={false}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[positions, 3]} />
      </bufferGeometry>
      <lineBasicMaterial color="#a8d4ff" transparent opacity={0.35} depthWrite={false} />
    </lineSegments>
  );
}
