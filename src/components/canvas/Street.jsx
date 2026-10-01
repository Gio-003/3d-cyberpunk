import { Suspense, useEffect, useMemo } from 'react';
import { useThree } from '@react-three/fiber';
import { Text, useGLTF, useTexture } from '@react-three/drei';
import * as THREE from 'three';
import { useJourneyProgress } from '../holograms/HologramSystem';

const STREET_MODEL = '/models/cyber_street.glb';
const MOTOR_MODEL = '/models/motor.glb';
// One image per panel, in Billboard_* name order. Add a file here to give
// the next panel its own texture.
const BILLBOARD_TEXTURES = [
  '/textures/billboards/01-helmet.png',
  '/textures/billboards/02-shoulders.png',
  '/textures/billboards/03-peace.png',
  '/textures/billboards/04-sword.png',
  '/textures/billboards/05-torso.png',
  '/textures/billboards/06-cables-left.png',
  '/textures/billboards/07-cables-right.png',
  '/textures/billboards/08-boots.png',
  '/textures/billboards/09-reflection.png',
  '/textures/billboards/10-circle.png',
];

function neonColor(name) {
  let hash = 0;
  for (let i = 0; i < name.length; i += 1) hash += name.charCodeAt(i);
  return hash % 2 === 0 ? '#00ffff' : '#ff00ff';
}

function makeWetMaterial(color) {
  return new THREE.MeshStandardMaterial({
    color,
    roughness: 0.6,
    metalness: 0.2,
  });
}

const BUILDING_COLORS = [
  '#505b70', // cold slate
  '#455e62', // muted teal
  '#63505f', // dusty magenta
  '#5c604d', // industrial olive
  '#4e4965', // violet concrete
  '#53616b', // blue steel
];

function buildingColor(name) {
  let hash = 0;
  for (let i = 0; i < name.length; i += 1) {
    hash = (hash * 31 + name.charCodeAt(i)) >>> 0;
  }
  return BUILDING_COLORS[hash % BUILDING_COLORS.length];
}

function isExitSign(object) {
  let node = object;
  while (node) {
    const name = node.name || '';
    if (name === 'Interactive_Exit_Sign' || name.includes('SignBoard_EXIT')) return true;
    node = node.parent;
  }
  return false;
}

function makeBillboardMaterial(source, mesh) {
  const texture = source.clone();
  // glTF UVs have V pointing down; textures loaded outside GLTFLoader must match.
  texture.flipY = false;
  texture.colorSpace = THREE.SRGBColorSpace;

  // Crop like CSS object-fit: cover. Panels are thin along X, wide along Z, tall along Y.
  mesh.geometry.computeBoundingBox();
  const size = new THREE.Vector3();
  mesh.geometry.boundingBox.getSize(size);
  const panelAspect = size.z / size.y;
  const imageAspect = source.image.width / source.image.height;
  if (panelAspect > imageAspect) {
    texture.repeat.set(1, imageAspect / panelAspect);
  } else {
    texture.repeat.set(panelAspect / imageAspect, 1);
  }
  texture.offset.set((1 - texture.repeat.x) / 2, (1 - texture.repeat.y) / 2);
  texture.needsUpdate = true;

  return new THREE.MeshBasicMaterial({ map: texture, toneMapped: false });
}

