"""Re-author the astronaut's locomotion cycles (walk_slow, lunar_lope) for the rigged team astronaut.

Feet first: each foot follows a planted path (on the ground, sliding backwards at exactly the cycle's ground speed
while in stance; an arc forward while in swing/flight), and the legs are solved to it with two-bone IK. So planted
feet never skate when the game plays the cycle at  speed / NATIVE_SPEED  (see scenes/mission/astronaut.gd).

  walk_slow   0.9 m/s, 1.10 s cycle, 60 % stance: heel strike -> flat -> toe-off, hip bob, pelvis/shoulder
              counter-twist, arm swing (right arm steadier: it holds the scanner).
  lunar_lope  2.3 m/s, 0.95 s cycle: Apollo-style bounding skip. Trailing foot then leading foot touch down, the body
              compresses and springs off, then floats ~0.7 s on a ballistic arc (lunar g = 1.62 m/s²), arms out for
              balance, torso leaned forward.

Runs headless:  blender -b --python blender/scripts/animate_astronaut_locomotion.py
Reads/writes blender/astronaut_team.blend; exports assets/models/astronaut_team.glb; previews in assets/previews/.
Frame axes (Blender): -Y forward, +Z up, +X = character's left.
"""
import math
import sys
from pathlib import Path
import bpy
from mathutils import Matrix, Quaternion, Vector

sys.path.insert(0, str(Path(r'C:\dev\godot\new-game-project\blender\scripts')))
import importlib
import sunline_common as C
importlib.reload(C)

FPS = 24
G = 1.62
ANKLE_Z = 0.11			# ankle (foot bone head) height when the foot is flat on the ground

WALK = dict(name='walk_slow', T=1.10, v=0.90, stance=0.60, lift=0.10, hip=0.91, bob=0.015)
LOPE = dict(name='lunar_lope', T=0.95, v=2.30, lift=0.07, crouch=0.05, base=0.86)


def T(v):
    return Matrix.Translation(v)


def about(h, R):
    return T(h) @ R @ T(-h)


def rx(d):
    return Matrix.Rotation(math.radians(d), 4, 'X')


def ry(d):
    return Matrix.Rotation(math.radians(d), 4, 'Y')


def rz(d):
    return Matrix.Rotation(math.radians(d), 4, 'Z')


def smooth(s):
    s = min(1.0, max(0.0, s))
    return s * s * (3 - 2 * s)


class Rig:
    def __init__(self, arm):
        self.arm = arm
        self.rest = {b.name: b.matrix_local.copy() for b in arm.data.bones}
        self.head = {b.name: b.head_local.copy() for b in arm.data.bones}
        self.tail = {b.name: b.tail_local.copy() for b in arm.data.bones}
        self.parent = {b.name: (b.parent.name if b.parent else None) for b in arm.data.bones}
        self.order = [b.name for b in arm.data.bones]		# parents before children
        self.L1 = (self.tail['thigh.L'] - self.head['thigh.L']).length
        self.L2 = (self.tail['shin.L'] - self.head['shin.L']).length
        self.prev_q = {}

    def dir(self, n):
        return (self.tail[n] - self.head[n]).normalized()

    def solve(self, body, ankles, foot_pitch):
        """body: {bone: rest-space rotation about its head} for the upper body/hips (+ 'hips_move' offset);
        ankles: {'L'/'R': world ankle target}; foot_pitch: {'L'/'R': degrees}. Returns deform matrices D."""
        D = {}
        for n in self.order:
            p = self.parent[n]
            Dp = D[p] if p else Matrix.Identity(4)
            h = self.head[n]
            if n == 'hips':
                D[n] = T(body.get('hips_move', Vector())) @ about(h, body.get('hips', Matrix.Identity(4)))
            elif n.startswith('thigh.') or n.startswith('shin.'):
                side = n[-1]
                Hj = Dp @ self.head[f'thigh.{side}'] if n.startswith('thigh.') else None
                if n.startswith('thigh.'):
                    K = self._knee(Hj, ankles[side])
                    D[n] = Dp @ about(h, self._aim(Dp, n, K - Hj))
                    self._knee_pos = getattr(self, '_knee_pos', {})
                    self._knee_pos[side] = K
                else:
                    K = self._knee_pos[side]
                    D[n] = Dp @ about(h, self._aim(Dp, n, ankles[side] - K))
            elif n.startswith('foot.'):
                side = n[-1]
                want = rx(foot_pitch[side]).to_3x3()		# world orientation of the foot (flat = rest)
                Q = (Dp.to_3x3().inverted() @ want).to_4x4()
                D[n] = Dp @ about(h, Q)
            elif n in body:
                D[n] = Dp @ about(h, body[n])
            else:
                D[n] = Dp
        return D

    def _aim(self, Dp, n, world_dir):
        local = (Dp.to_3x3().inverted() @ world_dir).normalized()
        return self.dir(n).rotation_difference(local).to_matrix().to_4x4()

    def _knee(self, H, A):
        """Two-bone IK in the leg's plane; the knee bends forward (-Y)."""
        d = A - H
        dist = min(d.length, self.L1 + self.L2 - 1e-4)
        u = d.normalized()
        fwd = Vector((0, -1, 0))
        f = (fwd - u * fwd.dot(u))
        f = f.normalized() if f.length > 1e-6 else fwd
        a = (self.L1 ** 2 - self.L2 ** 2 + dist ** 2) / (2 * dist)
        b = math.sqrt(max(0.0, self.L1 ** 2 - a * a))
        return H + u * a + f * b

    def key(self, D, frame):
        for pb in self.arm.pose.bones:
            n = pb.name
            p = self.parent[n]
            Dp = D[p] if p else Matrix.Identity(4)
            basis = self.rest[n].inverted() @ Dp.inverted() @ D[n] @ self.rest[n]
            loc, q, _ = basis.decompose()
            prev = self.prev_q.get(n)
            if prev is not None and prev.dot(q) < 0:		# keep quaternions on one hemisphere: no flips
                q = -q
            self.prev_q[n] = q
            pb.rotation_quaternion = q
            pb.location = loc
            pb.keyframe_insert('rotation_quaternion', frame=frame)
            pb.keyframe_insert('location', frame=frame)


