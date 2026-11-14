"""Rig the teammate's astronaut (assets/team/models/astronaut.glb, a static T-pose made with MINT) to the Sunline
astronaut skeleton, so it gets all seven existing animations (idle, lunar_lope, walk_slow, turn_in_place, scan_raise,
scan_sweep, kneel_sample) and the scanner on the right hand.

How (no UI operators, so it runs headless:  blender -b --python blender/scripts/rig_team_astronaut.py):
 1. Open blender/astronaut.blend (rig + procedural body + scanner + actions).
 2. Import the team mesh, bake its transform, scale it to 1.88 m, feet on the ground, facing -Y like our body.
 3. Pose our rig into the team mesh's T-pose (arm chains straightened toward its measured hand height/reach).
 4. Bake our body in that T-pose (with its vertex groups) and copy the weights onto the team mesh
    (nearest-face interpolation), so both are weighted in the same pose.
 5. Fold the team mesh's arms down by deforming it with the inverse of the T-pose, i.e. into the rig's rest pose,
    then bind it to the rig with an Armature modifier. Our procedural body is removed from this file.
Outputs: blender/astronaut_team.blend, assets/models/astronaut_team.glb, assets/previews/astronaut_team_*.png
"""
import sys
from pathlib import Path
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(r'C:\dev\godot\new-game-project\blender\scripts')))
import importlib
import sunline_common as C
importlib.reload(C)

TEAM = C.REPO/'assets'/'team'/'models'/'astronaut.glb'
HEIGHT = 1.88
ARMS = ['upper_arm', 'forearm', 'hand']


def update():
    bpy.context.view_layer.update()


