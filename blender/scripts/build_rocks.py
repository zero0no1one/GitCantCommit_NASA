"""Sunline rock set: cobbles, rocks, blocks and a split boulder for scattering on the site terrain.

References viewed before modelling (NASA Image and Video Library):
- AS17-146-22294: Apollo 17 Station 6 boulder, several metres tall: blocky, flat fracture faces, edges rounded by
  micrometeorite erosion, pitted surface, lighter grey than the surrounding regolith, broken slabs at its base,
  angular 5–20 cm cobbles half-buried around it.
- AS16-107-17573: ~0.5 m block at Apollo 16: angular, faceted fracture planes, slightly rounded edges, granular
  pitted surface; the pit it was rolled out of shows cohesive regolith with clods and 1–5 cm pebbles.
Method: convex hull of few seeded points (big fracture facets) -> random corner chips along fracture planes ->
slight edge bevel (erosion) + small jitter (pitting) -> flat shading -> bottom ~20% below z = 0 (half-buried). Elongation about 1 : 0.7 : 0.5.
Scatter rule for Godot: rocks are ILLUSTRATIVE (not from data). Place them so they never rise above the scoring
skyline seen from the panel (the same clamp used for the terrain); small rocks near the player are always fine.
Outputs: blender/rocks.blend, assets/models/rocks.glb (one mesh per variant, origin at ground level).
"""
import math
import sys
from pathlib import Path
import bpy
import bmesh
import numpy as np
from mathutils import Vector, noise

sys.path.insert(0, str(Path(r'C:\dev\godot\new-game-project\blender\scripts')))
import importlib
import sunline_common as C
importlib.reload(C)

VARIANTS = [  # name, size (m), hull points (fewer = bigger facets), jitter (fraction of size), seed
    ('Cobble_A', 0.14, 9, 0.03, 11), ('Cobble_B', 0.18, 8, 0.03, 12), ('Cobble_C', 0.12, 10, 0.03, 13),
    ('Rock_A', 0.45, 11, 0.025, 21), ('Rock_B', 0.6, 12, 0.025, 22), ('Rock_C', 0.5, 10, 0.025, 23),
    ('Block_A', 1.0, 12, 0.02, 31), ('Block_B', 1.3, 14, 0.02, 32),
]


def hull_rock(name, size, npts, amp, seed, material_, stretch=(1.0, 0.7, 0.5), bury=0.2, chips=5):
    """Angular fractured rock: convex hull (big facets) + random corner chips (fracture planes) + tiny jitter."""
    rng = np.random.default_rng(seed)
    bm = bmesh.new()
    pts = rng.normal(size=(npts, 3))
    pts /= np.linalg.norm(pts, axis=1, keepdims=True)
    pts *= rng.uniform(0.8, 1.0, (npts, 1))
    for p in pts:
        bm.verts.new(Vector((p[0]*stretch[0], p[1]*stretch[1], p[2]*stretch[2]))*size/2)
    bmesh.ops.convex_hull(bm, input=bm.verts)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    for k in range(chips):                            # knock off corners along random fracture planes
        n = Vector(rng.normal(size=3)).normalized()
        reach = max(v.co.dot(n) for v in bm.verts)
        co = n*reach*rng.uniform(0.70, 0.88)
        res = bmesh.ops.bisect_plane(bm, geom=bm.verts[:]+bm.edges[:]+bm.faces[:], plane_co=co, plane_no=n,
                                     clear_outer=True)
        edges = [e for e in res['geom_cut'] if isinstance(e, bmesh.types.BMEdge)]
        if edges:
            bmesh.ops.edgenet_fill(bm, edges=edges)
    # cuts of a convex hull stay convex: re-hull the vertices for a clean closed mesh (no fill flaps)
    pts = [v.co.copy() for v in bm.verts]
    bm.free()
    bm = bmesh.new()
    for q in pts:
        bm.verts.new(q)
    bmesh.ops.convex_hull(bm, input=bm.verts)
    bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(2), verts=bm.verts[:], edges=bm.edges[:])
    bmesh.ops.bevel(bm, geom=bm.edges[:], offset=size*0.012, segments=1, affect='EDGES')   # slight erosion
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    off = Vector(rng.uniform(-50, 50, 3))
    for v in bm.verts:                                # small pitting jitter, keeps facets flat-ish
        v.co += Vector((noise.noise(v.co/size*6+off), noise.noise(v.co/size*6+off+Vector((7, 0, 0))),
                        noise.noise(v.co/size*6+off+Vector((0, 7, 0)))))*amp*size*0.5
    zmin = min(v.co.z for v in bm.verts)
    zmax = max(v.co.z for v in bm.verts)
    for v in bm.verts:
        v.co.z -= zmin+bury*(zmax-zmin)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    ob = C.mesh_object(name, bm, material_, smooth=False)   # flat shading: crisp fracture facets
    return ob


def split_boulder(name, material_):
    """Station-6-style boulder: two halves of one hull separated by a fracture gap, plus slabs at the foot."""
    whole = hull_rock(name+'_src', 3.2, 16, 0.02, 41, material_, stretch=(1.0, 0.8, 0.62), bury=0.15, chips=7)
    parts = []
    for side, shift in ((1, 0.16), (-1, -0.16)):
        bm = bmesh.new()
        bm.from_mesh(whole.data)
        geom = bm.verts[:]+bm.edges[:]+bm.faces[:]
        res = bmesh.ops.bisect_plane(bm, geom=geom, plane_co=(0.15, 0, 0), plane_no=(side*0.85, side*-0.45, 0.1),
                                     clear_outer=True, clear_inner=False)
        bmesh.ops.contextual_create(bm, geom=[e for e in res['geom_cut'] if isinstance(e, bmesh.types.BMEdge)])
        bmesh.ops.triangulate(bm, faces=bm.faces[:])
        for v in bm.verts:
            v.co.x += shift
            v.co.y -= shift*0.5
        parts.append(C.mesh_object(f'{name}_half{side}', bm, material_, smooth=False))
    bpy.data.objects.remove(whole, do_unlink=True)
    for k, (x, y, s) in enumerate(((1.7, 0.8, 0.5), (1.5, -0.9, 0.35), (-1.6, 0.4, 0.45), (0.3, 1.4, 0.3))):
        slab = hull_rock(f'{name}_slab{k}', s, 10, 0.03, 50+k, material_, stretch=(1.0, 0.8, 0.35), bury=0.3, chips=3)
        slab.location = (x, y, 0)
        slab.rotation_euler = (0, 0, k*1.3)
        parts.append(slab)
    C.apply_transforms(parts)
    ob = C.join(parts, name)
    for f in ob.data.polygons:
        f.use_smooth = False
    return ob


def main():
    C.new_scene()
    rock = C.texture_material('lunar_rock', (0.40, 0.39, 0.375, 1), normal='rock_detail_normal.png', roughness=1.0, normal_strength=1.4)
    objs = []
    for name, size, npts, amp, seed in VARIANTS:
        objs.append(hull_rock(name, size, npts, amp, seed, rock))
    objs.append(split_boulder('Boulder_Split', rock))
    for o in objs:
        C.box_uv(o, 0.4)                             # granular pitting from the detail normal map
    for i, o in enumerate(objs):                     # lay them out in a row for previews; export resets per mesh
        o.location = (i*1.8 if i < 8 else 18.0, 0, 0)
    C.export_glb('rocks', objs, animations=False)
    C.save_blend('rocks')
    return {o.name: C.triangles([o]) for o in objs}


result = main()