def foot_track(p, a, b, y0, y1, lift, ground_z, air_z):
    """Foot path over one cycle: stance on [a, b) moving y0 -> y1 on the ground; otherwise an arc back to y0.
    air_z: ankle height while airborne (follows the body in the lope)."""
    p %= 1.0
    if (a <= p < b) if a < b else (p >= a or p < b):
        s = ((p - a) % 1.0) / ((b - a) % 1.0 or 1.0)
        return Vector((0, y0 + (y1 - y0) * s, ground_z)), s, True
    span = 1.0 - ((b - a) % 1.0)
    s = ((p - b) % 1.0) / span
    y = y1 + (y0 - y1) * smooth(s)
    z = max(ground_z + lift * math.sin(math.pi * s), air_z + lift * math.sin(math.pi * s))
    return Vector((0, y, z)), s, False


def walk(rig, P):
    n = round(P['T'] * FPS)
    half = P['v'] * P['stance'] * P['T'] / 2				# stance runs from -half (front) to +half (back)
    for i in range(n + 1):
        p = i / n
        bob = P['bob'] * math.cos(4 * math.pi * (p - 0.30))		# highest at each mid-stance
        hip_z = P['hip'] + bob
        sway = 0.012 * math.sin(2 * math.pi * (p - 0.30))			# weight shifts over the stance leg
        twist = 6 * math.sin(2 * math.pi * p)						# pelvis follows the forward leg
        ankles, pitch = {}, {}
        for side, ph in (('L', 0.0), ('R', 0.5)):
            pos, s, stance = foot_track(p - ph, 0.0, P['stance'], -half, half, P['lift'], ANKLE_Z, 0.0)
            x = rig.head[f'foot.{side}'].x
            ankles[side] = Vector((x, pos.y, pos.z))
            if stance:	# heel strike (toe up) -> flat -> toe-off (heel up)
                pitch[side] = -12 * max(0.0, 1 - s / 0.15) + 22 * max(0.0, (s - 0.75) / 0.25)
            else:
                pitch[side] = 22 * max(0.0, 1 - s / 0.2) - 10 * math.sin(math.pi * s)
        swing = math.sin(2 * math.pi * p)
        body = {
            'hips_move': Vector((sway, 0, hip_z - rig.head['thigh.L'].z)),
            'hips': rz(-twist),
            'spine': rz(twist * 0.5) @ rx(4),
            'chest': rz(twist * 0.6) @ rx(2),
            'neck': rx(-3),
            'head': rz(-twist * 0.3) @ rx(-2),
            'upper_arm.L': ry(-10) @ rx(-18 * swing),			# opposite the left leg
            'forearm.L': rx(-18 - 8 * max(0, -swing)),
            'upper_arm.R': ry(10) @ rx(10 * swing - 8),			# holds the scanner: smaller swing, a bit forward
            'forearm.R': rx(-38),
        }
        rig.key(rig.solve(body, ankles, pitch), 1 + i)
    return n