def bake(obj, name):
    """Evaluated mesh (modifiers applied) as a new object that keeps the vertex groups."""
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(obj.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
    ob = bpy.data.objects.new(name, me)
    C.link(ob)
    for g in obj.vertex_groups:
        ob.vertex_groups.new(name=g.name)
    return ob


def main():
    bpy.ops.wm.open_mainfile(filepath=str(C.BLEND_DIR/'astronaut.blend'))
    rig = bpy.data.objects['AstronautRig']
    body = bpy.data.objects['Astronaut']
    scanner = bpy.data.objects['Scanner']
    saved_action = rig.animation_data.action if rig.animation_data else None
    if rig.animation_data:
        rig.animation_data.action = None
    muted = []
    for pb in rig.pose.bones:
        pb.matrix_basis = Matrix.Identity(4)
        for c in pb.constraints:
            if not c.mute:
                c.mute = True
                muted.append(c)
    update()

    # --- 2. import and normalise the team mesh
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(TEAM))
    new = [o for o in bpy.data.objects if o not in before]
    team = next(o for o in new if o.type == 'MESH')
    update()
    mw = team.matrix_world.copy()
    team.parent = None
    team.data.transform(mw)
    team.matrix_world = Matrix.Identity(4)
    for o in new:
        if o is not team:
            bpy.data.objects.remove(o, do_unlink=True)
    vs = [v.co for v in team.data.vertices]
    zmin, zmax = min(v.z for v in vs), max(v.z for v in vs)
    s = HEIGHT/(zmax-zmin)
    cx = (min(v.x for v in vs)+max(v.x for v in vs))/2
    cy = (min(v.y for v in vs)+max(v.y for v in vs))/2
    team.data.transform(Matrix.Diagonal((s, s, s, 1)) @ Matrix.Translation((-cx, -cy, -zmin)))
    # facing: the rig (knee/elbow poles, foot bones) is built for a body facing -Y. The imported MINT mesh needs
    # no turn to face -Y: an earlier automatic "which side sticks out more" test turned it 180° the wrong way
    # (renders showed the backpack toward a camera on -Y), which made the knees, elbows and walk run backwards.
    back_neg = False
    arm_v = [v.co for v in team.data.vertices if abs(v.co.x) > 0.6]
    arm_z = sum(v.z for v in arm_v)/max(1, len(arm_v))
    reach = max(abs(v.co.x) for v in team.data.vertices)

    # --- 3. pose our rig into the T-pose
    for side, sx in (('L', 1.0), ('R', -1.0)):
        names = [f'{n}.{side}' for n in ARMS]
        shoulder = rig.data.bones[names[0]].head_local.copy()
        chain = sum(rig.data.bones[n].length for n in names)
        tip = Vector((sx*min(reach*0.97, abs(shoulder.x)+chain), shoulder.y, arm_z))
        d1 = (tip-shoulder).normalized()
        pos = shoulder.copy()
        for n in names:
            b = rig.data.bones[n]
            d0 = (b.tail_local-b.head_local).normalized()
            R = d0.rotation_difference(d1).to_matrix().to_4x4()
            rig.pose.bones[n].matrix = Matrix.Translation(pos) @ R @ Matrix.Translation(-b.head_local) @ b.matrix_local
            update()
            pos = pos+d1*b.length

    # --- 4. our body in T-pose -> weights onto the team mesh
    our_t = bake(body, 'OurT')
    for g in body.vertex_groups:
        team.vertex_groups.new(name=g.name)
    dt = team.modifiers.new('Weights', 'DATA_TRANSFER')
    dt.object = our_t
    dt.use_vert_data = True
    dt.data_types_verts = {'VGROUP_WEIGHTS'}
    dt.vert_mapping = 'POLYINTERP_NEAREST'
    dt.layers_vgroup_select_src = 'ALL'
    dt.layers_vgroup_select_dst = 'NAME'
    update()
    weighted = bake(team, 'TeamWeighted')
    weighted.data.materials.clear()
    for m in team.data.materials:
        weighted.data.materials.append(m)
    bpy.data.objects.remove(team, do_unlink=True)
    team = weighted

    # --- 5. fold the arms down: deform by the inverse of the T-pose, then rest pose + armature modifier
    deform = {pb.name: pb.matrix @ pb.bone.matrix_local.inverted() for pb in rig.pose.bones}
    for pb in rig.pose.bones:			# parents come before children
        pb.matrix = deform[pb.name].inverted() @ pb.bone.matrix_local
        update()
    am = team.modifiers.new('Armature', 'ARMATURE')
    am.object = rig
    update()
    rested = bake(team, 'Astronaut_team')
    rested.data.materials.clear()
    for m in team.data.materials:
        rested.data.materials.append(m)
    bpy.data.objects.remove(team, do_unlink=True)
    for pb in rig.pose.bones:
        pb.matrix_basis = Matrix.Identity(4)
    update()

    # --- bind to the rig, drop the procedural body
    bpy.data.objects.remove(our_t, do_unlink=True)
    bpy.data.objects.remove(body, do_unlink=True)
    rested.name = rested.data.name = 'Astronaut'
    rested.parent = rig
    am = rested.modifiers.new('Armature', 'ARMATURE')
    am.object = rig
    for p in rested.data.polygons:
        p.use_smooth = True
    for c in muted:
        c.mute = False
    if saved_action:
        rig.animation_data.action = saved_action
    update()

    # --- previews: rest, and mid-stride in the lunar lope
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    C.preview('astronaut_team', target=(0, 0, 0.95), distance=4.2, azimuth_deg=-30, suffix='_rest', frame=1)
    if rig.animation_data:
        rig.animation_data.action = bpy.data.actions['lunar_lope']
        C.preview('astronaut_team', target=(0, 0, 0.95), distance=4.2, azimuth_deg=-60, suffix='_lope', frame=12)
        rig.animation_data.action = bpy.data.actions['scan_sweep']
        C.preview('astronaut_team', target=(0, 0, 0.95), distance=4.2, azimuth_deg=20, suffix='_scan', frame=20)
        rig.animation_data.action = saved_action
    for name in ('_PreviewCam', '_PreviewSun', '_PreviewFloor', '_PreviewBackdrop'):
        if name in bpy.data.objects:
            bpy.data.objects.remove(bpy.data.objects[name], do_unlink=True)

    # --- export (FK actions; constraints muted so IK is not baked in)
    objs = [rig, rested, scanner]
    for o in bpy.context.view_layer.objects:
        o.select_set(o in objs)
    for pb in rig.pose.bones:
        for c in pb.constraints:
            c.mute = True
    C._gltf(C.MODELS/'astronaut_team.glb', True, True)
    for c in muted:
        c.mute = False
    bpy.ops.wm.save_as_mainfile(filepath=str(C.BLEND_DIR/'astronaut_team.blend'), compress=True)
    print('TEAM_RIG', dict(scale=round(s, 3), flipped=back_neg, arm_z=round(arm_z, 3), reach=round(reach, 3),
                           verts=len(rested.data.vertices), groups=len(rested.vertex_groups)))


main()
