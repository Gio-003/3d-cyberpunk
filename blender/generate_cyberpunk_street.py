"""Procedural cyberpunk dead-end street for Blender, exported to glTF.

Run inside Blender's Scripting workspace (Open, then Run Script), or headless:

    blender --background --python generate_cyberpunk_street.py

Coordinate system (Blender, Z-up, meters):
    +Y  runs from the open entrance (y=0) toward the dead-end wall
    +X  is the right-hand sidewalk when looking down the street
    +Z  is up

glTF / Three.js is Y-up. Blender's exporter maps (x, y, z) to (x, z, -y),
so in Three.js the street runs toward -Z and height is +Y. Object names are
preserved. `Interactive_Exit_Sign` is the raycast target. Billboard meshes
are bare panels with a 0-1 UV map on the street-facing side (`video_target`
is stored in glTF extras / Three.js userData).

The script keeps every major element as its own mesh: buildings, the road,
each billboard, each neon frame, the cable network, the dead-end wall, and
the exit sign. They are parented under an empty named CyberpunkStreet.
"""

import math
import os
import random
import traceback

import bpy
import bmesh
from mathutils import Quaternion, Vector

# ---------------------------------------------------------------------------
# Scene scale. Real-world meters, tuned for a narrow oppressive alley.
# ---------------------------------------------------------------------------

SEED = 2077
STREET_LENGTH = 74.0
ROAD_HALF = 4.6  # full carriageway is 9.2 m
SIDEWALK_WIDTH = 1.8
BUILDING_LINE = ROAD_HALF + SIDEWALK_WIDTH  # facade plane, 6.4 m off center
CURB_HEIGHT = 0.18
ROAD_Y0 = -2.0  # short apron in front of the first buildings
JOINT_OVERLAP = 0.15  # back corners interpenetrate so party walls seal

NEON_COLORS = {
    "pink": (1.0, 0.02, 0.42),
    "cyan": (0.0, 0.86, 1.0),
    "orange": (1.0, 0.30, 0.02),
    "violet": (0.62, 0.08, 1.0),
}


def export_filepath():
    """glb path next to the web app, or beside this script if layout differs."""
    try:
        here = os.path.dirname(os.path.abspath(__file__))
    except NameError:
        here = None
    if here:
        return os.path.normpath(
            os.path.join(here, "..", "public", "models", "cyber_street.glb")
        )
    return os.path.join(
        os.path.expanduser("~"),
        "Desktop",
        "cyberpunk",
        "3d-cyberpunk",
        "public",
        "models",
        "cyber_street.glb",
    )


# ---------------------------------------------------------------------------
# Scene setup
# ---------------------------------------------------------------------------

def ensure_object_mode():
    active = bpy.context.active_object
    if active is not None and bpy.context.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")


def reset_scene():
    """Remove the default cube, light, and camera so each run starts empty."""
    ensure_object_mode()
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()
    for datablock in (
        bpy.data.meshes,
        bpy.data.curves,
        bpy.data.materials,
        bpy.data.lights,
        bpy.data.cameras,
    ):
        for block in list(datablock):
            if block.users == 0:
                datablock.remove(block)

    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0
    scene.unit_settings.length_unit = "METERS"

    world = scene.world
    if world is None:
        world = bpy.data.worlds.new("World")
        scene.world = world
    tree = world.node_tree
    if tree is None:
        world.use_nodes = True
        tree = world.node_tree
    background = tree.nodes.get("Background") if tree else None
    if background is not None:
        background.inputs[0].default_value = (0.008, 0.01, 0.016, 1.0)
        background.inputs[1].default_value = 0.2


def make_material(
    name,
    base,
    roughness,
    metallic,
    specular=0.25,
    emission=None,
    emission_strength=0.0,
):
    """Principled BSDF with only the sockets glTF exports cleanly to Three.js.

    Blender 5 creates a node tree by default. `use_nodes` is left untouched
    because that property is deprecated and scheduled for removal.
    """
    mat = bpy.data.materials.new(name)
    tree = mat.node_tree
    if tree is None:
        mat.use_nodes = True
        tree = mat.node_tree
    bsdf = next((node for node in tree.nodes if node.type == "BSDF_PRINCIPLED"), None)
    if bsdf is None:
        bsdf = tree.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = (base[0], base[1], base[2], 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    spec = bsdf.inputs.get("Specular IOR Level") or bsdf.inputs.get("Specular")
    if spec is not None:
        spec.default_value = specular
    if emission is not None:
        socket = bsdf.inputs.get("Emission Color") or bsdf.inputs.get("Emission")
        if socket is not None:
            socket.default_value = (emission[0], emission[1], emission[2], 1.0)
        strength = bsdf.inputs.get("Emission Strength")
        if strength is not None:
            strength.default_value = emission_strength
    mat.diffuse_color = (
        (emission[0], emission[1], emission[2], 1.0)
        if emission is not None
        else (base[0], base[1], base[2], 1.0)
    )
    return mat


def build_materials():
    mats = {
        "concrete_a": make_material("Mat_Building_Concrete_A", (0.045, 0.047, 0.052), 0.90, 0.04, 0.16),
        "concrete_b": make_material("Mat_Building_Concrete_B", (0.028, 0.030, 0.036), 0.94, 0.06, 0.14),
        "stain": make_material("Mat_Building_Stained", (0.055, 0.040, 0.036), 0.92, 0.08, 0.15),
        "metal": make_material("Mat_Building_Metal", (0.018, 0.020, 0.024), 0.52, 0.74, 0.38),
        "asphalt": make_material("Mat_Road_Asphalt", (0.012, 0.012, 0.014), 0.95, 0.0, 0.12),
        "asphalt_worn": make_material("Mat_Road_Worn", (0.007, 0.007, 0.008), 0.46, 0.14, 0.32),
        "sidewalk": make_material("Mat_Sidewalk", (0.034, 0.034, 0.038), 0.90, 0.02, 0.18),
        "deadend": make_material("Mat_DeadEnd", (0.016, 0.017, 0.020), 0.88, 0.16, 0.18),
        "cable": make_material("Mat_Cable", (0.012, 0.012, 0.013), 0.68, 0.42, 0.22),
        "bracket": make_material("Mat_Bracket", (0.02, 0.021, 0.024), 0.48, 0.78, 0.35),
        "exit_plate": make_material("Mat_Exit_Plate", (0.01, 0.008, 0.012), 0.40, 0.55, 0.3),
    }
    glow = {
        "pink": 26.0,
        "cyan": 22.0,
        "orange": 20.0,
        "violet": 20.0,
    }
    for key, color in NEON_COLORS.items():
        mats[key] = make_material(
            "Mat_Neon_%s" % key.capitalize(),
            color,
            0.32,
            0.0,
            0.5,
            emission=color,
            emission_strength=glow[key],
        )
    exit_color = (1.0, 0.03, 0.22)
    mats["exit_glow"] = make_material(
        "Mat_Exit_Glow",
        exit_color,
        0.28,
        0.0,
        0.5,
        emission=exit_color,
        emission_strength=32.0,
    )
    return mats


def link_object(name, mesh, materials, parent, smooth=False, props=None):
    for poly in mesh.polygons:
        poly.use_smooth = smooth
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    for mat in materials:
        obj.data.materials.append(mat)
    if parent is not None:
        obj.parent = parent
    if props:
        for key, value in props.items():
            obj[key] = value
    return obj


def finalize_mesh(name, bm, materials, parent, smooth=False, weld=0.0, props=None):
    """Copy a bmesh into a scene object. Caller still owns and must free `bm`."""
    if weld > 0.0 and len(bm.verts) > 0:
        bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=weld)
    if len(bm.faces) == 0:
        raise RuntimeError("Mesh '%s' was generated with no faces." % name)
    bmesh.ops.triangulate(
        bm,
        faces=list(bm.faces),
        quad_method="BEAUTY",
        ngon_method="EAR_CLIP",
    )
    bm.normal_update()
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    mesh.validate(verbose=False)
    mesh.update()
    return link_object(name, mesh, materials, parent, smooth=smooth, props=props)


