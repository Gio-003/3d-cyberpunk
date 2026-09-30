"""Procedural first-pass blockout of a futuristic electric street motorcycle."""

from __future__ import annotations

import math

import bpy

from .utils import (
    create_beam_between,
    create_box,
    create_cable_bundle,
    create_cylinder_between,
    create_profile_prism,
    create_torus,
    ensure_collection,
)


# Primary proportions in metres. These are the first values to tune on refinement.
DIMENSIONS = {
    "wheelbase": 1.62,
    "rear_wheel_radius": 0.375,
    "front_wheel_radius": 0.340,
    "rear_tire_width": 0.200,
    "front_tire_width": 0.120,
    "axle_height": 0.375,
    "body_width": 0.420,
    "seat_height": 0.820,
}


def _wheel(name: str, x: float, radius: float, tire_width: float, collection, materials, rear=False):
    axle_z = DIMENSIONS["axle_height"]
    wheel_collection = ensure_collection(name, collection)
    tire_section = tire_width * 0.43
    create_torus(
        f"{name}_tire",
        (x, 0.0, axle_z),
        radius - tire_section,
        tire_section,
        wheel_collection,
        materials["rubber"],
        major_segments=56,
        minor_segments=12,
    )
    rim_radius = radius * 0.71
    create_torus(f"{name}_rim", (x, 0.0, axle_z), rim_radius, 0.022, wheel_collection, materials["metal"])
    hub_width = tire_width * 0.72
    create_cylinder_between(
        f"{name}_hub", (x, -hub_width / 2, axle_z), (x, hub_width / 2, axle_z),
        0.055 if rear else 0.045, wheel_collection, materials["metal"], vertices=24,
    )

    # Broad, low-count radial spokes retain readability without becoming detail work.
    spoke_count = 8 if rear else 7
    for side in (-1, 1):
        y = side * hub_width * 0.43
        for index in range(spoke_count):
            angle = (index / spoke_count) * math.tau + (0.08 if side > 0 else 0.0)
            start = (x, y, axle_z)
            end = (x + math.cos(angle) * rim_radius * 0.90, y, axle_z + math.sin(angle) * rim_radius * 0.90)
            create_cylinder_between(
                f"{name}_spoke_{'right' if side > 0 else 'left'}_{index + 1:02d}",
                start, end, 0.009 if rear else 0.007, wheel_collection, materials["metal"], vertices=8,
            )
    return wheel_collection


def _build_wheels(root, materials):
    wheels = ensure_collection("Wheels", root)
    rear_x = -DIMENSIONS["wheelbase"] / 2
    front_x = DIMENSIONS["wheelbase"] / 2
    _wheel("rear", rear_x, DIMENSIONS["rear_wheel_radius"], DIMENSIONS["rear_tire_width"], wheels, materials, True)
    _wheel("front", front_x, DIMENSIONS["front_wheel_radius"], DIMENSIONS["front_tire_width"], wheels, materials, False)
    return rear_x, front_x


def _build_front_end(root, materials, front_x):
    front = ensure_collection("Front_End", root)
    axle_z = DIMENSIONS["axle_height"]
    fork_top = (0.555, 0.0, 1.125)
    for side, label in ((-1, "L"), (1, "R")):
        y = side * 0.105
        split = (0.695, y, 0.775)
        suffix = "left" if label == "L" else "right"
        create_cylinder_between(f"front_fork_{suffix}_upper", (fork_top[0], y, fork_top[2]), split, 0.030, front, materials["metal"], 20)
        create_cylinder_between(f"front_fork_{suffix}_lower", split, (front_x, y, axle_z), 0.037, front, materials["frame"], 20)
    create_cylinder_between("front_axle", (front_x, -0.145, axle_z), (front_x, 0.145, axle_z), 0.025, front, materials["metal"], 20)
    create_beam_between("triple_clamp_lower", (0.635, -0.14, 0.955), (0.635, 0.14, 0.955), 0.038, 0.045, front, materials["frame"])
    create_beam_between("triple_clamp_upper", (0.555, -0.14, 1.125), (0.555, 0.14, 1.125), 0.035, 0.042, front, materials["frame"])
    # Angular, close-fitting front fender.
    create_profile_prism("front_fender", [(0.55, 0.61), (0.68, 0.72), (0.93, 0.72), (1.08, 0.63), (1.01, 0.61), (0.82, 0.66), (0.62, 0.60)], 0.145, front, materials["body"], bevel=0.008)
    create_torus("front_brake_disc", (front_x, -0.074, axle_z), 0.178, 0.014, front, materials["metal"], major_segments=32, minor_segments=6)


