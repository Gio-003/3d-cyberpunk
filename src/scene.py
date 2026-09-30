"""Scene, lighting, camera, and presentation setup."""

from __future__ import annotations

import math

import bpy
from mathutils import Vector

from .utils import create_box, ensure_collection


def _point_camera(camera: bpy.types.Object, target=(0.0, 0.0, 0.58)) -> None:
    camera.rotation_euler = (Vector(target) - camera.location).to_track_quat("-Z", "Y").to_euler()


def setup_scene(materials: dict[str, bpy.types.Material]) -> None:
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.length_unit = "METERS"
    # Eevee's identifier has changed more than once across Blender releases.
    engine_items = scene.render.bl_rna.properties["engine"].enum_items
    engine_ids = {item.identifier for item in engine_items}
    scene.render.engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in engine_ids else "BLENDER_EEVEE"
    scene.render.resolution_x = 960
    scene.render.resolution_y = 540
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False

    world = scene.world or bpy.data.worlds.new("Motorcycle_World")
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.025, 0.045, 0.052, 1.0)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.35

    presentation = ensure_collection("Presentation")
    floor_material = bpy.data.materials.get("Studio_Floor") or bpy.data.materials.new("Studio_Floor")
    floor_material.diffuse_color = (0.055, 0.075, 0.078, 1.0)
    floor_material.use_nodes = True
    floor_shader = floor_material.node_tree.nodes.get("Principled BSDF")
    floor_shader.inputs["Base Color"].default_value = (0.04, 0.065, 0.07, 1.0)
    floor_shader.inputs["Roughness"].default_value = 0.38
    create_box("Studio_Floor", (0.0, 0.0, -0.035), (5.0, 4.0, 0.06), presentation, floor_material, bevel=0.0)

    bpy.ops.object.camera_add(location=(2.75, -4.35, 1.75))
    camera = bpy.context.object
    camera.name = "Camera_Hero_ThreeQuarter"
    camera.data.lens = 58
    _point_camera(camera)
    scene.camera = camera
    from .utils import move_to_collection
    move_to_collection(camera, presentation)

    light_specs = [
        ("Key_Area", (0.4, -2.4, 3.3), 1250.0, 3.0, (0.72, 0.93, 1.0)),
        ("Rim_Area", (-2.2, 1.4, 2.2), 900.0, 2.2, (0.20, 0.75, 0.82)),
        ("Fill_Area", (2.5, 2.2, 1.6), 700.0, 2.5, (0.95, 0.40, 0.24)),
    ]
    for name, location, energy, size, color in light_specs:
        data = bpy.data.lights.new(name, type="AREA")
        data.energy = energy
        data.shape = "DISK"
        data.size = size
        data.color = color
        light = bpy.data.objects.new(name, data)
        presentation.objects.link(light)
        light.location = location
        light.rotation_euler = (Vector((0.0, 0.0, 0.55)) - light.location).to_track_quat("-Z", "Y").to_euler()

    # Look names differ between Blender generations; assignment is cosmetic.
    try:
        scene.view_settings.look = "AgX - Medium High Contrast"
    except TypeError:
        try:
            scene.view_settings.look = "Medium High Contrast"
        except TypeError:
            pass
