"""Sunline astronaut: orange EVA suit, gold visor, backpack, rigged and animated; plus the cyan handheld scanner.

Run inside Blender (Blender MCP or Text Editor):
    exec(open(r'<repo>/blender/scripts/build_astronaut.py').read())
Outputs: blender/astronaut.blend, assets/models/astronaut.glb, assets/models/scanner.glb, previews.

Rig: deform bones root/hips/spine/chest/neck/head, upper_arm/forearm/hand, thigh/shin/foot (.L/.R), plus
non-deform sockets `scanner_socket` (child of hand.R, scanner grip) and `camera_anchor` (child of head, eye point
for the first-person camera), and IK controls (`ik_foot.*`, `ik_hand.*`, poles) for hand-animating in Blender.
The scripted actions below are FK, with IK influence 0, and are exported baked.
Skinning is rigid: each suit part follows one bone (the bulky suit hides the joints), which is cheap for the web.

Animations (24 fps, no root motion; Godot moves the character):
    idle, lunar_lope, walk_slow, turn_in_place, scan_raise, scan_sweep, kneel_sample
lunar_lope timing follows lunar gravity: a 0.18 m hop at 1.62 m/s² stays airborne 2*sqrt(2h/g) ≈ 0.94 s,
so one stride is 29 frames (≈1.2 s) with ~6 frames of ground contact.
Model faces Blender -Y, which becomes glTF/Godot +Z (Godot's MODEL_FRONT).
"""
import math
import sys
from pathlib import Path
import bpy
import bmesh
from mathutils import Vector, Matrix

sys.path.insert(0, str(Path(r'C:\dev\godot\new-game-project\blender\scripts')))
import importlib
import sunline_common as C
importlib.reload(C)

G = 1.62
HOP = 0.18
AIR_FRAMES = round(2*math.sqrt(2*HOP/G)*24)        # ≈ 23
CONTACT_FRAMES = 6
LOPE = AIR_FRAMES+CONTACT_FRAMES

# ---------------------------------------------------------------- skeleton (head, tail) in metres, Z up, front -Y
BONES = {
    'root': ((0, 0, 0), (0, 0, 0.25), None, False),
    'hips': ((0, 0, 0.98), (0, 0, 1.10), 'root', True),
    'spine': ((0, 0, 1.10), (0, 0, 1.30), 'hips', True),
    'chest': ((0, 0, 1.30), (0, 0, 1.52), 'spine', True),
    'neck': ((0, 0, 1.52), (0, 0, 1.60), 'chest', True),
    'head': ((0, 0, 1.60), (0, 0, 1.86), 'neck', True),
    'camera_anchor': ((0, -0.08, 1.72), (0, -0.22, 1.72), 'head', False),
}
for side, sx in (('L', 1), ('R', -1)):
    BONES.update({
        f'upper_arm.{side}': ((0.25*sx, 0, 1.46), (0.31*sx, 0.01, 1.18), 'chest', True),
        f'forearm.{side}': ((0.31*sx, 0.01, 1.18), (0.33*sx, -0.01, 0.94), f'upper_arm.{side}', True),
        f'hand.{side}': ((0.33*sx, -0.01, 0.94), (0.34*sx, -0.02, 0.82), f'forearm.{side}', True),
        f'thigh.{side}': ((0.11*sx, 0, 0.96), (0.12*sx, 0.0, 0.53), 'hips', True),
        f'shin.{side}': ((0.12*sx, 0.0, 0.53), (0.12*sx, 0.02, 0.11), f'thigh.{side}', True),
        f'foot.{side}': ((0.12*sx, 0.02, 0.11), (0.12*sx, -0.13, 0.04), f'shin.{side}', True),
        f'ik_foot.{side}': ((0.12*sx, 0.02, 0.11), (0.12*sx, 0.02, 0.0), 'root', False),
        f'pole_knee.{side}': ((0.12*sx, -0.6, 0.53), (0.12*sx, -0.7, 0.53), 'root', False),
        f'ik_hand.{side}': ((0.33*sx, -0.01, 0.94), (0.33*sx, -0.01, 0.84), 'root', False),
        f'pole_elbow.{side}': ((0.31*sx, 0.5, 1.18), (0.31*sx, 0.6, 1.18), 'root', False),
    })
# grip in the right fist, pointing out along the hand: down at rest, forward when the arm is raised to scan
BONES['scanner_socket'] = ((-0.336, -0.016, 0.885), (-0.343, -0.022, 0.785), 'hand.R', False)