// The street has no environment map, so glossy paint has nothing to reflect.
// A tiny private room of neon panels gives the bike its own reflections
// without brightening the rest of the scene.
function useNeonReflections() {
  const gl = useThree((state) => state.gl);
  const envMap = useMemo(() => {
    const room = new THREE.Scene();
    room.background = new THREE.Color('#020308');
    const panel = new THREE.PlaneGeometry(1, 1);
    const panels = [
      { color: [0, 4, 4], position: [-4, 2, 0], rotation: [0, Math.PI / 2, 0], size: [6, 1.5] },
      { color: [4, 0, 4], position: [4, 1, 0], rotation: [0, -Math.PI / 2, 0], size: [6, 1.5] },
      { color: [3, 3, 3.5], position: [0, 5, 0], rotation: [Math.PI / 2, 0, 0], size: [2, 8] },
      { color: [0, 2, 3], position: [0, 1, -5], rotation: [0, 0, 0], size: [4, 1] },
    ];
    panels.forEach(({ color, position, rotation, size }) => {
      const mesh = new THREE.Mesh(
        panel,
        new THREE.MeshBasicMaterial({ color: new THREE.Color(...color), side: THREE.DoubleSide }),
      );
      mesh.position.set(...position);
      mesh.rotation.set(...rotation);
      mesh.scale.set(size[0], size[1], 1);
      room.add(mesh);
    });
    const pmrem = new THREE.PMREMGenerator(gl);
    const target = pmrem.fromScene(room, 0.03);
    pmrem.dispose();
    room.traverse((child) => child.material?.dispose());
    panel.dispose();
    return target;
  }, [gl]);
  useEffect(() => () => envMap.dispose(), [envMap]);
  return envMap.texture;
}

const MOTOR_PAINT = {
  Paint_Turquoise: { color: '#13c4b4', metalness: 0.55, roughness: 0.16, clearcoat: 1 },
  Paint_Deep_Teal: { color: '#0d6f78', metalness: 0.55, roughness: 0.2, clearcoat: 1 },
  Structure_Black: { color: '#1b2026', metalness: 0.7, roughness: 0.22, clearcoat: 0.6 },
  Machined_Metal: { color: '#9aa7ad', metalness: 1, roughness: 0.14 },
  Fork_Gold: { color: '#d88a1c', metalness: 1, roughness: 0.15 },
  Seat_Vinyl: { color: '#14191c', metalness: 0, roughness: 0.35, clearcoat: 0.4 },
  Tire_Rubber: { color: '#0b0c0d', metalness: 0, roughness: 0.55 },
};
const MOTOR_RIMS = ['Front_Wheel_Rim', 'Rear_Wheel_Rim'];

function NeonStrip({ position, size, color }) {
  return (
    <mesh position={position} raycast={() => null}>
      <boxGeometry args={size} />
      <meshBasicMaterial color={color} toneMapped={false} />
    </mesh>
  );
}

function Motorcycle() {
  const { scene } = useGLTF(MOTOR_MODEL);
  const motor = useMemo(() => scene.clone(), [scene]);
  const envMap = useNeonReflections();

  useEffect(() => {
    const created = [];
    motor.traverse((child) => {
      if (!child.isMesh) return;
      let material;
      if (MOTOR_RIMS.includes(child.name)) {
        material = new THREE.MeshStandardMaterial({
          color: '#0a2a2a',
          emissive: '#00ffff',
          emissiveIntensity: 4,
        });
      } else {
        const paint = MOTOR_PAINT[child.material.name];
        if (!paint) return;
        material = new THREE.MeshPhysicalMaterial({
          ...paint,
          clearcoatRoughness: 0.04,
          envMap,
          envMapIntensity: 1.6,
        });
      }
      child.material = material;
      created.push(material);
    });
    return () => created.forEach((material) => material.dispose());
  }, [motor, envMap]);

  // Parked on the left sidewalk, parallel to the first building.
  // The model faces +X; a quarter turn points it down the alley.
  // Neon parts below are in the model's own units (before the 3x scale).
  return (
    <group position={[-4.95, 0.18, -6]} rotation={[0, Math.PI / 2, 0]} scale={3}>
      <primitive object={motor} />
      {/* Side strips along the battery panels */}
      <NeonStrip position={[-0.04, 0.33, 0.212]} size={[0.74, 0.018, 0.01]} color={[4, 0, 4]} />
      <NeonStrip position={[-0.04, 0.33, -0.212]} size={[0.74, 0.018, 0.01]} color={[4, 0, 4]} />
      {/* Upper body accent lines */}
      <NeonStrip position={[0.04, 0.78, 0.215]} size={[0.8, 0.012, 0.01]} color={[0, 3.5, 3.5]} />
      <NeonStrip position={[0.04, 0.78, -0.215]} size={[0.8, 0.012, 0.01]} color={[0, 3.5, 3.5]} />
      {/* Headlight and tail light */}
      <NeonStrip position={[0.725, 0.93, 0]} size={[0.012, 0.07, 0.24]} color={[4, 4.5, 5]} />
      <NeonStrip position={[-1.005, 0.89, 0]} size={[0.012, 0.04, 0.26]} color={[5, 0, 0.4]} />
      {/* Underglow on the wet sidewalk */}
      <NeonStrip position={[-0.04, 0.2, 0]} size={[0.9, 0.012, 0.03]} color={[3, 0, 4]} />
      <pointLight position={[0, 0.12, 0]} color="#c02cff" intensity={6} distance={5} decay={2} />
      <pointLight position={[0.9, 0.9, 0]} color="#7ffcff" intensity={3} distance={4} decay={2} />
    </group>
  );
}

