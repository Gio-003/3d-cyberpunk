import { useEffect, useMemo } from 'react';
import { useGLTF, useTexture } from '@react-three/drei';
import * as THREE from 'three';

const STREET_MODEL = '/models/cyber_street.glb';
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

export function Street() {
  const { scene } = useGLTF(STREET_MODEL);
  const billboardTextures = useTexture(BILLBOARD_TEXTURES);
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
        material = makeWetMaterial('#5c6679');
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

  return <primitive object={street} />;
}

useGLTF.preload(STREET_MODEL);
useTexture.preload(BILLBOARD_TEXTURES);
