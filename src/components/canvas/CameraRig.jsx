import { useFrame } from '@react-three/fiber';
import { useScroll } from '@react-three/drei';
import * as THREE from 'three';

// The glTF street runs toward -Z. Y is eye height, not the length of the alley.
const EYE_HEIGHT = 4;
const START_Z = 6;
const END_Z = -62;
const LOOK_AHEAD = 10;

export function CameraRig() {
  const scroll = useScroll();

  useFrame((state, delta) => {
    const targetZ = THREE.MathUtils.lerp(START_Z, END_Z, scroll.offset);

    state.camera.position.x = 0;
    state.camera.position.y = EYE_HEIGHT;
    state.camera.position.z = THREE.MathUtils.damp(
      state.camera.position.z,
      targetZ,
      3,
      delta,
    );
    state.camera.lookAt(0, EYE_HEIGHT, state.camera.position.z - LOOK_AHEAD);
  });

  return null;
}
