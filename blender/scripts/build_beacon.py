"""Sunline survey beacon v2: a lunar survey marker built like a geodetic tripod station with a cyan lamp.

References viewed before modelling (Wikimedia Commons):
- "Round prism and laser plummet on tripod.jpg": top-down stack: round prism in a yoke holder with a target plate,
  instrument body, tribrach with three levelling knobs, triangular tripod head with clamp blocks.
- "GNSS receiver at dusk among eucalyptus trees.jpg": full tripod: legs ~1.5 m, splayed ~22° from vertical, each a
  twin-rail upper section over a single telescoping lower section with clamp bands, pointed metal shoes with foot
  pegs, head at ~1.4 m with a dome receiver on top.
Sunline version: white legs with orange clamp bands (suit palette), a 360° ring of retro-prisms under the lamp
(laser ranging target), and a clear dome lamp with a cyan core and a rotating internal reflector.

Bones: root > head (tripod head and everything above; lowers as the legs open) > lamp (reflector spin);
root > leg.0/1/2 (hinged at the head). Animations (24 fps): deploy (36 f, legs open from closed to 22°, not
looping), pulse_idle (48 f loop, reflector turns once; Godot pulses the light). Faces Blender -Y.
Outputs: blender/beacon.blend, assets/models/beacon.glb.
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

LEG_L = 1.50
SPLAY = 22.0
HEAD_Z = LEG_L*math.cos(math.radians(SPLAY))+0.02     # ≈ 1.41 m, head plate when deployed
X, Z = (1, 0, 0), (0, 0, 1)
LEG_AZ = [90, 210, 330]                               # one leg straight ahead (-Y is front; see foot())


def foot(az, splay=SPLAY):
    a = math.radians(az)
    r = LEG_L*math.sin(math.radians(splay))
    return Vector((r*math.cos(a), -r*math.sin(a), 0.0))


BONES = {'root': ((0, 0, 0), (0, 0, .2), None, False),
         'head': ((0, 0, HEAD_Z), (0, 0, HEAD_Z+.15), 'root', True),
         'lamp': ((0, 0, HEAD_Z+.36), (0, 0, HEAD_Z+.46), 'head', True)}
for i, az in enumerate(LEG_AZ):
    f = foot(az)
    top = Vector((f.x*0.06, f.y*0.06, HEAD_Z-0.01))
    BONES[f'leg.{i}'] = (tuple(top), tuple(top.lerp(f, 0.3)), 'root', True)


def main():
    C.new_scene()
    arm = C.build_rig('BeaconRig', BONES)
    white, orange, dark = C.mat('suit_white', roughness=.5), C.mat('suit_orange', roughness=.7), C.mat('suit_dark', roughness=.5)
    metal = C.mat('metal', metallic=.85, roughness=.3)
    prism = C.material('retro_prism', (0.85, 0.55, 0.25, 1), metallic=.9, roughness=.08)
    dome = C.transparent('lamp_dome', (0.75, 0.95, 1.0, 1), alpha=0.25, roughness=.03)
    core = C.mat('scanner_cyan', emission=C.PALETTE['scanner_cyan'], strength=3.0)
    P = []
    # legs: twin-rail upper section, single lower section, clamp bands, shoe with spike and foot peg
    for i, az in enumerate(LEG_AZ):
        b = f'leg.{i}'
        f = foot(az)
        top = Vector((f.x*0.06, f.y*0.06, HEAD_Z-0.01))
        d = (f-top).normalized()
        side = d.cross(Vector((0, 0, 1))).normalized()
        knee = top+d*0.85
        for s in (-1, 1):
            P.append((C.strut(f'rail{i}{s}', top+side*0.018*s, knee+side*0.018*s, 0.011, segments=6, material_=white), b))
        P.append((C.rbox(f'hinge_block{i}', (0.06, 0.05, 0.05), top, radius=0.008, material_=orange), b))
        P.append((C.rbox(f'clamp{i}', (0.065, 0.045, 0.06), knee, radius=0.008, material_=orange), b))
        P.append((C.strut(f'lower{i}', knee-d*0.05, f+Vector((0, 0, 0.05)), 0.012, segments=6, material_=metal), b))
        P.append((C.rbox(f'shoe{i}', (0.04, 0.04, 0.07), f+Vector((0, 0, 0.07)), radius=0.008, material_=dark), b))
        P.append((C.cylinder(f'spike{i}', 0.012, 0.06, f+Vector((0, 0, 0.03)), segments=6, material_=metal, radius_top=0.012), b))
        P.append((C.strut(f'peg{i}', f+Vector((0, 0, 0.08)), f+Vector((0, 0, 0.08))+d.cross(side)*0.0+Vector((d.x, d.y, 0)).normalized()*0.06, 0.008, segments=5, material_=metal), b))
    # head: triangular plate, tribrach with three levelling knobs, instrument column, prism ring, lamp
    h = Vector((0, 0, HEAD_Z))
    plate = C.cylinder('head_plate', 0.10, 0.03, h+Vector((0, 0, 0.0)), segments=3, material_=metal)
    plate.rotation_euler = (0, 0, math.radians(90))
    P.append((plate, 'head'))
    P.append((C.cylinder('tribrach', 0.075, 0.035, h+Vector((0, 0, 0.035)), segments=18, material_=dark), 'head'))
    for k in range(3):
        a = math.radians(30+120*k)
        P.append((C.cylinder(f'knob{k}', 0.018, 0.025, h+Vector((0.07*math.cos(a), 0.07*math.sin(a), 0.035)), segments=10, material_=dark), 'head'))
    P.append((C.cylinder('column', 0.045, 0.22, h+Vector((0, 0, 0.16)), segments=16, material_=white), 'head'))
    P.append((C.torus('column_band', 0.046, 0.008, h+Vector((0, 0, 0.10)), segments=16, tube=5, material_=orange), 'head'))
    P.append((C.cylinder('prism_ring', 0.07, 0.06, h+Vector((0, 0, 0.30)), segments=8, material_=prism), 'head'))
    for k in range(8):                                 # dark frames between the 8 retro-prism facets
        a = 2*math.pi*(k+0.5)/8
        P.append((C.box(f'prism_frame{k}', (0.008, 0.008, 0.064), h+Vector((0.068*math.cos(a), 0.068*math.sin(a), 0.30)), material_=dark), 'head'))
    P.append((C.cylinder('lamp_base', 0.06, 0.025, h+Vector((0, 0, 0.345)), segments=16, material_=white), 'head'))
    P.append((C.sphere('lamp_dome', 0.065, h+Vector((0, 0, 0.395)), segments=18, rings=10, material_=dome, scale=(1, 1, 1.15)), 'head'))
    P.append((C.cylinder('lamp_core', 0.022, 0.08, h+Vector((0, 0, 0.395)), segments=10, material_=core), 'lamp'))
    P.append((C.rbox('reflector', (0.09, 0.008, 0.07), h+Vector((0, 0.03, 0.395)), radius=0.003, material_=metal), 'lamp'))
    P.append((C.cylinder('lamp_cap', 0.035, 0.02, h+Vector((0, 0, 0.475)), segments=14, material_=white), 'head'))
    P.append((C.cylinder('antenna', 0.004, 0.18, h+Vector((0.035, 0.0, 0.57)), segments=6, material_=dark), 'head'))
    body = C.skin(P, 'Beacon', arm)

    # deploy: legs open from closed (3°) to SPLAY while the head settles to HEAD_Z (feet stay on the ground)
    C.new_action(arm, 'deploy', (1, 36), loop=False)
    for f, splay in ((1, 3), (12, 12), (22, 20), (28, 23), (32, 21.5), (36, SPLAY)):
        z_closed = LEG_L*math.cos(math.radians(splay))+0.02
        rots, moves = {}, {'head': (0, 0, z_closed-HEAD_Z)}
        for i, az in enumerate(LEG_AZ):
            a = math.radians(az)
            outward = Vector((math.cos(a), -math.sin(a), 0))
            axis = Vector((0, 0, 1)).cross(outward)       # rotating about this swings the foot outward
            rots[f'leg.{i}'] = (tuple(axis), SPLAY-splay)     # positive about Z x outward swings the foot inward
            moves[f'leg.{i}'] = (0, 0, z_closed-HEAD_Z)
        C.key_pose(arm, f, rots, moves)
    C.new_action(arm, 'pulse_idle', (1, 49))
    for i, f in enumerate((1, 13, 25, 37, 49)):
        C.key_pose(arm, f, {'lamp': (Z, 90*i)})
    C.rest(arm)
    C.export_glb('beacon', [arm, body], animations=True)
    C.save_blend('beacon')
    return {'triangles': C.triangles([body]), 'head_z': round(HEAD_Z, 3), 'actions': [a.name for a in bpy.data.actions]}


result = main()
