"""Blender entry point for generating the motorcycle blockout.

Usage:
    blender --background --python build_motorcycle.py -- --save motorcycle_blockout.blend
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import bpy


def _find_project_root() -> Path:
    """Locate the repo when run from Blender CLI or its Text Editor.

    Blender can expose an opened Text datablock as ``\\build_motorcycle.py``
    instead of the original absolute filename, so ``__file__`` alone is not
    reliable in UI mode.
    """
    candidates: list[Path] = []

    raw_file = globals().get("__file__")
    if raw_file:
        candidates.append(Path(raw_file).expanduser())

    for text in bpy.data.texts:
        if Path(text.name).name == "build_motorcycle.py" and text.filepath:
            candidates.append(Path(bpy.path.abspath(text.filepath)))

    if bpy.data.filepath:
        candidates.append(Path(bpy.data.filepath).parent)
    candidates.append(Path(os.getcwd()))

    checked: set[Path] = set()
    for candidate in candidates:
        candidate = candidate.resolve()
        start = candidate if candidate.is_dir() else candidate.parent
        for directory in (start, *start.parents):
            if directory in checked:
                continue
            checked.add(directory)
            if (directory / "src" / "motorcycle.py").is_file() and (directory / "src" / "utils.py").is_file():
                return directory

    locations = "\n  - ".join(str(path) for path in candidates)
    raise RuntimeError(
        "Motorcycle project folder could not be found. Open build_motorcycle.py "
        "directly from the project folder. Checked:\n  - " + locations
    )


PROJECT_ROOT = _find_project_root()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.materials import create_materials
from src.motorcycle import build_motorcycle
from src.scene import setup_scene
from src.utils import clear_scene
from src.export import export_glb, prepare_for_web


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the procedural motorcycle blockout")
    parser.add_argument("--save", type=Path, help="Optional .blend output path")
    parser.add_argument("--render", type=Path, help="Optional PNG preview output path")
    parser.add_argument("--export-glb", type=Path, help="Optional optimized GLB output path")
    blender_args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    return parser.parse_args(blender_args)


def main() -> None:
    args = _arguments()
    clear_scene()
    materials = create_materials()
    motorcycle = build_motorcycle(materials)
    setup_scene(materials)

    if args.export_glb:
        stats = prepare_for_web(motorcycle)
        export_path = (PROJECT_ROOT / args.export_glb).resolve() if not args.export_glb.is_absolute() else args.export_glb
        export_glb(motorcycle, export_path)
        print(
            "WEB_EXPORT_STATS "
            f"objects={stats['objects']} vertices={stats['vertices']} triangles={stats['triangles']}"
        )

    if args.save:
        save_path = (PROJECT_ROOT / args.save).resolve() if not args.save.is_absolute() else args.save
        save_path.parent.mkdir(parents=True, exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=str(save_path))
    if args.render:
        render_path = (PROJECT_ROOT / args.render).resolve() if not args.render.is_absolute() else args.render
        render_path.parent.mkdir(parents=True, exist_ok=True)
        bpy.context.scene.render.filepath = str(render_path)
        bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    main()
