"""Turn a raw Hunyuan3D-2 sculpt into a game asset that drops in for the procedural one.

For ASSET (set before exec), using blender/<blend> (the procedural model + rig) and blender/hunyuan/raw/<raw>.glb:
1. import the sculpt, scale it to the procedural model's height, try 8 yaw angles (and a mirror) and keep the one
   whose surface sits closest to the procedural model (mean nearest-surface distance), then centre it;
2. decimate to the web triangle budget;
3. materials: every sculpt face takes the material of the nearest procedural face (the palette stays the design's);
4. rigging (rigged assets): vertex groups are transferred from the procedural mesh (nearest face, interpolated),
   smoothed and normalised, then bound to the same armature, so every existing animation drives the sculpt;
5. box-projected UVs (for the detail normal maps), export assets/models/<asset>.glb; the procedural export is kept
   at assets/models/procedural/<asset>.glb.
Run inside Blender:
    ASSET, BLEND, RAW, OBJECT, ARMATURE, BUDGET = 'astronaut', 'astronaut.blend', 'astronaut_s1234', 'Astronaut', 'AstronautRig', 15000
    exec(open(r'<repo>/blender/scripts/postprocess_sculpt.py', encoding='utf-8').read())
"""
import math
import shutil
import sys
from pathlib import Path
import bpy
import bmesh
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, str(Path(r'C:\dev\godot\new-game-project\blender\scripts')))
import importlib
import sunline_common as C
importlib.reload(C)

RAW_DIR = C.BLEND_DIR/'hunyuan'/'raw'


def world_bvh(ob):
    dg = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(dg)
    me = ev.to_mesh()
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.transform(ob.matrix_world)
    bm.faces.ensure_lookup_table()
    mats = [f.material_index for f in bm.faces]
    tree = BVHTree.FromBMesh(bm)
    pts = np.array([v.co[:] for v in bm.verts])
    ev.to_mesh_clear()
    return tree, mats, pts, bm


def fit(sculpt, ref_pts, ref_tree):
    """Scale to the reference height, then pick the yaw/mirror that best matches the reference surface."""
    me = sculpt.data
    co = np.array([v.co[:] for v in me.vertices])
    lo_r, hi_r = ref_pts.min(0), ref_pts.max(0)
    s = (hi_r[2]-lo_r[2])/(co[:, 2].max()-co[:, 2].min())
    best = None
    scores = []
    rng = np.random.default_rng(0)
    sample = co[rng.choice(len(co), min(4000, len(co)), replace=False)]
    for mirror in (1, -1):
        for k in range(8):
            yaw = k*math.pi/4
            R = np.array([[math.cos(yaw), -math.sin(yaw), 0], [math.sin(yaw), math.cos(yaw), 0], [0, 0, 1]])
            p = (sample*np.array([mirror, 1, 1]))@R.T*s
            # align bounding-box centres in x/y and the base in z
            p += np.array([(lo_r[0]+hi_r[0])/2-(p[:, 0].min()+p[:, 0].max())/2,
                           (lo_r[1]+hi_r[1])/2-(p[:, 1].min()+p[:, 1].max())/2, lo_r[2]-p[:, 2].min()])
            err = np.mean([(ref_tree.find_nearest(Vector(q))[3] or 0) for q in p[::4]])
            scores.append((err, mirror, yaw))
            if best is None or err < best[0]:
                best = (err, mirror, yaw)
    # Hunyuan's output already faces the input camera's front (-Y after glTF import), and a body matches its own
    # outline almost equally well turned round, so keep the unrotated fit unless another is clearly (30%) better.
    # Outline matching cannot tell a figure's front from its back (it picked 180° for the astronaut, putting the
    # visor at the back of the head), so orientation is FIXED: yaw 0, no mirror, unless the asset sets FORCE_YAW.
    # The search result is kept in the log as a diagnostic only.
    forced = globals().get('FORCE_YAW', 0)
    diag = best
    best = next(s for s in scores if s[1] == 1 and abs(math.degrees(s[2])-forced) < 1)
    err, mirror, yaw = best
    R = Matrix.Rotation(yaw, 4, 'Z') @ Matrix.Diagonal((mirror*s, s, s, 1))
    me.transform(R)
    if mirror < 0:
        me.flip_normals()
    co = np.array([v.co[:] for v in me.vertices])
    me.transform(Matrix.Translation(((lo_r[0]+hi_r[0])/2-(co[:, 0].min()+co[:, 0].max())/2,
                                     (lo_r[1]+hi_r[1])/2-(co[:, 1].min()+co[:, 1].max())/2, lo_r[2]-co[:, 2].min())))
    return {'fit_error_m': round(float(err), 4), 'mirror': mirror, 'yaw_deg': round(math.degrees(yaw)), 'scale': round(float(s), 4),
            'search_best': {'error_m': round(float(diag[0]), 4), 'yaw_deg': round(math.degrees(diag[2])), 'mirror': diag[1]}}


