# Futuristic Electric Motorcycle — Blender Blockout

This project includes a procedural Blender/Python blockout based on the supplied turquoise electric street-motorcycle reference. The first pass concentrates on silhouette, proportions, large body volumes, wheels, forks, frame, swingarm, seat, and tail. Major parts are separate, clearly named objects arranged into collections.

The source reference currently lives at `blender/blender-motorcycle/reference.png`.

## Run from the Blender UI

1. Open Blender and switch to the **Scripting** workspace.
2. In the Text Editor choose **Open**, then select `build_motorcycle.py` from this project.
3. Press **Run Script** (or `Alt+P` while the pointer is over the Text Editor).
4. Inspect the generated `Motorcycle_Blockout` collection in the Outliner. Use numpad `1` for a direct side view or numpad `0` for the configured three-quarter camera.

Running the script clears the currently open Blender scene first, so use a new file or save unrelated work before running it.

## Run from the command line

From the project root, with Blender available on `PATH`:

```powershell
blender --background --python build_motorcycle.py -- --save output/motorcycle_blockout.blend --render output/motorcycle_preview.png
```

To also bake the modifiers and export the web-ready model:

```powershell
blender --background --python build_motorcycle.py -- --export-glb output/motorcycle.glb --save output/motorcycle_blockout.blend
```

Both flags are optional. To launch Blender interactively and build into the open UI:

```powershell
blender --python build_motorcycle.py
```

If Blender is not on `PATH`, replace `blender` with the full path to the Blender executable.

## Project structure

```text
build_motorcycle.py       Main Blender entry point; optional save/render flags
src/
  motorcycle.py           Dimensions and procedural component construction
  materials.py            Teal, black, rubber, metal, fork, and seat materials
  scene.py                Camera, studio floor, lighting, units, and render setup
  utils.py                Reusable mesh, collection, bevel, beam, and prism helpers
blender/
  blender-motorcycle/
    reference.png         Visual reference used for the blockout
```

The existing JavaScript files in `src/` belong to the accompanying web project and are intentionally left untouched.

## Easy dimension adjustments

The `DIMENSIONS` dictionary near the top of `src/motorcycle.py` exposes the primary proportion controls:

- `wheelbase`
- `rear_wheel_radius` and `front_wheel_radius`
- `rear_tire_width` and `front_tire_width`
- `axle_height`
- `body_width`
- `seat_height`

Wheel positions derive from `wheelbase`. The large faceted volumes use readable X/Z profile point lists in `_build_chassis()` and `_build_body()`; editing those points is the quickest way to refine the battery enclosure, shoulder bodywork, seat, and tail silhouettes against the reference.
