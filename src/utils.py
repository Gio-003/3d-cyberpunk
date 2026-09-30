"""Small, reusable Blender construction helpers for the motorcycle blockout."""

from __future__ import annotations

import math
from typing import Iterable, Sequence

import bpy
from mathutils import Vector


def clear_scene() -> None:
    """Remove every object and collection from the current scene."""
    if bpy.context.object and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    # Remove linked child collections too; Scene Collection itself is not stored
    # in bpy.data.collections and therefore remains intact.
    for collection in list(bpy.data.collections):
        bpy.data.collections.remove(collection)


def ensure_collection(name: str, parent: bpy.types.Collection | None = None) -> bpy.types.Collection:
    collection = bpy.data.collections.get(name) or bpy.data.collections.new(name)
    parent = parent or bpy.context.scene.collection
    if collection.name not in {child.name for child in parent.children}:
        parent.children.link(collection)
    return collection


def move_to_collection(obj: bpy.types.Object, collection: bpy.types.Collection) -> None:
    if collection.objects.get(obj.name) is None:
        collection.objects.link(obj)
    for old_collection in list(obj.users_collection):
        if old_collection != collection:
            old_collection.objects.unlink(obj)


def assign_material(obj: bpy.types.Object, material: bpy.types.Material | None) -> None:
    if material and material.name not in obj.data.materials:
        obj.data.materials.append(material)


def add_bevel(obj: bpy.types.Object, width: float = 0.015, segments: int = 2) -> None:
    modifier = obj.modifiers.new(name="Edge Bevel", type="BEVEL")
    modifier.width = width
    modifier.segments = segments
    modifier.limit_method = "ANGLE"


def shade_smooth(obj: bpy.types.Object, angle_degrees: float = 40.0) -> None:
    for polygon in obj.data.polygons:
        polygon.use_smooth = True
    # Blender 4.1+ uses the geometry-nodes based operator for angle smoothing.
    if hasattr(obj.data, "set_sharp_from_angle"):
        obj.data.set_sharp_from_angle(angle=math.radians(angle_degrees))


def create_box(
    name: str,
    location: Sequence[float],
    dimensions: Sequence[float],
    collection: bpy.types.Collection,
    material: bpy.types.Material | None = None,
    rotation: Sequence[float] = (0.0, 0.0, 0.0),
    bevel: float = 0.01,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=location, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    move_to_collection(obj, collection)
    assign_material(obj, material)
    if bevel:
        add_bevel(obj, bevel)
    return obj


def create_cylinder_between(
    name: str,
    start: Sequence[float],
    end: Sequence[float],
    radius: float,
    collection: bpy.types.Collection,
    material: bpy.types.Material | None = None,
    vertices: int = 16,
    bevel: float = 0.0,
) -> bpy.types.Object:
    start_v, end_v = Vector(start), Vector(end)
    direction = end_v - start_v
    midpoint = (start_v + end_v) * 0.5
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=direction.length, location=midpoint)
    obj = bpy.context.object
    obj.name = name
    obj.rotation_mode = "QUATERNION"
    obj.rotation_quaternion = direction.to_track_quat("Z", "Y")
    move_to_collection(obj, collection)
    assign_material(obj, material)
    if bevel:
        add_bevel(obj, bevel, 2)
    shade_smooth(obj)
    return obj


def create_beam_between(
    name: str,
    start: Sequence[float],
    end: Sequence[float],
    thickness: float,
    width: float,
    collection: bpy.types.Collection,
    material: bpy.types.Material | None = None,
    bevel: float = 0.01,
) -> bpy.types.Object:
    """Create a rectangular beam whose long local X axis joins two points."""
    start_v, end_v = Vector(start), Vector(end)
    direction = end_v - start_v
    obj = create_box(
        name,
        (start_v + end_v) * 0.5,
        (direction.length, width, thickness),
        collection,
        material,
        bevel=bevel,
    )
    obj.rotation_mode = "QUATERNION"
    obj.rotation_quaternion = direction.to_track_quat("X", "Z")
    return obj


def create_torus(
    name: str,
    location: Sequence[float],
    major_radius: float,
    minor_radius: float,
    collection: bpy.types.Collection,
    material: bpy.types.Material | None = None,
    major_segments: int = 48,
    minor_segments: int = 10,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_torus_add(
        major_radius=major_radius,
        minor_radius=minor_radius,
        major_segments=major_segments,
        minor_segments=minor_segments,
        location=location,
        rotation=(math.radians(90.0), 0.0, 0.0),
    )
    obj = bpy.context.object
    obj.name = name
    move_to_collection(obj, collection)
    assign_material(obj, material)
    shade_smooth(obj)
    return obj


def create_profile_prism(
    name: str,
    profile: Iterable[Sequence[float]],
    width: float,
    collection: bpy.types.Collection,
    material: bpy.types.Material | None = None,
    center_y: float = 0.0,
    bevel: float = 0.01,
) -> bpy.types.Object:
    """Extrude a closed X/Z side profile symmetrically along Y."""
    points = list(profile)
    count = len(points)
    half_width = width * 0.5
    vertices = [(x, center_y - half_width, z) for x, z in points]
    vertices += [(x, center_y + half_width, z) for x, z in points]

    # Caps face outward; side quads connect matching profile edges.
    faces = [tuple(reversed(range(count))), tuple(range(count, count * 2))]
    for index in range(count):
        next_index = (index + 1) % count
        faces.append((index, next_index, count + next_index, count + index))

    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    assign_material(obj, material)
    if bevel:
        add_bevel(obj, bevel, 2)
    return obj


def create_cable_bundle(
    name: str,
    paths: Iterable[Iterable[Sequence[float]]],
    radius: float,
    collection: bpy.types.Collection,
    material: bpy.types.Material | None = None,
) -> bpy.types.Object:
    """Create several low-resolution cable paths as one shared Curve object."""
    curve = bpy.data.curves.new(f"{name}_Curve", type="CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = 1
    curve.bevel_depth = radius
    curve.bevel_resolution = 1
    curve.resolution_u = 1
    for path in paths:
        points = list(path)
        spline = curve.splines.new(type="POLY")
        spline.points.add(len(points) - 1)
        for point, coordinate in zip(spline.points, points):
            point.co = (*coordinate, 1.0)
    obj = bpy.data.objects.new(name, curve)
    collection.objects.link(obj)
    assign_material(obj, material)
    return obj
