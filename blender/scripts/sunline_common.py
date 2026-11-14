"""Shared helpers for Sunline's Blender build scripts (Blender 5.2).

Every asset script builds its scene from nothing, saves blender/<asset>.blend and exports assets/models/<asset>.glb,
so re-running a script rebuilds that asset exactly. Conventions: metres, +Z up in Blender (exported as +Y up glTF),
origin on the ground, forward = -Y in Blender (= +Z... Godot's -Z forward after export, see export()).
Materials are plain Principled BSDF (base colour, metallic, roughness, emission) so they import cleanly into Godot's
Compatibility renderer; no image textures unless an asset needs one (max 1024 px).
"""
import math
from pathlib import Path
import bpy
import bmesh
from mathutils import Vector, Matrix

REPO = Path(__file__).resolve().parents[2]
BLEND_DIR = REPO/'blender'
MODELS = REPO/'assets'/'models'
PREVIEWS = REPO/'assets'/'previews'
VFX = REPO/'assets'/'vfx'

PALETTE = {
    'suit_orange': (0.92, 0.22, 0.03, 1),
    'suit_white': (0.86, 0.85, 0.82, 1),
    'suit_dark': (0.10, 0.10, 0.11, 1),
    'visor_gold': (1.00, 0.72, 0.30, 1),
    'scanner_cyan': (0.20, 0.92, 0.95, 1),
    'metal': (0.62, 0.63, 0.65, 1),
    'kapton': (0.89, 0.70, 0.29, 1),
    'panel_blue': (0.05, 0.08, 0.20, 1),
    'regolith': (0.42, 0.41, 0.39, 1),
    'rubber': (0.06, 0.06, 0.06, 1),
}


def new_scene():
    """Start from an empty file with metric units, 24 fps."""
    bpy.ops.wm.read_homefile(use_empty=True)
    s = bpy.context.scene
    s.unit_settings.system = 'METRIC'
    s.unit_settings.scale_length = 1.0
    s.render.fps = 24
    return s


def material(name, color, metallic=0.0, roughness=0.6, emission=None, strength=0.0):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes.get('Principled BSDF')
    b.inputs['Base Color'].default_value = color
    b.inputs['Metallic'].default_value = metallic
    b.inputs['Roughness'].default_value = roughness
    if emission is not None:
        b.inputs['Emission Color'].default_value = emission
        b.inputs['Emission Strength'].default_value = strength
    m.diffuse_color = color
    return m


def mat(key, **kw):
    return material(key, PALETTE[key], **kw)


def link(obj, collection=None):
    (collection or bpy.context.scene.collection).objects.link(obj)
    return obj


def mesh_object(name, bm, material_=None, smooth=True, collection=None):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    if smooth:
        for p in me.polygons:
            p.use_smooth = True
    ob = bpy.data.objects.new(name, me)
    if material_ is not None:
        ob.data.materials.append(material_)
    return link(ob, collection)


def capsule(name, radius, length, location=(0, 0, 0), rotation=(0, 0, 0), segments=12, rings=4, material_=None,
            scale=(1, 1, 1)):
    """Capsule along local Z, centred at location."""
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings*2, radius=radius)
    half = max(length/2-radius, 0)
    for v in bm.verts:
        v.co.z += half if v.co.z > 1e-6 else (-half if v.co.z < -1e-6 else 0)
        v.co.x *= scale[0]
        v.co.y *= scale[1]
        v.co.z *= scale[2]
    ob = mesh_object(name, bm, material_)
    ob.location = location
    ob.rotation_euler = rotation
    return ob


def sphere(name, radius, location=(0, 0, 0), segments=16, rings=10, material_=None, scale=(1, 1, 1)):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=radius)
    for v in bm.verts:
        v.co.x *= scale[0]
        v.co.y *= scale[1]
        v.co.z *= scale[2]
    ob = mesh_object(name, bm, material_)
    ob.location = location
    return ob