def lope(rig, P):
    n = round(P['T'] * FPS)
    Tt = P['T']
    trail, lead = (0.00, 0.17), (0.07, 0.25)		# stance windows (phase): trailing (R) then leading (L) foot
    flight0 = lead[1]
    t_flight = (1 - flight0) * Tt
    v0 = G * t_flight / 2
    apex = v0 * v0 / (2 * G)							# ballistic rise in lunar gravity
    for i in range(n + 1):
        p = i / n
        if p < flight0:			# contact: compress and spring
            s = p / flight0
            hip_z = P['base'] - P['crouch'] * math.sin(math.pi * s)
        else:					# flight: ballistic arc
            s = (p - flight0) / (1 - flight0)
            hip_z = P['base'] + 4 * apex * s * (1 - s)
        air_z = hip_z - (rig.L1 + rig.L2) * 0.88 + 0.0
        ankles, pitch = {}, {}
        for side, (a, b), y0 in (('R', trail, 0.06), ('L', lead, -0.30)):
            y1 = y0 + P['v'] * Tt * (b - a)
            pos, s2, stance = foot_track(p, a, b, y0, y1, P['lift'], ANKLE_Z, air_z)
            x = rig.head[f'foot.{side}'].x
            ankles[side] = Vector((x, pos.y, pos.z))
            pitch[side] = (-10 * max(0.0, 1 - s2 / 0.3) + 25 * max(0.0, (s2 - 0.6) / 0.4)) if stance \
                else (20 * max(0.0, 1 - s2 / 0.25) - 12 * math.sin(math.pi * s2))
        push = math.sin(math.pi * min(1.0, p / flight0))		# 0..1 during contact
        body = {
            'hips_move': Vector((0, 0, hip_z - rig.head['thigh.L'].z)),
            'hips': rx(6 + 4 * push),
            'spine': rx(6),
            'chest': rx(4 - 3 * push),
            'neck': rx(-5),
            'head': rx(-7),
            'upper_arm.L': ry(-24) @ rx(-20 - 10 * push),		# arms out and forward for balance
            'forearm.L': rx(-35),
            'upper_arm.R': ry(18) @ rx(-22 - 6 * push),
            'forearm.R': rx(-45),
        }
        rig.key(rig.solve(body, ankles, pitch), 1 + i)
    return n


def main():
    bpy.ops.wm.open_mainfile(filepath=str(C.BLEND_DIR / 'astronaut_team.blend'))
    arm = bpy.data.objects['AstronautRig']
    keep = arm.animation_data.action if arm.animation_data else None
    muted = []
    for pb in arm.pose.bones:
        pb.rotation_mode = 'QUATERNION'
        for c in pb.constraints:
            if not c.mute:
                c.mute = True
                muted.append(c)
    rig = Rig(arm)
    info = {}
    for P, fn in ((WALK, walk), (LOPE, lope)):
        old = bpy.data.actions.get(P['name'])
        if old:
            bpy.data.actions.remove(old)
        n = round(P['T'] * FPS)
        act = C.new_action(arm, P['name'], (1, 1 + n))
        rig.prev_q.clear()
        fn(rig, P)
        for fc in getattr(act, 'fcurves', []):
            for kp in fc.keyframe_points:
                kp.interpolation = 'LINEAR'
        info[P['name']] = dict(frames=n, seconds=P['T'], native_speed=P['v'])
    if keep and keep.name in bpy.data.actions:
        arm.animation_data.action = bpy.data.actions[keep.name]
    else:
        arm.animation_data.action = bpy.data.actions.get('idle')
    for c in muted:
        c.mute = False

    # contact sheets: 6 frames per cycle, side view
    for name in ('walk_slow', 'lunar_lope'):
        arm.animation_data.action = bpy.data.actions[name]
        f0, f1 = (int(v) for v in bpy.data.actions[name].frame_range)
        for k in range(6):
            f = f0 + round(k * (f1 - f0) / 6)
            C.preview('astrolocomotion', target=(0, 0, 0.95), distance=3.8, elevation_deg=6, azimuth_deg=-90,
                      size=(360, 420), frame=f, suffix=f'_{name}_{k}')
    arm.animation_data.action = bpy.data.actions.get('idle')
    for name in ('_PreviewCam', '_PreviewSun', '_PreviewFloor', '_PreviewBackdrop'):
        if name in bpy.data.objects:
            bpy.data.objects.remove(bpy.data.objects[name], do_unlink=True)

    objs = [o for o in bpy.data.objects if o.name in ('AstronautRig', 'Astronaut', 'Scanner')]
    for o in bpy.context.view_layer.objects:
        o.select_set(o in objs)
    for pb in arm.pose.bones:
        for c in pb.constraints:
            c.mute = True
    C._gltf(C.MODELS / 'astronaut_team.glb', True, True)
    for c in muted:
        c.mute = False
    bpy.ops.wm.save_as_mainfile(filepath=str(C.BLEND_DIR / 'astronaut_team.blend'), compress=True)
    print('LOCOMOTION', info)


main()