# ---------------------------------------------------------------------------
# Mesh primitives
# ---------------------------------------------------------------------------

def signed_area(pts):
    area = 0.0
    count = len(pts)
    for i, (x1, y1) in enumerate(pts):
        x2, y2 = pts[(i + 1) % count]
        area += x1 * y2 - x2 * y1
    return area * 0.5


def clean_pts(pts):
    cleaned = []
    for point in pts:
        if not cleaned:
            cleaned.append(point)
            continue
        px, py = cleaned[-1]
        if abs(point[0] - px) > 1e-5 or abs(point[1] - py) > 1e-5:
            cleaned.append(point)
    if len(cleaned) > 1:
        x0, y0 = cleaned[0]
        x1, y1 = cleaned[-1]
        if abs(x0 - x1) < 1e-5 and abs(y0 - y1) < 1e-5:
            cleaned.pop()
    return cleaned


def ensure_ccw(pts):
    """Blender extrudes a +Z cap with outward normals when the ring is CCW."""
    pts = clean_pts(pts)
    if signed_area(pts) < 0.0:
        pts = list(reversed(pts))
    return pts


def orient_faces_outward(faces):
    """Flip any face whose normal points toward the shell centroid.

    Used per convex or mildly concave shell (a building mass, a box). Not
    used for cables: a sagging tube's centroid sits outside the mesh.
    """
    if not faces:
        return
    center = Vector((0.0, 0.0, 0.0))
    for face in faces:
        center += face.calc_center_median()
    center /= float(len(faces))
    for face in faces:
        face.normal_update()
        if face.normal.dot(face.calc_center_median() - center) < 0.0:
            face.normal_flip()


def add_box(bm, center, size, mat_index=0):
    """Axis-aligned box. `size` is full width, depth, and height in meters."""
    hx, hy, hz = size[0] * 0.5, size[1] * 0.5, size[2] * 0.5
    if hx < 1e-4 or hy < 1e-4 or hz < 1e-4:
        return []
    cx, cy, cz = center
    verts = [
        bm.verts.new((cx - hx, cy - hy, cz - hz)),
        bm.verts.new((cx + hx, cy - hy, cz - hz)),
        bm.verts.new((cx + hx, cy + hy, cz - hz)),
        bm.verts.new((cx - hx, cy + hy, cz - hz)),
        bm.verts.new((cx - hx, cy - hy, cz + hz)),
        bm.verts.new((cx + hx, cy - hy, cz + hz)),
        bm.verts.new((cx + hx, cy + hy, cz + hz)),
        bm.verts.new((cx - hx, cy + hy, cz + hz)),
    ]
    # Winding is corrected by orient_faces_outward, so the order only needs
    # to be a closed shell.
    quads = (
        (0, 1, 2, 3),
        (4, 7, 6, 5),
        (0, 4, 5, 1),
        (1, 5, 6, 2),
        (2, 6, 7, 3),
        (3, 7, 4, 0),
    )
    faces = []
    for quad in quads:
        face = bm.faces.new(tuple(verts[i] for i in quad))
        face.material_index = mat_index
        faces.append(face)
    orient_faces_outward(faces)
    return faces


def add_prism(bm, pts, z0, z1, cap_bottom=True, cap_top=True, mat_index=0, taper=0.0, sign=1.0):
    """Extrude a CCW footprint from z0 to z1.

    `taper` drops the back edge of the top cap (positive depth = away from
    the street) so a roof can slope without a boolean.
    """
    pts = ensure_ccw(pts)
    if len(pts) < 3 or abs(signed_area(pts)) < 0.4:
        raise RuntimeError("Degenerate building footprint: %s" % (pts,))
    if z1 < z0 + 0.05:
        z1 = z0 + 0.05
    bottom = [bm.verts.new((p[0], p[1], z0)) for p in pts]
    top = [bm.verts.new((p[0], p[1], z1)) for p in pts]
    if taper > 0.0:
        keys = [sign * vert.co.x for vert in top]
        lo, hi = min(keys), max(keys)
        span = (hi - lo) or 1.0
        drop = min(taper, (z1 - z0) * 0.5)
        for vert, key in zip(top, keys):
            vert.co.z -= drop * ((key - lo) / span)
    faces = []
    if cap_bottom:
        faces.append(bm.faces.new(list(reversed(bottom))))
    if cap_top:
        faces.append(bm.faces.new(list(top)))
    count = len(pts)
    for i in range(count):
        j = (i + 1) % count
        faces.append(bm.faces.new((bottom[i], bottom[j], top[j], top[i])))
    for face in faces:
        face.material_index = mat_index
    orient_faces_outward(faces)
    return faces


def add_prism_y(bm, poly_xz, y0, y1, mat_index=0):
    """Extrude an XZ polygon along Y. Used for the diagonal strokes of X."""
    if y1 < y0:
        y0, y1 = y1, y0
    back = [bm.verts.new((x, y1, z)) for x, z in poly_xz]
    front = [bm.verts.new((x, y0, z)) for x, z in poly_xz]
    faces = [bm.faces.new(back), bm.faces.new(list(reversed(front)))]
    count = len(poly_xz)
    for i in range(count):
        j = (i + 1) % count
        faces.append(bm.faces.new((back[i], front[i], front[j], back[j])))
    for face in faces:
        face.material_index = mat_index
    orient_faces_outward(faces)
    return faces


# ---------------------------------------------------------------------------
# Lot planning and buildings
# ---------------------------------------------------------------------------