def build_armature():
    arm_data = bpy.data.armatures.new('AstronautRig')
    arm = C.link(bpy.data.objects.new('AstronautRig', arm_data))
    C.set_mode(arm, 'EDIT')
    eb = arm_data.edit_bones
    for name, (h, t, parent, deform) in BONES.items():
        b = eb.new(name)
        b.head, b.tail = Vector(h), Vector(t)
        b.use_deform = deform
        b.align_roll(Vector((0, -1, 0)) if abs((b.tail-b.head).normalized().y) < .9 else Vector((0, 0, 1)))
    for name, (h, t, parent, deform) in BONES.items():
        if parent:
            eb[name].parent = eb[parent]
            eb[name].use_connect = (Vector(h)-eb[parent].tail).length < 1e-4 and name not in ('hips',)
    C.set_mode(arm, 'POSE')
    for side in 'LR':
        for chain_end, target, pole, angle in ((f'shin.{side}', f'ik_foot.{side}', f'pole_knee.{side}', -90),
                                                (f'forearm.{side}', f'ik_hand.{side}', f'pole_elbow.{side}', -90)):
            c = arm.pose.bones[chain_end].constraints.new('IK')
            c.target, c.subtarget = arm, target
            c.pole_target, c.pole_subtarget = arm, pole
            c.pole_angle = math.radians(angle)
            c.chain_count = 2
            c.influence = 0.0          # FK by default; animators can raise it in Blender
    for pb in arm.pose.bones:
        pb.rotation_mode = 'XYZ'
    C.set_mode(arm, 'OBJECT')
    return arm


# ---------------------------------------------------------------- suit parts (rigid to one bone each)
def build_body():
    orange, white, dark = C.mat('suit_orange', roughness=.75), C.mat('suit_white', roughness=.6), C.mat('suit_dark', roughness=.5)
    gold = C.mat('visor_gold', metallic=1.0, roughness=.12)
    parts = []

    def part(ob, bone):
        C.assign_group(ob, bone)
        parts.append(ob)
        return ob

    def between(a, b):
        """(midpoint, length, rotation) for a capsule from point a to point b."""
        a, b = Vector(a), Vector(b)
        d = b-a
        rot = d.to_track_quat('Z', 'Y').to_euler()
        return (a+b)/2, d.length, rot

    # torso and pelvis
    part(C.capsule('pelvis', .17, .30, (0, 0, 1.02), material_=orange, scale=(1.15, .85, 1)), 'hips')
    part(C.cylinder('belt', .185, .06, (0, 0, 1.12), segments=20, material_=dark), 'hips')
    part(C.capsule('abdomen', .175, .28, (0, 0, 1.22), material_=orange, scale=(1.12, .85, 1)), 'spine')
    part(C.capsule('torso', .21, .36, (0, 0, 1.40), material_=orange, scale=(1.18, .9, 1)), 'chest')
    part(C.box('chest_panel', (.26, .05, .16), (0, -.19, 1.40), bevel=.015, material_=white), 'chest')
    part(C.box('chest_display', (.12, .02, .05), (0, -.218, 1.43), bevel=.005, material_=dark), 'chest')
    part(C.box('backpack', (.42, .22, .52), (0, .26, 1.36), bevel=.04, material_=white), 'chest')
    part(C.box('backpack_top', (.36, .16, .06), (0, .27, 1.645), bevel=.02, material_=dark), 'chest')
    part(C.cylinder('neck_ring', .15, .06, (0, -.01, 1.555), segments=24, material_=dark), 'neck')
    # helmet: white shell + gold visor (front part of a slightly larger sphere)
    part(C.sphere('helmet', .165, (0, 0, 1.72), segments=24, rings=14, material_=white), 'head')
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=24, v_segments=14, radius=.172)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.y > -.035 or v.co.z < -.10 or v.co.z > .13], context='VERTS')
    visor = C.mesh_object('visor', bm, gold)
    visor.location = (0, 0, 1.72)
    part(visor, 'head')
    part(C.box('helmet_light', (.05, .04, .03), (.13, -.08, 1.83), bevel=.008, material_=dark), 'head')

    for side, sx in (('L', 1), ('R', -1)):
        def B(n):
            h, t, *_ = BONES[f'{n}.{side}']
            return h, t
        for bone, rad, col in (('upper_arm', .075, orange), ('forearm', .068, orange), ('thigh', .095, orange), ('shin', .085, orange)):
            h, t = B(bone)
            mid, length, rot = between(h, t)
            part(C.capsule(f'{bone}.{side}', rad, length+.06, mid, rot, material_=col), f'{bone}.{side}')
        # joint rings (white) on elbows and knees, shoulder caps
        for bone, rad in (('forearm', .074), ('shin', .092)):
            h, t = B(bone)
            mid, _, rot = between(h, t)
            ring = C.cylinder(f'{bone}_ring.{side}', rad, .05, Vector(h)+(Vector(t)-Vector(h)).normalized()*.03, rot, segments=16, material_=white)
            part(ring, f'{bone}.{side}')
        part(C.sphere(f'shoulder.{side}', .095, (.245*sx, 0, 1.47), material_=white), f'upper_arm.{side}')
        h, t = B('hand')
        part(C.sphere(f'glove.{side}', .055, (Vector(h)+Vector(t))/2, material_=white, scale=(.85, 1, 1.25)), f'hand.{side}')
        part(C.cylinder(f'cuff.{side}', .066, .04, Vector(h)+Vector((0, 0, .02)), segments=14, material_=dark), f'hand.{side}')
        h, t = B('foot')
        part(C.box(f'boot.{side}', (.13, .27, .12), (.12*sx, -.04, .07), bevel=.03, material_=white), f'foot.{side}')
        part(C.box(f'sole.{side}', (.135, .28, .03), (.12*sx, -.04, .015), bevel=.01, material_=dark), f'foot.{side}')

    C.apply_transforms(parts)
    body = C.join(parts, 'Astronaut')
    return body


