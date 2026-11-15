"""Sunline rover v2: a VIPER-inspired polar sampling rover with its solar panels centred at the 1.0 m panel height.

References viewed before modelling:
- Wikimedia Commons "VIPER lunar rover.jpg" (NASA illustration): boxy body ~1.5 m wide wrapped in crinkled silver
  MLI, VERTICAL solar panels on the sides (the polar Sun is always low), four large wheels with open rims on a
  gold-toned lower chassis, tall mast with cameras and headlights, drill under the body.
- NASA jsc2024e013783 (mast installation): pan/tilt camera head with paired stereo cameras each side and lamp units,
  white-wrapped mast column.
- Commons "Volatiles Investigating Polar Exploration Rover (Viper) (GRC-2021-C-00710)" (mobility platform): wheels
  ~0.5 m diameter x ~0.25 m wide with chevron grouser paddles and a coloured hub, each wheel on its own swing arm
  with a steering drive.
Sunline choices: smaller than VIPER (1.2 m body), panels on left/right/back centred at exactly PANEL_HEIGHT_M = 1.0 m
(the observer height of the scoring skyline, tools/data/sunline_data/constants.py), a TRIDENT-style drill on a
vertical carriage at the front (VIPER samples with a drill, not a scoop).

Bones (rigid skinning): root > chassis > susp.{FL,FR,RL,RR} > steer.* > wheel.*; chassis > mast > mast_head;
chassis > drill_carriage > drill_bit; chassis > panel (static marker of the panel centre, never animated).
Animations (24 fps, no root motion): drive_loop (24 f = one wheel turn = 1.57 m), steer_turn (24 f, wheels turned
for a turn in place), sample_drill_cycle (96 f), mast_look (48 f). Faces Blender -Y (Godot +Z).
Outputs: blender/rover.blend, assets/models/rover.glb.
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

PANEL_HEIGHT_M = 1.0
BODY = dict(w=1.10, l=1.20, z0=0.58, z1=1.46)          # body box: width (x), length (y), bottom, top
WHEEL_R, WHEEL_W = 0.25, 0.22
WX, WY = 0.74, 0.60                                     # wheel centres at (±WX, ±WY, WHEEL_R)
MAST = Vector((0.0, -0.40, BODY['z1']))
X, Y, Z = (1, 0, 0), (0, 1, 0), (0, 0, 1)
CORNERS = {'FL': (1, -1), 'FR': (-1, -1), 'RL': (1, 1), 'RR': (-1, 1)}

BONES = {
    'root': ((0, 0, 0), (0, 0, .3), None, False),
    'chassis': ((0, 0, .5), (0, 0, .8), 'root', True),
    'panel': ((0, 0, PANEL_HEIGHT_M), (0, 0, PANEL_HEIGHT_M+.1), 'chassis', True),
    'mast': (tuple(MAST), tuple(MAST+Vector((0, 0, .62))), 'chassis', True),
    'mast_head': (tuple(MAST+Vector((0, 0, .66))), tuple(MAST+Vector((0, -.15, .66))), 'mast', True),
    'drill_carriage': ((0, -.66, .95), (0, -.66, 1.20), 'chassis', True),
    'drill_bit': ((0, -.66, .70), (0, -.66, .40), 'drill_carriage', True),
}
for k, (sx, sy) in CORNERS.items():
    BONES[f'susp.{k}'] = ((sx*.50, sy*.42, .52), (sx*.62, sy*.52, .40), 'chassis', True)
    BONES[f'steer.{k}'] = ((sx*WX, sy*WY, .50), (sx*WX, sy*WY, .30), f'susp.{k}', True)
    BONES[f'wheel.{k}'] = ((sx*WX, sy*WY, WHEEL_R), (sx*WX+.1, sy*WY, WHEEL_R), f'steer.{k}', True)


def materials():
    return dict(
        mli=C.texture_material('mli_silver', (0.80, 0.81, 0.82, 1), normal='mli_crinkle_normal.png', roughness=0.42,
                               normal_strength=0.7, metallic=0.55),
        seam=C.material('mli_seam', (0.35, 0.36, 0.38, 1), metallic=0.6, roughness=0.5),
        gold=C.mat('kapton', metallic=.7, roughness=.32),
        white=C.mat('suit_white', roughness=.55),
        dark=C.mat('suit_dark', roughness=.5),
        metal=C.mat('metal', metallic=.85, roughness=.3),
        rim=C.material('wheel_rim', (0.70, 0.71, 0.72, 1), metallic=.8, roughness=.35),
        hub=C.material('hub_gold', (0.85, 0.66, 0.20, 1), metallic=.6, roughness=.35),
        cells=C.mat('panel_blue', metallic=.3, roughness=.18),
        grid=C.material('cell_grid', (0.55, 0.58, 0.62, 1), metallic=.8, roughness=.3),
        lamp=C.material('lamp_white', (1, 1, 1, 1), emission=(1, .98, .92, 1), strength=5.0),
        cyan=C.mat('scanner_cyan', emission=C.PALETTE['scanner_cyan'], strength=3.0),
        glass=C.material('lens_glass', (0.03, 0.04, 0.05, 1), metallic=.3, roughness=.05),
    )


def solar_panel(name, centre, normal_axis, sign, M, width, height, parts):
    """Vertical panel on a body face: frame, cells, and a grid of thin bus bars."""
    cx, cy, cz = centre
    if normal_axis == 'x':
        frame = C.rbox(f'{name}_frame', (0.025, width, height), (cx, cy, cz), radius=0.006, material_=M['metal'])
        cells = C.rbox(f'{name}_cells', (0.006, width-0.04, height-0.04), (cx+sign*0.014, cy, cz), radius=0.002, material_=M['cells'])
        bars = [C.box(f'{name}_bar{k}', (0.004, width-0.04, 0.006), (cx+sign*0.018, cy, cz-height/2+0.02+k*(height-0.04)/6), material_=M['grid']) for k in range(1, 6)]
        bars += [C.box(f'{name}_col{k}', (0.004, 0.006, height-0.04), (cx+sign*0.018, cy-width/2+0.02+k*(width-0.04)/8, cz), material_=M['grid']) for k in range(1, 8)]
    else:
        frame = C.rbox(f'{name}_frame', (width, 0.025, height), (cx, cy, cz), radius=0.006, material_=M['metal'])
        cells = C.rbox(f'{name}_cells', (width-0.04, 0.006, height-0.04), (cx, cy+sign*0.014, cz), radius=0.002, material_=M['cells'])
        bars = [C.box(f'{name}_bar{k}', (width-0.04, 0.004, 0.006), (cx, cy+sign*0.018, cz-height/2+0.02+k*(height-0.04)/6), material_=M['grid']) for k in range(1, 6)]
        bars += [C.box(f'{name}_col{k}', (0.006, 0.004, height-0.04), (cx-width/2+0.02+k*(width-0.04)/8, cy+sign*0.018, cz), material_=M['grid']) for k in range(1, 8)]
    for o in [frame, cells]+bars:
        parts.append((o, 'chassis'))


def wheel(k, sx, sy, M, parts):
    c = Vector((sx*WX, sy*WY, WHEEL_R))
    wb = f'wheel.{k}'
    # double rim hoops, spokes, hub, 16 chevron grouser paddles
    for side in (-1, 1):
        parts.append((C.torus(f'rim{side}.{k}', WHEEL_R-0.012, 0.010, c+Vector((side*WHEEL_W/2*0.92, 0, 0)), normal=X, segments=24, tube=4, material_=M['rim']), wb))
    parts.append((C.cylinder(f'drum.{k}', WHEEL_R-0.03, WHEEL_W*0.85, c, (0, math.radians(90), 0), segments=24, material_=M['dark'], cap=False), wb))
    parts.append((C.cylinder(f'hub.{k}', 0.07, WHEEL_W*1.02, c, (0, math.radians(90), 0), segments=14, material_=M['hub']), wb))
    for s in range(6):
        a = 2*math.pi*s/6
        for side in (-1, 1):
            p = c+Vector((side*WHEEL_W*0.44, 0, 0))
            q = p+Vector((0, (WHEEL_R-0.03)*math.sin(a), (WHEEL_R-0.03)*math.cos(a)))
            parts.append((C.strut(f'spoke{s}{side}.{k}', p, q, 0.009, segments=5, material_=M['rim']), wb))
    for g in range(16):
        a = 2*math.pi*g/16
        r = WHEEL_R-0.008
        for half in (-1, 1):                        # chevron: two angled blades meeting at the tread centre
            p0 = c+Vector((0, r*math.sin(a), r*math.cos(a)))
            p1 = c+Vector((half*WHEEL_W*0.46, r*math.sin(a+0.12), r*math.cos(a+0.12)))
            parts.append((C.strut(f'grouser{g}{half}.{k}', p0, p1, 0.007, segments=4, material_=M['rim']), wb))
    # steering drive housing above the wheel, and the swing arm to the chassis
    parts.append((C.cylinder(f'steer_motor.{k}', 0.06, 0.12, c+Vector((0, 0, WHEEL_R+0.09)), segments=12, material_=M['gold']), f'steer.{k}'))
    parts.append((C.strut(f'fork.{k}', c+Vector((-sx*0.02, 0, WHEEL_R+0.05)), c+Vector((-sx*WHEEL_W*0.55, 0, 0.03)), 0.022, segments=8, material_=M['metal']), f'steer.{k}'))
    a0 = Vector((sx*0.50, sy*0.42, 0.52))
    parts.append((C.strut(f'swing_arm.{k}', a0, c+Vector((0, 0, WHEEL_R+0.15)), 0.035, segments=10, material_=M['gold']), f'susp.{k}'))
    parts.append((C.cylinder(f'pivot.{k}', 0.05, 0.08, a0, (0, math.radians(90), 0), segments=12, material_=M['dark']), f'susp.{k}'))


def build_mesh(arm, M):
    P = []
    w, l, z0, z1 = BODY['w'], BODY['l'], BODY['z0'], BODY['z1']
    zc = (z0+z1)/2
    # MLI-wrapped body with blanket seams, top deck, radiator, lower gold frame and truss
    P.append((C.rbox('body', (w, l, z1-z0), (0, 0, zc), radius=0.04, segments=2, material_=M['mli']), 'chassis'))
    for k in range(1, 4):
        z = z0+k*(z1-z0)/4
        P.append((C.box(f'seam_front{k}', (w-0.1, 0.006, 0.01), (0, -l/2-0.002, z), material_=M['seam']), 'chassis'))
    P.append((C.rbox('deck', (w-0.06, l-0.06, 0.03), (0, 0, z1+0.012), radius=0.008, material_=M['white']), 'chassis'))
    P.append((C.rbox('radiator', (w-0.30, l-0.50, 0.012), (0.08, 0.15, z1+0.032), radius=0.004, material_=M['white']), 'chassis'))
    for k in range(6):
        P.append((C.box(f'radiator_fin{k}', (w-0.32, 0.01, 0.01), (0.08, -0.05+k*0.08, z1+0.042), material_=M['seam']), 'chassis'))
    P.append((C.rbox('lower_frame', (w*0.92, l*0.88, 0.10), (0, 0, z0-0.06), radius=0.015, material_=M['gold']), 'chassis'))
    for sx in (1, -1):
        for sy in (1, -1):
            P.append((C.strut(f'truss{sx}{sy}', (sx*0.45, sy*0.48, z0-0.10), (sx*0.30, sy*0.10, z0-0.10), 0.015, segments=6, material_=M['metal']), 'chassis'))
    # vertical solar panels centred at the panel height on left, right and back
    ph = 0.74
    solar_panel('panel_L', (w/2+0.015, 0.0, PANEL_HEIGHT_M), 'x', 1, M, l-0.10, ph, P)
    solar_panel('panel_R', (-w/2-0.015, 0.0, PANEL_HEIGHT_M), 'x', -1, M, l-0.10, ph, P)
    solar_panel('panel_B', (0.0, l/2+0.015, PANEL_HEIGHT_M), 'y', 1, M, w-0.10, ph, P)
    # front face: hazard cameras, headlights, drill rail and housing
    for sx in (1, -1):
        P.append((C.rbox(f'hazcam{sx}', (0.07, 0.05, 0.05), (sx*0.30, -l/2-0.02, z0+0.14), radius=0.008, material_=M['dark']), 'chassis'))
        P.append((C.cylinder(f'hazcam_lens{sx}', 0.016, 0.01, (sx*0.30, -l/2-0.047, z0+0.14), (math.radians(90), 0, 0), segments=10, material_=M['glass']), 'chassis'))
        P.append((C.rbox(f'headlight{sx}', (0.12, 0.03, 0.035), (sx*0.30, -l/2-0.01, z0+0.24), radius=0.006, material_=M['lamp']), 'chassis'))
    for sx in (1, -1):
        P.append((C.rbox(f'drill_rail{sx}', (0.02, 0.03, 0.62), (sx*0.075, -l/2-0.015, 0.92), radius=0.004, material_=M['metal']), 'chassis'))
    P.append((C.rbox('drill_housing', (0.13, 0.10, 0.26), (0, -0.66, 1.07), radius=0.015, material_=M['white']), 'drill_carriage'))
    P.append((C.cylinder('drill_motor', 0.045, 0.08, (0, -0.66, 1.24), segments=12, material_=M['gold']), 'drill_carriage'))
    P.append((C.cylinder('drill_chuck', 0.03, 0.06, (0, -0.66, 0.92), segments=12, material_=M['dark']), 'drill_carriage'))
    P.append((C.cylinder('drill_bit', 0.016, 0.34, (0, -0.66, 0.72), segments=8, material_=M['metal'], radius_top=0.016), 'drill_bit'))
    for k in range(6):                                # auger flutes so the spin reads
        z = 0.58+k*0.05
        P.append((C.box(f'flute{k}', (0.05, 0.008, 0.008), (0, -0.66, z), material_=M['metal'], rotation=(0, 0, math.radians(30*k))), 'drill_bit'))
    # mast: white-wrapped column, pan/tilt head with stereo pairs and lamp bars
    P.append((C.cylinder('mast_column', 0.045, 0.64, MAST+Vector((0, 0, .32)), segments=14, material_=M['white']), 'mast'))
    for k in range(4):
        P.append((C.torus(f'mast_wrap{k}', 0.047, 0.006, MAST+Vector((0, 0, .1+k*.14)), segments=14, tube=4, material_=M['seam']), 'mast'))
    P.append((C.cylinder('mast_base', 0.08, 0.06, MAST+Vector((0, 0, .03)), segments=14, material_=M['gold']), 'mast'))
    H = MAST+Vector((0, 0, .70))
    P.append((C.rbox('head', (0.34, 0.14, 0.12), H, radius=0.02, material_=M['white']), 'mast_head'))
    for sx in (1, -1):
        for dx in (0.03, 0.08):
            x = sx*(0.06+dx)
            P.append((C.cylinder(f'stereo{sx}{dx}', 0.018, 0.03, H+Vector((x-sx*0.03, -0.08, 0.015)), (math.radians(90), 0, 0), segments=12, material_=M['glass']), 'mast_head'))
            P.append((C.torus(f'stereo_ring{sx}{dx}', 0.019, 0.004, H+Vector((x-sx*0.03, -0.095, 0.015)), normal=(0, -1, 0), segments=12, tube=4, material_=M['dark']), 'mast_head'))
        P.append((C.rbox(f'lamp_bar{sx}', (0.12, 0.03, 0.025), H+Vector((sx*0.10, -0.075, -0.045)), radius=0.006, material_=M['lamp']), 'mast_head'))
    P.append((C.cylinder('head_antenna', 0.006, 0.20, H+Vector((0.12, 0.04, 0.16)), segments=6, material_=M['dark']), 'mast_head'))
    P.append((C.sphere('nav_light', 0.015, H+Vector((-0.12, 0.04, 0.075)), segments=8, rings=6, material_=M['cyan']), 'mast_head'))
    for k, (sx, sy) in CORNERS.items():
        wheel(k, sx, sy, M, P)
    return C.skin(P, 'Rover', arm)


def build_actions(arm):
    wheels = [f'wheel.{k}' for k in CORNERS]
    steers = [f'steer.{k}' for k in CORNERS]
    C.new_action(arm, 'drive_loop', (1, 25))                   # positive about +X rolls toward -Y (forward)
    for i, f in enumerate((1, 7, 13, 19, 25)):
        rot = {w: (X, 90*i) for w in wheels}
        rot['susp.FL'] = (Y, 1.5*math.sin(math.pi*i/2))
        rot['susp.RR'] = (Y, -1.5*math.sin(math.pi*i/2))
        C.key_pose(arm, f, rot, {'chassis': (0, 0, .006*math.sin(math.pi*i/2))})
    C.new_action(arm, 'steer_turn', (1, 25))                   # wheels toed for a turn in place, rolling
    for i, f in enumerate((1, 7, 13, 19, 25)):
        rot = {}
        for k, (sx, sy) in CORNERS.items():
            rot[f'steer.{k}'] = (Z, 45*sx*sy)
            rot[f'wheel.{k}'] = (X, 90*i*sx)
        C.key_pose(arm, f, rot)
    C.new_action(arm, 'sample_drill_cycle', (1, 97), loop=False)
    # lower the carriage (0-20), drill 0.18 m into the regolith while spinning (20-60), hold, retract (60-78)
    for f in range(1, 98, 2):
        if f <= 20:
            dz = -0.30*f/20
        elif f <= 60:
            dz = -0.30-0.18*(f-20)/40
        elif f <= 78:
            dz = -0.48*(1-(f-60)/18)
        else:
            dz = 0.0
        spin = (45*(f-20)) % 360 if 20 <= f <= 60 else 0     # 45° per 2 frames: quaternion keys stay unambiguous
        C.key_pose(arm, f, {'drill_bit': (Z, spin)}, {'drill_carriage': (0, 0, dz)})
    C.new_action(arm, 'mast_look', (1, 49))
    for f, yaw, pitch in ((1, 0, 0), (13, 45, -8), (25, 0, 6), (37, -45, -8), (49, 0, 0)):
        C.key_pose(arm, f, {'mast': (Z, yaw), 'mast_head': (X, pitch)})
    C.rest(arm)


def main():
    C.new_scene()
    arm = C.build_rig('RoverRig', BONES)
    M = materials()
    body = build_mesh(arm, M)
    C.box_uv(body, 0.7)                            # crinkled-foil normal map on the MLI body
    build_actions(arm)
    C.export_glb('rover', [arm, body], animations=True)
    C.save_blend('rover')
    zs = [(body.matrix_world @ v.co).z for v in body.data.vertices]
    return {'triangles': C.triangles([body]), 'panel_centre_m': PANEL_HEIGHT_M, 'height_m': round(max(zs), 2),
            'actions': [a.name for a in bpy.data.actions]}


result = main()