def make_footprint(sign, y0, y1, depth, recess, bow):
    """Irregular lot ring.

    The street edge stays on the shared facade line so neighboring blocks
    touch. Party corners at the sidewalk are exact. Back corners extend
    `JOINT_OVERLAP` past the shared boundary so the two closed shells
    interpenetrate instead of leaving a see-through slit or a coplanar
    z-fighting wall. Recesses and the back kink break the box silhouette.
    """
    x_face = sign * BUILDING_LINE

    def x_at(depth_pos):
        return x_face + sign * depth_pos

    length = max(y1 - y0, 0.01)
    depth0 = max(recess + 2.6, depth)
    depth1 = max(recess + 2.6, depth + bow)
    kink_depth = max(recess + 2.6, (depth0 + depth1) * 0.5 + bow * 0.22)
    r0 = y0 + length * 0.30
    r1 = y1 - length * 0.30
    use_recess = recess > 0.35 and (r1 - r0) > 1.7

    pts = [(x_at(0.0), y0)]
    if use_recess:
        pts.extend(
            [
                (x_at(0.0), r0),
                (x_at(recess), r0),
                (x_at(recess), r1),
                (x_at(0.0), r1),
            ]
        )
    pts.append((x_at(0.0), y1))
    pts.append((x_at(depth1), y1 + JOINT_OVERLAP))
    pts.append((x_at(kink_depth), (y0 + y1) * 0.5))
    pts.append((x_at(depth0), y0 - JOINT_OVERLAP))
    pts = ensure_ccw(pts)
    if abs(signed_area(pts)) < 8.0:
        raise RuntimeError("Footprint area collapsed: %s" % (pts,))
    return pts, use_recess, r0, r1


def make_upper(sign, y0, y1, depth, street, back, margin, cut):
    """Upper-mass ring, inset from the party walls.

    `street` is depth from the facade. Negative values overhang the sidewalk.
    `cut` chamfers a back corner so the mass is not a second box.
    """
    x_face = sign * BUILDING_LINE

    def x_at(depth_pos):
        return x_face + sign * depth_pos

    ya = y0 + margin
    yb = y1 - margin
    if yb - ya < 2.2:
        ya = y0 + 0.35
        yb = y1 - 0.35
    d1 = max(street + 1.8, depth - back)
    cut = min(cut, (yb - ya) * 0.34, max(0.15, (d1 - street) * 0.34))
    d_cut = max(street + 0.9, d1 - cut)
    pts = [
        (x_at(street), ya),
        (x_at(d1), ya + cut * 0.22),
        (x_at(d_cut), yb),
        (x_at(street + min(cut * 0.18, (d1 - street) * 0.2)), yb),
    ]
    return ensure_ccw(pts)


def design_levels(sign, y0, y1, height, depth, recess, bow, variant):
    base_pts, use_recess, r0, r1 = make_footprint(sign, y0, y1, depth, recess, bow)
    levels = []
    margin = 0.62

    def add_level(pts, z0, z1, cap_bottom, cap_top, taper=0.0):
        levels.append(
            {
                "pts": pts,
                "z0": z0,
                "z1": z1,
                "cap_bottom": cap_bottom,
                "cap_top": cap_top,
                "taper": taper,
            }
        )

    if variant == "overhang":
        h_base = max(5.2, height * random.uniform(0.30, 0.42))
        add_level(base_pts, 0.0, h_base, True, True)
        upper = make_upper(
            sign, y0, y1, depth,
            street=-random.uniform(0.55, 1.1),
            back=random.uniform(1.0, 2.8),
            margin=margin,
            cut=random.uniform(0.6, 2.0),
        )
        # Bottom cap is the soffit over the sidewalk. It sits 2 cm under the
        # base roof so the two horizontal faces are not coplanar.
        add_level(upper, h_base - 0.02, height, True, True)
    elif variant == "triple":
        h1 = height * random.uniform(0.30, 0.42)
        h2 = height * random.uniform(0.58, 0.74)
        if h2 < h1 + 2.4:
            h2 = h1 + 2.4
        add_level(base_pts, 0.0, h1, True, True)
        add_level(
            make_upper(sign, y0, y1, depth, random.uniform(0.45, 1.4), random.uniform(0.8, 2.2), margin, random.uniform(0.4, 1.6)),
            h1 - 0.05, h2, False, True,
        )
        if height > h2 + 2.6:
            add_level(
                make_upper(sign, y0, y1, depth, random.uniform(1.2, 2.6), random.uniform(1.5, 3.4), margin + 0.25, random.uniform(1.0, 2.4)),
                h2 - 0.05, height, False, True,
            )
    elif variant == "wedge":
        h_base = height * random.uniform(0.62, 0.78)
        add_level(base_pts, 0.0, h_base, True, True)
        add_level(
            make_upper(sign, y0, y1, depth, random.uniform(0.3, 1.3), random.uniform(0.4, 1.8), margin, random.uniform(1.4, 3.2)),
            h_base - 0.05, height, False, True,
            taper=random.uniform(1.6, 4.0),
        )
    else:
        h_base = height * random.uniform(0.42, 0.62)
        add_level(base_pts, 0.0, h_base, True, True)
        add_level(
            make_upper(sign, y0, y1, depth, random.uniform(0.7, 2.2), random.uniform(0.6, 2.6), margin, random.uniform(0.5, 2.2)),
            h_base - 0.05, height, False, True,
        )
    return levels, use_recess, r0, r1


def plan_side(side_name, sign):
    """Pack touching lots along one side of the alley."""
    lots = []
    y = 0.0
    index = 1
    variants = ("stack", "stack", "overhang", "triple", "wedge")
    materials = ("concrete_a", "concrete_a", "concrete_b", "stain", "metal")
    while y < STREET_LENGTH - 0.05 and index < 24:
        remaining = STREET_LENGTH - y
        if remaining <= 16.0:
            length = remaining
        else:
            length = random.uniform(8.5, 14.5)
            if remaining - length < 8.5:
                length = remaining
        if length < 4.0:
            break
        y1 = y + length
        depth = random.uniform(8.0, 15.0)
        bow = random.uniform(-2.4, 3.0)
        recess = random.uniform(0.55, 1.75) if random.random() < 0.74 else 0.0
        if random.random() < 0.55:
            height = random.uniform(15.0, 26.0)
        else:
            height = random.uniform(26.0, 40.0)
        variant = random.choice(variants)
        levels, use_recess, r0, r1 = design_levels(
            sign, y, y1, height, depth, recess, bow, variant
        )
        lots.append(
            {
                "name": "Building_%s_%02d" % (side_name, index),
                "side": side_name,
                "sign": sign,
                "index": index,
                "y0": y,
                "y1": y1,
                "height": height,
                "depth": depth,
                "recess": recess if use_recess else 0.0,
                "use_recess": use_recess,
                "r0": r0,
                "r1": r1,
                "variant": variant,
                "levels": levels,
                "material_key": random.choice(materials),
            }
        )
        y = y1
        index += 1
    if not lots or abs(lots[-1]["y1"] - STREET_LENGTH) > 0.05:
        raise RuntimeError("%s lots did not reach the dead end (y=%s)." % (side_name, y))
    return lots


