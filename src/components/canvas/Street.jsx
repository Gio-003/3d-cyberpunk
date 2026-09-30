import { Suspense, useEffect, useMemo } from 'react';
import { Text, useGLTF, useScroll, useTexture } from '@react-three/drei';
import * as THREE from 'three';

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

function Motorcycle() {
  const { scene } = useGLTF(MOTOR_MODEL);
  const motor = useMemo(() => scene.clone(), [scene]);
  // Parked on the left sidewalk, parallel to the first building.
  // The model faces +X; a quarter turn points it down the alley.
  return (
    <primitive
      object={motor}
      position={[-4.95, 0.18, -6]}
      rotation={[0, Math.PI / 2, 0]}
      scale={3}
    />
  );
}

export function Street() {
  const { scene } = useGLTF(STREET_MODEL);
  const billboardTextures = useTexture(BILLBOARD_TEXTURES);
  const scroll = useScroll();

  const scrollToStart = () => {
    // CameraRig eases toward scroll offset 0, so the view glides back to the entrance.
    scroll.el.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const returnToStart = (event) => {
    if (!isExitSign(event.object)) return;
    event.stopPropagation();
    scrollToStart();
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
        onClick={returnToStart}
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
            scrollToStart();
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
