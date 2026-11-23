"""Build and render a mechanically accurate 3D planetary gearbox in Blender 5.3.

Usage:
  blender --background --python build_gearbox.py -- --mode preview --out /tmp/preview
  blender --background --python build_gearbox.py -- --mode anim --out /tmp/frames --frames 240
"""
import argparse
import math
import os
import sys
import bpy
import bmesh
from mathutils import Vector, Matrix, Euler


# ---------------------------------------------------------------------------
# Mechanical parameters (exact planetary assembly: Z_r = Z_s + 2 * Z_p)
# (Z_s + Z_r) / N_p = (16 + 40) / 4 = 14 (exact integer -> zero phase error)
# ---------------------------------------------------------------------------
MODULE = 0.12
Z_SUN = 16
Z_PLANET = 12
Z_RING = Z_SUN + 2 * Z_PLANET  # 40
N_PLANETS = 4

R_SUN = MODULE * Z_SUN / 2.0        # 0.96
R_PLANET = MODULE * Z_PLANET / 2.0  # 0.72
R_RING = MODULE * Z_RING / 2.0      # 2.40
R_ORBIT = R_SUN + R_PLANET          # 1.68

GEAR_THICKNESS = 0.42
PRESSURE_ANGLE = math.radians(20.0)


def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def involute_point(r_base, t):
    """Return (x, y) on the involute of a circle of radius r_base at parameter t."""
    x = r_base * (math.cos(t) + t * math.sin(t))
    y = r_base * (math.sin(t) - t * math.cos(t))
    return x, y


def build_external_gear_profile(z, m, backlash=0.012):
    """Return 2D (x, y) CCW vertices for an accurate involute external spur gear."""
    rp = m * z / 2.0
    rb = rp * math.cos(PRESSURE_ANGLE)
    ra = rp + 0.88 * m
    rd = max(0.25 * m, rp - 1.15 * m)

    # Half angular tooth thickness at pitch circle (minus slight backlash)
    alpha_p = math.acos(min(1.0, rb / rp))
    inv_alpha_p = math.tan(alpha_p) - alpha_p
    half_tooth_angle = (math.pi / (2.0 * z)) - backlash / (2.0 * rp)
    base_half_angle = half_tooth_angle + inv_alpha_p

    t_max = math.sqrt(max(0.0, (ra / rb) ** 2 - 1.0))
    t_min = math.sqrt(max(0.0, (max(rd, rb) / rb) ** 2 - 1.0))

    steps = 5
    pts = []
    pitch_step = 2.0 * math.pi / z

    for i in range(z):
        center_angle = i * pitch_step
        # Root start before tooth
        root_angle_start = center_angle - pitch_step * 0.5
        root_angle_1 = center_angle - base_half_angle - 0.08 * pitch_step
        pts.append((rd * math.cos(root_angle_start), rd * math.sin(root_angle_start)))
        if rd < rb:
            pts.append((rd * math.cos(root_angle_1), rd * math.sin(root_angle_1)))

        # Rising flank (right side of tooth when going CCW)
        for s in range(steps + 1):
            t = t_min + (t_max - t_min) * (s / steps)
            ix, iy = involute_point(rb, t)
            r = math.hypot(ix, iy)
            ang = math.atan2(iy, ix)
            a = center_angle - base_half_angle + ang
            pts.append((r * math.cos(a), r * math.sin(a)))

        # Falling flank (mirror)
        for s in range(steps, -1, -1):
            t = t_min + (t_max - t_min) * (s / steps)
            ix, iy = involute_point(rb, t)
            r = math.hypot(ix, iy)
            ang = math.atan2(iy, ix)
            a = center_angle + base_half_angle - ang
            pts.append((r * math.cos(a), r * math.sin(a)))

        if rd < rb:
            root_angle_2 = center_angle + base_half_angle + 0.08 * pitch_step
            pts.append((rd * math.cos(root_angle_2), rd * math.sin(root_angle_2)))

    return pts, rd, ra


def build_internal_gear_profile(z, m, backlash=0.014):
    """Return 2D (x, y) vertices for an internal ring gear tooth profile."""
    rp = m * z / 2.0
    rb = rp * math.cos(PRESSURE_ANGLE)
    # For internal gear, addendum goes INWARD, dedendum goes OUTWARD
    r_tip = rp - 0.82 * m
    r_root = rp + 1.18 * m

    alpha_p = math.acos(min(1.0, rb / rp))
    inv_alpha_p = math.tan(alpha_p) - alpha_p
    # Space width at pitch circle matches external tooth thickness (+ backlash)
    half_space_angle = (math.pi / (2.0 * z)) + backlash / (2.0 * rp)
    base_half_space = half_space_angle + inv_alpha_p

    t_max = math.sqrt(max(0.0, (r_root / rb) ** 2 - 1.0))
    t_min = math.sqrt(max(0.0, (max(r_tip, rb) / rb) ** 2 - 1.0))

    steps = 4
    pts = []
    pitch_step = 2.0 * math.pi / z

    for i in range(z):
        # Center of SPACE at i * pitch_step (so external tooth at angle 0 fits cleanly!)
        center_angle = i * pitch_step

        # Tip before space
        tip_start = center_angle - pitch_step * 0.5
        pts.append((r_tip * math.cos(tip_start), r_tip * math.sin(tip_start)))

        # Left flank going from tip outward to root
        for s in range(steps + 1):
            t = t_min + (t_max - t_min) * (s / steps)
            ix, iy = involute_point(rb, t)
            r = math.hypot(ix, iy)
            ang = math.atan2(iy, ix)
            a = center_angle - base_half_space + ang
            pts.append((r * math.cos(a), r * math.sin(a)))

        # Right flank going from root inward to tip
        for s in range(steps, -1, -1):
            t = t_min + (t_max - t_min) * (s / steps)
            ix, iy = involute_point(rb, t)
            r = math.hypot(ix, iy)
            ang = math.atan2(iy, ix)
            a = center_angle + base_half_space - ang
            pts.append((r * math.cos(a), r * math.sin(a)))

    return pts, r_tip, r_root