def weather_building(bm, y0, y1):
    """Chip vertical corners. Party-wall verts stay put so blocks still meet."""
    for vert in bm.verts:
        if vert.co.z < 2.0:
            continue
        if vert.co.y < y0 + 0.5 or vert.co.y > y1 - 0.5:
            continue
        if len(vert.link_edges) < 3 or len(vert.link_edges) > 6:
            continue
        vertical = False
        for edge in vert.link_edges:
            delta = edge.other_vert(vert).co - vert.co
            if delta.length < 1e-6:
                continue
            if abs(delta.normalized().z) > 0.9:
                vertical = True
                break
        if not vertical:
            continue
        vert.co.x += random.uniform(-0.08, 0.08)
        vert.co.y += random.uniform(-0.05, 0.05)
        vert.co.z += random.uniform(-0.04, 0.05)


def add_facade_details(bm, lot):
    """Horizontal ribs and one vertical fin. No windows, rails, or AC units."""
    sign = lot["sign"]
    base_top = lot["levels"][0]["z1"]
    spans = []
    if lot["use_recess"]:
        if lot["r0"] - lot["y0"] > 2.2:
            spans.append((lot["y0"] + 0.55, lot["r0"] - 0.2))
        if lot["y1"] - lot["r1"] > 2.2:
            spans.append((lot["r1"] + 0.2, lot["y1"] - 0.55))
    else:
        spans.append((lot["y0"] + 0.55, lot["y1"] - 0.55))

    band_zs = [base_top * random.uniform(0.38, 0.55)]
    if base_top > 8.0 and random.random() < 0.55:
        band_zs.append(base_top * random.uniform(0.68, 0.84))
    protrude = random.uniform(0.28, 0.5)
    for z_band in band_zs:
        for y_a, y_b in spans:
            if y_b - y_a < 1.4:
                continue
            x_outer = sign * BUILDING_LINE - sign * protrude
            x_inner = sign * BUILDING_LINE + sign * 0.1
            add_box(
                bm,
                ((x_outer + x_inner) * 0.5, (y_a + y_b) * 0.5, z_band),
                (abs(x_outer - x_inner), y_b - y_a, 0.34),
            )

    if lot["height"] > 16.0 and spans and random.random() < 0.8:
        y_a, y_b = max(spans, key=lambda span: span[1] - span[0])
        if y_b - y_a > 1.0:
            fin_y = y_a + (y_b - y_a) * random.uniform(0.25, 0.75)
            fin_h = min(lot["height"] * 0.55, base_top + 6.0)
            x_outer = sign * BUILDING_LINE - sign * random.uniform(0.45, 0.75)
            x_inner = sign * BUILDING_LINE + sign * 0.12
            add_box(
                bm,
                ((x_outer + x_inner) * 0.5, fin_y, 1.6 + fin_h * 0.5),
                (abs(x_outer - x_inner), 0.22, fin_h),
            )


def create_building(lot, materials, root):
    bm = bmesh.new()
    try:
        for level in lot["levels"]:
            add_prism(
                bm,
                level["pts"],
                level["z0"],
                level["z1"],
                cap_bottom=level["cap_bottom"],
                cap_top=level["cap_top"],
                taper=level["taper"],
                sign=lot["sign"],
            )
        add_facade_details(bm, lot)
        weather_building(bm, lot["y0"], lot["y1"])
        return finalize_mesh(
            lot["name"],
            bm,
            [materials[lot["material_key"]]],
            root,
        )
    finally:
        bm.free()


# ---------------------------------------------------------------------------
# Road
# ---------------------------------------------------------------------------

def add_height_strip(bm, rows, mat_index):
    """Quad strip. `rows[iy][ix]` is an (x, y, z) tuple. Normals point +Z."""
    vert_rows = []
    for row in rows:
        vert_rows.append([bm.verts.new(point) for point in row])
    faces = []
    for iy in range(len(rows) - 1):
        for ix in range(len(rows[iy]) - 1):
            face = bm.faces.new(
                (
                    vert_rows[iy][ix],
                    vert_rows[iy][ix + 1],
                    vert_rows[iy + 1][ix + 1],
                    vert_rows[iy + 1][ix],
                )
            )
            face.material_index = mat_index
            faces.append(face)
    return faces


def add_curb_wall(bm, bottom_pts, top_pts, normal_sign, mat_index):
    """Vertical curb. `normal_sign` +1 points toward +X (left curb)."""
    bottom = [bm.verts.new(point) for point in bottom_pts]
    top = [bm.verts.new(point) for point in top_pts]
    for iy in range(len(bottom) - 1):
        if normal_sign > 0:
            quad = (bottom[iy], bottom[iy + 1], top[iy + 1], top[iy])
        else:
            quad = (bottom[iy], top[iy], top[iy + 1], bottom[iy + 1])
        face = bm.faces.new(quad)
        face.material_index = mat_index