def _build_chassis(root, materials, rear_x):
    chassis = ensure_collection("Chassis", root)
    # Dark geometric battery/motor core.
    create_profile_prism(
        "battery_enclosure",
        [(-0.44, 0.31), (-0.51, 0.48), (-0.36, 0.75), (0.10, 0.82), (0.45, 0.62), (0.42, 0.28), (-0.18, 0.24)],
        0.34, chassis, materials["frame"], bevel=0.025,
    )
    # Two side covers leave the structural black core visible around their edges.
    panel_profile = [(-0.39, 0.37), (-0.42, 0.54), (-0.28, 0.70), (0.10, 0.75), (0.34, 0.59), (0.31, 0.36), (-0.12, 0.30)]
    for side, label in ((-1, "L"), (1, "R")):
        suffix = "left" if label == "L" else "right"
        create_profile_prism(f"body_panel_{suffix}", panel_profile, 0.035, chassis, materials["body"], center_y=side * 0.188, bevel=0.012)
        create_beam_between(f"frame_rail_{suffix}", (-0.40, side * 0.215, 0.72), (0.34, side * 0.215, 0.94), 0.050, 0.045, chassis, materials["body"], 0.012)
        create_beam_between(f"frame_downtube_{suffix}", (0.34, side * 0.215, 0.94), (0.38, side * 0.215, 0.39), 0.050, 0.045, chassis, materials["body"], 0.012)

    # Twin-sided swingarm tapers visually from the central pivot to the exposed rear hub.
    pivot = (-0.30, 0.0, 0.43)
    for side, label in ((-1, "L"), (1, "R")):
        y = side * 0.145
        suffix = "left" if label == "L" else "right"
        create_beam_between(f"swingarm_{suffix}", (rear_x, y, 0.375), (pivot[0], y, pivot[2]), 0.085, 0.055, chassis, materials["frame"], 0.016)
        create_beam_between(f"swingarm_brace_{suffix}", (rear_x + 0.10, y, 0.47), (-0.23, y, 0.54), 0.045, 0.045, chassis, materials["frame"], 0.012)
    create_cylinder_between("swingarm_pivot", (-0.30, -0.22, 0.43), (-0.30, 0.22, 0.43), 0.055, chassis, materials["metal"], 24)
    create_torus("rear_brake_disc", (rear_x, -0.109, 0.375), 0.195, 0.014, chassis, materials["metal"], major_segments=32, minor_segments=6)
    create_cable_bundle(
        "orange_cables",
        [
            [
                (-0.66, -0.205, 0.53 + offset), (-0.54, -0.215, 0.49 + offset),
                (-0.40, -0.220, 0.45 + offset), (-0.25, -0.220, 0.43 + offset),
                (-0.10, -0.215, 0.46 + offset), (0.03, -0.205, 0.53 + offset),
            ]
            for offset in (-0.022, 0.0, 0.022)
        ],
        0.010, chassis, materials["cables"],
    )


def _build_body(root, materials):
    body = ensure_collection("Bodywork", root)
    body_width = DIMENSIONS["body_width"]
    seat_z = DIMENSIONS["seat_height"]
    # Tank/shoulder mass is split into upper teal shell and black waist insert.
    create_profile_prism("upper_body_shell", [(-0.40, 0.75), (-0.23, 1.03), (0.12, 1.15), (0.45, 1.03), (0.48, 0.86), (0.12, 0.78)], body_width, body, materials["body"], bevel=0.018)
    create_profile_prism("body_waist", [(-0.40, 0.75), (-0.10, 0.79), (0.28, 0.88), (0.43, 0.81), (0.17, 0.69), (-0.27, 0.66)], body_width + 0.015, body, materials["frame"], bevel=0.012)
    create_profile_prism("headlight_cowl", [(0.42, 0.84), (0.52, 1.10), (0.72, 1.00), (0.69, 0.79), (0.52, 0.73)], 0.34, body, materials["body"], bevel=0.014)

    create_profile_prism("seat", [(-0.78, seat_z - 0.04), (-0.66, seat_z + 0.02), (-0.27, seat_z + 0.02), (-0.17, seat_z - 0.04), (-0.34, seat_z - 0.08), (-0.70, seat_z - 0.08)], 0.30, body, materials["seat"], bevel=0.018)
    create_profile_prism("tail_section", [(-1.00, seat_z + 0.01), (-0.79, seat_z + 0.14), (-0.47, seat_z + 0.11), (-0.35, seat_z + 0.02), (-0.76, seat_z)], 0.31, body, materials["body"], bevel=0.014)
    create_profile_prism("tail_underside", [(-0.98, seat_z - 0.03), (-0.75, seat_z), (-0.40, seat_z - 0.03), (-0.51, seat_z - 0.09), (-0.89, seat_z - 0.10)], 0.27, body, materials["frame"], bevel=0.010)


def build_motorcycle(materials: dict[str, bpy.types.Material]) -> bpy.types.Collection:
    """Build the complete blockout and return its root collection."""
    root = ensure_collection("Motorcycle_Blockout")
    rear_x, front_x = _build_wheels(root, materials)
    _build_front_end(root, materials, front_x)
    _build_chassis(root, materials, rear_x)
    _build_body(root, materials)
    return root