def create_extruded_ring_mesh(name, outer_pts, inner_pts, thickness, chamfer=0.015, z_offset=0.0):
    """Create a solid 3D mesh between outer_pts and inner_pts with chamfered front/back edges."""
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()

    n_out = len(outer_pts)
    n_in = len(inner_pts)
    # Resample inner circle to match outer vertex count if inner is a simple circle
    half_t = thickness / 2.0
    z_f = z_offset + half_t
    z_b = z_offset - half_t

    if n_in != n_out:
        # Assume inner_pts is [(r_inner,)] indicator or rebuild evenly
        r_in = inner_pts[0] if isinstance(inner_pts[0], (int, float)) else math.hypot(*inner_pts[0])
        inner_pts = []
        for x, y in outer_pts:
            ang = math.atan2(y, x)
            inner_pts.append((r_in * math.cos(ang), r_in * math.sin(ang)))
        n_in = n_out

    v_out_f = [bm.verts.new((x, y, z_f)) for x, y in outer_pts]
    v_out_b = [bm.verts.new((x, y, z_b)) for x, y in outer_pts]
    v_in_f = [bm.verts.new((x, y, z_f)) for x, y in inner_pts]
    v_in_b = [bm.verts.new((x, y, z_b)) for x, y in inner_pts]

    bm.verts.ensure_lookup_table()

    for i in range(n_out):
        j = (i + 1) % n_out
        # Outer wall
        bm.faces.new((v_out_b[i], v_out_b[j], v_out_f[j], v_out_f[i]))
        # Inner wall
        bm.faces.new((v_in_f[i], v_in_f[j], v_in_b[j], v_in_b[i]))
        # Front face
        bm.faces.new((v_in_f[i], v_out_f[i], v_out_f[j], v_in_f[j]))
        # Back face
        bm.faces.new((v_out_b[i], v_in_b[i], v_in_b[j], v_out_b[j]))

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)

    if chamfer > 0:
        # Bevel front/back rim edges for crisp realistic specular highlights
        rim_edges = [
            e for e in bm.edges
            if abs(e.verts[0].co.z - e.verts[1].co.z) < 1e-4
            and (abs(e.verts[0].co.z - z_f) < 1e-4 or abs(e.verts[0].co.z - z_b) < 1e-4)
            and abs(math.hypot(e.verts[0].co.x, e.verts[0].co.y) - math.hypot(e.verts[1].co.x, e.verts[1].co.y)) < 0.08
        ]
        if rim_edges:
            bmesh.ops.bevel(
                bm,
                geom=rim_edges,
                offset=chamfer,
                segments=2,
                affect='EDGES',
                clamp_overlap=True,
            )

    bm.to_mesh(mesh)
    bm.free()

    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    for poly in mesh.polygons:
        poly.use_smooth = True
    es = obj.modifiers.new("EdgeSplit", 'EDGE_SPLIT')
    es.split_angle = math.radians(32.0)
    return obj


def add_cylinder(name, radius, depth, loc=(0, 0, 0), rot=(0, 0, 0), verts=64, bevel=0.015):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=radius, depth=depth, location=loc, rotation=rot)
    obj = bpy.context.active_object
    obj.name = name
    for p in obj.data.polygons:
        p.use_smooth = True
    if bevel > 0:
        mod = obj.modifiers.new("Bevel", 'BEVEL')
        mod.width = bevel
        mod.segments = 2
        mod.limit_method = 'ANGLE'
    es = obj.modifiers.new("EdgeSplit", 'EDGE_SPLIT')
    es.split_angle = math.radians(32.0)
    return obj


def add_tube(name, r_outer, r_inner, depth, loc=(0, 0, 0), verts=64, chamfer=0.012):
    outer = [(r_outer * math.cos(2 * math.pi * i / verts), r_outer * math.sin(2 * math.pi * i / verts)) for i in range(verts)]
    inner = [(r_inner * math.cos(2 * math.pi * i / verts), r_inner * math.sin(2 * math.pi * i / verts)) for i in range(verts)]
    obj = create_extruded_ring_mesh(name, outer, inner, depth, chamfer=chamfer, z_offset=0.0)
    obj.location = loc
    return obj


