# Comprehensive Prompt & Technical Specification: Blender Python Script for Cyberpunk Dead-End Street

## Role & Context
You are an expert Blender Python (bpy) developer and 3D environment artist. Your task is to write a robust, production-ready, and self-contained Python script to be executed inside Blender. The script will procedurally generate a complete, realistic, dead-end cyberpunk street optimized for a web-based Three.js interactive scrolling experience.

---

## Core Requirements & Specifications

### 1. Street Layout & Building Architecture
- **Dimensions:** Design real-world relative dimensions for a narrow, oppressive dead-end cyberpunk alleyway/street (e.g., street length of ~60-80 meters, road width of ~8-10 meters, and building heights ranging from 15 to 40 meters).
- **Building Arrangement:** Buildings must line both sides of the street consecutively (touching/connected blocks with no gaps), but each building block must feature completely randomized, irregular footprints, varied heights, and asymmetrical futuristic architectural massing (recesses, setbacks, angular cuts).
- **Road Details:** The road mesh must feature subtle physical imperfections (minor depressions/potholes, jagged, worn edges along the sidewalks) to give it an authentic, dystopian feel.

### 2. Geometry Optimization & Detail Strategy
- **Optimization Strategy:** Balance low-to-mid poly geometry efficiency for web/Three.js performance with rich structural visual diversity.
- **Structural Wear:** Model worn, jagged, or weathered edges on building corners.
- **Exclusions:** Do **not** model micro-geometry details such as individual window panes, intricate AC units, or complex railing/balcony meshes (these will be handled via textures or secondary passes).

### 3. Cables & Neon Billboards
- **Cables:** Procedurally generate a chaotic network of curved cables/tubes (`bezier curves` converted to meshes or low-poly cylinders) that stretch across the street overhead, randomly connecting opposing or adjacent buildings in sweeping arcs.
- **Billboards:** Generate simple flat panel meshes that protrude *outward* from the walls (mounted on brackets/frames, never embedded into the walls). These are designated for dynamic texture/video mapping in Three.js.
- **Neon Light Frames:** Each billboard panel must feature a distinct, surrounding neon light border frame mesh immediately offset from the panel edge, configured with strong emission properties.

### 4. Dead-End & Interactive Exit Element
- **Dead-End Wall:** The street must terminate at a massive, imposing cyberpunk block/wall structure sealing off the end of the alley.
- **EXIT Sign:** The "EXIT" sign must be modeled as a distinct, entirely separate standalone mesh object. It must be named uniquely (e.g., `Interactive_Exit_Sign`) so it can be precisely targeted via raycasting for click events in Three.js.

### 5. Hierarchy & Export Structure
- **Object Separation:** Every major structural element must remain a distinct, individual mesh object in the Blender Outliner rather than being joined into a single mesh. This includes:
  - Individual buildings (e.g., `Building_Left_01`, `Building_Right_01`, etc.)
  - The road surface (`Street_Road`)
  - Separate billboard panels and their corresponding neon frames
  - The cable network (`Cables_Network`)
  - The separate exit sign (`Interactive_Exit_Sign`)
- **Export Automation:** At the end of the script, include an automated export routine using `bpy.ops.export_scene.gltf()` to export the entire scene into a single optimized `.glb` file while preserving the individual object hierarchy and assigned materials.

### 6. Materials & Shading Setup
- Create and assign clean, functional Principled BSDF materials programmatically in Blender so they map cleanly when loaded into Three.js:
  - **Buildings:** Dark industrial concrete/metal texture tint (rough, low specular).
  - **Road:** Dark worn asphalt material with visual roughness variations.
  - **Neon Frames & Exit Sign:** Bright, saturated emission materials (e.g., hot pink, cyan, electric orange) with high emission strength values.

---

## Python Script Architecture Guidelines

When writing the script, adhere to these coding standards:
1. **Clean Imports:** Import only necessary modules (`bpy`, `math`, `random`, `bmesh`).
2. **Scene Cleanup:** Begin the script by clearing default objects (cube, light, camera) to ensure a clean slate.
3. **Modular Functions:** Write modular helper functions (e.g., `create_building(...)`, `generate_billboards(...)`, `create_cables(...)`, `build_road(...)`).
4. **Error Handling & Performance:** Use efficient mesh construction methods and wrap operations cleanly to avoid context-switching errors in Blender.
5. **Comments:** Add clear docstrings and comments explaining coordinate logic, extrusion math, and export paths.

---

## Expected Output from Cursor / Gemini Pro
Provide a single, complete Python script block that can be copied and pasted directly into Blender's Scripting workspace and executed to build the entire scene and trigger the `.glb` export.