import { Suspense, useEffect, useRef } from 'react';
import { useFrame } from '@react-three/fiber';
import { Text } from '@react-three/drei';
import * as THREE from 'three';

const PANEL_DISTANCE = 6;
const ENTER_DURATION = 0.45;
const EXIT_DURATION = 0.3;

function FrameBar({ position, scale, color = '#00f0ff', opacity = 0.9 }) {
  return (
    <mesh position={position} scale={scale} userData={{ baseOpacity: opacity }}>
      <planeGeometry />
      <meshBasicMaterial
        color={color}
        transparent
        opacity={opacity}
        toneMapped={false}
        depthWrite={false}
        depthTest={false}
      />
    </mesh>
  );
}

export function Hologram({ checkpoint, onDismissed }) {
  const anchor = useRef(null);
  const animated = useRef(null);
  const elapsed = useRef(0);
  const phase = useRef('entering');
  const hovered = useRef(false);

  const dismiss = (event) => {
    event.stopPropagation();
    if (phase.current === 'exiting') return;
    phase.current = 'exiting';
    elapsed.current = 0;
    hovered.current = false;
    document.body.style.cursor = 'auto';
  };

  useEffect(
    () => () => {
      if (hovered.current) document.body.style.cursor = 'auto';
    },
    [],
  );

  useFrame(({ camera, clock }, delta) => {
    if (!anchor.current || !animated.current) return;

    anchor.current.position.copy(camera.position);
    anchor.current.quaternion.copy(camera.quaternion);
    anchor.current.translateZ(-PANEL_DISTANCE);
    anchor.current.translateY(0.25 + Math.sin(clock.elapsedTime * 1.8) * 0.08);

    elapsed.current += delta;
    let visibility = 1;

    if (phase.current === 'entering') {
      visibility = THREE.MathUtils.smoothstep(elapsed.current / ENTER_DURATION, 0, 1);
      if (elapsed.current >= ENTER_DURATION) phase.current = 'visible';
    } else if (phase.current === 'exiting') {
      visibility = 1 - THREE.MathUtils.smoothstep(elapsed.current / EXIT_DURATION, 0, 1);
      if (elapsed.current >= EXIT_DURATION) {
        onDismissed(checkpoint.id);
        return;
      }
    }

    const pulse = 1 + Math.sin(clock.elapsedTime * 2.6) * 0.012;
    const exitShrink = phase.current === 'exiting' ? 0.82 + visibility * 0.18 : 1;
    animated.current.scale.setScalar((0.82 + visibility * 0.18) * pulse * exitShrink);
    animated.current.traverse((object) => {
      if (!object.material || object.userData.baseOpacity === undefined) return;
      object.material.opacity = object.userData.baseOpacity * visibility;
    });
  });

  return (
    <group ref={anchor}>
      <group
        ref={animated}
        renderOrder={10}
        onClick={dismiss}
        onPointerOver={(event) => {
          event.stopPropagation();
          hovered.current = true;
          document.body.style.cursor = 'pointer';
        }}
        onPointerOut={(event) => {
          event.stopPropagation();
          hovered.current = false;
          document.body.style.cursor = 'auto';
        }}
      >
        <mesh position={[0, 0, -0.015]} userData={{ baseOpacity: 0.24 }}>
          <planeGeometry args={[5.4, 2.3]} />
          <meshBasicMaterial
            color="#031923"
            transparent
            opacity={0.24}
            toneMapped={false}
            depthWrite={false}
            depthTest={false}
            side={THREE.DoubleSide}
          />
        </mesh>

        <FrameBar position={[0, 1.14, 0]} scale={[5.55, 0.035, 1]} />
        <FrameBar position={[0, -1.14, 0]} scale={[5.55, 0.035, 1]} />
        <FrameBar position={[-2.76, 0, 0]} scale={[0.035, 2.3, 1]} color="#ff3df2" />
        <FrameBar position={[2.76, 0, 0]} scale={[0.035, 2.3, 1]} color="#ff3df2" />

        {[0.72, 0.36, 0, -0.36, -0.72].map((y, index) => (
          <mesh
            key={y}
            position={[0, y, -0.005]}
            scale={[5.25, 0.012, 1]}
            userData={{ baseOpacity: index % 2 === 0 ? 0.18 : 0.1 }}
          >
            <planeGeometry />
            <meshBasicMaterial
              color="#58f7ff"
              transparent
              opacity={index % 2 === 0 ? 0.18 : 0.1}
              toneMapped={false}
              depthWrite={false}
              depthTest={false}
            />
          </mesh>
        ))}

        <Suspense fallback={null}>
          <Text
            position={[0, 0.2, 0.03]}
            fontSize={0.48}
            maxWidth={4.8}
            textAlign="center"
            letterSpacing={0.08}
            anchorX="center"
            anchorY="middle"
            userData={{ baseOpacity: 1 }}
          >
            {checkpoint.title}
            <meshBasicMaterial
              color="#9cffff"
              transparent
              opacity={1}
              toneMapped={false}
              depthWrite={false}
              depthTest={false}
            />
          </Text>
          {checkpoint.description && (
            <Text
              position={[0, -0.58, 0.03]}
              fontSize={0.18}
              letterSpacing={0.16}
              anchorX="center"
              anchorY="middle"
              userData={{ baseOpacity: 0.82 }}
            >
              {checkpoint.description}
              <meshBasicMaterial
                color="#ff73ef"
                transparent
                opacity={0.82}
                toneMapped={false}
                depthWrite={false}
                depthTest={false}
              />
            </Text>
          )}
        </Suspense>
      </group>
    </group>
  );
}