# ---------------------------------------------------------------------------
# Materials: Signature CAD-Blueprint (left) <-> Photorealistic Steel (right)
# ---------------------------------------------------------------------------
def make_split_material(name, base_color, metallic=1.0, roughness=0.25, bump_strength=0.03,
                        bevel_radius=0.012, wire_size=0.0042):
    """Create a shader that renders glowing cyan CAD wireframe for X < split_x
    and photorealistic machined metal for X > split_x, with a bright cyan scanline."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()

    out = nt.nodes.new("ShaderNodeOutputMaterial")
    out.location = (900, 0)

    # --- 1. Realistic Metal Branch ---
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (220, 220)
    bsdf.inputs["Base Color"].default_value = (*base_color, 1.0)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = 0.6
    if "Coat Weight" in bsdf.inputs:
        bsdf.inputs["Coat Weight"].default_value = 0.12
        bsdf.inputs["Coat Roughness"].default_value = 0.15

    # Procedural fine machined micro-texture
    tex_coord = nt.nodes.new("ShaderNodeTexCoord")
    tex_coord.location = (-700, 220)

    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.location = (-440, 220)
    noise.inputs["Scale"].default_value = 65.0
    noise.inputs["Detail"].default_value = 8.0
    noise.inputs["Roughness"].default_value = 0.65
    nt.links.new(tex_coord.outputs["Object"], noise.inputs["Vector"])

    # Roughness variation
    rough_map = nt.nodes.new("ShaderNodeMapRange")
    rough_map.location = (-180, 300)
    rough_map.inputs["From Min"].default_value = 0.2
    rough_map.inputs["From Max"].default_value = 0.8
    rough_map.inputs["To Min"].default_value = max(0.04, roughness - 0.07)
    rough_map.inputs["To Max"].default_value = min(0.9, roughness + 0.08)
    nt.links.new(noise.outputs["Fac"], rough_map.inputs["Value"])
    nt.links.new(rough_map.outputs["Result"], bsdf.inputs["Roughness"])

    # Bevel + subtle micro-bump normal
    bevel = nt.nodes.new("ShaderNodeBevel")
    bevel.location = (-200, 60)
    bevel.samples = 4
    bevel.inputs["Radius"].default_value = bevel_radius

    bump = nt.nodes.new("ShaderNodeBump")
    bump.location = (10, 80)
    bump.inputs["Strength"].default_value = bump_strength
    bump.inputs["Distance"].default_value = 0.004
    nt.links.new(noise.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bevel.outputs["Normal"], bump.inputs["Normal"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])

    # --- 2. CAD Blueprint Hologram Branch (Left Side) ---
    lw = nt.nodes.new("ShaderNodeLayerWeight")
    lw.location = (-360, -280)
    lw.inputs["Blend"].default_value = 0.36

    wire = nt.nodes.new("ShaderNodeWireframe")
    wire.location = (-360, -440)
    wire.inputs["Size"].default_value = wire_size

    edge_add = nt.nodes.new("ShaderNodeMath")
    edge_add.operation = 'MAXIMUM'
    edge_add.location = (-120, -340)
    nt.links.new(lw.outputs["Facing"], edge_add.inputs[0])
    nt.links.new(wire.outputs["Fac"], edge_add.inputs[1])

    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.location = (60, -340)
    ramp.color_ramp.elements[0].position = 0.28
    ramp.color_ramp.elements[0].color = (0.008, 0.055, 0.085, 1.0)
    ramp.color_ramp.elements[1].position = 0.88
    ramp.color_ramp.elements[1].color = (0.16, 0.78, 0.84, 1.0)
    nt.links.new(edge_add.outputs["Value"], ramp.inputs["Fac"])

    cad_emit = nt.nodes.new("ShaderNodeEmission")
    cad_emit.location = (320, -260)
    cad_emit.inputs["Strength"].default_value = 1.35
    nt.links.new(ramp.outputs["Color"], cad_emit.inputs["Color"])

    cad_transp = nt.nodes.new("ShaderNodeBsdfTransparent")
    cad_transp.location = (320, -420)
    cad_transp.inputs["Color"].default_value = (0.08, 0.28, 0.34, 1.0)

    cad_mix = nt.nodes.new("ShaderNodeMixShader")
    cad_mix.location = (520, -300)
    nt.links.new(edge_add.outputs["Value"], cad_mix.inputs["Fac"])
    nt.links.new(cad_transp.outputs["BSDF"], cad_mix.inputs[1])
    nt.links.new(cad_emit.outputs["Emission"], cad_mix.inputs[2])

    # --- 3. World-X Split Mask + Glowing Cyan Scanline ---
    geom = nt.nodes.new("ShaderNodeNewGeometry")
    geom.location = (-700, -100)
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    sep.location = (-520, -100)
    nt.links.new(geom.outputs["Position"], sep.inputs["Vector"])

    # Animated split X value node (keyframed later!)
    split_val = nt.nodes.new("ShaderNodeValue")
    split_val.name = "SplitX"
    split_val.location = (-520, -240)
    split_val.outputs[0].default_value = -0.15

    diff = nt.nodes.new("ShaderNodeMath")
    diff.operation = 'SUBTRACT'
    diff.location = (-320, -120)
    nt.links.new(sep.outputs["X"], diff.inputs[0])
    nt.links.new(split_val.outputs["Value"], diff.inputs[1])

    # Smooth transition mask (0 = CAD left, 1 = Metal right)
    mask = nt.nodes.new("ShaderNodeMapRange")
    mask.location = (-120, -120)
    mask.inputs["From Min"].default_value = -0.04
    mask.inputs["From Max"].default_value = 0.04
    mask.inputs["To Min"].default_value = 0.0
    mask.inputs["To Max"].default_value = 1.0
    nt.links.new(diff.outputs["Value"], mask.inputs["Value"])

    # Scanline glow right at |X - split_x| < 0.035
    abs_diff = nt.nodes.new("ShaderNodeMath")
    abs_diff.operation = 'ABSOLUTE'
    abs_diff.location = (-120, -560)
    nt.links.new(diff.outputs["Value"], abs_diff.inputs[0])

    scan_mask = nt.nodes.new("ShaderNodeMapRange")
    scan_mask.location = (80, -560)
    scan_mask.inputs["From Min"].default_value = 0.0
    scan_mask.inputs["From Max"].default_value = 0.018
    scan_mask.inputs["To Min"].default_value = 1.0
    scan_mask.inputs["To Max"].default_value = 0.0
    nt.links.new(abs_diff.outputs["Value"], scan_mask.inputs["Value"])

    scan_emit = nt.nodes.new("ShaderNodeEmission")
    scan_emit.location = (320, -560)
    scan_emit.inputs["Color"].default_value = (0.35, 0.92, 0.96, 1.0)
    scan_emit.inputs["Strength"].default_value = 5.5

    # Combine CAD & Metal
    mix_main = nt.nodes.new("ShaderNodeMixShader")
    mix_main.location = (640, 40)
    nt.links.new(mask.outputs["Result"], mix_main.inputs["Fac"])
    nt.links.new(cad_mix.outputs["Shader"], mix_main.inputs[1])
    nt.links.new(bsdf.outputs["BSDF"], mix_main.inputs[2])

    # Add scanline highlight
    mix_scan = nt.nodes.new("ShaderNodeMixShader")
    mix_scan.location = (780, 0)
    nt.links.new(scan_mask.outputs["Result"], mix_scan.inputs["Fac"])
    nt.links.new(mix_main.outputs["Shader"], mix_scan.inputs[1])
    nt.links.new(scan_emit.outputs["Emission"], mix_scan.inputs[2])

    nt.links.new(mix_scan.outputs["Shader"], out.inputs["Surface"])
    return mat


def assign_mat(obj, mat):
    if obj.data.materials:
        obj.data.materials[0] = mat
    else:
        obj.data.materials.append(mat)


def build_bearing(name, r_outer, r_inner, width, loc, parent, mat_chrome, mat_cage, n_balls=8):
    """Build a realistic ball bearing (outer race, inner race, chrome balls, dark cage)."""
    empty = bpy.data.objects.new(name, None)
    bpy.context.collection.objects.link(empty)
    empty.location = loc
    empty.parent = parent

    race_t = (r_outer - r_inner) * 0.28
    r_mid = (r_outer + r_inner) / 2.0
    r_ball = (r_outer - r_inner - 2 * race_t) * 0.52

    outer_r = add_tube(f"{name}_outer", r_outer, r_outer - race_t, width, chamfer=0.008)
    outer_r.parent = empty
    assign_mat(outer_r, mat_chrome)

    inner_r = add_tube(f"{name}_inner", r_inner + race_t, r_inner, width, chamfer=0.008)
    inner_r.parent = empty
    assign_mat(inner_r, mat_chrome)

    cage = add_tube(f"{name}_cage", r_mid + r_ball * 0.45, r_mid - r_ball * 0.45, width * 0.48, chamfer=0.004)
    cage.parent = empty
    assign_mat(cage, mat_cage)

    for b in range(n_balls):
        ang = 2 * math.pi * b / n_balls
        bpy.ops.mesh.primitive_uv_sphere_add(
            segments=16, ring_count=10, radius=r_ball,
            location=(r_mid * math.cos(ang), r_mid * math.sin(ang), 0.0)
        )
        ball = bpy.context.active_object
        ball.name = f"{name}_ball_{b}"
        for p in ball.data.polygons:
            p.use_smooth = True
        ball.parent = empty
        assign_mat(ball, mat_chrome)

    return empty


def build_hex_bolt(name, r_head, height, loc, parent, mat_bolt):
    """Build a realistic socket-head cap screw (M-style industrial bolt)."""
    bolt = add_cylinder(name, r_head, height, loc=loc, verts=24, bevel=0.008)
    bolt.parent = parent
    assign_mat(bolt, mat_bolt)
    # Recessed hex socket cap detail (dark ring)
    cap = add_cylinder(f"{name}_hex", r_head * 0.52, height * 0.25,
                       loc=(loc[0], loc[1], loc[2] + height * 0.42), verts=6, bevel=0.002)
    cap.parent = parent
    assign_mat(cap, mat_bolt)
    return bolt


def build_gearbox_scene():
    clear_scene()

    # Create materials
    mat_gunmetal = make_split_material("GunmetalSteel", (0.34, 0.39, 0.46), metallic=1.0, roughness=0.24, bump_strength=0.022)
    mat_steel = make_split_material("BrushedSteel", (0.64, 0.69, 0.75), metallic=1.0, roughness=0.20, bump_strength=0.018)
    mat_dark_housing = make_split_material("DarkHousing", (0.22, 0.27, 0.33), metallic=0.95, roughness=0.28, bump_strength=0.025)
    mat_chrome = make_split_material("Chrome", (0.82, 0.86, 0.90), metallic=1.0, roughness=0.06, bump_strength=0.005, bevel_radius=0.005)
    mat_bolt = make_split_material("BlackOxide", (0.13, 0.15, 0.18), metallic=0.92, roughness=0.30, bump_strength=0.015, bevel_radius=0.005)
    mat_bronze = make_split_material("BearingBronze", (0.62, 0.46, 0.24), metallic=1.0, roughness=0.24, bump_strength=0.02, bevel_radius=0.008)

    all_materials = [mat_gunmetal, mat_steel, mat_dark_housing, mat_chrome, mat_bolt, mat_bronze]

    # Root assembly empty (tilted slightly for dramatic 3/4 silhouette)
    root = bpy.data.objects.new("GearboxRoot", None)
    bpy.context.collection.objects.link(root)

    # ------------------------------------------------------------------
    # 1. FIXED INTERNAL RING GEAR + MACHINED FLANGE HOUSING
    # ------------------------------------------------------------------
    ring_inner_pts, r_ring_tip, r_ring_root = build_internal_gear_profile(Z_RING, MODULE)
    r_ring_outer = R_RING + 0.58  # 2.98
    ring_outer_pts = [
        (r_ring_outer * math.cos(math.atan2(y, x)), r_ring_outer * math.sin(math.atan2(y, x)))
        for x, y in ring_inner_pts
    ]
    ring_gear = create_extruded_ring_mesh(
        "RingGear", ring_outer_pts, ring_inner_pts, GEAR_THICKNESS + 0.14, chamfer=0.014, z_offset=0.0
    )
    ring_gear.parent = root
    ring_gear.rotation_euler = (0.0, 0.0, math.pi / Z_RING)
    assign_mat(ring_gear, mat_dark_housing)

    # Front & rear chamfered housing bezel rings
    bezel_f = add_tube("RingBezelFront", r_ring_outer + 0.18, r_ring_outer - 0.16, 0.16, loc=(0, 0, 0.24), verts=96, chamfer=0.022)
    bezel_f.parent = root
    assign_mat(bezel_f, mat_steel)

    bezel_b = add_tube("RingBezelBack", r_ring_outer + 0.22, R_RING - 0.1, 0.18, loc=(0, 0, -0.34), verts=96, chamfer=0.022)
    bezel_b.parent = root
    assign_mat(bezel_b, mat_dark_housing)

    # 12 Perimeter socket-head mounting bolts on the outer flange
    for i in range(12):
        ang = 2 * math.pi * i / 12.0 + math.pi / 12.0
        r_b = r_ring_outer + 0.01
        build_hex_bolt(
            f"FlangeBolt_{i}", 0.075, 0.08,
            loc=(r_b * math.cos(ang), r_b * math.sin(ang), 0.34),
            parent=root, mat_bolt=mat_bolt
        )

    # ------------------------------------------------------------------
    # 2. SUN GEAR + INPUT SHAFT ASSEMBLY
    # ------------------------------------------------------------------
    sun_empty = bpy.data.objects.new("SunAssembly", None)
    bpy.context.collection.objects.link(sun_empty)
    sun_empty.parent = root

    sun_pts, r_sun_root, _ = build_external_gear_profile(Z_SUN, MODULE)
    sun_gear = create_extruded_ring_mesh("SunGear", sun_pts, [0.46], GEAR_THICKNESS + 0.04, chamfer=0.014)
    sun_gear.parent = sun_empty
    assign_mat(sun_gear, mat_steel)

    # Bronze inner collar + central input shaft
    sun_collar = add_tube("SunCollar", 0.56, 0.36, GEAR_THICKNESS + 0.16, loc=(0, 0, 0.04), verts=48, chamfer=0.012)
    sun_collar.parent = sun_empty
    assign_mat(sun_collar, mat_bronze)

    sun_shaft = add_tube("SunShaft", 0.36, 0.18, 2.2, loc=(0, 0, -0.15), verts=48, chamfer=0.018)
    sun_shaft.parent = sun_empty
    assign_mat(sun_shaft, mat_chrome)

    # Central front nut/cap detail
    sun_cap = add_tube("SunFrontCap", 0.42, 0.22, 0.14, loc=(0, 0, 0.92), verts=6, chamfer=0.01)
    sun_cap.parent = sun_empty
    assign_mat(sun_cap, mat_bolt)

    # ------------------------------------------------------------------
    # 3. PLANET CARRIER + 4 MESHING PLANET GEARS WITH BALL BEARINGS
    # ------------------------------------------------------------------
    carrier_empty = bpy.data.objects.new("CarrierAssembly", None)
    bpy.context.collection.objects.link(carrier_empty)
    carrier_empty.parent = root

    # Rear CNC carrier plate (sits cleanly behind the planets so front stays wide open!)
    rear_carrier = add_tube("RearCarrierPlate", R_ORBIT + 0.34, 0.52, 0.18, loc=(0, 0, -0.42), verts=64, chamfer=0.018)
    rear_carrier.parent = carrier_empty
    assign_mat(rear_carrier, mat_steel)

    # Rear output drum & secondary stepped spur gear (adds depth when orbiting!)
    out_drum = add_tube("OutputDrum", 1.35, 0.56, 0.55, loc=(0, 0, -0.78), verts=64, chamfer=0.02)
    out_drum.parent = carrier_empty
    assign_mat(out_drum, mat_dark_housing)

    sec_pts, _, _ = build_external_gear_profile(32, 0.11)
    sec_gear = create_extruded_ring_mesh("SecondaryGear", sec_pts, [1.28], 0.32, chamfer=0.014, z_offset=-1.02)
    sec_gear.parent = carrier_empty
    assign_mat(sec_gear, mat_gunmetal)

    # Rear output bearing housing
    out_collar = add_tube("OutputCollar", 0.92, 0.42, 0.42, loc=(0, 0, -1.32), verts=48, chamfer=0.02)
    out_collar.parent = carrier_empty
    assign_mat(out_collar, mat_steel)

    # Build 4 planets
    planet_pts, r_planet_root, _ = build_external_gear_profile(Z_PLANET, MODULE)
    planet_empties = []

    for i in range(N_PLANETS):
        ang = i * (2.0 * math.pi / N_PLANETS)
        px = R_ORBIT * math.cos(ang)
        py = R_ORBIT * math.sin(ang)

        # Planet rotating empty
        p_empty = bpy.data.objects.new(f"Planet_{i}", None)
        bpy.context.collection.objects.link(p_empty)
        p_empty.location = (px, py, 0.0)
        p_empty.parent = carrier_empty
        # Phase alignment: Sun has tooth crest at ang=0 -> planet needs tooth SPACE at ang=pi
        # Since Z_PLANET=12 is even, rotating planet by pi/Z_PLANET puts a space at 0 and pi!
        p_empty.rotation_euler = (0.0, 0.0, ang + math.pi / Z_PLANET)
        planet_empties.append((p_empty, ang + math.pi / Z_PLANET))

        p_gear = create_extruded_ring_mesh(
            f"PlanetGear_{i}", planet_pts, [0.42], GEAR_THICKNESS, chamfer=0.014
        )
        p_gear.parent = p_empty
        assign_mat(p_gear, mat_gunmetal)

        # Bronze inner spacer ring
        p_ring = add_tube(f"PlanetBronze_{i}", 0.46, 0.39, GEAR_THICKNESS - 0.06, chamfer=0.008)
        p_ring.parent = p_empty
        assign_mat(p_ring, mat_bronze)

        # Precision ball bearing inside each planet!
        build_bearing(
            f"PlanetBearing_{i}", r_outer=0.39, r_inner=0.19, width=GEAR_THICKNESS - 0.08,
            loc=(0, 0, 0.0), parent=p_empty, mat_chrome=mat_chrome, mat_cage=mat_bolt, n_balls=8
        )

        # Fixed carrier pin + front hex cap bolt (parented to carrier, NOT rotating with planet!)
        pin = add_cylinder(f"PlanetPin_{i}", 0.19, 0.82, loc=(px, py, -0.06), verts=32, bevel=0.012)
        pin.parent = carrier_empty
        assign_mat(pin, mat_steel)

        build_hex_bolt(
            f"PlanetCapBolt_{i}", 0.14, 0.09,
            loc=(px, py, 0.35),
            parent=carrier_empty, mat_bolt=mat_bolt
        )

        # Sleek bridge arm connecting rear carrier to next planet pin on rear side
        arm_ang = ang + math.pi / N_PLANETS
        arm_r = R_ORBIT * 0.92
        bpy.ops.mesh.primitive_cube_add(size=1.0, location=(arm_r * math.cos(arm_ang), arm_r * math.sin(arm_ang), -0.42))
        arm = bpy.context.active_object
        arm.name = f"CarrierSpoke_{i}"
        arm.scale = (0.28, 1.45, 0.14)
        arm.rotation_euler = (0, 0, arm_ang)
        mod = arm.modifiers.new("Bevel", 'BEVEL')
        mod.width = 0.02
        mod.segments = 2
        arm.parent = carrier_empty
        assign_mat(arm, mat_dark_housing)

    # ------------------------------------------------------------------
    # 4. SUBTLE DARK BLUEPRINT GRID BACKDROP
    # ------------------------------------------------------------------
    bpy.ops.mesh.primitive_plane_add(size=60.0, location=(0, 0, -5.5))
    bg = bpy.context.active_object
    bg.name = "BlueprintBackdrop"
    bg_mat = bpy.data.materials.new("BackdropGrid")
    bg_mat.use_nodes = True
    nt = bg_mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    emit = nt.nodes.new("ShaderNodeEmission")
    emit.inputs["Strength"].default_value = 1.0

    tc = nt.nodes.new("ShaderNodeTexCoord")
    brick = nt.nodes.new("ShaderNodeTexBrick")
    brick.offset = 0.0
    brick.inputs["Scale"].default_value = 34.0
    brick.inputs["Mortar Size"].default_value = 0.014
    brick.inputs["Mortar Smooth"].default_value = 0.3
    brick.inputs["Brick Width"].default_value = 1.0
    brick.inputs["Row Height"].default_value = 1.0
    brick.inputs["Color1"].default_value = (0.008, 0.015, 0.026, 1.0)
    brick.inputs["Color2"].default_value = (0.008, 0.015, 0.026, 1.0)
    brick.inputs["Mortar"].default_value = (0.028, 0.11, 0.14, 1.0)
    nt.links.new(tc.outputs["Object"], brick.inputs["Vector"])
    nt.links.new(brick.outputs["Color"], emit.inputs["Color"])
    nt.links.new(emit.outputs["Emission"], out.inputs["Surface"])
    assign_mat(bg, bg_mat)

    # ------------------------------------------------------------------
    # 5. STUDIO LIGHTING (Dramatic Engineering Key + Cyan Rim + Dark World)
    # ------------------------------------------------------------------
    world = bpy.data.worlds.new("StudioWorld")
    bpy.context.scene.world = world
    world.use_nodes = True
    wnt = world.node_tree
    bg_node = wnt.nodes.get("Background")
    bg_node.inputs["Color"].default_value = (0.007, 0.013, 0.022, 1.0)
    bg_node.inputs["Strength"].default_value = 0.45

    def add_area_light(name, loc, rot_deg, energy, size, color):
        ldata = bpy.data.lights.new(name, type='AREA')
        ldata.energy = energy
        ldata.size = size
        ldata.color = color
        lobj = bpy.data.objects.new(name, ldata)
        bpy.context.collection.objects.link(lobj)
        lobj.location = loc
        lobj.rotation_euler = tuple(math.radians(a) for a in rot_deg)
        return lobj

    # Broad overhead-right studio softbox (creates silky metallic gradients on CNC faces!)
    add_area_light("SoftboxTopRight", (4.8, 4.5, 8.5), (26, 26, -20), 720, 9.5, (0.92, 0.96, 1.0))
    # Front-right angled specular strip (highlights bevels & gear flanks)
    add_area_light("KeyStripRight", (6.5, -1.5, 5.8), (12, 46, 0), 460, 5.5, (0.88, 0.93, 1.0))
    # Subtle lower bounce so bottom teeth & bearings show detail
    add_area_light("FillLower", (2.0, -6.5, 6.0), (-42, 12, 0), 220, 7.5, (0.80, 0.88, 0.96))
    # Cyan engineering rim light from left (echoes the blueprint glow!)
    add_area_light("RimCyanLeft", (-7.5, 1.5, 3.2), (10, -64, 0), 650, 6.5, (0.38, 0.92, 0.96))
    # Top-back rim light to outline the outer housing ring
    add_area_light("RimTopBack", (1.2, 6.8, -1.2), (102, 0, 180), 520, 6.5, (0.82, 0.93, 1.0))

    # ------------------------------------------------------------------
    # 6. CAMERA + SMOOTH CINEMATIC SCROLL ANIMATION
    # ------------------------------------------------------------------
    cam_data = bpy.data.cameras.new("MainCamera")
    cam_data.lens = 52.0
    cam_data.dof.use_dof = True
    cam_data.dof.focus_distance = 13.8
    cam_data.dof.aperture_fstop = 5.6
    cam_obj = bpy.data.objects.new("MainCamera", cam_data)
    bpy.context.collection.objects.link(cam_obj)
    bpy.context.scene.camera = cam_obj

    target = bpy.data.objects.new("CamTarget", None)
    bpy.context.collection.objects.link(target)

    return root, sun_empty, carrier_empty, planet_empties, cam_obj, target, all_materials


def animate_scene(root, sun_empty, carrier_empty, planet_empties, cam_obj, target, all_materials, total_frames):
    scene = bpy.context.scene
    scene.frame_start = 1
    scene.frame_end = total_frames
    scene.render.fps = 24

    # Sun turns 3.5 full revolutions over the full scroll -> carrier turns 1.0 full revolution!
    # Exact ratio: carrier = (16/56) * sun = (2/7) * sun -> sun = 3.5 * 2pi => carrier = 1.0 * 2pi!
    sun_total = 3.5 * 2.0 * math.pi
    carrier_total = (Z_SUN / (Z_SUN + Z_RING)) * sun_total
    planet_local_total = -(Z_RING / Z_PLANET) * carrier_total

    def set_linear(obj, data_path):
        if obj.animation_data and obj.animation_data.action:
            action = obj.animation_data.action
            # Blender 5.0+ slotted actions or legacy fcurves
            fcurves = []
            if hasattr(action, "fcurves"):
                fcurves = action.fcurves
            elif hasattr(action, "layers"):
                for layer in action.layers:
                    for strip in layer.strips:
                        for bag in strip.channelbags:
                            fcurves.extend(bag.fcurves)
            for fc in fcurves:
                if fc.data_path == data_path:
                    for kp in fc.keyframe_points:
                        kp.interpolation = 'LINEAR'

    # Keyframe exact kinematics (linear so scroll progress == constant mechanical speed)
    sun_empty.rotation_euler = (0, 0, 0)
    sun_empty.keyframe_insert(data_path="rotation_euler", frame=1)
    sun_empty.rotation_euler = (0, 0, sun_total)
    sun_empty.keyframe_insert(data_path="rotation_euler", frame=total_frames)
    set_linear(sun_empty, "rotation_euler")

    carrier_empty.rotation_euler = (0, 0, 0)
    carrier_empty.keyframe_insert(data_path="rotation_euler", frame=1)
    carrier_empty.rotation_euler = (0, 0, carrier_total)
    carrier_empty.keyframe_insert(data_path="rotation_euler", frame=total_frames)
    set_linear(carrier_empty, "rotation_euler")

    for p_empty, init_rot in planet_empties:
        p_empty.rotation_euler = (0, 0, init_rot)
        p_empty.keyframe_insert(data_path="rotation_euler", frame=1)
        p_empty.rotation_euler = (0, 0, init_rot + planet_local_total)
        p_empty.keyframe_insert(data_path="rotation_euler", frame=total_frames)
        set_linear(p_empty, "rotation_euler")

    # Smooth cinematic camera glide:
    # Frame 1 (Hero): centered, iconic slight 3/4 view showing both CAD left & steel right
    # Mid-scroll: graceful orbit right & slightly down to reveal the 3D thickness & bearings
    # End-scroll: closer dramatic macro angle on the meshing gears
    # Direct upright camera keyframes: (frame, cam_loc, cam_rot_deg_xyz, split_x)
    # Zero gimbal lock -> split plane stays rock-solid vertical while camera orbits & zooms!
    cam_keys = [
        (1,                        (0.0,  0.0,  15.6), ( 0.0,  0.0, 0.0),  0.00),
        (int(total_frames * 0.35), (3.8, -0.5,  13.2), ( 2.5, 16.0, 0.0), -0.45),
        (int(total_frames * 0.70), (5.2, -1.1,  10.2), ( 6.5, 25.5, 0.0), -1.15),
        (total_frames,             (2.2, -0.9,   8.2), ( 6.0, 14.0, 0.0), -0.10),
    ]

    for fr, cloc, crot_deg, split_x in cam_keys:
        cam_obj.location = cloc
        cam_obj.keyframe_insert(data_path="location", frame=fr)
        cam_obj.rotation_euler = tuple(math.radians(a) for a in crot_deg)
        cam_obj.keyframe_insert(data_path="rotation_euler", frame=fr)
        for mat in all_materials:
            sv = mat.node_tree.nodes.get("SplitX")
            if sv:
                sv.outputs[0].default_value = split_x
                sv.outputs[0].keyframe_insert(data_path="default_value", frame=fr)


def configure_render(res_x=1280, res_y=720, samples=20):
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = samples
    scene.cycles.use_adaptive_sampling = True
    scene.cycles.adaptive_threshold = 0.03
    scene.render.use_persistent_data = True
    scene.cycles.use_denoising = True
    scene.cycles.denoising_input_passes = 'RGB_ALBEDO_NORMAL'
    scene.cycles.max_bounces = 6
    scene.cycles.diffuse_bounces = 2
    scene.cycles.glossy_bounces = 3
    scene.cycles.transmission_bounces = 4
    scene.cycles.transparent_max_bounces = 6

    scene.render.resolution_x = res_x
    scene.render.resolution_y = res_y
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGB'

    # Filmic / AgX tone mapping for rich cinematic contrast
    scene.view_settings.view_transform = 'AgX'
    try:
        scene.view_settings.look = 'AgX - Medium High Contrast'
    except Exception:
        pass
    scene.view_settings.exposure = -0.35


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["preview", "anim"], default="preview")
    parser.add_argument("--out", required=True)
    parser.add_argument("--frames", type=int, default=180)
    parser.add_argument("--samples", type=int, default=20)
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--end", type=int, default=0)
    args = parser.parse_args(argv)

    os.makedirs(args.out, exist_ok=True)
    root, sun_e, car_e, plan_es, cam, tgt, mats = build_gearbox_scene()
    animate_scene(root, sun_e, car_e, plan_es, cam, tgt, mats, args.frames)
    configure_render(1280, 720, samples=args.samples)

    scene = bpy.context.scene
    if args.mode == "preview":
        # Render Hero frame 1, Mid frame, and End close-up frame
        for label, fr in [("hero", 1), ("mid", int(args.frames * 0.45)), ("close", args.frames)]:
            scene.frame_set(fr)
            scene.render.filepath = os.path.join(args.out, f"preview_{label}.png")
            bpy.ops.render.render(write_still=True)
    else:
        scene.frame_start = args.start
        scene.frame_end = args.end if args.end > 0 else args.frames
        scene.render.filepath = os.path.join(args.out, "frame_")
        bpy.ops.render.render(animation=True)


if __name__ == "__main__":
    main()
