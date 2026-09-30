# Three.js / glTF Export

The web-ready motorcycle is exported to:

```text
output/motorcycle.glb
```

It uses metres, is centered around the world origin in X/Y, and rests on the ground at Z = 0. The studio floor, camera, and lights are not included in the GLB.

## Object names

The GLB contains 65 separate mesh nodes. Major nodes include:

- `body_panel_left`, `body_panel_right`
- `upper_body_shell`, `body_waist`, `headlight_cowl`, `front_fender`
- `battery_enclosure`
- `frame_rail_left`, `frame_rail_right`
- `frame_downtube_left`, `frame_downtube_right`
- `front_tire`, `rear_tire`
- `front_rim`, `rear_rim`
- `front_hub`, `rear_hub`
- `front_spoke_left_01` through numbered left/right spoke objects
- `rear_spoke_left_01` through numbered left/right spoke objects
- `front_fork_left_upper`, `front_fork_left_lower`
- `front_fork_right_upper`, `front_fork_right_lower`
- `front_brake_disc`, `rear_brake_disc`
- `swingarm_left`, `swingarm_right`
- `swingarm_brace_left`, `swingarm_brace_right`, `swingarm_pivot`
- `orange_cables`
- `seat`, `tail_section`, `tail_underside`

The objects remain separate so they can be found with `gltf.scene.getObjectByName()` and manipulated independently.

## Materials

All materials use only the Principled BSDF inputs supported by glTF and are shared between compatible parts:

- `MAT_Body` — turquoise painted bodywork
- `MAT_Frame` — dark structural parts and battery enclosure
- `MAT_Rubber` — tires
- `MAT_Metal` — rims, spokes, hubs, forks, axles, and brake discs
- `MAT_Seat` — dark seat vinyl
- `MAT_Cables` — orange high-voltage cables

## Geometry statistics

- Mesh objects: approximately **65**
- Vertices: approximately **4,930**
- Triangles: approximately **9,592**
- Dimensions: approximately **2.34 m × 0.48 m × 1.15 m**

Bevel modifiers and the cable curves are baked before export. Object rotation and scale are applied, origins are reset to geometry bounds, and smooth shading is preserved.

## Textures

No bitmap textures or normal maps are used in this blockout. Base color, metallic, and roughness are stored directly in the glTF PBR materials, so the GLB is self-contained.

## Changing the body color in Three.js

`MAT_Body` is shared by all turquoise components. Change it once after loading to recolor the motorcycle consistently:

```js
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';

const loader = new GLTFLoader();

loader.load('/output/motorcycle.glb', (gltf) => {
  let bodyMaterial;

  gltf.scene.traverse((object) => {
    if (!object.isMesh) return;

    const materials = Array.isArray(object.material)
      ? object.material
      : [object.material];

    bodyMaterial ??= materials.find(
      (material) => material?.name === 'MAT_Body'
    );
  });

  if (bodyMaterial) {
    bodyMaterial.color.set('#00a99d');
    bodyMaterial.needsUpdate = true;
  }

  scene.add(gltf.scene);
});
```

An individual component can be accessed directly:

```js
const frontWheel = gltf.scene.getObjectByName('front_tire');
const leftPanel = gltf.scene.getObjectByName('body_panel_left');
```

## Rebuilding the GLB

From the project root:

```powershell
& "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" `
  --background `
  --python build_motorcycle.py `
  -- `
  --export-glb output\motorcycle.glb `
  --save output\motorcycle_blockout.blend
```