def build_scanner():
    """Handheld scanner, origin at the grip, pointing -Y (forward). Separate object and glb."""
    dark, cyan = C.mat('suit_dark', roughness=.5), C.mat('scanner_cyan', emission=C.PALETTE['scanner_cyan'], strength=3.0)
    white = C.mat('suit_white', roughness=.6)
    p = [C.cylinder('grip', .018, .11, (0, 0, -.04), segments=10, material_=dark),
         C.box('scanner_body', (.07, .16, .05), (0, -.05, .025), bevel=.012, material_=white),
         C.box('scanner_screen', (.05, .07, .004), (0, -.03, .052), bevel=.002, material_=cyan),
         C.cylinder('scanner_lens', .018, .02, (0, -.135, .025), (math.radians(90), 0, 0), segments=12, material_=cyan),
         C.box('scanner_fin', (.008, .05, .03), (0, .01, .06), bevel=.003, material_=dark)]
    C.apply_transforms(p)
    return C.join(p, 'Scanner')


# ---------------------------------------------------------------- animation helpers
def axis_sign(arm, bone, axis, want):
    """+1/-1 so that a positive rotation about the bone's local `axis` moves its tail toward world direction `want`."""
    pb = arm.pose.bones[bone]
    m = (arm.matrix_world @ pb.bone.matrix_local).to_3x3()
    ax = m.col['XYZ'.index(axis)].normalized()
    along = (pb.bone.tail_local-pb.bone.head_local).normalized()
    if abs(ax.dot(along)) > .99:                 # twist axis: use the bone's local Z as the probe
        probe = m.col[2].normalized()
        move = ax.cross(probe)
    else:
        move = ax.cross(along)
    return 1 if move.dot(Vector(want)) >= 0 else -1


class Poser:
    def __init__(self, arm):
        self.arm = arm
        self.fwd = {b: axis_sign(arm, b, 'X', (0, -1, 0)) for b in arm.pose.bones.keys()}
        self.out = {b: axis_sign(arm, b, 'Z', (1 if b.endswith('.L') else -1, 0, 0)) for b in arm.pose.bones.keys()}
        self.yaw = {}
        for b in ('hips', 'spine', 'chest', 'neck', 'head'):
            # positive yaw turns the bone's front (-Y) toward +X (to the character's left)
            pb = arm.pose.bones[b]
            m = (arm.matrix_world @ pb.bone.matrix_local).to_3x3()
            ax = m.col[1].normalized()
            self.yaw[b] = 1 if ax.cross(Vector((0, -1, 0))).dot(Vector((1, 0, 0))) >= 0 else -1

    def reset(self):
        for pb in self.arm.pose.bones:
            pb.location = (0, 0, 0)
            pb.rotation_euler = (0, 0, 0)

    def pose(self, frame, **angles):
        """angles: '<bone>:fwd|out|yaw' degrees, or 'hips:up' metres."""
        touched = set()
        for key, value in angles.items():
            bone, kind = key.replace('__', '.').split(':')
            pb = self.arm.pose.bones[bone]
            if kind == 'up':
                pb.location.y = value
            elif kind == 'fwd':
                pb.rotation_euler.x = math.radians(value)*self.fwd[bone]
            elif kind == 'out':
                pb.rotation_euler.z = math.radians(value)*self.out[bone]
            elif kind == 'yaw':
                pb.rotation_euler.y = math.radians(value)*self.yaw[bone]
            touched.add(bone)
        for pb in self.arm.pose.bones:
            if pb.bone.use_deform or pb.name == 'root':
                pb.keyframe_insert('rotation_euler', frame=frame)
                pb.keyframe_insert('location', frame=frame)