def build_road(materials, root):
    """Asphalt, raised sidewalks, jagged curbs, and a handful of potholes.

    Seam vertices are written twice (road edge + curb, curb + sidewalk) and
    welded so the surface is one connected mesh with a vertical curb.
    """
    y_segs = 72
    x_segs = 14
    ys = [ROAD_Y0 + (STREET_LENGTH - ROAD_Y0) * i / y_segs for i in range(y_segs + 1)]
    potholes = []
    for _ in range(8):
        potholes.append(
            (
                random.uniform(-ROAD_HALF + 0.9, ROAD_HALF - 0.9),
                random.uniform(2.0, STREET_LENGTH - 2.5),
                random.uniform(1.25, 2.7),
                random.uniform(0.045, 0.17),
            )
        )

    left_curb_x, right_curb_x = [], []
    left_outer_x, right_outer_x = [], []
    left_top_z, right_top_z = [], []
    left_edge_z, right_edge_z = [], []
    for y in ys:
        left_curb_x.append(-ROAD_HALF + random.uniform(-0.12, 0.16))
        right_curb_x.append(ROAD_HALF + random.uniform(-0.16, 0.12))
        left_outer_x.append(-BUILDING_LINE - random.uniform(0.06, 0.32))
        right_outer_x.append(BUILDING_LINE + random.uniform(0.06, 0.32))
        broken_l = random.random() < 0.08
        broken_r = random.random() < 0.08
        left_top_z.append(0.025 if broken_l else CURB_HEIGHT + random.uniform(-0.02, 0.025))
        right_top_z.append(0.025 if broken_r else CURB_HEIGHT + random.uniform(-0.02, 0.025))
        wave = 0.012 * math.sin(y * 0.38)
        left_edge_z.append(wave + random.uniform(-0.012, 0.012))
        right_edge_z.append(wave + random.uniform(-0.012, 0.012))

    def surface_z(x, y):
        t = min(1.0, abs(x) / ROAD_HALF)
        z = 0.04 * (1.0 - t * t) + 0.012 * math.sin(y * 0.38)
        z += random.uniform(-0.008, 0.008)
        for px, py, radius, depth in potholes:
            dist = math.hypot(x - px, y - py)
            if dist < radius:
                falloff = (1.0 - dist / radius) ** 2
                z -= depth * falloff
        return max(z, -0.22)

    road_rows = []
    left_rows = []
    right_rows = []
    left_bottom, left_top = [], []
    right_bottom, right_top = [], []
    for iy, y in enumerate(ys):
        road = []
        for ix in range(x_segs + 1):
            t = ix / x_segs
            x = left_curb_x[iy] + (right_curb_x[iy] - left_curb_x[iy]) * t
            if ix == 0:
                z = left_edge_z[iy]
            elif ix == x_segs:
                z = right_edge_z[iy]
            else:
                z = surface_z(x, y)
            road.append((x, y, z))
        road_rows.append(road)

        left = []
        right = []
        for ix in range(4):
            t = ix / 3.0
            xl = left_outer_x[iy] + (left_curb_x[iy] - left_outer_x[iy]) * t
            xr = right_curb_x[iy] + (right_outer_x[iy] - right_curb_x[iy]) * t
            if ix == 3:
                zl = left_top_z[iy]
            else:
                zl = left_top_z[iy] + random.uniform(-0.012, 0.018) * (1.0 - t)
            if ix == 0:
                zr = right_top_z[iy]
            else:
                zr = right_top_z[iy] + random.uniform(-0.012, 0.018) * t
            left.append((xl, y, zl))
            right.append((xr, y, zr))
        left_rows.append(left)
        right_rows.append(right)
        left_bottom.append((left_curb_x[iy], y, left_edge_z[iy]))
        left_top.append((left_curb_x[iy], y, left_top_z[iy]))
        right_bottom.append((right_curb_x[iy], y, right_edge_z[iy]))
        right_top.append((right_curb_x[iy], y, right_top_z[iy]))

    bm = bmesh.new()
    try:
        road_faces = add_height_strip(bm, road_rows, 0)
        add_height_strip(bm, left_rows, 2)
        add_height_strip(bm, right_rows, 2)
        add_curb_wall(bm, left_bottom, left_top, 1, 2)
        add_curb_wall(bm, right_bottom, right_top, -1, 2)
        for face in road_faces:
            if min(vert.co.z for vert in face.verts) < -0.02:
                face.material_index = 1
        return finalize_mesh(
            "Street_Road",
            bm,
            [materials["asphalt"], materials["asphalt_worn"], materials["sidewalk"]],
            root,
            weld=0.001,
        )
    finally:
        bm.free()


# ---------------------------------------------------------------------------
# Billboards and neon frames
# ---------------------------------------------------------------------------

def facade_spans(lot):
    """Y intervals and the facade depth the bracket must bolt to."""
    spans = []
    margin = 0.4
    if lot["use_recess"]:
        if lot["r0"] - lot["y0"] > 2.4:
            spans.append((lot["y0"] + margin, lot["r0"] - 0.15, 0.0))
        if lot["y1"] - lot["r1"] > 2.4:
            spans.append((lot["r1"] + 0.15, lot["y1"] - margin, 0.0))
        if lot["r1"] - lot["r0"] > 2.4:
            spans.append((lot["r0"] + 0.25, lot["r1"] - 0.25, lot["recess"]))
    else:
        spans.append((lot["y0"] + margin, lot["y1"] - margin, 0.0))
    return [span for span in spans if span[1] - span[0] > 2.0]


def assign_panel_uv(bm, sign):
    """Map the street-facing panel face to the 0-1 UV square.

    When a viewer stands in the road looking at the panel, +U runs to their
    right and +V runs up, so a video texture is not mirrored.
    """
    uv_layer = bm.loops.layers.uv.new("UVMap")
    street_dir = -sign
    target = None
    best = -1.0
    for face in bm.faces:
        facing = face.normal.x * street_dir
        if facing > best:
            best = facing
            target = face
    if target is None or best < 0.5:
        raise RuntimeError("Billboard panel has no street-facing face.")
    ys = [loop.vert.co.y for loop in target.loops]
    zs = [loop.vert.co.z for loop in target.loops]
    min_y, max_y = min(ys), max(ys)
    min_z, max_z = min(zs), max(zs)
    span_y = (max_y - min_y) or 1.0
    span_z = (max_z - min_z) or 1.0
    for loop in target.loops:
        if sign > 0:
            u = (max_y - loop.vert.co.y) / span_y
        else:
            u = (loop.vert.co.y - min_y) / span_y
        v = (loop.vert.co.z - min_z) / span_z
        loop[uv_layer].uv = (u, v)


