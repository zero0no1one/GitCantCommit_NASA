"""Sunline astronaut body v3: built to the team's character turnaround sheet (front, 3/4, side, rear 3/4, back).

Reference: the turnaround concept art supplied by the user (orange suit, five views). Read from it:
- Proportions: slimmer and more human than a bulky pressure suit; fitted one-piece orange coverall.
- Helmet: white hard shell with a big round front opening and a glossy black visor (the sheet's light blue on the
  glass is reflected light, so all glass is black: visor, its rim and the side windows); round white
  ear pods on both sides; a light-blue side window; a rectangular panel on the back; white neck ring over a navy collar.
- Chest: light-blue round gauges/ports with navy and grey rims; a central vertical hose; a small round chest patch.
- Harness: navy straps over both shoulders, down the back to a navy belt with a buckle.
- Backpack: compact, rounded, white, about half the torso height.
- Gloves royal blue with wide navy wrist cuffs; boots chunky royal blue.
- Legs: white oval knee pads; horizontal ribbing on the shins; blue flap pocket on the left thigh, outlined pocket on
  the right thigh. Flag patches on both shoulders. Seam lines: front yoke, centre zip, V across the upper back.
Bone positions are unchanged (build_astronaut.BONES), so every animation still fits. Each part is rigid to one bone.
"""
import math
from mathutils import Vector
import sunline_common as C

NAVY = (0.09, 0.17, 0.36, 1)
ROYAL = (0.13, 0.30, 0.68, 1)
LIGHT_BLUE = (0.52, 0.80, 0.90, 1)


def flag_patch(name, centre, normal, width, P, bone):
    """Small flag patch: white field, red stripes, blue canton (plain geometry, no texture)."""
    n = Vector(normal).normalized()
    up = Vector((0, 0, 1))
    side = up.cross(n).normalized()
    up = n.cross(side).normalized()
    h = width*0.6
    red = C.material('flag_red', (0.72, 0.10, 0.10, 1), roughness=.7)
    white = C.material('flag_white', (0.92, 0.92, 0.90, 1), roughness=.7)
    blue = C.material('flag_blue', (0.12, 0.18, 0.42, 1), roughness=.7)
    def quad(nm, c, w, hh, mat, lift):
        ob = C.box(nm, (w, 0.002, hh), (0, 0, 0), material_=mat)
        rot = n.to_track_quat('-Y', 'Z').to_euler()
        ob.rotation_euler = rot
        ob.location = Vector(c)+n*lift
        P(ob, bone)
    quad(f'{name}_field', centre, width, h, white, 0.001)
    for k in range(3):
        quad(f'{name}_stripe{k}', Vector(centre)+up*(h/2-h*(2*k+1)/6), width, h/7, red, 0.002)
    quad(f'{name}_canton', Vector(centre)+up*h/4-side*width/4, width/2, h/2, blue, 0.003)