def box(name, size, location=(0, 0, 0), bevel=0.0, material_=None, rotation=(0, 0, 0), segments=2):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co.x *= size[0]
        v.co.y *= size[1]
        v.co.z *= size[2]
    if bevel > 0:
        bmesh.ops.bevel(bm, geom=bm.edges[:], offset=bevel, segments=segments, affect='EDGES', profile=0.5)
    ob = mesh_object(name, bm, material_, smooth=bevel > 0)
    ob.location = location
    ob.rotation_euler = rotation
    if bevel > 0:
        ob.data.set_sharp_from_angle(angle=math.radians(40))
    return ob


def cylinder(name, radius, depth, location=(0, 0, 0), rotation=(0, 0, 0), segments=16, material_=None,
             radius_top=None, cap=True):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=cap, segments=segments, radius1=radius,
                          radius2=radius if radius_top is None else radius_top, depth=depth)
    ob = mesh_object(name, bm, material_)
    ob.location = location
    ob.rotation_euler = rotation
    ob.data.set_sharp_from_angle(angle=math.radians(40))
    return ob


def override(obj):
    """Context override so mode switches work when scripts run outside the UI (e.g. the Blender MCP)."""
    win = bpy.context.window_manager.windows[0]
    area = next((a for a in win.screen.areas if a.type == 'VIEW_3D'), win.screen.areas[0])
    region = next((r for r in area.regions if r.type == 'WINDOW'), area.regions[0])
    bpy.context.view_layer.objects.active = obj
    return bpy.context.temp_override(window=win, area=area, region=region, active_object=obj, object=obj,
                                     selected_objects=[obj], selected_editable_objects=[obj])


def set_mode(obj, mode):
    with override(obj):
        bpy.ops.object.mode_set(mode=mode)


def apply_transforms(objs):
    """Bake each mesh object's transform into its mesh data (no operators needed)."""
    for o in objs:
        if o.type == 'MESH':
            o.data.transform(o.matrix_basis)
            o.matrix_basis = Matrix.Identity(4)


def join(objs, name):
    """Merge mesh objects into one (transforms baked, material slots and vertex groups kept)."""
    bm = bmesh.new()
    mats, groups = [], []
    deform = bm.verts.layers.deform.verify()
    for o in objs:
        part = bmesh.new()
        part.from_mesh(o.data)
        # matrix_basis, not matrix_world: matrix_world is a cached value that is stale until the depsgraph
        # updates, so using it double-applies transforms after any operator ran mid-build (parts are unparented)
        part.transform(o.matrix_basis)
        slot_map = []
        for m in o.data.materials:
            if m not in mats:
                mats.append(m)
            slot_map.append(mats.index(m))
        pd = part.verts.layers.deform.active
        names = [g.name for g in o.vertex_groups]
        for n in names:
            if n not in groups:
                groups.append(n)
        vmap = {}
        for v in part.verts:
            nv = bm.verts.new(v.co)
            if pd is not None:
                for gi, w in v[pd].items():
                    nv[deform][groups.index(names[gi])] = w
            vmap[v] = nv
        bm.verts.index_update()
        for f in part.faces:
            try:
                nf = bm.faces.new([vmap[v] for v in f.verts])
            except ValueError:
                continue
            nf.material_index = slot_map[f.material_index] if slot_map else 0
            nf.smooth = f.smooth
        part.free()
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    for m in mats:
        me.materials.append(m)
    for g in groups:
        ob.vertex_groups.new(name=g)
    link(ob)
    for o in objs:
        bpy.data.objects.remove(o, do_unlink=True)
    me.set_sharp_from_angle(angle=math.radians(35))
    return ob


def assign_group(obj, group):
    """Put every vertex of obj in one vertex group (rigid skinning to the bone of the same name)."""
    vg = obj.vertex_groups.get(group) or obj.vertex_groups.new(name=group)
    vg.add([v.index for v in obj.data.vertices], 1.0, 'REPLACE')
    return obj


def triangles(objs):
    total = 0
    for o in objs:
        if o.type == 'MESH':
            dg = bpy.context.evaluated_depsgraph_get()
            me = o.evaluated_get(dg).to_mesh()
            total += sum(len(p.vertices)-2 for p in me.polygons)
            o.evaluated_get(dg).to_mesh_clear()
    return total


def save_blend(name):
    path = BLEND_DIR/f'{name}.blend'
    bpy.ops.wm.save_as_mainfile(filepath=str(path), compress=True)
    return path