def create_billboards(lots, materials, root):
    neon_keys = ("pink", "cyan", "orange", "violet")
    made = []
    for lot in lots:
        if random.random() > 0.64:
            continue
        spans = facade_spans(lot)
        if not spans:
            continue
        random.shuffle(spans)
        count = 1 if random.random() < 0.7 else min(2, len(spans))
        slot_names = "AB"
        for slot_i in range(count):
            y0, y1, depth = spans[slot_i % len(spans)]
            avail = y1 - y0
            width = min(random.uniform(2.6, 5.4), avail - 0.25)
            if width < 1.8:
                continue
            height = random.uniform(1.5, 3.8)
            center_y = max(y0 + width * 0.5, min(y1 - width * 0.5, (y0 + y1) * 0.5))
            z_lo = 3.4 + height * 0.5
            z_hi = min(max(lot["levels"][0]["z1"] - 0.8, z_lo), 17.0)
            center_z = z_lo if z_hi <= z_lo else random.uniform(z_lo, z_hi)
            sign = lot["sign"]
            wall_x = sign * (BUILDING_LINE + depth)
            bracket = random.uniform(0.5, 0.95)
            thick = 0.06
            center_x = wall_x - sign * (bracket + thick * 0.5)
            front_x = center_x - sign * (thick * 0.5)
            slot = slot_names[slot_i]
            panel_name = "Billboard_%s_%02d_%s" % (lot["side"], lot["index"], slot)
            frame_name = "NeonFrame_%s_%02d_%s" % (lot["side"], lot["index"], slot)

            panel_mat = make_material(
                "Mat_%s" % panel_name,
                (0.012, 0.013, 0.016),
                0.42,
                0.04,
                0.22,
            )
            panel_bm = bmesh.new()
            try:
                add_box(panel_bm, (center_x, center_y, center_z), (thick, width, height))
                assign_panel_uv(panel_bm, sign)
                panel = finalize_mesh(
                    panel_name,
                    panel_bm,
                    [panel_mat],
                    root,
                    props={"video_target": 1},
                )
            finally:
                panel_bm.free()

            neon_key = random.choice(neon_keys)
            frame_bm = bmesh.new()
            try:
                frame_x = front_x - sign * 0.06
                bar = 0.075
                gap = 0.05
                bottom_z = center_z - (height * 0.5 + gap + bar * 0.5)
                top_z = center_z + (height * 0.5 + gap + bar * 0.5)
                bar_length = width + 2.0 * gap + 2.0 * bar
                side_height = height + 2.0 * gap + 2.0 * bar
                add_box(frame_bm, (frame_x, center_y, bottom_z), (bar, bar_length, bar), 0)
                add_box(frame_bm, (frame_x, center_y, top_z), (bar, bar_length, bar), 0)
                for y_sign in (-1.0, 1.0):
                    side_y = center_y + y_sign * (width * 0.5 + gap + bar * 0.5)
                    add_box(frame_bm, (frame_x, side_y, center_z), (bar, bar, side_height), 0)
                panel_back_x = center_x + sign * (thick * 0.5)
                embed = 0.07
                if sign > 0:
                    x0, x1 = panel_back_x, wall_x + embed
                else:
                    x0, x1 = wall_x - embed, panel_back_x
                arm_center = ((x0 + x1) * 0.5, 0.0, center_z)
                arm_size_x = abs(x1 - x0)
                for y_off in (-width * 0.32, width * 0.32):
                    add_box(
                        frame_bm,
                        (arm_center[0], center_y + y_off, center_z),
                        (arm_size_x, 0.08, 0.11),
                        1,
                    )
                frame = finalize_mesh(
                    frame_name,
                    frame_bm,
                    [materials[neon_key], materials["bracket"]],
                    root,
                )
            finally:
                frame_bm.free()
            made.append((panel, frame))
    if not made:
        raise RuntimeError("No billboards were generated.")
    return made


# ---------------------------------------------------------------------------
# Cables
# ---------------------------------------------------------------------------

def sample_quadratic(p0, p1, p2, steps):
    points = []
    for i in range(steps + 1):
        t = i / float(steps)
        u = 1.0 - t
        points.append((u * u) * p0 + (2.0 * u * t) * p1 + (t * t) * p2)
    return points


def add_tube(bm, points, radius, sides=5):
    """Low-poly tube along a polyline. Frames are parallel-transported."""
    count = len(points)
    if count < 2 or radius <= 0.0:
        return
    tangents = []
    for i in range(count):
        if i == 0:
            tangent = points[1] - points[0]
        elif i == count - 1:
            tangent = points[-1] - points[-2]
        else:
            tangent = points[i + 1] - points[i - 1]
        if tangent.length < 1e-6:
            tangent = Vector((0.0, 1.0, 0.0))
        tangents.append(tangent.normalized())

    reference = Vector((0.0, 0.0, 1.0))
    if abs(tangents[0].dot(reference)) > 0.85:
        reference = Vector((1.0, 0.0, 0.0))
    normal = tangents[0].cross(reference).normalized()
    normals = [normal]
    for i in range(1, count):
        prev_t = tangents[i - 1]
        tangent = tangents[i]
        axis = prev_t.cross(tangent)
        carried = normals[-1].copy()
        if axis.length > 1e-6:
            axis.normalize()
            angle = math.acos(max(-1.0, min(1.0, prev_t.dot(tangent))))
            carried.rotate(Quaternion(axis, angle))
        carried = carried - tangent * carried.dot(tangent)
        if carried.length < 1e-6:
            carried = tangent.cross(reference)
        normals.append(carried.normalized())

    rings = []
    for i, point in enumerate(points):
        tangent = tangents[i]
        normal = normals[i]
        bitangent = normal.cross(tangent).normalized()
        ring = []
        for s in range(sides):
            angle = 2.0 * math.pi * s / sides
            offset = (normal * math.cos(angle) + bitangent * math.sin(angle)) * radius
            ring.append(bm.verts.new(point + offset))
        rings.append(ring)

    for i in range(count - 1):
        for s in range(sides):
            s2 = (s + 1) % sides
            bm.faces.new(
                (rings[i][s], rings[i + 1][s], rings[i + 1][s2], rings[i][s2])
            )
    bm.faces.new(rings[0])
    bm.faces.new(list(reversed(rings[-1])))


def create_cables(lots, materials, root):
    anchors = []
    for lot in lots:
        x = lot["sign"] * BUILDING_LINE - lot["sign"] * 0.22
        for _ in range(2):
            z_hi = min(lot["height"] - 1.0, 30.0)
            anchors.append(
                {
                    "x": x,
                    "y": random.uniform(lot["y0"] + 0.8, lot["y1"] - 0.8),
                    "z": random.uniform(7.0, max(8.5, z_hi)),
                    "side": lot["side"],
                }
            )
    left = [anchor for anchor in anchors if anchor["side"] == "Left"]
    right = [anchor for anchor in anchors if anchor["side"] == "Right"]
    random.shuffle(left)
    random.shuffle(right)
    pairs = []
    for a, b in zip(left, right):
        pairs.append((a, b))
        if len(pairs) >= 12:
            break
    for group in (left, right):
        ordered = sorted(group, key=lambda anchor: anchor["y"])
        for i in range(0, len(ordered) - 1, 2):
            pairs.append((ordered[i], ordered[i + 1]))
            if len(pairs) >= 18:
                break
    pool = left + right
    for _ in range(4):
        if not pool:
            break
        src = random.choice(pool)
        end = {
            "x": random.uniform(-3.5, 3.5),
            "y": STREET_LENGTH - 0.25,
            "z": random.uniform(9.0, 26.0),
            "side": "End",
        }
        pairs.append((src, end))

    bm = bmesh.new()
    try:
        for a, b in pairs[:20]:
            p0 = Vector((a["x"], a["y"], a["z"]))
            p2 = Vector((b["x"], b["y"], b["z"]))
            if (p2 - p0).length < 3.0:
                continue
            mid = (p0 + p2) * 0.5
            mid.z -= random.uniform(0.8, 3.3)
            if a["side"] != b["side"]:
                mid.x += random.uniform(-0.7, 0.7)
            else:
                mid.x -= math.copysign(random.uniform(0.15, 0.5), a["x"])
            if mid.z < 4.3:
                mid.z = 4.3
            radius = random.uniform(0.025, 0.065)
            add_tube(bm, sample_quadratic(p0, mid, p2, 8), radius, sides=5)
        for face in bm.faces:
            face.material_index = 0
        return finalize_mesh(
            "Cables_Network",
            bm,
            [materials["cable"]],
            root,
            smooth=True,
        )
    finally:
        bm.free()


