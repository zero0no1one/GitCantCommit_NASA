"""Render clean single-object input images for Hunyuan3D-2 image-to-3D (blender/references/hy_input_<asset>.png).

Hunyuan3D-2 works best from one centred object, 3/4 front view, soft even light, plain light background (its
background remover cuts the object out). These renders come from the current procedural models, which were built
from the reference photos and the team's turnaround sheet, so the AI sculpts keep the same designs.
Run inside Blender:  exec(open(r'<repo>/blender/scripts/render_hunyuan_inputs.py', encoding='utf-8').read())
"""
import math
import sys
from pathlib import Path
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(r'C:\dev\godot\new-game-project\blender\scripts')))
import importlib
import sunline_common as C
importlib.reload(C)

OUT = C.BLEND_DIR/'references'
# asset: (blend file, objects to show, azimuth deg, elevation deg)
ASSETS = {
    'astronaut': ('astronaut.blend', ['Astronaut'], -30, 6),
    'scanner': ('astronaut.blend', ['Scanner'], -55, 18),
    'rover': ('rover.blend', ['Rover'], -35, 16),
    'beacon': ('beacon.blend', ['Beacon'], -30, 8),
    'lander': ('lander.blend', ['Lander'], -30, 10),
    # the Station 6 photo crop failed (background removal kept the whole frame -> a flat relief), so the
    # boulder is sculpted from the procedural split boulder, itself modelled from that photo
    'boulder': ('rocks.blend', ['Boulder_Split'], -30, 12),
}


def render(name, blend, show, az, el):
    bpy.ops.wm.open_mainfile(filepath=str(C.BLEND_DIR/blend))
    s = bpy.context.scene
    for o in s.objects:
        if o.type == 'ARMATURE' and o.animation_data:
            o.animation_data.action = None
            for pb in o.pose.bones:
                pb.location = (0, 0, 0)
                pb.rotation_quaternion = (1, 0, 0, 0)
                pb.rotation_euler = (0, 0, 0)
    objs = [bpy.data.objects[n] for n in show]
    if name == 'scanner':                      # isolate the scanner from the hand
        sc = objs[0]
        sc.parent = None
        sc.matrix_world = C.Matrix.Identity(4)
    for o in s.objects:
        o.hide_render = o not in objs and o.type not in ('ARMATURE',)
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    pts = []
    for o in objs:
        ev = o.evaluated_get(dg)
        me = ev.to_mesh()
        pts += [ev.matrix_world @ v.co for v in me.vertices]
        ev.to_mesh_clear()
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    centre, size = (lo+hi)/2, (hi-lo).length
    cam = C.link(bpy.data.objects.new('_HyCam', bpy.data.cameras.new('_HyCam')))
    cam.data.lens = 50
    d = size*1.75
    a, e = math.radians(az), math.radians(el)
    cam.location = centre+Vector((d*math.cos(e)*math.sin(a), -d*math.cos(e)*math.cos(a), d*math.sin(e)))
    cam.rotation_euler = (centre-cam.location).to_track_quat('-Z', 'Y').to_euler()
    for k, (rx, rz, en) in enumerate(((50, -35, 3.0), (60, 140, 1.2), (20, 60, 0.8))):   # key, rim, fill
        L = C.link(bpy.data.objects.new(f'_HyL{k}', bpy.data.lights.new(f'_HyL{k}', 'SUN')))
        L.data.energy = en
        L.rotation_euler = (math.radians(rx), 0, math.radians(rz))
    w = s.world or bpy.data.worlds.new('W')
    s.world = w
    w.use_nodes = True
    w.node_tree.nodes['Background'].inputs['Color'].default_value = (0.92, 0.92, 0.93, 1)
    w.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.6
    s.camera = cam
    s.render.engine = 'BLENDER_EEVEE'
    s.render.resolution_x = s.render.resolution_y = 1024
    s.render.film_transparent = False
    s.view_settings.view_transform = 'Standard'
    s.render.filepath = str(OUT/f'hy_input_{name}.png')
    bpy.ops.render.render(write_still=True)
    return s.render.filepath


OUT.mkdir(parents=True, exist_ok=True)
ONLY = globals().get('ONLY')
result = {name: render(name, *spec) for name, spec in ASSETS.items() if not ONLY or name in ONLY}
