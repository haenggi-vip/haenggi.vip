"""Build and render a cinematic 3D Engineering-to-Digitalization scroll video in Blender 5.3.

Theme: Precision dark obsidian PCB & titanium/glass processor core with animated
cyan/violet data pulses, gold vias, SMD components, and a floating holographic
digital ring constellation.

Usage:
  blender --background --python build_digital_core.py -- --mode preview --out /tmp/preview
  blender --background --python build_digital_core.py -- --mode anim --out /tmp/frames --frames 120
"""
import argparse
import math
import os
import random
import sys
import bpy
import bmesh
from mathutils import Vector


def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def set_linear(obj, data_path):
    if obj.animation_data and obj.animation_data.action:
        action = obj.animation_data.action
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


def assign_mat(obj, mat):
    if obj.data.materials:
        obj.data.materials[0] = mat
    else:
        obj.data.materials.append(mat)


def add_beveled_box(name, size_xyz, loc=(0, 0, 0), rot=(0, 0, 0), bevel=0.02, mat=None, parent=None):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc, rotation=rot)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = size_xyz
    bpy.ops.object.transform_apply(scale=True)
    if bevel > 0:
        mod = obj.modifiers.new("Bevel", 'BEVEL')
        mod.width = bevel
        mod.segments = 2
        mod.limit_method = 'ANGLE'
    for p in obj.data.polygons:
        p.use_smooth = True
    es = obj.modifiers.new("EdgeSplit", 'EDGE_SPLIT')
    es.split_angle = math.radians(32.0)
    if mat:
        assign_mat(obj, mat)
    if parent:
        obj.parent = parent
    return obj


def add_beveled_cyl(name, radius, depth, loc=(0, 0, 0), rot=(0, 0, 0), verts=48, bevel=0.012, mat=None, parent=None):
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
    if mat:
        assign_mat(obj, mat)
    if parent:
        obj.parent = parent
    return obj


def add_ring_torus(name, major_r, minor_r, loc=(0, 0, 0), rot=(0, 0, 0), maj_seg=96, min_seg=16, mat=None, parent=None):
    bpy.ops.mesh.primitive_torus_add(
        major_radius=major_r, minor_radius=minor_r,
        major_segments=maj_seg, minor_segments=min_seg,
        location=loc, rotation=rot
    )
    obj = bpy.context.active_object
    obj.name = name
    for p in obj.data.polygons:
        p.use_smooth = True
    if mat:
        assign_mat(obj, mat)
    if parent:
        obj.parent = parent
    return obj


# ---------------------------------------------------------------------------
# Materials
# ---------------------------------------------------------------------------
def make_metal_mat(name, color, metallic=1.0, roughness=0.20, bump=0.005, coat=0.12, bevel_r=0.008):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()

    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    if "Coat Weight" in bsdf.inputs:
        bsdf.inputs["Coat Weight"].default_value = coat
        bsdf.inputs["Coat Roughness"].default_value = 0.12

    tc = nt.nodes.new("ShaderNodeTexCoord")
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 220.0
    noise.inputs["Detail"].default_value = 8.0
    nt.links.new(tc.outputs["Object"], noise.inputs["Vector"])

    rmap = nt.nodes.new("ShaderNodeMapRange")
    rmap.inputs["From Min"].default_value = 0.25
    rmap.inputs["From Max"].default_value = 0.75
    rmap.inputs["To Min"].default_value = max(0.04, roughness - 0.025)
    rmap.inputs["To Max"].default_value = min(0.85, roughness + 0.03)
    nt.links.new(noise.outputs["Fac"], rmap.inputs["Value"])
    nt.links.new(rmap.outputs["Result"], bsdf.inputs["Roughness"])

    bev = nt.nodes.new("ShaderNodeBevel")
    bev.samples = 4
    bev.inputs["Radius"].default_value = bevel_r

    bmp = nt.nodes.new("ShaderNodeBump")
    bmp.inputs["Strength"].default_value = bump
    bmp.inputs["Distance"].default_value = 0.003
    nt.links.new(noise.outputs["Fac"], bmp.inputs["Height"])
    nt.links.new(bev.outputs["Normal"], bmp.inputs["Normal"])
    nt.links.new(bmp.outputs["Normal"], bsdf.inputs["Normal"])

    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat


def make_pcb_substrate_mat():
    """Deep dark-obsidian matte solder-mask PCB with subtle micro-grid texture."""
    mat = bpy.data.materials.new("PCBSubstrate")
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Metallic"].default_value = 0.18
    bsdf.inputs["Roughness"].default_value = 0.34
    if "Coat Weight" in bsdf.inputs:
        bsdf.inputs["Coat Weight"].default_value = 0.35
        bsdf.inputs["Coat Roughness"].default_value = 0.18

    tc = nt.nodes.new("ShaderNodeTexCoord")
    brick = nt.nodes.new("ShaderNodeTexBrick")
    brick.offset = 0.0
    brick.inputs["Scale"].default_value = 18.0
    brick.inputs["Mortar Size"].default_value = 0.018
    brick.inputs["Mortar Smooth"].default_value = 0.2
    brick.inputs["Brick Width"].default_value = 1.0
    brick.inputs["Row Height"].default_value = 1.0
    brick.inputs["Color1"].default_value = (0.010, 0.018, 0.028, 1.0)
    brick.inputs["Color2"].default_value = (0.012, 0.021, 0.032, 1.0)
    brick.inputs["Mortar"].default_value = (0.020, 0.045, 0.062, 1.0)
    nt.links.new(tc.outputs["Object"], brick.inputs["Vector"])
    nt.links.new(brick.outputs["Color"], bsdf.inputs["Base Color"])

    bmp = nt.nodes.new("ShaderNodeBump")
    bmp.inputs["Strength"].default_value = 0.04
    bmp.inputs["Distance"].default_value = 0.002
    nt.links.new(brick.outputs["Fac"], bmp.inputs["Height"])
    nt.links.new(bmp.outputs["Normal"], bsdf.inputs["Normal"])

    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat


def make_silicon_die_mat():
    """Iridescent dark mirror-silicon die with subtle micro-circuit sheen."""
    mat = bpy.data.materials.new("SiliconDie")
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Metallic"].default_value = 0.92
    bsdf.inputs["Roughness"].default_value = 0.08
    if "Coat Weight" in bsdf.inputs:
        bsdf.inputs["Coat Weight"].default_value = 0.8
        bsdf.inputs["Coat Roughness"].default_value = 0.04

    lw = nt.nodes.new("ShaderNodeLayerWeight")
    lw.inputs["Blend"].default_value = 0.35
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.15
    ramp.color_ramp.elements[0].color = (0.02, 0.04, 0.07, 1.0)
    e1 = ramp.color_ramp.elements.new(0.55)
    e1.color = (0.06, 0.24, 0.30, 1.0)
    ramp.color_ramp.elements[-1].position = 0.90
    ramp.color_ramp.elements[-1].color = (0.28, 0.22, 0.48, 1.0)
    nt.links.new(lw.outputs["Facing"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])

    # Subtle circuit grid etched onto silicon die
    tc = nt.nodes.new("ShaderNodeTexCoord")
    brick = nt.nodes.new("ShaderNodeTexBrick")
    brick.offset = 0.0
    brick.inputs["Scale"].default_value = 26.0
    brick.inputs["Mortar Size"].default_value = 0.05
    brick.inputs["Brick Width"].default_value = 1.0
    brick.inputs["Row Height"].default_value = 1.0
    brick.inputs["Color1"].default_value = (0.0, 0.0, 0.0, 1.0)
    brick.inputs["Color2"].default_value = (0.0, 0.0, 0.0, 1.0)
    brick.inputs["Mortar"].default_value = (0.20, 0.85, 0.92, 1.0)
    nt.links.new(tc.outputs["Object"], brick.inputs["Vector"])
    if "Emission Color" in bsdf.inputs:
        nt.links.new(brick.outputs["Color"], bsdf.inputs["Emission Color"])
        bsdf.inputs["Emission Strength"].default_value = 1.1

    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat


def make_glass_mat():
    mat = bpy.data.materials.new("OpticalGlass")
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = (0.78, 0.95, 1.0, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.04
    bsdf.inputs["IOR"].default_value = 1.52
    if "Transmission Weight" in bsdf.inputs:
        bsdf.inputs["Transmission Weight"].default_value = 0.92
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat


def make_emission_mat(name, color, strength=6.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (*color, 1.0)
    em.inputs["Strength"].default_value = strength
    nt.links.new(em.outputs["Emission"], out.inputs["Surface"])
    return mat


def make_holo_ring_mat(name, color, strength=2.6):
    """Translucent glowing holographic ring shader."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    lw = nt.nodes.new("ShaderNodeLayerWeight")
    lw.inputs["Blend"].default_value = 0.35
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (*color, 1.0)
    em.inputs["Strength"].default_value = strength
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    tr.inputs["Color"].default_value = (0.85, 0.95, 1.0, 1.0)
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(lw.outputs["Facing"], mix.inputs["Fac"])
    nt.links.new(tr.outputs["BSDF"], mix.inputs[1])
    nt.links.new(em.outputs["Emission"], mix.inputs[2])
    nt.links.new(mix.outputs["Shader"], out.inputs["Surface"])
    return mat


def make_pulse_trace_mat(name, base_metal_color, pulse_color, phase_offset=0.0):
    """Copper/cyan PCB trace with an animated radial data-pulse wave traveling outward!"""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")

    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = (*base_metal_color, 1.0)
    bsdf.inputs["Metallic"].default_value = 1.0
    bsdf.inputs["Roughness"].default_value = 0.22

    # Compute radial distance from center (0, 0) in world space
    geom = nt.nodes.new("ShaderNodeNewGeometry")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(geom.outputs["Position"], sep.inputs["Vector"])

    # R = sqrt(X^2 + Y^2)
    comb = nt.nodes.new("ShaderNodeCombineXYZ")
    nt.links.new(sep.outputs["X"], comb.inputs["X"])
    nt.links.new(sep.outputs["Y"], comb.inputs["Y"])
    vlen = nt.nodes.new("ShaderNodeVectorMath")
    vlen.operation = 'LENGTH'
    nt.links.new(comb.outputs["Vector"], vlen.inputs[0])

    # Animated phase node (keyframed!)
    phase = nt.nodes.new("ShaderNodeValue")
    phase.name = "PulsePhase"
    phase.outputs[0].default_value = phase_offset

    # wave = sin(R * 1.35 - phase)
    mul = nt.nodes.new("ShaderNodeMath")
    mul.operation = 'MULTIPLY'
    mul.inputs[1].default_value = 1.35
    nt.links.new(vlen.outputs["Value"], mul.inputs[0])

    sub = nt.nodes.new("ShaderNodeMath")
    sub.operation = 'SUBTRACT'
    nt.links.new(mul.outputs["Value"], sub.inputs[0])
    nt.links.new(phase.outputs["Value"], sub.inputs[1])

    sine = nt.nodes.new("ShaderNodeMath")
    sine.operation = 'SINE'
    nt.links.new(sub.outputs["Value"], sine.inputs[0])

    # Sharp pulse peak when sin > 0.72
    pulse_map = nt.nodes.new("ShaderNodeMapRange")
    pulse_map.inputs["From Min"].default_value = 0.72
    pulse_map.inputs["From Max"].default_value = 0.99
    pulse_map.inputs["To Min"].default_value = 0.08
    pulse_map.inputs["To Max"].default_value = 10.5
    nt.links.new(sine.outputs["Value"], pulse_map.inputs["Value"])

    if "Emission Color" in bsdf.inputs:
        bsdf.inputs["Emission Color"].default_value = (*pulse_color, 1.0)
        nt.links.new(pulse_map.outputs["Result"], bsdf.inputs["Emission Strength"])

    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat


def add_trace_polyline(name, points_xy, z, width, height, mat, parent):
    """Build a crisp 3D extruded PCB copper trace along a 2D polyline (45-deg routing!)."""
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    hw = width / 2.0

    # Create a clean flat ribbon per segment with chamfered joints
    for idx in range(len(points_xy) - 1):
        p0 = Vector((points_xy[idx][0], points_xy[idx][1], z))
        p1 = Vector((points_xy[idx + 1][0], points_xy[idx + 1][1], z))
        d = p1 - p0
        if d.length < 1e-4:
            continue
        perp = Vector((-d.y, d.x, 0.0)).normalized() * hw
        # Extend slightly at joints so corners close cleanly
        ext = d.normalized() * (hw * 0.55)
        a0 = p0 - ext
        a1 = p1 + ext
        v0 = bm.verts.new(a0 - perp)
        v1 = bm.verts.new(a0 + perp)
        v2 = bm.verts.new(a1 + perp)
        v3 = bm.verts.new(a1 - perp)
        v4 = bm.verts.new(a0 - perp + Vector((0, 0, height)))
        v5 = bm.verts.new(a0 + perp + Vector((0, 0, height)))
        v6 = bm.verts.new(a1 + perp + Vector((0, 0, height)))
        v7 = bm.verts.new(a1 - perp + Vector((0, 0, height)))
        bm.faces.new((v4, v5, v6, v7))
        bm.faces.new((v0, v1, v5, v4))
        bm.faces.new((v1, v2, v6, v5))
        bm.faces.new((v2, v3, v7, v6))
        bm.faces.new((v3, v0, v4, v7))

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    assign_mat(obj, mat)
    obj.parent = parent
    return obj


# ---------------------------------------------------------------------------
# Build the Complete Engineering -> Digitalization Scene
# ---------------------------------------------------------------------------
def build_scene():
    clear_scene()
    rng = random.Random(42)

    # Materials
    mat_pcb = make_pcb_substrate_mat()
    mat_titanium = make_metal_mat("DarkTitanium", (0.14, 0.17, 0.22), metallic=0.95, roughness=0.26, bump=0.005)
    mat_steel = make_metal_mat("BrushedSteel", (0.48, 0.54, 0.62), metallic=1.0, roughness=0.20, bump=0.004)
    mat_gold = make_metal_mat("PCBGold", (0.82, 0.62, 0.26), metallic=1.0, roughness=0.16, bump=0.01, bevel_r=0.004)
    mat_copper = make_metal_mat("Copper", (0.76, 0.42, 0.24), metallic=1.0, roughness=0.22, bump=0.004)
    mat_smd_dark = make_metal_mat("SMDBody", (0.04, 0.05, 0.07), metallic=0.2, roughness=0.35, bump=0.01, bevel_r=0.005)
    mat_silicon = make_silicon_die_mat()
    mat_glass = make_glass_mat()

    mat_trace_cyan = make_pulse_trace_mat("TraceCyan", (0.18, 0.36, 0.42), (0.28, 0.94, 0.98), phase_offset=0.0)
    mat_trace_violet = make_pulse_trace_mat("TraceViolet", (0.24, 0.20, 0.38), (0.64, 0.46, 1.0), phase_offset=2.1)
    mat_trace_gold = make_pulse_trace_mat("TraceGold", (0.68, 0.50, 0.22), (0.98, 0.80, 0.36), phase_offset=4.2)

    mat_cyan_glow = make_emission_mat("CyanNode", (0.38, 0.96, 1.0), strength=9.0)
    mat_violet_glow = make_emission_mat("VioletNode", (0.68, 0.50, 1.0), strength=8.5)
    mat_holo_cyan = make_holo_ring_mat("HoloCyan", (0.24, 0.90, 0.98), strength=4.2)
    mat_holo_violet = make_holo_ring_mat("HoloViolet", (0.58, 0.42, 1.0), strength=3.6)

    pulse_mats = [mat_trace_cyan, mat_trace_violet, mat_trace_gold]

    root = bpy.data.objects.new("DigitalCoreRoot", None)
    bpy.context.collection.objects.link(root)

    # ------------------------------------------------------------------
    # 1. MAIN DARK OBSIDIAN PCB MOTHERBOARD PLATFORM
    # ------------------------------------------------------------------
    add_beveled_box("PCBBoard", (16.0, 16.0, 0.22), loc=(0, 0, -0.11), bevel=0.04, mat=mat_pcb, parent=root)

    # Precision recessed aluminum sub-frame around the central core
    add_beveled_box("CoreChassisBase", (5.2, 5.2, 0.16), loc=(0, 0, 0.08), bevel=0.05, mat=mat_titanium, parent=root)
    # 4 Corner mounting hex-bolts on the core chassis
    for sx in (-2.25, 2.25):
        for sy in (-2.25, 2.25):
            add_beveled_cyl(f"ChassisBolt_{sx}_{sy}", 0.13, 0.12, loc=(sx, sy, 0.20), verts=6, bevel=0.012, mat=mat_steel, parent=root)

    # ------------------------------------------------------------------
    # 2. HERO PROCESSOR (SoC): TITANIUM FRAME + SILICON DIE + GLASS + 64 GOLD PINS
    # ------------------------------------------------------------------
    add_beveled_box("SoCSubstrate", (3.2, 3.2, 0.18), loc=(0, 0, 0.24), bevel=0.03, mat=mat_smd_dark, parent=root)
    # Machined titanium heat-spreader bezel (4 rails around central silicon window)
    add_beveled_box("SoCRailN", (2.85, 0.34, 0.16), loc=(0, 1.25, 0.40), bevel=0.025, mat=mat_steel, parent=root)
    add_beveled_box("SoCRailS", (2.85, 0.34, 0.16), loc=(0, -1.25, 0.40), bevel=0.025, mat=mat_steel, parent=root)
    add_beveled_box("SoCRailE", (0.34, 2.18, 0.16), loc=(1.25, 0, 0.40), bevel=0.025, mat=mat_steel, parent=root)
    add_beveled_box("SoCRailW", (0.34, 2.18, 0.16), loc=(-1.25, 0, 0.40), bevel=0.025, mat=mat_steel, parent=root)

    # Exposed mirror silicon die in the center
    add_beveled_box("SiliconDie", (2.05, 2.05, 0.10), loc=(0, 0, 0.36), bevel=0.015, mat=mat_silicon, parent=root)
    # Optical glass cover plate floating just over the silicon die
    add_beveled_box("OpticalCover", (2.14, 2.14, 0.06), loc=(0, 0, 0.46), bevel=0.01, mat=mat_glass, parent=root)

    # 64 Gold Gull-Wing Pins (16 per side) + radiating 45-degree PCB traces!
    n_pins = 12
    for side in range(4):
        rot_z = side * (math.pi / 2.0)
        ca, sa = math.cos(rot_z), math.sin(rot_z)

        def rot_pt(x, y):
            return (x * ca - y * sa, x * sa + y * ca)

        for i in range(n_pins):
            offset = (i - (n_pins - 1) / 2.0) * 0.21
            # Gold pin sticking out of SoC package
            px, py = rot_pt(1.74, offset)
            sx, sy = (0.32, 0.065) if side % 2 == 0 else (0.065, 0.32)
            add_beveled_box(f"Pin_{side}_{i}", (sx, sy, 0.055), loc=(px, py, 0.19), bevel=0.006, mat=mat_gold, parent=root)

            # Radiating 45-deg PCB trace from pin out into the motherboard!
            t_mat = mat_trace_cyan if (i % 3 != 1) else (mat_trace_violet if (i % 6 == 1) else mat_trace_gold)
            spread = offset * 2.55
            p1 = rot_pt(1.88, offset)
            p2 = rot_pt(2.75 + abs(offset) * 0.35, offset)
            p3 = rot_pt(3.90 + abs(offset) * 0.65, spread)
            p4 = rot_pt(6.90 + (i % 3) * 0.45, spread)
            add_trace_polyline(f"Trace_{side}_{i}", [p1, p2, p3, p4], z=0.005, width=0.052, height=0.022, mat=t_mat, parent=root)

            # Gold via pad at trace bend & endpoint
            if i % 2 == 0:
                vx, vy = p3
                add_beveled_cyl(f"Via_{side}_{i}", 0.075, 0.035, loc=(vx, vy, 0.018), verts=20, bevel=0.005, mat=mat_gold, parent=root)
            vx2, vy2 = p4
            add_beveled_cyl(f"ViaEnd_{side}_{i}", 0.09, 0.04, loc=(vx2, vy2, 0.02), verts=20, bevel=0.005, mat=mat_gold, parent=root)

    # ------------------------------------------------------------------
    # 3. SECONDARY HARDWARE MODULES (SMD Chips, Capacitors, Copper Coils, Heatsinks)
    # ------------------------------------------------------------------
    # 4 Diagonal Auxiliary ICs with brushed metallic caps
    for idx, (cx, cy) in enumerate([(4.1, 4.1), (-4.1, 4.1), (-4.1, -4.1), (4.1, -4.1)]):
        add_beveled_box(f"AuxIC_{idx}", (1.35, 1.35, 0.24), loc=(cx, cy, 0.12), bevel=0.025, mat=mat_smd_dark, parent=root)
        add_beveled_box(f"AuxCap_{idx}", (1.05, 1.05, 0.08), loc=(cx, cy, 0.26), bevel=0.015, mat=mat_titanium, parent=root)
        # Tiny cyan status LED on each auxiliary IC
        add_beveled_box(f"AuxLED_{idx}", (0.14, 0.06, 0.04), loc=(cx - 0.38, cy - 0.38, 0.31), bevel=0.005,
                        mat=mat_cyan_glow if idx % 2 == 0 else mat_violet_glow, parent=root)

    # Copper toroidal inductors & aluminum electrolytic capacitors flanking the core
    cap_locs = [
        (3.4, 2.3), (3.4, -2.3), (-3.4, 2.3), (-3.4, -2.3),
        (2.3, 3.4), (-2.3, 3.4), (2.3, -3.4), (-2.3, -3.4),
        (5.4, 2.2), (-5.4, -2.2), (5.4, -2.2), (-5.4, 2.2),
    ]
    for idx, (cx, cy) in enumerate(cap_locs):
        if idx % 3 == 0:
            # Copper-wound inductor ring
            add_ring_torus(f"Coil_{idx}", 0.24, 0.09, loc=(cx, cy, 0.16), maj_seg=32, min_seg=12, mat=mat_copper, parent=root)
            add_beveled_cyl(f"CoilCore_{idx}", 0.16, 0.22, loc=(cx, cy, 0.11), verts=24, bevel=0.01, mat=mat_titanium, parent=root)
        else:
            # Brushed aluminum SMD capacitor
            add_beveled_cyl(f"Cap_{idx}", 0.20, 0.42, loc=(cx, cy, 0.21), verts=28, bevel=0.018, mat=mat_steel, parent=root)
            add_beveled_cyl(f"CapTop_{idx}", 0.15, 0.04, loc=(cx, cy, 0.43), verts=28, bevel=0.005, mat=mat_titanium, parent=root)

    # Fine rows of micro-SMD resistors / capacitors
    for k in range(44):
        ang = rng.uniform(0, 2 * math.pi)
        rad = rng.uniform(2.9, 6.8)
        sx, sy = rad * math.cos(ang), rad * math.sin(ang)
        if abs(sx) < 2.6 and abs(sy) < 2.6:
            continue
        rot_z = (math.pi / 2.0) if rng.random() > 0.5 else 0.0
        add_beveled_box(f"SMD_{k}", (0.26, 0.13, 0.09), loc=(sx, sy, 0.045), rot=(0, 0, rot_z),
                        bevel=0.008, mat=mat_smd_dark, parent=root)
        # Gold end-caps
        dx = 0.12 if rot_z == 0 else 0.0
        dy = 0.12 if rot_z != 0 else 0.0
        add_beveled_box(f"SMDcA_{k}", (0.06, 0.135, 0.095), loc=(sx + dx, sy + dy, 0.048), rot=(0, 0, rot_z),
                        bevel=0.005, mat=mat_gold, parent=root)
        add_beveled_box(f"SMDcB_{k}", (0.06, 0.135, 0.095), loc=(sx - dx, sy - dy, 0.048), rot=(0, 0, rot_z),
                        bevel=0.005, mat=mat_gold, parent=root)

    # ------------------------------------------------------------------
    # 4. FLOATING HOLOGRAPHIC DIGITALIZATION CORE (Rings + Data Constellation)
    # ------------------------------------------------------------------
    holo_group = bpy.data.objects.new("HoloCoreGroup", None)
    bpy.context.collection.objects.link(holo_group)
    holo_group.location = (0, 0, 1.35)
    holo_group.parent = root

    # Three precision nested glowing gyroscope/data rings
    ring1 = add_ring_torus("HoloRingOuter", 2.45, 0.009, loc=(0, 0, 0.0), rot=(math.radians(16), 0, 0),
                           maj_seg=128, min_seg=12, mat=mat_holo_cyan, parent=holo_group)
    ring2 = add_ring_torus("HoloRingMid", 1.82, 0.008, loc=(0, 0, 0.18), rot=(math.radians(-22), math.radians(14), 0),
                           maj_seg=112, min_seg=12, mat=mat_holo_violet, parent=holo_group)
    ring3 = add_ring_torus("HoloRingInner", 1.18, 0.009, loc=(0, 0, 0.34), rot=(math.radians(10), math.radians(-18), 0),
                           maj_seg=96, min_seg=12, mat=mat_holo_cyan, parent=holo_group)

    # Glowing orbital data nodes attached to rings
    for idx, (r_parent, rad, n_nodes, mat_n) in enumerate([
        (ring1, 2.45, 6, mat_cyan_glow),
        (ring2, 1.82, 5, mat_violet_glow),
        (ring3, 1.18, 4, mat_cyan_glow),
    ]):
        for j in range(n_nodes):
            a = 2 * math.pi * j / n_nodes
            bpy.ops.mesh.primitive_uv_sphere_add(
                segments=16, ring_count=10, radius=0.028,
                location=(rad * math.cos(a), rad * math.sin(a), 0.0)
            )
            node = bpy.context.active_object
            node.name = f"HoloNode_{idx}_{j}"
            assign_mat(node, mat_n)
            node.parent = r_parent

    # Floating digital data particles (soft bokeh sparks rising from the PCB)
    beam_group = bpy.data.objects.new("DataBeams", None)
    bpy.context.collection.objects.link(beam_group)
    beam_group.parent = root
    for b in range(42):
        ang = rng.uniform(0, 2 * math.pi)
        rad = rng.uniform(2.1, 7.4)
        bx, by = rad * math.cos(ang), rad * math.sin(ang)
        bz = rng.uniform(0.35, 3.2)
        bm_mat = mat_cyan_glow if b % 3 != 0 else mat_violet_glow
        if b % 2 == 0:
            bpy.ops.mesh.primitive_uv_sphere_add(segments=10, ring_count=6, radius=rng.uniform(0.018, 0.036), location=(bx, by, bz))
        else:
            bpy.ops.mesh.primitive_cube_add(size=rng.uniform(0.03, 0.06), location=(bx, by, bz),
                                            rotation=(rng.uniform(0, 3), rng.uniform(0, 3), rng.uniform(0, 3)))
        dot = bpy.context.active_object
        dot.name = f"DataPacket_{b}"
        assign_mat(dot, bm_mat)
        dot.parent = beam_group

    # ------------------------------------------------------------------
    # 5. STUDIO LIGHTING + DEEP OBSIDIAN WORLD
    # ------------------------------------------------------------------
    world = bpy.data.worlds.new("DigitalWorld")
    bpy.context.scene.world = world
    world.use_nodes = True
    bg_node = world.node_tree.nodes.get("Background")
    bg_node.inputs["Color"].default_value = (0.005, 0.009, 0.016, 1.0)
    bg_node.inputs["Strength"].default_value = 0.35

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

    # Dramatic cool-white key softbox catching titanium bevels & silicon die
    add_area_light("KeySoftbox", (5.5, -4.5, 7.5), (36, 26, 20), 680, 7.5, (0.88, 0.95, 1.0))
    # Electric cyan rim from back-left
    add_area_light("CyanRim", (-7.5, 5.5, 4.8), (52, -38, 130), 620, 6.5, (0.28, 0.92, 0.98))
    # Subtle violet accent from back-right (echoes OpenGames / digital constellation)
    add_area_light("VioletAccent", (6.5, 6.2, 4.2), (55, 30, -140), 420, 5.5, (0.62, 0.45, 1.0))
    # Warm gold grazing accent to make copper coils & gold pins gleam
    add_area_light("GoldGraze", (-3.5, -6.5, 3.2), (-62, -20, 0), 260, 4.5, (1.0, 0.86, 0.65))

    # ------------------------------------------------------------------
    # 6. CAMERA WITH CINEMATIC DEPTH OF FIELD
    # ------------------------------------------------------------------
    cam_data = bpy.data.cameras.new("MainCamera")
    cam_data.lens = 42.0
    cam_data.dof.use_dof = True
    cam_data.dof.focus_distance = 8.5
    cam_data.dof.aperture_fstop = 3.2
    cam_obj = bpy.data.objects.new("MainCamera", cam_data)
    bpy.context.collection.objects.link(cam_obj)
    bpy.context.scene.camera = cam_obj

    target = bpy.data.objects.new("CamTarget", None)
    bpy.context.collection.objects.link(target)
    target.location = (0.0, 0.0, 0.6)
    cam_data.dof.focus_object = target

    track = cam_obj.constraints.new('TRACK_TO')
    track.target = target
    track.track_axis = 'TRACK_NEGATIVE_Z'
    track.up_axis = 'UP_Y'

    return root, holo_group, [ring1, ring2, ring3], pulse_mats, cam_obj, target


def animate_scene(root, holo_group, rings, pulse_mats, cam_obj, target, total_frames):
    scene = bpy.context.scene
    scene.frame_start = 1
    scene.frame_end = total_frames
    scene.render.fps = 24

    # 1. Counter-rotating holographic rings (continuous smooth motion!)
    ring1, ring2, ring3 = rings
    for obj, delta_rot in [
        (ring1, (math.radians(16), 0, math.radians(180))),
        (ring2, (math.radians(-22), math.radians(14), math.radians(-270))),
        (ring3, (math.radians(10), math.radians(-18), math.radians(360))),
    ]:
        obj.keyframe_insert(data_path="rotation_euler", frame=1)
        obj.rotation_euler = (obj.rotation_euler.x, obj.rotation_euler.y, obj.rotation_euler.z + delta_rot[2])
        obj.keyframe_insert(data_path="rotation_euler", frame=total_frames)
        set_linear(obj, "rotation_euler")

    # Gentle vertical breathing of holographic core
    holo_group.location = (0, 0, 1.35)
    holo_group.keyframe_insert(data_path="location", frame=1)
    holo_group.location = (0, 0, 1.75)
    holo_group.keyframe_insert(data_path="location", frame=int(total_frames * 0.5))
    holo_group.location = (0, 0, 1.45)
    holo_group.keyframe_insert(data_path="location", frame=total_frames)

    # 2. Data pulses racing outward along all PCB traces!
    for mat in pulse_mats:
        ph = mat.node_tree.nodes.get("PulsePhase")
        if ph:
            start_v = ph.outputs[0].default_value
            ph.outputs[0].keyframe_insert(data_path="default_value", frame=1)
            ph.outputs[0].default_value = start_v + 6.0 * math.pi
            ph.outputs[0].keyframe_insert(data_path="default_value", frame=total_frames)

    # 3. Sweeping cinematic scroll camera journey:
    # Frame 1 (Hero): Dramatic centered 3/4 establishing shot of the glowing Silicon Core & Holo Rings
    # 35%: Smooth dive down & orbit right toward the gold pins and racing cyan PCB traces
    # 70%: Low macro fly-over across the titanium SoC, copper coils & glowing fiber-optic data skyline
    # 100%: Rising wide orbit out above the illuminated digital constellation
    cam_keys = [
        (1,                        ( 0.0, -7.8,  5.6), ( 0.0,  0.0, 0.75)),
        (int(total_frames * 0.33), ( 4.6, -5.2,  3.1), ( 0.3,  0.2, 0.55)),
        (int(total_frames * 0.68), ( 3.2,  2.8,  2.1), (-0.4,  0.0, 0.65)),
        (total_frames,             (-4.8,  5.6,  4.8), ( 0.0,  0.0, 0.85)),
    ]

    for fr, cloc, tloc in cam_keys:
        cam_obj.location = cloc
        cam_obj.keyframe_insert(data_path="location", frame=fr)
        target.location = tloc
        target.keyframe_insert(data_path="location", frame=fr)


def configure_render(res_x=1280, res_y=720, samples=18):
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

    scene.view_settings.view_transform = 'AgX'
    try:
        scene.view_settings.look = 'AgX - Medium High Contrast'
    except Exception:
        pass
    scene.view_settings.exposure = -0.25

    # Cinematic Fog Glow bloom in compositor (Blender 5.x compatible)
    try:
        scene.use_nodes = True
        cnt = scene.compositing_node_group if hasattr(scene, "compositing_node_group") and scene.compositing_node_group else getattr(scene, "node_tree", None)
        if cnt is None and hasattr(bpy.data, "node_groups"):
            cnt = bpy.data.node_groups.new("BloomComp", 'CompositorNodeTree')
            scene.compositing_node_group = cnt
        if cnt:
            cnt.nodes.clear()
            rl = cnt.nodes.new("CompositorNodeRLayers")
            glare = cnt.nodes.new("CompositorNodeGlare")
            glare.glare_type = 'FOG_GLOW'
            glare.quality = 'HIGH'
            if "Threshold" in glare.inputs:
                glare.inputs["Threshold"].default_value = 1.4
            elif hasattr(glare, "threshold"):
                glare.threshold = 1.4
            if "Size" in glare.inputs:
                glare.inputs["Size"].default_value = 7
            elif hasattr(glare, "size"):
                glare.size = 7
            if "Mix" in glare.inputs:
                glare.inputs["Mix"].default_value = 0.0
            elif hasattr(glare, "mix"):
                glare.mix = 0.0
            comp = cnt.nodes.new("CompositorNodeComposite") if "CompositorNodeComposite" in dir(bpy.types) else cnt.nodes.new("NodeGroupOutput")
            cnt.links.new(rl.outputs["Image"], glare.inputs["Image"])
            cnt.links.new(glare.outputs["Image"], comp.inputs[0])
    except Exception as exc:
        print("Compositor bloom note:", exc)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["preview", "anim"], default="preview")
    parser.add_argument("--out", required=True)
    parser.add_argument("--frames", type=int, default=120)
    parser.add_argument("--samples", type=int, default=16)
    args = parser.parse_args(argv)

    os.makedirs(args.out, exist_ok=True)
    root, holo, rings, pulse_mats, cam, tgt = build_scene()
    animate_scene(root, holo, rings, pulse_mats, cam, tgt, args.frames)
    configure_render(1280, 720, samples=args.samples)

    scene = bpy.context.scene
    if args.mode == "preview":
        for label, fr in [("hero", 1), ("mid", int(args.frames * 0.38)), ("flyover", int(args.frames * 0.72)), ("end", args.frames)]:
            scene.frame_set(fr)
            scene.render.filepath = os.path.join(args.out, f"preview_{label}.png")
            bpy.ops.render.render(write_still=True)
    else:
        scene.render.filepath = os.path.join(args.out, "frame_")
        bpy.ops.render.render(animation=True)


if __name__ == "__main__":
    main()