# ---------------------------------------------------------------------------
# Dead end and EXIT sign
# ---------------------------------------------------------------------------

def create_dead_end(materials, root):
    """Seal the alley. Attachments are sunk into the slab to avoid coplanar faces."""
    front = STREET_LENGTH
    thickness = 6.4
    height = 43.0
    half_w = BUILDING_LINE + 0.4
    bm = bmesh.new()
    try:
        add_box(
            bm,
            (0.0, front + thickness * 0.5, (height - 0.35) * 0.5),
            (half_w * 2.0, thickness, height + 0.35),
        )
        add_box(
            bm,
            (0.0, front + thickness * 0.55, height + 2.2),
            (half_w * 1.15, thickness * 0.72, 5.2),
        )
        # Edge towers and street-side buttresses, overlapped 0.4 m into the slab.
        for x_sign, tower_h, tower_w in ((-1.0, 48.0, 2.6), (1.0, 44.0, 2.9)):
            add_box(
                bm,
                (x_sign * (half_w - 1.15), front + 1.35, tower_h * 0.5 - 0.2),
                (tower_w, 3.4, tower_h),
            )
        for x_sign, butt_w in ((-1.0, 1.7), (1.0, 1.85)):
            size_y = 2.5
            center_y = (front - 2.05) + size_y * 0.5
            add_box(
                bm,
                (x_sign * 5.35, center_y, 15.5),
                (butt_w, size_y, 31.0),
            )
        # Lintel clears the exit sign, which tops out around z=8.7.
        lintel_y = 0.85
        add_box(
            bm,
            (0.0, front - 0.55 + lintel_y * 0.5, 10.15),
            (7.6, lintel_y, 0.7),
        )
        for z_band, depth in ((13.5, 0.45), (24.0, 0.38)):
            size_y = depth
            add_box(
                bm,
                (0.0, front - (depth - 0.18) + size_y * 0.5, z_band),
                (half_w * 1.85, size_y, 0.55),
            )
        return finalize_mesh("DeadEnd_Wall", bm, [materials["deadend"]], root)
    finally:
        bm.free()


def add_diagonal_stroke(bm, x0, z0, x1, z1, stroke, y0, y1, mat_index):
    dx = x1 - x0
    dz = z1 - z0
    length = math.hypot(dx, dz) or 1.0
    px = -dz / length * stroke * 0.5
    pz = dx / length * stroke * 0.5
    poly = (
        (x0 + px, z0 + pz),
        (x0 - px, z0 - pz),
        (x1 - px, z1 - pz),
        (x1 + px, z1 + pz),
    )
    add_prism_y(bm, poly, y0, y1, mat_index)


def create_exit_sign(materials, root):
    """Chunky EXIT glyphs, a dark backplate, and a neon border.

    One mesh, two materials. The plate gives raycasts a solid hit target;
    the glyphs and frame carry the emission material.
    Local -Y points back toward the street entrance.
    """
    stroke = 0.42
    height = 2.5
    gap = 0.28
    e_w, x_w, i_w, t_w = 1.7, 1.55, 0.86, 1.72
    total = e_w + gap + x_w + gap + i_w + gap + t_w
    cursor = -total * 0.5
    z0 = 5.55
    z1 = z0 + height
    # Plate sits just off the wall. Glyphs and the frame step toward -Y.
    plate_y0, plate_y1 = -0.16, -0.06
    glyph_y0, glyph_y1 = -0.42, -0.18
    frame_y0, frame_y1 = -0.56, -0.40

    bm = bmesh.new()
    try:
        def block(x_a, x_b, z_a, z_b, y_a, y_b, mat_index):
            add_box(
                bm,
                ((x_a + x_b) * 0.5, (y_a + y_b) * 0.5, (z_a + z_b) * 0.5),
                (abs(x_b - x_a), abs(y_b - y_a), abs(z_b - z_a)),
                mat_index,
            )

        # E
        block(cursor, cursor + stroke, z0, z1, glyph_y0, glyph_y1, 0)
        block(cursor + stroke, cursor + e_w, z0, z0 + stroke, glyph_y0, glyph_y1, 0)
        mid_z = z0 + height * 0.5 - stroke * 0.5
        block(cursor + stroke, cursor + e_w * 0.86, mid_z, mid_z + stroke, glyph_y0, glyph_y1, 0)
        block(cursor + stroke, cursor + e_w, z1 - stroke, z1, glyph_y0, glyph_y1, 0)
        cursor += e_w + gap

        # X. The second stroke is 2 cm forward so the crossing faces do not z-fight.
        add_diagonal_stroke(bm, cursor, z0, cursor + x_w, z1, stroke * 0.72, glyph_y0, glyph_y1, 0)
        add_diagonal_stroke(
            bm, cursor, z1, cursor + x_w, z0, stroke * 0.72, glyph_y0 - 0.02, glyph_y1 - 0.02, 0
        )
        cursor += x_w + gap

        # I
        serif = 0.18
        block(cursor + (i_w - stroke) * 0.5, cursor + (i_w + stroke) * 0.5, z0, z1, glyph_y0, glyph_y1, 0)
        block(cursor, cursor + i_w, z0, z0 + serif, glyph_y0, glyph_y1, 0)
        block(cursor, cursor + i_w, z1 - serif, z1, glyph_y0, glyph_y1, 0)
        cursor += i_w + gap

        # T
        block(
            cursor + t_w * 0.5 - stroke * 0.5,
            cursor + t_w * 0.5 + stroke * 0.5,
            z0,
            z1 - stroke,
            glyph_y0,
            glyph_y1,
            0,
        )
        block(cursor, cursor + t_w, z1 - stroke, z1, glyph_y0, glyph_y1, 0)

        pad = 0.5
        plate_x0, plate_x1 = -total * 0.5 - pad, total * 0.5 + pad
        plate_z0, plate_z1 = z0 - pad, z1 + pad
        block(plate_x0, plate_x1, plate_z0, plate_z1, plate_y0, plate_y1, 1)

        bar = 0.12
        gap_frame = 0.06
        frame_x0 = plate_x0 - gap_frame - bar
        frame_x1 = plate_x1 + gap_frame + bar
        frame_z0 = plate_z0 - gap_frame - bar
        frame_z1 = plate_z1 + gap_frame + bar
        block(frame_x0, frame_x1, frame_z0, frame_z0 + bar, frame_y0, frame_y1, 0)
        block(frame_x0, frame_x1, frame_z1 - bar, frame_z1, frame_y0, frame_y1, 0)
        block(frame_x0, frame_x0 + bar, frame_z0, frame_z1, frame_y0, frame_y1, 0)
        block(frame_x1 - bar, frame_x1, frame_z0, frame_z1, frame_y0, frame_y1, 0)

        obj = finalize_mesh(
            "Interactive_Exit_Sign",
            bm,
            [materials["exit_glow"], materials["exit_plate"]],
            root,
            props={"interactive": 1},
        )
        # Wall front is y = STREET_LENGTH. Local -Y reaches toward the camera.
        obj.location = (0.0, STREET_LENGTH - 0.02, 0.0)
        return obj
    finally:
        bm.free()