export function Street() {
  const { scene } = useGLTF(STREET_MODEL);
  const billboardTextures = useTexture(BILLBOARD_TEXTURES);
  const { returnToStart } = useJourneyProgress();

  const handleExitClick = (event) => {
    if (!isExitSign(event.object)) return;
    event.stopPropagation();
    returnToStart();
  };
  const street = useMemo(() => scene.clone(), [scene]);

  useEffect(() => {
    const created = [];
    const billboards = [];

    street.traverse((child) => {
      if (child.isMesh && (child.name || '').startsWith('Billboard')) billboards.push(child);
    });
    billboards.sort((a, b) => a.name.localeCompare(b.name));
    const billboardMaterial = new Map(
      billboards.map((mesh, index) => [
        mesh,
        makeBillboardMaterial(billboardTextures[index % billboardTextures.length], mesh),
      ]),
    );

    street.traverse((child) => {
      if (!child.isMesh) return;

      const name = child.name || '';
      let material = null;

      // SignBoard_EXIT is the spec name. This model calls the exit mesh
      // Interactive_Exit_Sign, so both get the red neon treatment.
      if (name.includes('SignBoard_EXIT') || name === 'Interactive_Exit_Sign') {
        material = new THREE.MeshStandardMaterial({
          color: '#ff0000',
          emissive: '#ff0000',
          emissiveIntensity: 8,
        });
      } else if (name.includes('SignText') || name.startsWith('NeonFrame')) {
        material = new THREE.MeshStandardMaterial({
          color: '#ffffff',
          emissive: neonColor(name),
          emissiveIntensity: 5,
        });
      } else if (name.startsWith('Billboard')) {
        material = billboardMaterial.get(child);
      } else if (name === 'Street_Road') {
        material = makeWetMaterial('#12141a');
      } else if (name.startsWith('Building')) {
        material = makeWetMaterial(buildingColor(name));
      }

      if (!material) return;
      child.material = material;
      created.push(material);
    });

    return () => {
      created.forEach((material) => {
        material.map?.dispose();
        material.dispose();
      });
    };
  }, [street, billboardTextures]);

  return (
    <>
      <primitive
        object={street}
        onClick={handleExitClick}
        onPointerOver={(event) => {
          if (!isExitSign(event.object)) return;
          event.stopPropagation();
          document.body.style.cursor = 'pointer';
        }}
        onPointerOut={(event) => {
          if (!isExitSign(event.object)) return;
          document.body.style.cursor = 'auto';
        }}
      />
      <Motorcycle />
      {/* Text fetches its font at runtime; its own boundary keeps the street visible meanwhile. */}
      <Suspense fallback={null}>
        <Text
          position={[0, 4.15, -73.3]}
          fontSize={0.5}
          letterSpacing={0.12}
          anchorX="center"
          anchorY="middle"
          onClick={(event) => {
            event.stopPropagation();
            returnToStart();
          }}
          onPointerOver={(event) => {
            event.stopPropagation();
            document.body.style.cursor = 'pointer';
          }}
          onPointerOut={() => {
            document.body.style.cursor = 'auto';
          }}
        >
          CLICK TO GO BACK
          <meshBasicMaterial color={[2.4, 1.2, 1.8]} toneMapped={false} />
        </Text>
      </Suspense>
    </>
  );
}

useGLTF.preload(STREET_MODEL);
useGLTF.preload(MOTOR_MODEL);
useTexture.preload(BILLBOARD_TEXTURES);