def export_glb(name, objects=None, animations=True):
    """Export to assets/models/<name>.glb (+Y up, metres, applied modifiers, named actions as glTF animations)."""
    path = MODELS/f'{name}.glb'
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    use_selection = objects is not None
    if objects:
        for o in objects:
            o.select_set(True)
    win = bpy.context.window_manager.windows[0]
    area = next((a for a in win.screen.areas if a.type == 'VIEW_3D'), win.screen.areas[0])
    first = objects[0] if objects else None
    # FK actions are exported; mute IK/other bone constraints so they are not baked in (and don't spam warnings)
    muted = []
    for o in (objects or bpy.context.scene.objects):
        if o.type == 'ARMATURE':
            for pb in o.pose.bones:
                for c in pb.constraints:
                    if not c.mute:
                        c.mute = True
                        muted.append(c)
    try:
        with bpy.context.temp_override(window=win, area=area, active_object=first, object=first,
                                       selected_objects=list(objects or []), view_layer=bpy.context.view_layer):
            _gltf(path, use_selection, animations)
    finally:
        for c in muted:
            c.mute = False
    return path


def _gltf(path, use_selection, animations):
    bpy.ops.export_scene.gltf(
        filepath=str(path), export_format='GLB', use_selection=use_selection, export_yup=True,
        export_apply=True, export_animations=animations, export_animation_mode='ACTIONS',
        export_force_sampling=True, export_frame_step=1, export_def_bones=False,
        export_anim_single_armature=True, export_reset_pose_bones=True, export_optimize_animation_size=True,
        export_materials='EXPORT', export_image_format='AUTO', export_cameras=False, export_lights=False)
    return path


def preview(name, target=(0, 0, 0.9), distance=4.0, elevation_deg=12, azimuth_deg=-35, size=(900, 900),
            lens=50, frame=None, suffix='', sun_rotation=None):
    """Render a quick EEVEE review image to assets/previews/<name><suffix>.png against a dark backdrop."""
    s = bpy.context.scene
    if frame is not None:
        s.frame_set(frame)
    cam = bpy.data.objects.get('_PreviewCam')
    if cam is None:
        cam = link(bpy.data.objects.new('_PreviewCam', bpy.data.cameras.new('_PreviewCam')))
        sun = link(bpy.data.objects.new('_PreviewSun', bpy.data.lights.new('_PreviewSun', 'SUN')))
        sun.data.energy = 4.0
        sun.rotation_euler = (math.radians(55), 0, math.radians(-40))
        fill = link(bpy.data.objects.new('_PreviewFill', bpy.data.lights.new('_PreviewFill', 'SUN')))
        fill.data.energy = 0.6
        fill.rotation_euler = (math.radians(70), 0, math.radians(140))
    if sun_rotation is not None:
        bpy.data.objects['_PreviewSun'].rotation_euler = sun_rotation
    cam.data.lens = lens
    el, az = math.radians(elevation_deg), math.radians(azimuth_deg)
    t = Vector(target)
    cam.location = t+Vector((distance*math.cos(el)*math.sin(az), -distance*math.cos(el)*math.cos(az), distance*math.sin(el)))
    direction = t-cam.location
    cam.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
    s.camera = cam
    w = s.world or bpy.data.worlds.new('World')
    s.world = w
    w.use_nodes = True
    w.node_tree.nodes['Background'].inputs['Color'].default_value = (0.02, 0.02, 0.025, 1)
    s.render.engine = 'BLENDER_EEVEE'
    s.render.resolution_x, s.render.resolution_y = size
    s.render.film_transparent = False
    s.view_settings.view_transform = 'Standard'
    out = PREVIEWS/f'{name}{suffix}.png'
    s.render.filepath = str(out)
    bpy.ops.render.render(write_still=True)
    return out


def remove_preview_rig():
    for n in ('_PreviewCam', '_PreviewSun', '_PreviewFill'):
        o = bpy.data.objects.get(n)
        if o:
            bpy.data.objects.remove(o, do_unlink=True)