# ---------------------------------------------------------------------------
# Preview camera, lights, export
# ---------------------------------------------------------------------------

def add_preview_rig():
    """Viewport-only camera and lights. glTF export skips both."""
    cam_data = bpy.data.cameras.new("Preview_Camera")
    cam_data.lens = 24
    cam_data.clip_start = 0.1
    cam_data.clip_end = 400.0
    camera = bpy.data.objects.new("Preview_Camera", cam_data)
    bpy.context.collection.objects.link(camera)
    camera.location = (0.0, -12.0, 4.2)
    # Camera looks down local -Z. +80 deg about X aims it down +Y, slightly down.
    camera.rotation_euler = (math.radians(80.0), 0.0, 0.0)
    bpy.context.scene.camera = camera

    sun_data = bpy.data.lights.new("Preview_Sun", "SUN")
    sun_data.energy = 1.4
    sun_data.color = (0.55, 0.66, 0.85)
    sun = bpy.data.objects.new("Preview_Sun", sun_data)
    bpy.context.collection.objects.link(sun)
    sun.rotation_euler = (math.radians(48.0), math.radians(8.0), math.radians(24.0))

    def point(name, location, color, energy):
        data = bpy.data.lights.new(name, "POINT")
        data.energy = energy
        data.color = color
        data.shadow_soft_size = 1.5
        obj = bpy.data.objects.new(name, data)
        bpy.context.collection.objects.link(obj)
        obj.location = location
        return obj

    point("Preview_Light_Cyan", (0.0, 18.0, 7.5), (0.15, 0.85, 1.0), 350.0)
    point("Preview_Light_Pink", (-1.5, 42.0, 6.0), (1.0, 0.1, 0.45), 280.0)
    point("Preview_Light_Exit", (0.0, STREET_LENGTH - 6.0, 6.5), (1.0, 0.15, 0.35), 220.0)

    screen = bpy.context.screen
    if screen is None:
        return
    for area in screen.areas:
        if area.type != "VIEW_3D":
            continue
        for space in area.spaces:
            if space.type == "VIEW_3D":
                space.clip_end = 500.0
                space.shading.type = "MATERIAL"
                space.region_3d.view_perspective = "CAMERA"


def export_glb(filepath):
    directory = os.path.dirname(filepath)
    if directory:
        os.makedirs(directory, exist_ok=True)
    if os.path.exists(filepath):
        os.remove(filepath)
    if not hasattr(bpy.ops.export_scene, "gltf"):
        bpy.ops.preferences.addon_enable(module="io_scene_gltf2")

    kwargs = {
        "filepath": filepath,
        "export_format": "GLB",
        "use_selection": False,
        "export_apply": False,
        "export_yup": True,
        "export_materials": "EXPORT",
        "export_cameras": False,
        "export_lights": False,
        "export_extras": True,
        "export_normals": True,
        "export_texcoords": True,
        "export_animations": False,
        "export_hierarchy_full_collections": False,
        "check_existing": False,
    }
    operator = bpy.ops.export_scene.gltf
    valid = {prop.identifier for prop in operator.get_rna_type().properties}
    operator(**{key: value for key, value in kwargs.items() if key in valid})


def validate_scene():
    names = {obj.name for obj in bpy.data.objects}
    required = ("Street_Road", "Cables_Network", "DeadEnd_Wall", "Interactive_Exit_Sign")
    missing = [name for name in required if name not in names]
    if missing:
        raise RuntimeError("Missing objects: %s" % ", ".join(missing))
    if not any(name.startswith("Building_Left_") for name in names):
        raise RuntimeError("No left-side buildings.")
    if not any(name.startswith("Building_Right_") for name in names):
        raise RuntimeError("No right-side buildings.")
    if not any(name.startswith("Billboard_") for name in names):
        raise RuntimeError("No billboards.")
    if not any(name.startswith("NeonFrame_") for name in names):
        raise RuntimeError("No neon frames.")

    right = bpy.data.objects["Building_Right_01"]
    street_face = min(right.data.polygons, key=lambda poly: poly.center.x)
    if street_face.normal.x > -0.25:
        raise RuntimeError(
            "Right facade normal points the wrong way: %s" % (street_face.normal[:],)
        )
    left = bpy.data.objects["Building_Left_01"]
    street_face = max(left.data.polygons, key=lambda poly: poly.center.x)
    if street_face.normal.x < 0.25:
        raise RuntimeError(
            "Left facade normal points the wrong way: %s" % (street_face.normal[:],)
        )

    road = bpy.data.objects["Street_Road"]
    average_up = sum(poly.normal.z for poly in road.data.polygons) / len(road.data.polygons)
    if average_up < 0.75:
        raise RuntimeError("Road normals are not pointing up (avg z=%s)." % average_up)

    sign = bpy.data.objects["Interactive_Exit_Sign"]
    if abs(sign.location.y - (STREET_LENGTH - 0.02)) > 0.02:
        raise RuntimeError("Exit sign is not mounted on the dead-end wall.")
    if "interactive" not in sign.keys():
        raise RuntimeError("Exit sign is missing the interactive custom property.")

    sample = next(obj for obj in bpy.data.objects if obj.name.startswith("Billboard_"))
    if not sample.data.uv_layers:
        raise RuntimeError("Billboard %s has no UV map." % sample.name)


def print_report():
    print("--- Cyberpunk street ---")
    total_tris = 0
    for obj in sorted(bpy.data.objects, key=lambda item: item.name):
        if obj.type != "MESH":
            continue
        tris = sum(len(poly.vertices) - 2 for poly in obj.data.polygons)
        total_tris += tris
        print("  %s  tris=%d  mats=%d" % (obj.name, tris, len(obj.data.materials)))
    print("  total tris: %d" % total_tris)
    print("------------------------")


def main():
    random.seed(SEED)
    reset_scene()
    materials = build_materials()
    root = bpy.data.objects.new("CyberpunkStreet", None)
    root.empty_display_type = "PLAIN_AXES"
    root.empty_display_size = 1.0
    bpy.context.collection.objects.link(root)

    left = plan_side("Left", -1.0)
    right = plan_side("Right", 1.0)
    build_road(materials, root)
    for lot in left + right:
        create_building(lot, materials, root)
    create_billboards(left + right, materials, root)
    create_cables(left + right, materials, root)
    create_dead_end(materials, root)
    create_exit_sign(materials, root)
    add_preview_rig()

    bpy.context.view_layer.update()
    validate_scene()
    print_report()

    filepath = export_filepath()
    export_glb(filepath)
    print("Exported %s" % filepath)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        raise