def decimate(ob, budget):
    tris = sum(len(p.vertices)-2 for p in ob.data.polygons)
    if tris > budget:
        m = ob.modifiers.new('Decimate', 'DECIMATE')
        m.ratio = budget/tris
        with C.override(ob):
            bpy.ops.object.modifier_apply(modifier=m.name)
    return sum(len(p.vertices)-2 for p in ob.data.polygons)


def transfer_materials(sculpt, ref_ob, ref_tree, ref_mats, reach=0.08, passes=3):
    """Each sculpt face takes the material of the procedural surface found by projecting along its normal (like a
    bake cage), falling back to the nearest surface; then a majority (mode) filter over face neighbours removes
    speckle so material regions follow the sculpt's own shapes."""
    sculpt.data.materials.clear()
    for m in ref_ob.data.materials:
        sculpt.data.materials.append(m)
    me = sculpt.data
    mats = np.zeros(len(me.polygons), dtype=np.int32)
    for p in me.polygons:
        c, n = Vector(p.center), Vector(p.normal)
        hit = ref_tree.ray_cast(c+n*reach, -n, 2*reach)
        idx = hit[2]
        if idx is None:
            idx = ref_tree.find_nearest(c)[2]
        mats[p.index] = ref_mats[idx] if idx is not None else 0
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.faces.ensure_lookup_table()
    nbrs = [[e.index for edge in f.edges for e in edge.link_faces if e.index != f.index] for f in bm.faces]
    bm.free()
    for _ in range(passes):
        new = mats.copy()
        for i, ns in enumerate(nbrs):
            if ns:
                vals, counts = np.unique(np.append(mats[ns], mats[i]), return_counts=True)
                new[i] = vals[np.argmax(counts)]
        mats = new
    for p in me.polygons:
        p.material_index = int(mats[p.index])
        p.use_smooth = True


def glass_region(sculpt, ref_ob, spec):
    """Paint a clean visor: every sculpt face inside a cone around the helmet's forward axis becomes glass, and any
    'recolor' material left on the helmet (the light-blue side windows) does too. The helmet centre is the bounding-
    box centre of the procedural head part. spec: dict(group, axis, half_angle_deg, radius, material, recolor)."""
    gi = ref_ob.vertex_groups[spec['group']].index
    pts = [ref_ob.matrix_world @ v.co for v in ref_ob.data.vertices if any(g.group == gi and g.weight > 0.5 for g in v.groups)]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    hc = (lo+hi)/2
    names = [m.name for m in sculpt.data.materials]
    glass = names.index(spec['material'])
    recolor = {names.index(n) for n in spec.get('recolor', []) if n in names}
    axis = Vector(spec['axis']).normalized()
    me = sculpt.data
    # The visor edge is (close to) a circle on a plane across the helmet front. Cut the mesh exactly on that plane so
    # the glass border is a clean circle instead of whole decimated triangles flipping (stair steps). The plane sits
    # at cos(half_angle) of the helmet's forward extent; side features (ear pods) never reach it.
    bm = bmesh.new()
    bm.from_mesh(me)
    near = [f for f in bm.faces if (f.calc_center_median()-hc).length <= spec['radius']]
    reach = max((v.co-hc).dot(axis) for f in near for v in f.verts)
    d = reach*math.cos(math.radians(spec['half_angle_deg']))
    geom = list({e for f in near for e in f.edges})+list({v for f in near for v in f.verts})+near
    bmesh.ops.bisect_plane(bm, geom=geom, plane_co=hc+axis*d, plane_no=axis)
    disc_r = reach*math.sin(math.radians(spec['half_angle_deg']))*1.05    # opening radius, with a little slack
    n_cone = n_re = 0
    for f in bm.faces:
        c = f.calc_center_median()-hc
        if c.length > spec['radius']:
            continue
        lateral = (c-axis*c.dot(axis)).length                            # distance from the helmet's forward axis
        if c.dot(axis) > d and lateral <= disc_r:                        # in front of the cut AND inside the visor disc
            f.material_index = glass
            n_cone += 1
        elif f.material_index in recolor:
            f.material_index = glass
            n_re += 1
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = True
    return {'helmet_centre': [round(x, 3) for x in hc], 'cut_depth_m': round(d, 3), 'visor_faces': n_cone,
            'recolored_faces': n_re}