def build_rig(name, bones):
    """bones: {name: (head, tail, parent or None, deform)} -> armature object (rest pose)."""
    arm = link(bpy.data.objects.new(name, bpy.data.armatures.new(name)))
    set_mode(arm, 'EDIT')
    eb = arm.data.edit_bones
    for n, (h, t, parent, deform) in bones.items():
        b = eb.new(n)
        b.head, b.tail = Vector(h), Vector(t)
        b.use_deform = deform
    for n, (h, t, parent, deform) in bones.items():
        if parent:
            eb[n].parent = eb[parent]
    set_mode(arm, 'OBJECT')
    for pb in arm.pose.bones:
        pb.rotation_mode = 'QUATERNION'
    return arm


def rotate_world(arm, bone, axis, degrees):
    """Pose `bone` by a rotation about a WORLD axis given in the rest pose (composes correctly down a chain)."""
    from mathutils import Quaternion
    pb = arm.pose.bones[bone]
    local_axis = (pb.bone.matrix_local.to_3x3().inverted() @ Vector(axis)).normalized()
    pb.rotation_quaternion = Quaternion(local_axis, math.radians(degrees))


def key_pose(arm, frame, rotations=None, moves=None):
    """rotations: {bone: (world_axis, degrees)}; moves: {bone: world offset (x, y, z) in metres}. Keys every bone."""
    from mathutils import Quaternion
    for pb in arm.pose.bones:
        pb.rotation_quaternion = Quaternion()
        pb.location = (0, 0, 0)
    for b, (axis, deg) in (rotations or {}).items():
        rotate_world(arm, b, axis, deg)
    for b, off in (moves or {}).items():
        pb = arm.pose.bones[b]
        pb.location = pb.bone.matrix_local.to_3x3().inverted() @ Vector(off)
    for pb in arm.pose.bones:
        pb.keyframe_insert('rotation_quaternion', frame=frame)
        pb.keyframe_insert('location', frame=frame)


def new_action(arm, name, frames, loop=True):
    act = bpy.data.actions.new(name)
    act.use_fake_user = True
    arm.animation_data_create()
    arm.animation_data.action = act
    act.frame_range = frames
    act.use_frame_range = True
    act.use_cyclic = loop
    return act


def rest(arm):
    from mathutils import Quaternion
    if arm.animation_data:
        arm.animation_data.action = None
    for pb in arm.pose.bones:
        pb.location = (0, 0, 0)
        pb.rotation_quaternion = Quaternion()
        pb.rotation_euler = (0, 0, 0)


def skin(parts_by_bone, name, arm):
    """parts_by_bone: list of (object, bone). Rigid-skins each part to its bone, joins them and binds to arm."""
    objs = []
    for ob, bone in parts_by_bone:
        assign_group(ob, bone)
        objs.append(ob)
    apply_transforms(objs)
    body = join(objs, name)
    mod = body.modifiers.new('Armature', 'ARMATURE')
    mod.object = arm
    body.parent = arm
    return body


def strut(name, p1, p2, radius, segments=8, material_=None):
    """Cylinder from point p1 to point p2."""
    a, b = Vector(p1), Vector(p2)
    d = b-a
    ob = cylinder(name, radius, d.length, (a+b)/2, d.to_track_quat('Z', 'Y').to_euler(), segments=segments, material_=material_)
    return ob


# ------------------------------------------------------------------ detail helpers (v2 assets)
def lathe(name, profile, segments=24, material_=None, scale_xy=(1.0, 1.0), cap_ends=True):
    """Surface of revolution around local Z. profile: [(radius, z), ...] bottom to top. Optional elliptical section."""
    bm = bmesh.new()
    rings = []
    for r, z in profile:
        ring = []
        for i in range(segments):
            a = 2*math.pi*i/segments
            ring.append(bm.verts.new((r*math.cos(a)*scale_xy[0], r*math.sin(a)*scale_xy[1], z)))
        rings.append(ring)
    for k in range(len(rings)-1):
        for i in range(segments):
            j = (i+1) % segments
            bm.faces.new((rings[k][i], rings[k][j], rings[k+1][j], rings[k+1][i]))
    if cap_ends:
        if profile[0][0] > 1e-6:
            bm.faces.new(list(reversed(rings[0])))
        if profile[-1][0] > 1e-6:
            bm.faces.new(rings[-1])
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    return mesh_object(name, bm, material_)