def build_body(BONES):
    orange = C.texture_material('suit_orange', C.PALETTE['suit_orange'], normal='suit_fabric_normal.png', roughness=.82,
                                normal_strength=0.3)
    white = C.mat('suit_white', roughness=.5)
    navy = C.material('suit_navy', NAVY, roughness=.6)
    royal = C.material('suit_royal', ROYAL, roughness=.55)
    lblue = C.material('suit_light_blue', LIGHT_BLUE, roughness=.35, metallic=.1)
    grey = C.material('fitting_grey', (0.55, 0.57, 0.6, 1), metallic=.7, roughness=.3)
    seam = C.material('seam_dark_orange', (0.55, 0.15, 0.03, 1), roughness=.8)
    # black glass: near-black base, very smooth, full-strength specular so the Sun and scene read as reflections
    visor = C.material('visor_black', (0.004, 0.004, 0.006, 1), metallic=0.0, roughness=0.03)
    visor.node_tree.nodes['Principled BSDF'].inputs['Specular IOR Level'].default_value = 1.0
    parts = []

    def P(ob, bone):
        C.assign_group(ob, bone)
        parts.append(ob)
        return ob

    def B(n):
        h, t, *_ = BONES[n]
        return Vector(h), Vector(t)

    # ---------------- torso: fitted coverall, belt, seams
    P(C.lathe('hips', [(0.0, 0.88), (0.12, 0.885), (0.16, 0.92), (0.17, 0.98), (0.165, 1.05), (0.16, 1.10)], 18, orange,
              scale_xy=(1.1, .82)), 'hips')
    P(C.torus('belt', 0.168, 0.022, (0, 0, 1.08), segments=22, tube=6, material_=navy, scale_xy=(1.1, .84)), 'hips')
    P(C.rbox('buckle', (0.07, 0.02, 0.045), (0, -0.152, 1.08), radius=0.006, material_=grey), 'hips')
    P(C.lathe('abdomen', [(0.16, 1.09), (0.165, 1.18), (0.175, 1.26), (0.19, 1.31)], 18, orange, scale_xy=(1.1, .82),
              cap_ends=False), 'spine')
    P(C.lathe('chest', [(0.19, 1.30), (0.215, 1.37), (0.225, 1.44), (0.215, 1.51), (0.18, 1.56), (0.12, 1.585)], 20, orange,
              scale_xy=(1.16, .84)), 'chest')
    P(C.tube('centre_zip', [(0, -0.188, 1.10), (0, -0.19, 1.30), (0, -0.188, 1.50)], 0.004, 5, seam), 'chest')
    P(C.tube('front_yoke', [(-0.22, -0.13, 1.47), (-0.10, -0.18, 1.49), (0.10, -0.18, 1.49), (0.22, -0.13, 1.47)], 0.0035, 5, seam), 'chest')
    P(C.tube('back_v_L', [(0.22, 0.13, 1.50), (0.0, 0.19, 1.30)], 0.0035, 5, seam), 'chest')
    P(C.tube('back_v_R', [(-0.22, 0.13, 1.50), (0.0, 0.19, 1.30)], 0.0035, 5, seam), 'chest')
    # chest gauges and ports (light blue with rims), central hose, small round patch
    for k, (x, z, r) in enumerate(((-0.075, 1.44, 0.032), (0.075, 1.44, 0.03), (-0.08, 1.35, 0.022), (0.06, 1.33, 0.028),
                                   (-0.07, 1.25, 0.026))):
        c = Vector((x, -0.192+abs(x)*0.25, z))
        P(C.cylinder(f'gauge{k}', r, 0.016, c, (math.radians(90), 0, 0), segments=16, material_=lblue), 'chest')
        P(C.torus(f'gauge_rim{k}', r, 0.005, c+Vector((0, -0.006, 0)), normal=(0, -1, 0), segments=16, tube=5,
                  material_=navy if k % 2 else grey), 'chest')
    P(C.tube('chest_hose', [(0.025, -0.20, 1.53), (0.03, -0.215, 1.42), (0.022, -0.21, 1.30), (0.03, -0.19, 1.17)], 0.011, 8,
             C.material('hose_light', (0.80, 0.82, 0.84, 1), roughness=.5)), 'chest')
    P(C.cylinder('chest_patch', 0.022, 0.006, (-0.13, -0.17, 1.50), (math.radians(80), 0, math.radians(-25)), segments=14, material_=navy), 'chest')
    # harness: navy straps over the shoulders, down the back to the belt
    for side, sx in (('L', 1), ('R', -1)):
        P(C.tube(f'strap_front.{side}', [(0.10*sx, -0.19, 1.12), (0.115*sx, -0.20, 1.30), (0.13*sx, -0.17, 1.50),
                                         (0.15*sx, -0.06, 1.585), (0.15*sx, 0.07, 1.58)], 0.016, 6, navy), 'chest')
        P(C.tube(f'strap_back.{side}', [(0.15*sx, 0.07, 1.58), (0.13*sx, 0.19, 1.48), (0.10*sx, 0.20, 1.30), (0.09*sx, 0.17, 1.10)],
                 0.016, 6, navy), 'chest')
        P(C.rbox(f'strap_clip.{side}', (0.04, 0.02, 0.03), (0.115*sx, -0.212, 1.30), radius=0.005, material_=grey), 'chest')
    # compact rounded white backpack with navy mounts
    P(C.rbox('backpack', (0.24, 0.11, 0.32), (0, 0.255, 1.42), radius=0.045, segments=3, material_=white), 'chest')
    P(C.rbox('backpack_lid', (0.19, 0.02, 0.22), (0, 0.315, 1.42), radius=0.018, material_=white), 'chest')
    for sx in (1, -1):
        P(C.rbox(f'backpack_mount{sx}', (0.05, 0.05, 0.05), (0.09*sx, 0.19, 1.54), radius=0.01, material_=navy), 'chest')
        P(C.cylinder(f'backpack_valve{sx}', 0.016, 0.03, (0.13*sx, 0.255, 1.33), (0, math.radians(90), 0), segments=10, material_=lblue), 'chest')
    # ---------------- neck ring, navy collar, helmet
    P(C.torus('collar', 0.15, 0.022, (0, -0.01, 1.555), normal=(0, -0.2, 1), segments=22, tube=6, material_=navy), 'neck')
    P(C.torus('neck_ring', 0.145, 0.02, (0, -0.012, 1.585), normal=(0, -0.2, 1), segments=22, tube=6, material_=white), 'neck')
    hc = Vector((0, -0.01, 1.73))
    # white shell: sphere with the front cut open (lathe around the forward axis)
    shell = C.lathe('helmet_shell', [(0.0, -0.17), (0.08, -0.155), (0.13, -0.11), (0.16, -0.05), (0.17, 0.0), (0.165, 0.05),
                                     (0.15, 0.09), (0.125, 0.115)], 24, white, cap_ends=False)   # open at the front for the visor
    shell.rotation_euler = (math.radians(90), 0, 0)    # lathe axis -> -Y (front); the opening faces forward
    shell.location = hc
    P(shell, 'head')
    vis = C.lathe('visor', [(0.0, 0.135), (0.06, 0.13), (0.10, 0.12), (0.125, 0.108)], 22, visor, cap_ends=False)
    vis.rotation_euler = (math.radians(90), 0, 0)
    vis.location = hc
    P(vis, 'head')
    P(C.torus('visor_rim', 0.126, 0.010, hc+Vector((0, -0.112, 0)), normal=(0, -1, 0), segments=24, tube=6, material_=visor), 'head')   # glass edge
    for sx in (1, -1):
        P(C.cylinder(f'ear_pod{sx}', 0.062, 0.035, hc+Vector((0.168*sx, 0.01, -0.005)), (0, math.radians(90), 0), segments=20, material_=white), 'head')
        P(C.torus(f'ear_pod_rim{sx}', 0.058, 0.006, hc+Vector((0.186*sx, 0.01, -0.005)), normal=(sx, 0, 0), segments=18, tube=5, material_=grey), 'head')
        win = C.sphere(f'side_window{sx}', 0.05, hc+Vector((0.14*sx, -0.07, 0.03)), segments=12, rings=8, material_=visor, scale=(0.35, 1.0, 0.8))   # side glass
        P(win, 'head')
    P(C.rbox('helmet_back_panel', (0.12, 0.02, 0.09), hc+Vector((0, 0.165, 0.0)), radius=0.012, material_=white), 'head')
    P(C.rbox('helmet_back_inset', (0.09, 0.006, 0.065), hc+Vector((0, 0.176, 0.0)), radius=0.006, material_=grey), 'head')

    HELMET_SCALE = 1.08
    first = next(k for k, o in enumerate(parts) if o.name == 'helmet_shell')
    for o in parts[first:]:
        o.location = hc+(Vector(o.location)-hc)*HELMET_SCALE
        o.scale = Vector(o.scale)*HELMET_SCALE
    # ---------------- arms (slimmer), flag patches, navy cuffs, royal-blue gloves
    for side, sx in (('L', 1), ('R', -1)):
        ua_h, ua_t = B(f'upper_arm.{side}')
        fa_h, fa_t = B(f'forearm.{side}')
        h_h, h_t = B(f'hand.{side}')
        P(C.sphere(f'shoulder.{side}', 0.085, (0.24*sx, 0.0, 1.475), segments=14, rings=8, material_=orange), f'upper_arm.{side}')
        P(C.limb_folds(f'upper_arm.{side}', ua_h+Vector((0, 0, -0.02)), ua_t, [0.074, 0.071, 0.067, 0.064], 12, orange,
                       folds=[(0.78, 1.0, 2, 0.05)]), f'upper_arm.{side}')
        flag_patch(f'flag.{side}', ua_h.lerp(ua_t, 0.28)+Vector((0.07*sx, -0.012, 0)), (sx, -0.25, 0), 0.092, P, f'upper_arm.{side}')
        P(C.limb_folds(f'forearm.{side}', fa_h, fa_t, [0.065, 0.062, 0.058, 0.054], 12, orange,
                       folds=[(0.0, 0.2, 2, 0.05)]), f'forearm.{side}')
        cuff = C.lathe(f'cuff.{side}', [(0.064, 0.0), (0.072, 0.1), (0.072, 0.9), (0.064, 1.0)], 16, navy)
        P(C.align(cuff, fa_t+(fa_h-fa_t).normalized()*0.075, fa_t+(fa_t-fa_h).normalized()*0.01), f'forearm.{side}')
        d = (h_t-h_h).normalized()
        palm_c = h_h+d*0.05
        palm = C.rbox(f'palm.{side}', (0.10, 0.05, 0.105), (0, 0, 0), radius=0.02, material_=royal)
        palm.rotation_euler = d.to_track_quat('Z', 'Y').to_euler()
        palm.location = palm_c
        P(palm, f'hand.{side}')
        for k in range(4):
            x = (-0.034+k*0.0227)*sx
            base = palm_c+d*0.048+Vector((x, -0.004, 0))
            mid_ = base+d*0.03+Vector((0, -0.006, 0))
            tip = mid_+d*0.024+Vector((0, -0.012, 0))
            P(C.tube(f'finger{k}.{side}', [base, mid_, tip], 0.0125, 6, royal), f'hand.{side}')
            P(C.sphere(f'fingertip{k}.{side}', 0.0125, tip, segments=8, rings=5, material_=royal), f'hand.{side}')
        tb = palm_c+Vector((0.044*sx, -0.02, 0.02))
        P(C.tube(f'thumb.{side}', [tb, tb+Vector((0.01*sx, -0.022, -0.028)), tb+Vector((0.004*sx, -0.036, -0.046))], 0.014, 6, royal), f'hand.{side}')

    # ---------------- legs: slim, knee pads, shin ribbing, pockets, chunky blue boots
    for side, sx in (('L', 1), ('R', -1)):
        th_h, th_t = B(f'thigh.{side}')
        sh_h, sh_t = B(f'shin.{side}')
        P(C.limb_folds(f'thigh.{side}', th_h+Vector((0, 0, 0.03)), th_t, [0.098, 0.094, 0.087, 0.08], 12, orange,
                       folds=[(0.86, 1.0, 1, 0.04)]), f'thigh.{side}')
        P(C.limb_folds(f'shin.{side}', sh_h, sh_t+Vector((0, 0, 0.04)), [0.078, 0.076, 0.072, 0.07], 12, orange,
                       folds=[(0.30, 0.95, 7, 0.035)]), f'shin.{side}')      # the sheet's horizontal shin ribbing
        P(C.sphere(f'knee_pad.{side}', 0.06, sh_h+Vector((0, -0.062, -0.01)), segments=14, rings=8, material_=white,
                   scale=(0.95, 0.42, 1.12)), f'shin.{side}')
        pk = th_h.lerp(th_t, 0.6)+Vector((sx*0.03, -0.085, 0))
        if side == 'L':      # blue flap pocket on the left thigh
            P(C.rbox('pocket_L', (0.085, 0.022, 0.10), pk, radius=0.008, material_=royal, rotation=(0, 0, math.radians(-12))), 'thigh.L')
            P(C.rbox('pocket_flap_L', (0.09, 0.026, 0.028), pk+Vector((0, -0.002, 0.045)), radius=0.006, material_=navy, rotation=(0, 0, math.radians(-12))), 'thigh.L')
        else:                # outlined orange pocket on the right thigh
            P(C.rbox('pocket_R', (0.085, 0.02, 0.10), pk, radius=0.008, material_=orange, rotation=(0, 0, math.radians(12))), 'thigh.R')
            P(C.tube('pocket_R_seam', [pk+Vector((-0.04, -0.012, 0.045)), pk+Vector((0.04, -0.012, 0.045))], 0.003, 4, seam), 'thigh.R')
        # boot: chunky royal-blue upper, rounded toe, navy sole
        P(C.lathe(f'boot_cuff.{side}', [(0.074, 0.0), (0.082, 0.03), (0.084, 0.07)], 16, royal, cap_ends=False), f'foot.{side}') \
            .location = (0.12*sx, 0.01, 0.11)
        P(C.rbox(f'boot_upper.{side}', (0.14, 0.27, 0.13), (0.12*sx, -0.035, 0.095), radius=0.05, segments=2, material_=royal), f'foot.{side}')
        P(C.sphere(f'boot_toe.{side}', 0.07, (0.12*sx, -0.15, 0.065), segments=14, rings=8, material_=royal, scale=(1.0, 0.95, 0.75)), f'foot.{side}')
        P(C.rbox(f'boot_sole.{side}', (0.15, 0.30, 0.035), (0.12*sx, -0.04, 0.018), radius=0.012, material_=navy), f'foot.{side}')
    C.apply_transforms(parts)
    body = C.join(parts, 'Astronaut')
    C.box_uv(body, 0.45)
    return body