def flatten_baked_materials(ref_ob):
    """For models whose colours live in a baked texture atlas laid out for the procedural UVs (the lander), give each
    material a plain base colour: the mean of its texture over the faces that use it. The sculpt has its own UVs,
    so the atlas cannot be reused."""
    me = ref_ob.data
    uv = me.uv_layers.active
    plain = []
    for i, m in enumerate(me.materials):
        nodes = m.node_tree.nodes if m and m.use_nodes else []
        bsdf = next((n for n in nodes if n.type == 'BSDF_PRINCIPLED'), None)
        tex = None
        if bsdf and bsdf.inputs['Base Color'].is_linked:
            src = bsdf.inputs['Base Color'].links[0].from_node
            tex = src if src.type == 'TEX_IMAGE' else None
        if not tex or not tex.image or uv is None:
            plain.append(m)
            continue
        img = tex.image
        w, h = img.size
        px = np.array(img.pixels[:]).reshape(h, w, 4)
        cols = []
        for p in me.polygons:
            if p.material_index == i:
                for li in p.loop_indices:
                    u, v = uv.data[li].uv
                    cols.append(px[min(h-1, max(0, int(v*h))), min(w-1, max(0, int(u*w))), :3])
        c = np.mean(cols, axis=0) if cols else np.array([0.5, 0.5, 0.5])
        pm = C.material(m.name+' (sculpt)', (float(c[0]), float(c[1]), float(c[2]), 1),
                        metallic=bsdf.inputs['Metallic'].default_value, roughness=bsdf.inputs['Roughness'].default_value)
        plain.append(pm)
    return plain


def transfer_weights(sculpt, ref_ob, arm):
    for vg in ref_ob.vertex_groups:
        sculpt.vertex_groups.new(name=vg.name)
    m = sculpt.modifiers.new('WeightsFromProcedural', 'DATA_TRANSFER')
    m.object = ref_ob
    m.use_vert_data = True
    m.data_types_verts = {'VGROUP_WEIGHTS'}
    m.vert_mapping = 'POLYINTERP_NEAREST'
    m.layers_vgroup_select_src = 'ALL'
    m.layers_vgroup_select_dst = 'NAME'
    with C.override(sculpt):
        bpy.ops.object.modifier_apply(modifier=m.name)
    # soft goods (the suit): soften part boundaries so joints bend instead of tearing. Machines (SMOOTH_WEIGHTS =
    # False): keep rigid boundaries, or a moving part (the rover's drill) drags the panel it is fused to.
    with C.override(sculpt):
        bpy.ops.object.mode_set(mode='WEIGHT_PAINT')
        if globals().get('SMOOTH_WEIGHTS', True):
            bpy.ops.object.vertex_group_smooth(group_select_mode='ALL', factor=0.5, repeat=2)
        bpy.ops.object.vertex_group_normalize_all(lock_active=False)
        bpy.ops.object.mode_set(mode='OBJECT')
    mod = sculpt.modifiers.new('Armature', 'ARMATURE')
    mod.object = arm
    sculpt.parent = arm