def align(ob, a, b, length_scale=True, roll=0.0):
    """Place an object modelled along +Z from z=0 to z=1 (if length_scale) so it runs from point a to point b."""
    a, b = Vector(a), Vector(b)
    d = b-a
    q = d.to_track_quat('Z', 'Y')
    if roll:
        from mathutils import Quaternion
        q = q @ Quaternion((0, 0, 1), roll)
    ob.rotation_mode = 'QUATERNION'
    ob.rotation_quaternion = q
    ob.location = a
    if length_scale:
        ob.scale = (1, 1, d.length)
    ob.rotation_mode = 'XYZ'
    ob.rotation_euler = q.to_euler()
    return ob


def limb(name, a, b, radii, segments=20, material_=None, scale_xy=(1.0, 1.0)):
    """Tapered limb from a to b; radii: list of radii evenly spaced along the length (rounded by extra end rings)."""
    n = len(radii)
    prof = [(radii[0]*.55, -0.02), (radii[0]*.9, 0.0)]
    prof += [(r, k/(n-1)) for k, r in enumerate(radii)]
    prof += [(radii[-1]*.9, 1.0), (radii[-1]*.55, 1.02)]
    prof = [(r, z) for r, z in prof]
    ob = lathe(name, prof, segments, material_, scale_xy)
    return align(ob, a, b)


def torus(name, major, minor, location=(0, 0, 0), normal=(0, 0, 1), segments=24, tube=8, material_=None, scale_xy=(1, 1)):
    bm = bmesh.new()
    rings = []
    for i in range(segments):
        a = 2*math.pi*i/segments
        ring = []
        for k in range(tube):
            t = 2*math.pi*k/tube
            r = major+minor*math.cos(t)
            ring.append(bm.verts.new((r*math.cos(a)*scale_xy[0], r*math.sin(a)*scale_xy[1], minor*math.sin(t))))
        rings.append(ring)
    for i in range(segments):
        for k in range(tube):
            bm.faces.new((rings[i][k], rings[(i+1) % segments][k], rings[(i+1) % segments][(k+1) % tube], rings[i][(k+1) % tube]))
    ob = mesh_object(name, bm, material_)
    n = Vector(normal).normalized()
    ob.rotation_euler = n.to_track_quat('Z', 'Y').to_euler()
    ob.location = location
    return ob


def tube(name, points, radius, segments=10, material_=None):
    """Swept circle along a polyline (hoses, cables, rails)."""
    pts = [Vector(p) for p in points]
    bm = bmesh.new()
    rings = []
    prev_n = None
    for i, p in enumerate(pts):
        t = (pts[min(i+1, len(pts)-1)]-pts[max(i-1, 0)]).normalized()
        if prev_n is None:
            prev_n = t.orthogonal().normalized()
        n = (prev_n-t*prev_n.dot(t)).normalized()
        prev_n = n
        bnorm = t.cross(n)
        rings.append([bm.verts.new(p+radius*(math.cos(2*math.pi*k/segments)*n+math.sin(2*math.pi*k/segments)*bnorm))
                      for k in range(segments)])
    for i in range(len(rings)-1):
        for k in range(segments):
            bm.faces.new((rings[i][k], rings[i][(k+1) % segments], rings[i+1][(k+1) % segments], rings[i+1][k]))
    bm.faces.new(list(reversed(rings[0])))
    bm.faces.new(rings[-1])
    return mesh_object(name, bm, material_)


def rbox(name, size, location=(0, 0, 0), radius=0.02, segments=3, material_=None, rotation=(0, 0, 0)):
    """Rounded box (bevelled on all edges) — the workhorse for hard parts."""
    return box(name, size, location, bevel=radius, material_=material_, rotation=rotation, segments=segments)


def transparent(name, color, alpha, roughness=0.05, metallic=0.0):
    m = material(name, color, metallic=metallic, roughness=roughness)
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Alpha'].default_value = alpha
    try:
        m.surface_render_method = 'BLENDED'
    except Exception:
        pass
    m.blend_method = 'BLEND' if hasattr(m, 'blend_method') else None
    return m


