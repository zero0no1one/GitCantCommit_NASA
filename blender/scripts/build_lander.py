"""Sunline lander: the team's CLPS-class lander from Echo-Path, rigged for a touchdown shot.

Starts from the baked Echo-Path export (web/public/models/lander.glb in the NASA_GITCANTCOMMIT repo, built by
design/blender/lander.py + materials.py + export_lander.py: 11.7k triangles, 1024 px colour and normal bakes).
That film rig used drivers and stretch-to struts, which glTF cannot carry, so this script splits the baked mesh into
rigid parts by geometry and adds plain bones:
    root (ground, between the footpads) > body > engine_bell (gimbal at the throat)
    root > leg_lower.1..4 (footpads and lower struts; they stay on the ground)
Animation `touchdown` (36 frames, 24 fps): the body sinks 8 cm (the leg stroke in lander.py, STROKE_M) onto the
legs, rebounds and settles; the bell gimbal shakes and centres as the engine cuts off. Godot moves the lander down
during descent and plays `touchdown` at contact.
References checked before the Sunline rework (NASA High-Res-Moon-Base-June-30-Update-Image: Astrobotic Peregrine,
Intuitive Machines Nova-C and Firefly Blue Ghost renders; Wikimedia Commons "Firefly Blue Ghost lander mockup.jpg"):
the Echo-Path geometry already matches them (hexagonal Nova-C-style body in gold MLI with body-mounted solar panels,
radiator, RCS quads near the top corners, payload boxes, camera mast, dish; legs of dark struts with gold
shock-absorber sleeves and dish footpads). The one mismatch was the gold and silver foil reading dark brown/black
without a bright environment, because the materials were fully metallic and glossy; MLI_TUNING below makes them read
as bright foil under direct sunlight in Godot's Compatibility renderer.
Outputs: blender/lander.blend, assets/models/lander.glb.
"""
import math
import sys
from pathlib import Path
import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, str(Path(r'C:\dev\godot\new-game-project\blender\scripts')))
import importlib
import sunline_common as C
importlib.reload(C)

SOURCE = Path(r'C:\dev\NASA Apps Challenge 2026\NASA Space Apps\web\public\models\lander.glb')
STROKE = 0.08
LEG_CUT_Z = 0.55          # below this, outside the body footprint, geometry belongs to the footpads / lower struts
BODY_R = 0.75
# (metallic, roughness): crinkled foil scatters light, so it reads bright even when nothing bright is mirrored
MLI_TUNING = {'MLI gold (web)': (0.55, 0.42), 'MLI silver (web)': (0.55, 0.40), 'Radiator (web)': (0.3, 0.35),
              'Aluminium (web)': (0.75, 0.35), 'Titanium (web)': (0.75, 0.35)}


def main():
    C.new_scene()
    bpy.ops.import_scene.gltf(filepath=str(SOURCE))
    body = next(o for o in bpy.data.objects if o.type == 'MESH')
    for name, (metal, rough) in MLI_TUNING.items():
        m = bpy.data.materials.get(name)
        if m:
            b = m.node_tree.nodes['Principled BSDF']
            b.inputs['Metallic'].default_value = metal
            b.inputs['Roughness'].default_value = rough
    body.name = 'Lander'
    me = body.data
    bell_slots = [i for i, m in enumerate(me.materials) if m and 'Engine bell' in m.name]
    co = np.array([v.co[:] for v in me.vertices])
    r = np.hypot(co[:, 0], co[:, 1])
    az = (np.degrees(np.arctan2(co[:, 1], co[:, 0])) % 360)
    leg_of = np.floor(az/90).astype(int)+1                     # legs sit at 45/135/225/315°
    bell_verts = set()
    for p in me.polygons:
        if p.material_index in bell_slots:
            bell_verts.update(p.vertices)
    groups = {n: body.vertex_groups.new(name=n) for n in ('body', 'engine_bell', 'leg_lower.1', 'leg_lower.2', 'leg_lower.3', 'leg_lower.4')}
    counts = {n: 0 for n in groups}
    for i in range(len(co)):
        if i in bell_verts:
            g = 'engine_bell'
        elif co[i, 2] < LEG_CUT_Z and r[i] > BODY_R:
            g = f'leg_lower.{leg_of[i]}'
        else:
            g = 'body'
        groups[g].add([i], 1.0, 'REPLACE')
        counts[g] += 1
    bell = co[list(bell_verts)] if bell_verts else np.zeros((1, 3))
    throat = Vector((0, 0, float(bell[:, 2].max())))
    pads = {k: co[(leg_of == k) & (co[:, 2] < .1) & (r > BODY_R)].mean(0) for k in (1, 2, 3, 4)}

    arm = C.link(bpy.data.objects.new('LanderRig', bpy.data.armatures.new('LanderRig')))
    C.set_mode(arm, 'EDIT')
    eb = arm.data.edit_bones
    def bone(name, h, t, parent=None, deform=True):
        b = eb.new(name)
        b.head, b.tail = Vector(h), Vector(t)
        b.use_deform = deform
        if parent:
            b.parent = eb[parent]
        return b
    bone('root', (0, 0, 0), (0, 0, .4), deform=False)
    bone('body', (0, 0, 1.05), (0, 0, 2.2), 'root')
    bone('engine_bell', throat, throat-Vector((0, 0, .35)), 'body')
    for k, p in pads.items():
        bone(f'leg_lower.{k}', (p[0], p[1], .02), (p[0], p[1], .45), 'root')
    C.set_mode(arm, 'OBJECT')
    mod = body.modifiers.new('Armature', 'ARMATURE')
    mod.object = arm
    body.parent = arm
    for pb in arm.pose.bones:
        pb.rotation_mode = 'XYZ'

    act = bpy.data.actions.new('touchdown')
    act.use_fake_user = True
    arm.animation_data_create()
    arm.animation_data.action = act
    keys = [(1, 0, 0, 0), (4, -STROKE, 2.0, 1.0), (8, -.052, -1.5, -.8), (12, -.074, 1.0, .5), (16, -.062, -.5, -.3),
            (22, -.068, .2, 0), (28, -.066, 0, 0), (36, -.066, 0, 0)]
    for f, dz, gx, gy in keys:
        b, g = arm.pose.bones['body'], arm.pose.bones['engine_bell']
        b.location = (0, dz, 0)                                  # body bone points up: local Y = world Z
        g.rotation_euler = (math.radians(gx), 0, math.radians(gy))
        for pb in (b, g):
            pb.keyframe_insert('location', frame=f)
            pb.keyframe_insert('rotation_euler', frame=f)
    act.frame_range = (1, 36)
    act.use_frame_range = True
    arm.animation_data.action = None
    for pb in arm.pose.bones:
        pb.location = (0, 0, 0)
        pb.rotation_euler = (0, 0, 0)

    C.export_glb('lander', [arm, body], animations=True)
    C.save_blend('lander')
    return {'triangles': C.triangles([body]), 'groups': counts, 'throat_z': round(throat.z, 3),
            'pads': {k: [round(float(x), 2) for x in v] for k, v in pads.items()}}


result = main()
