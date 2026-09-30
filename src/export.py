"""Real-time cleanup and glTF/GLB export helpers."""

from __future__ import annotations

from pathlib import Path

import bpy
from mathutils import Vector


def _activate_only(obj: bpy.types.Object) -> None:
    bpy.ops.object.select_all(action="DESELECT")
    obj.hide_set(False)
    obj.hide_viewport = False
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def motorcycle_objects(root: bpy.types.Collection) -> list[bpy.types.Object]:
    """Return only model objects, excluding studio presentation objects."""
    return list(root.all_objects)


def prepare_for_web(root: bpy.types.Collection) -> dict[str, int]:
    """Bake procedural geometry, normalize transforms/origins, and ground model."""
    objects = motorcycle_objects(root)

    # Curves (the cable bundle) are explicitly converted so every exported part
    # has predictable mesh geometry in Three.js.
    for obj in list(objects):
        if obj.type == "CURVE":
            _activate_only(obj)
            bpy.ops.object.convert(target="MESH")

    objects = motorcycle_objects(root)
    mesh_objects = [obj for obj in objects if obj.type == "MESH"]
    for obj in mesh_objects:
        _activate_only(obj)
        for modifier in list(obj.modifiers):
            bpy.ops.object.modifier_apply(modifier=modifier.name)
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
        bpy.ops.object.origin_set(type="ORIGIN_GEOMETRY", center="BOUNDS")

    # Center in X/Y and place the bottom of the tires at Z=0.
    bounds = [obj.matrix_world @ Vector(corner) for obj in mesh_objects for corner in obj.bound_box]
    minimum = Vector((min(v.x for v in bounds), min(v.y for v in bounds), min(v.z for v in bounds)))
    maximum = Vector((max(v.x for v in bounds), max(v.y for v in bounds), max(v.z for v in bounds)))
    offset = Vector((-(minimum.x + maximum.x) * 0.5, -(minimum.y + maximum.y) * 0.5, -minimum.z))
    for obj in objects:
        if obj.parent is None:
            obj.location += offset

    triangles = 0
    vertices = 0
    for obj in mesh_objects:
        obj.data.calc_loop_triangles()
        triangles += len(obj.data.loop_triangles)
        vertices += len(obj.data.vertices)
    bpy.ops.object.select_all(action="DESELECT")
    return {"objects": len(mesh_objects), "vertices": vertices, "triangles": triangles}


def export_glb(root: bpy.types.Collection, filepath: Path) -> None:
    """Export the motorcycle collection as one binary glTF with separate nodes."""
    filepath = filepath.resolve()
    filepath.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    for obj in motorcycle_objects(root):
        obj.hide_set(False)
        obj.hide_viewport = False
        obj.select_set(True)
    bpy.ops.export_scene.gltf(
        filepath=str(filepath),
        export_format="GLB",
        use_selection=True,
        export_apply=True,
        export_yup=True,
        export_materials="EXPORT",
        export_cameras=False,
        export_lights=False,
        export_extras=True,
    )
    bpy.ops.object.select_all(action="DESELECT")