def make_action(arm, poser, name, keys, loop=True):
    """keys: list of (frame, {pose kwargs}); every key starts from the rest pose."""
    act = bpy.data.actions.new(name)
    act.use_fake_user = True
    arm.animation_data_create()
    arm.animation_data.action = act
    for frame, kw in keys:
        poser.reset()
        poser.pose(frame, **kw)
    act.frame_range = (keys[0][0], keys[-1][0])
    act.use_frame_range = True
    act.use_cyclic = loop
    return act


def rest_arms(sx=8):
    return {'upper_arm__L:out': sx, 'upper_arm__R:out': sx, 'forearm__L:fwd': 12, 'forearm__R:fwd': 12}


def build_actions(arm):
    P = Poser(arm)
    acts = []
    # idle: slow breathing sway, 2 s loop
    k = []
    for f, s in ((1, 0), (13, 1), (25, 0), (37, -1), (49, 0)):
        k.append((f, {**rest_arms(9+s), 'chest:fwd': 1.5*s, 'head:fwd': -1*s, 'head:yaw': 2*s, 'hips:up': -.004*abs(s)}))
    acts.append(make_action(arm, P, 'idle', k))

    # lunar_lope: contact (crouch, push) then a long ballistic flight; lead leg L forward
    k = []
    n = LOPE
    for f in range(0, n+1):
        u = f/n
        if f <= CONTACT_FRAMES:                      # crouch then push
            c = math.sin(math.pi*f/CONTACT_FRAMES)
            up = -.07*c
            knee = 35*c
            lean = 10+4*c
        else:                                        # flight: parabola from 0 up to HOP and back
            p = (f-CONTACT_FRAMES)/AIR_FRAMES
            up = 4*HOP*p*(1-p)
            knee = 18
            lean = 10
        swing = math.sin(2*math.pi*u)
        k.append((f+1, {'hips:up': up, 'spine:fwd': lean*.5, 'chest:fwd': lean*.5, 'head:fwd': -lean*.6,
                        'thigh__L:fwd': 22+8*swing+knee*.5, 'shin__L:fwd': -(knee+10), 'foot__L:fwd': 8,
                        'thigh__R:fwd': -6-6*swing+knee*.6, 'shin__R:fwd': -(knee+20), 'foot__R:fwd': 12,
                        'upper_arm__L:fwd': -10*swing+8, 'upper_arm__R:fwd': 10*swing+8,
                        'upper_arm__L:out': 14, 'upper_arm__R:out': 14, 'forearm__L:fwd': 30, 'forearm__R:fwd': 30}))
    acts.append(make_action(arm, P, 'lunar_lope', k))

    # walk_slow: careful suited walk, 32-frame cycle
    k = []
    for f in range(0, 33, 2):
        ph = 2*math.pi*f/32
        s = math.sin(ph)
        k.append((f+1, {'hips:up': .025*abs(math.cos(ph)), 'chest:yaw': 3*s, 'spine:fwd': 4,
                        'thigh__L:fwd': 18*s, 'thigh__R:fwd': -18*s,
                        'shin__L:fwd': -max(0, -s)*30-6, 'shin__R:fwd': -max(0, s)*30-6,
                        'foot__L:fwd': 4*s, 'foot__R:fwd': -4*s,
                        'upper_arm__L:fwd': -12*s, 'upper_arm__R:fwd': 12*s,
                        'upper_arm__L:out': 10, 'upper_arm__R:out': 10, 'forearm__L:fwd': 18, 'forearm__R:fwd': 18}))
    acts.append(make_action(arm, P, 'walk_slow', k))

    # turn_in_place: two small stepping lifts with torso twist, 24 frames (Godot rotates the body)
    k = []
    for f in range(0, 25, 2):
        ph = 2*math.pi*f/24
        s, lift_l, lift_r = math.sin(ph), max(0, math.sin(ph)), max(0, -math.sin(ph))
        k.append((f+1, {**rest_arms(10), 'spine:yaw': 6*s, 'chest:yaw': 6*s, 'head:yaw': 8*s,
                        'thigh__L:fwd': 20*lift_l, 'shin__L:fwd': -35*lift_l,
                        'thigh__R:fwd': 20*lift_r, 'shin__R:fwd': -35*lift_r, 'hips:up': -.01*abs(s)}))
    acts.append(make_action(arm, P, 'turn_in_place', k))

    # scan_raise: right arm raises the scanner to eye line, 16 frames, holds
    k = []
    for f in range(0, 17, 2):
        u = f/16
        e = u*u*(3-2*u)
        k.append((f+1, {'upper_arm__L:out': 9, 'forearm__L:fwd': 12,
                        'upper_arm__R:fwd': 78*e, 'upper_arm__R:out': 8-6*e, 'forearm__R:fwd': 12+14*e,
                        'hand__R:fwd': -6*e, 'head:fwd': 6*e, 'chest:yaw': -6*e}))
    acts.append(make_action(arm, P, 'scan_raise', k, loop=False))

    # scan_sweep: scanner held up, torso and head sweep left-right, 48-frame loop
    k = []
    for f in range(0, 49, 3):
        s = math.sin(2*math.pi*f/48)
        k.append((f+1, {'upper_arm__L:out': 9, 'forearm__L:fwd': 12,
                        'upper_arm__R:fwd': 78, 'upper_arm__R:out': 2, 'forearm__R:fwd': 26, 'hand__R:fwd': -6,
                        'spine:yaw': 12*s, 'chest:yaw': 14*s-6, 'head:yaw': 10*s, 'head:fwd': 6}))
    acts.append(make_action(arm, P, 'scan_sweep', k))

    # kneel_sample: drop to the right knee and reach to the ground, 48 frames, holds
    k = []
    for f in range(0, 49, 3):
        u = min(1, f/32)
        e = u*u*(3-2*u)
        k.append((f+1, {'hips:up': -.42*e, 'spine:fwd': 22*e, 'chest:fwd': 10*e, 'head:fwd': 10*e,
                        'thigh__L:fwd': 75*e, 'shin__L:fwd': -95*e, 'foot__L:fwd': 20*e,
                        'thigh__R:fwd': 5*e, 'shin__R:fwd': -100*e, 'foot__R:fwd': -10*e,
                        'upper_arm__R:fwd': 45*e, 'forearm__R:fwd': 20*e, 'upper_arm__R:out': 6,
                        'upper_arm__L:fwd': 30*e, 'upper_arm__L:out': 10, 'forearm__L:fwd': 50*e}))
    acts.append(make_action(arm, P, 'kneel_sample', k, loop=False))
    arm.animation_data.action = None
    P.reset()
    return acts