def rigid_segments(sculpt):
    """Machines: give every face to one bone (majority of its vertices' strongest group), split the mesh along every
    boundary between bones so each part is its own island, close the openings, and make each island 100% rigid to
    its bone. Moving parts (wheels, drill, legs, mast) then move without dragging the surface they were fused to."""
    me = sculpt.data
    names = [g.name for g in sculpt.vertex_groups]
    bm = bmesh.new()
    bm.from_mesh(me)
    dl = bm.verts.layers.deform.active
    vdom = {}
    for v in bm.verts:
        w = v[dl]
        vdom[v] = max(w.items(), key=lambda kv: kv[1])[0] if len(w) else -1
    fgrp = {}
    for f in bm.faces:
        vals = [vdom[v] for v in f.verts]
        fgrp[f] = max(set(vals), key=vals.count)
    cut = [e for e in bm.edges if len(e.link_faces) == 2 and fgrp[e.link_faces[0]] != fgrp[e.link_faces[1]]]
    bmesh.ops.split_edges(bm, edges=cut)
    for v in bm.verts:                                    # each vertex now touches faces of one group only
        g = fgrp[v.link_faces[0]] if v.link_faces else vdom.get(v, -1)
        w = v[dl]
        for k in list(w.keys()):
            del w[k]
        if g >= 0:
            w[g] = 1.0
    boundary = [e for e in bm.edges if e.is_boundary]
    # only close small openings: filling long, uneven split boundaries makes large shard-like faces (seen under the
    # rover); the bigger seams sit behind the moving part that covers them
    filled = bmesh.ops.holes_fill(bm, edges=boundary, sides=24)
    bmesh.ops.triangulate(bm, faces=filled['faces'])
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = True
    return {'parts': len(set(fgrp.values())), 'cut_edges': len(cut), 'filled_faces': len(filled['faces'])}


def main():
    bpy.ops.wm.open_mainfile(filepath=str(C.BLEND_DIR/BLEND))
    ref = bpy.data.objects[OBJECT]
    arm = bpy.data.objects.get(ARMATURE) if ARMATURE else None
    if arm:
        C.rest(arm)
    bpy.context.view_layer.update()
    ref_tree, ref_mats, ref_pts, ref_bm = world_bvh(ref)
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(RAW_DIR/f'{RAW}.glb'))
    new = [o for o in set(bpy.data.objects)-before]
    meshes = [o for o in new if o.type == 'MESH']
    sculpt = meshes[0] if len(meshes) == 1 else C.join(meshes, 'sculpt')
    for o in new:
        if o is not sculpt and o.name in bpy.data.objects:
            bpy.data.objects.remove(o, do_unlink=True)
    sculpt.parent = None
    sculpt.data.transform(sculpt.matrix_world)
    sculpt.matrix_world = Matrix.Identity(4)
    info = fit(sculpt, ref_pts, ref_tree)
    info['triangles_raw'] = sum(len(p.vertices)-2 for p in sculpt.data.polygons)
    info['triangles'] = decimate(sculpt, BUDGET)
    transfer_materials(sculpt, ref, ref_tree, ref_mats)
    if globals().get('GLASS'):
        info['glass'] = glass_region(sculpt, ref, GLASS)
    if globals().get('FLATTEN_BAKED'):
        for i, m in enumerate(flatten_baked_materials(ref)):
            sculpt.data.materials[i] = m
    C.box_uv(sculpt, 0.45)
    if arm:
        transfer_weights(sculpt, ref, arm)
        if globals().get('RIGID_SEGMENTS'):
            info['segments'] = rigid_segments(sculpt)
    name = ref.name
    ref.name = name+'_procedural'
    sculpt.name = name
    sculpt.data.name = name
    ref.hide_render = True
    ref.hide_viewport = True
    proc_dir = C.MODELS/'procedural'
    proc_dir.mkdir(exist_ok=True)
    if not (proc_dir/f'{ASSET}.glb').exists() and (C.MODELS/f'{ASSET}.glb').exists():
        shutil.copy2(C.MODELS/f'{ASSET}.glb', proc_dir/f'{ASSET}.glb')
    extra = [o for o in bpy.data.objects if o.name in EXTRA_EXPORT] if 'EXTRA_EXPORT' in globals() else []
    C.export_glb(ASSET, [o for o in (arm, sculpt) if o]+extra, animations=bool(arm))
    bpy.ops.wm.save_as_mainfile(filepath=str(C.BLEND_DIR/f'{ASSET}_sculpt.blend'), compress=True)
    return info


result = main()