TEXTURES = REPO/'assets'/'textures'


def texture_material(name, color=(0.5, 0.5, 0.5, 1), albedo=None, normal=None, roughness=0.95, normal_strength=1.0,
                     metallic=0.0):
    """Principled material with optional albedo and normal images from assets/textures (embedded on GLB export)."""
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = color
    b.inputs['Roughness'].default_value = roughness
    b.inputs['Metallic'].default_value = metallic
    if albedo:
        t = nt.nodes.new('ShaderNodeTexImage')
        t.image = bpy.data.images.load(str(TEXTURES/albedo), check_existing=True)
        nt.links.new(t.outputs['Color'], b.inputs['Base Color'])
    if normal:
        n = nt.nodes.new('ShaderNodeTexImage')
        n.image = bpy.data.images.load(str(TEXTURES/normal), check_existing=True)
        n.image.colorspace_settings.name = 'Non-Color'
        nm = nt.nodes.new('ShaderNodeNormalMap')
        nm.inputs['Strength'].default_value = normal_strength
        nt.links.new(n.outputs['Color'], nm.inputs['Color'])
        nt.links.new(nm.outputs['Normal'], b.inputs['Normal'])
    return m


def box_uv(ob, metres_per_tile=0.5):
    """Box-projected UVs (each face projected along its dominant axis), for detail textures on hull rocks."""
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    uv = bm.loops.layers.uv.verify()
    for f in bm.faces:
        n = f.normal
        ax = max(range(3), key=lambda i: abs(n[i]))
        for loop in f.loops:
            c = loop.vert.co
            u, v = [(c.y, c.z), (c.x, c.z), (c.x, c.y)][ax]
            loop[uv].uv = (u/metres_per_tile, v/metres_per_tile)
    bm.to_mesh(ob.data)
    bm.free()


def limb_folds(name, a, b, radii, segments=14, material_=None, folds=(), samples=10):
    """Tapered limb from a to b with soft-goods convolute folds.

    radii: radii evenly spaced along the length. folds: [(t0, t1, count, depth)] — `count` ridges between
    fractions t0..t1 of the length, each bulging by `depth` x radius (pressure-suit convolutes / fabric folds).
    """
    ts = set(k/(samples-1) for k in range(samples))
    for t0, t1, count, depth in folds:
        for k in range(count*3+1):
            ts.add(t0+(t1-t0)*k/(count*3))
    ts = sorted(ts)
    def base(t):
        x = t*(len(radii)-1)
        i = min(int(x), len(radii)-2)
        f = x-i
        return radii[i]*(1-f)+radii[i+1]*f
    prof = [(radii[0]*.55, -0.02), (radii[0]*.9, 0.0)]
    for t in ts:
        r = base(t)
        for t0, t1, count, depth in folds:
            if t0 <= t <= t1:
                ph = (t-t0)/(t1-t0)*count
                r *= 1+depth*abs(math.sin(math.pi*ph))
        prof.append((r, t))
    prof += [(radii[-1]*.9, 1.0), (radii[-1]*.55, 1.02)]
    ob = lathe(name, prof, segments, material_)
    return align(ob, a, b)


def strip(name, a, b, width, thickness, material_=None, offset=(0, 0, 0)):
    """Flat strip (seam panel) from a to b, offset sideways; width along the offset direction's normal."""
    a, b = Vector(a)+Vector(offset), Vector(b)+Vector(offset)
    ob = box(name, (width, thickness, 1.0), (0, 0, 0), material_=material_)
    ob.data.transform(Matrix.Translation((0, 0, 0.5)))      # run from z = 0 to z = 1
    side = Vector(offset).normalized() if Vector(offset).length > 1e-6 else Vector((1, 0, 0))
    d = (b-a).normalized()
    z = d
    y = side
    x = y.cross(z).normalized()
    y = z.cross(x).normalized()
    M = Matrix((x, y, z)).transposed().to_4x4()
    ob.matrix_basis = Matrix.Translation(a) @ M @ Matrix.Diagonal((1, 1, (b-a).length, 1))
    return ob
