"""Material palette for the futuristic electric motorcycle."""

from __future__ import annotations

import bpy


def _material(name: str, color, metallic: float, roughness: float) -> bpy.types.Material:
    material = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    material.use_nodes = True
    shader = material.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = color
    shader.inputs["Metallic"].default_value = metallic
    shader.inputs["Roughness"].default_value = roughness
    return material


def create_materials() -> dict[str, bpy.types.Material]:
    """Create a small shared, glTF-compatible Principled BSDF palette."""
    return {
        "body": _material("MAT_Body", (0.025, 0.42, 0.39, 1.0), 0.55, 0.24),
        "frame": _material("MAT_Frame", (0.012, 0.016, 0.019, 1.0), 0.40, 0.28),
        "rubber": _material("MAT_Rubber", (0.008, 0.009, 0.010, 1.0), 0.0, 0.72),
        "metal": _material("MAT_Metal", (0.24, 0.29, 0.31, 1.0), 0.82, 0.24),
        "seat": _material("MAT_Seat", (0.018, 0.023, 0.026, 1.0), 0.0, 0.48),
        "cables": _material("MAT_Cables", (0.82, 0.16, 0.025, 1.0), 0.15, 0.32),
    }