def main():
    C.new_scene()
    arm = build_armature()
    import astronaut_body_v3
    importlib.reload(astronaut_body_v3)
    body = astronaut_body_v3.build_body(BONES)     # built to the team's turnaround sheet (see that module)
    mod = body.modifiers.new('Armature', 'ARMATURE')
    mod.object = arm
    body.parent = arm
    import scanner_v2
    importlib.reload(scanner_v2)
    scanner = scanner_v2.build_scanner()     # references in scanner_v2's docstring
    # preview copy of the scanner on the socket (export as its own glb)
    scanner.parent = arm
    scanner.parent_type = 'BONE'
    scanner.parent_bone = 'scanner_socket'
    sock = arm.pose.bones['scanner_socket'].bone
    # socket frame: Y = forward, Z = up; the scanner points -Y with +Z up, so turn it 180° about Z
    scanner.matrix_world = arm.matrix_world @ sock.matrix_local @ Matrix.Rotation(math.radians(180), 4, 'Z')
    acts = build_actions(arm)
    tris = {'astronaut': C.triangles([body]), 'scanner': C.triangles([scanner])}

    # exports
    C.export_glb('astronaut', [arm, body, scanner], animations=True)   # scanner rides on scanner_socket
    sp, sm = scanner.parent, scanner.matrix_world.copy()
    scanner.parent = None
    scanner.matrix_world = Matrix.Identity(4)
    C.export_glb('scanner', [scanner], animations=False)
    scanner.parent = sp
    scanner.parent_type = 'BONE'
    scanner.parent_bone = 'scanner_socket'
    scanner.matrix_world = sm
    C.save_blend('astronaut')
    return {'triangles': tris, 'actions': [a.name for a in acts],
            'lope_frames': LOPE, 'air_frames': AIR_FRAMES,
            'glb': [str(C.MODELS/'astronaut.glb'), str(C.MODELS/'scanner.glb')]}


result = main()
