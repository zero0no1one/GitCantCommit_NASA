"""Sunline rock set, Hunyuan3D-2 sculpted: replaces the procedural rocks, blocks and boulder with AI sculpts.

Inputs (blender/hunyuan/raw/): rock_s1234, rock_s7, rock_s21 (from the Apollo 16 photo AS16-107-17573 crop) and
boulder_s1234 (from the procedural split boulder render; the Station 6 photo crop failed background removal).
For each: cut off the photo-ground skirt (everything below SKIRT of the height), close the cut, scale to its size
class, rotate/stretch for variety, sit it ~20% into the ground, decimate to its budget, rock material with the
pitting normal map and box UVs. The small procedural cobbles are kept (10–20 cm stones gain nothing from sculpting).
Outputs: blender/rocks_sculpt.blend, assets/models/rocks.glb (procedural version kept in assets/models/procedural/).
"""
import math
import shutil
import sys
from pathlib import Path
import bpy
import bmesh
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(r'C:\dev\godot\new-game-project\blender\scripts')))
import importlib
import sunline_common as C
importlib.reload(C)

RAW = C.BLEND_DIR/'hunyuan'/'raw'
SKIRT = 0.14
# name, raw sculpt, longest size (m), yaw (deg), stretch (x, y, z), triangle budget
VARIANTS = [
    ('Rock_A', 'rock_s1234', 0.45, 20, (1.0, 0.8, 0.7), 3000),      # below ~3k the sculpted pitting is lost
    ('Rock_B', 'rock_s21', 0.60, 110, (1.0, 0.75, 0.6), 3000),
    ('Rock_C', 'rock_s7', 0.50, 230, (0.9, 1.0, 0.65), 3000),
    ('Block_A', 'rock_s7', 1.00, 60, (1.0, 0.85, 0.8), 5000),
    ('Block_B', 'rock_s1234', 1.30, 300, (1.0, 0.7, 0.75), 5000),
    ('Boulder_Split', 'boulder_s1234', 3.50, 0, (1.0, 1.0, 1.0), 8000),
]


def load_raw(name):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(RAW/f'{name}.glb'))
    new = list(set(bpy.data.objects)-before)
    ob = next(o for o in new if o.type == 'MESH')
    ob.data.transform(ob.matrix_world)
    ob.parent = None
    ob.matrix_world = Matrix.Identity(4)
    for o in new:
        if o is not ob:
            bpy.data.objects.remove(o, do_unlink=True)
    return ob


def cut_skirt(ob, frac):
    me = ob.data
    zs = [v.co.z for v in me.vertices]
    z0, z1 = min(zs), max(zs)
    bm = bmesh.new()
    bm.from_mesh(me)
    res = bmesh.ops.bisect_plane(bm, geom=bm.verts[:]+bm.edges[:]+bm.faces[:], plane_co=(0, 0, z0+frac*(z1-z0)),
                                 plane_no=(0, 0, 1), clear_inner=True)
    edges = [e for e in res['geom_cut'] if isinstance(e, bmesh.types.BMEdge)]
    if edges:
        bmesh.ops.holes_fill(bm, edges=[e for e in bm.edges if e.is_boundary], sides=0)
    bm.to_mesh(me)
    bm.free()


def main():
    bpy.ops.wm.open_mainfile(filepath=str(C.BLEND_DIR/'rocks.blend'))
    rock_mat = bpy.data.materials['lunar_rock']
    keep = [o for o in bpy.data.objects if o.name.startswith('Cobble')]
    for o in list(bpy.data.objects):
        if o.type == 'MESH' and o not in keep:
            o.name = o.name+'_procedural'
            o.hide_render = o.hide_viewport = True
    out = {}
    cache = {}
    for i, (name, raw, size, yaw, stretch, budget) in enumerate(VARIANTS):
        if raw not in cache:
            src = load_raw(raw)
            cut_skirt(src, SKIRT if raw.startswith('rock') else 0.0)
            m0 = src.modifiers.new('Pre', 'DECIMATE')            # pre-reduce once (500k -> 20k) before the variants
            m0.ratio = min(1.0, 20000/max(1, len(src.data.polygons)))
            with C.override(src):
                bpy.ops.object.modifier_apply(modifier=m0.name)
            cache[raw] = src
            src.hide_render = src.hide_viewport = True
        ob = cache[raw].copy()
        ob.data = cache[raw].data.copy()
        C.link(ob)
        ob.hide_render = ob.hide_viewport = False
        ob.name = ob.data.name = name
        me = ob.data
        d = max(ob.dimensions)
        me.transform(Matrix.Rotation(math.radians(yaw), 4, 'Z') @ Matrix.Diagonal((stretch[0]*size/d, stretch[1]*size/d, stretch[2]*size/d, 1)))
        zs = [v.co.z for v in me.vertices]
        me.transform(Matrix.Translation((0, 0, -min(zs)-0.2*(max(zs)-min(zs)))))     # ~20% buried
        m = ob.modifiers.new('Decimate', 'DECIMATE')
        m.ratio = min(1.0, budget/max(1, sum(len(p.vertices)-2 for p in me.polygons)))
        with C.override(ob):
            bpy.ops.object.modifier_apply(modifier=m.name)
        me.materials.clear()
        me.materials.append(rock_mat)
        for p in me.polygons:
            p.use_smooth = True
        C.box_uv(ob, 0.4)
        ob.location = (i*2.0 if name != 'Boulder_Split' else 18.0, 0, 0)
        out[name] = C.triangles([ob])
    for src in cache.values():
        bpy.data.objects.remove(src, do_unlink=True)
    proc = C.MODELS/'procedural'
    proc.mkdir(exist_ok=True)
    if not (proc/'rocks.glb').exists():
        shutil.copy2(C.MODELS/'rocks.glb', proc/'rocks.glb')
    objs = keep+[bpy.data.objects[v[0]] for v in VARIANTS]
    C.export_glb('rocks', objs, animations=False)
    bpy.ops.wm.save_as_mainfile(filepath=str(C.BLEND_DIR/'rocks_sculpt.blend'), compress=True)
    return out


result = main()
