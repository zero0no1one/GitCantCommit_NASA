"""Detailed EVA suit body for the Sunline astronaut (imported by build_astronaut.py).

References viewed before modelling (NASA Image and Video Library):
- NHQ201910150008: xEMU close front: bubble helmet on a hard upper torso, chest display-and-control module (DCM)
  with red connectors and hoses, bearing rings at shoulder and wrist, segmented gloves.
- axiom-axemu-full: AxEMU prototype, full front: helmet with a light/camera halo, torso ~1.5x hip width, bearing
  rings at shoulders/upper arms/wrists, coloured bands at thighs, knees and boot cuffs, thick-soled boots.
- com-axiom-suitsshots-20240103-0929: AxEMU kneeling: halo with side lamp pods, tall DCM with toggles and a slider,
  waist bearing ring, chunky gloves with gauntlet cuffs.
- axemu-prada-spacesuit-mockup-20241007-423: AxEMU 3/4 rear: PLSS ~0.55 m wide x 0.8 m tall x 0.3 m deep with
  rounded edges, top level with the helmet, coloured piping on its edges; grey abrasion patches on elbows and knees.
Sunline colour scheme (from the game brief): orange soft goods, white hard parts, grey bearings and abrasion patches,
gold sun visor. No logos.
Soft-goods polish references (viewed before modelling): Wikimedia Commons "Buzz Aldrin's spacesuit for
Apollo 11 2007-06-27.jpg" (A7L: stacked convolute folds at knees, elbows and waist, quilted seams, thigh cargo
pocket, wrinkled outer layer) and NASA axemu-axiom-suitcover-20230621-dgb-axp00653 (AxEMU cover: folds and seam
piping on the upper arm, grey fingertip caps, tall outer-leg panel with piping).
Every part is rigid to one bone of build_astronaut.BONES (bone positions unchanged so the animations still fit).
"""
import math
from mathutils import Vector
import sunline_common as C


def build_body(BONES):
    orange = C.texture_material('suit_orange', C.PALETTE['suit_orange'], normal='suit_fabric_normal.png', roughness=.8, normal_strength=0.35)
    white = C.mat('suit_white', roughness=.55)
    dark = C.mat('suit_dark', roughness=.5)
    grey = C.material('abrasion_grey', (0.30, 0.30, 0.31, 1), roughness=.9)
    bearing = C.material('bearing_metal', (0.55, 0.56, 0.58, 1), metallic=.85, roughness=.3)
    gold = C.mat('visor_gold', metallic=.75, roughness=.28)   # reads as gold even without a bright environment
    glass = C.transparent('helmet_bubble', (0.85, 0.9, 0.95, 1), alpha=0.18, roughness=0.02)
    lamp = C.material('lamp_white', (1, 1, 1, 1), emission=(1, .98, .92, 1), strength=4.0)
    red = C.material('connector_red', (0.75, 0.08, 0.06, 1), roughness=.4)
    blue = C.material('stripe_blue', (0.10, 0.22, 0.55, 1), roughness=.7)
    parts = []

    def P(ob, bone):
        C.assign_group(ob, bone)
        parts.append(ob)
        return ob

    def B(n):
        h, t, *_ = BONES[n]
        return Vector(h), Vector(t)

    # ---------------- lower torso: brief, waist bearing, hip bearings
    P(C.lathe('brief', [(0.0, 0.88), (0.13, 0.885), (0.175, 0.92), (0.19, 0.98), (0.185, 1.05), (0.175, 1.10)],
              18, orange, scale_xy=(1.12, 0.86)), 'hips')
    P(C.torus('waist_bearing', 0.182, 0.018, (0, 0, 1.105), segments=22, tube=6, material_=bearing, scale_xy=(1.1, .86)), 'hips')
    for side, sx in (('L', 1), ('R', -1)):
        P(C.torus(f'hip_bearing.{side}', 0.10, 0.014, (0.105*sx, 0, 0.90), normal=(0.25*sx, 0, -1), segments=16, tube=5,
                  material_=bearing), 'hips')
    # ---------------- abdomen and hard upper torso (HUT) under the orange cover
    P(C.lathe('abdomen', [(0.17, 1.10), (0.184, 1.122), (0.172, 1.145), (0.188, 1.168), (0.176, 1.19), (0.19, 1.213),
                            (0.182, 1.236), (0.185, 1.25), (0.20, 1.31)], 18, orange, scale_xy=(1.12, .86),
              cap_ends=False), 'spine')
    P(C.lathe('hut', [(0.20, 1.30), (0.235, 1.36), (0.25, 1.43), (0.245, 1.50), (0.215, 1.555), (0.15, 1.585)],
              20, orange, scale_xy=(1.22, .88)), 'chest')
    for side, sx in (('L', 1), ('R', -1)):          # shoulder stripes (white/blue) over the yoke
        P(C.tube(f'yoke_white.{side}', [(0.06*sx, -0.20, 1.53), (0.16*sx, -0.17, 1.56), (0.25*sx, -0.06, 1.55), (0.29*sx, 0.06, 1.50)],
                 0.012, 8, white), 'chest')
        P(C.tube(f'yoke_blue.{side}', [(0.07*sx, -0.215, 1.505), (0.17*sx, -0.19, 1.535), (0.27*sx, -0.07, 1.525), (0.31*sx, 0.05, 1.48)],
                 0.009, 8, blue), 'chest')
    # chest display-and-control module with knobs, toggles, slider and hoses to the PLSS
    P(C.rbox('dcm', (0.20, 0.075, 0.22), (0, -0.245, 1.36), radius=0.012, material_=white), 'chest')
    P(C.rbox('dcm_display', (0.11, 0.006, 0.045), (0, -0.284, 1.43), radius=0.003, material_=dark), 'chest')
    P(C.rbox('dcm_slider_track', (0.012, 0.006, 0.10), (0.065, -0.284, 1.34), radius=0.002, material_=dark), 'chest')
    P(C.rbox('dcm_slider', (0.022, 0.014, 0.02), (0.065, -0.29, 1.36), radius=0.004, material_=red), 'chest')
    for k, x in enumerate((-0.06, -0.02, 0.02)):
        P(C.cylinder(f'dcm_knob{k}', 0.011, 0.016, (x, -0.29, 1.355), (math.radians(90), 0, 0), segments=10, material_=dark), 'chest')
        P(C.rbox(f'dcm_toggle{k}', (0.008, 0.02, 0.008), (x, -0.293, 1.30), radius=0.002, material_=bearing), 'chest')
    for side, sx in (('L', 1), ('R', -1)):
        P(C.cylinder(f'dcm_port.{side}', 0.016, 0.03, (0.105*sx, -0.24, 1.29), (0, math.radians(90), 0), segments=10, material_=red), 'chest')
        P(C.tube(f'hose.{side}', [(0.12*sx, -0.24, 1.29), (0.19*sx, -0.22, 1.26), (0.25*sx, -0.12, 1.27), (0.27*sx, 0.02, 1.32), (0.24*sx, 0.18, 1.38)],
                 0.013, 10, dark), 'chest')
    # ---------------- PLSS backpack
    P(C.rbox('plss', (0.54, 0.30, 0.80), (0, 0.33, 1.38), radius=0.06, segments=2, material_=white), 'chest')
    P(C.rbox('plss_mount', (0.36, 0.10, 0.46), (0, 0.17, 1.38), radius=0.03, material_=grey), 'chest')   # interface plate, closes the gap to the torso
    for side, sx in (('L', 1), ('R', -1)):
        P(C.tube(f'plss_piping.{side}', [(0.272*sx, 0.19, 0.99), (0.272*sx, 0.19, 1.76)], 0.007, 6, red), 'chest')
        P(C.rbox(f'plss_vent.{side}', (0.01, 0.16, 0.10), (0.272*sx, 0.35, 1.12), radius=0.003, material_=dark), 'chest')
    P(C.rbox('plss_top', (0.44, 0.22, 0.03), (0, 0.34, 1.785), radius=0.01, material_=grey), 'chest')
    P(C.tube('plss_handle', [(-0.12, 0.27, 1.79), (-0.12, 0.27, 1.83), (0.12, 0.27, 1.83), (0.12, 0.27, 1.79)], 0.011, 8, bearing), 'chest')
    P(C.cylinder('plss_antenna', 0.006, 0.16, (0.22, 0.41, 1.87), segments=6, material_=dark), 'chest')
    for k in range(5):                               # radiator ribs on the back face
        P(C.rbox(f'plss_rib{k}', (0.40, 0.012, 0.012), (0, 0.483, 1.10+k*0.05), radius=0.003, material_=grey), 'chest')
    # ---------------- neck ring, helmet, sun visor, halo with lamps and camera
    P(C.torus('neck_ring', 0.155, 0.02, (0, -0.02, 1.565), normal=(0, -0.25, 1), segments=22, tube=6, material_=bearing), 'neck')
    P(C.sphere('helmet_inner', 0.150, (0, -0.02, 1.72), segments=14, rings=8, material_=dark), 'head')
    P(C.sphere('helmet_bubble', 0.172, (0, -0.02, 1.72), segments=22, rings=12, material_=glass), 'head')
    # sun visor: a spherical cap (radius 0.18) just outside the 0.172 m bubble, covering the front ~100°
    vis = C.lathe('sun_visor', [(0.18*math.sin(math.radians(a)), 0.18*math.cos(math.radians(a))) for a in range(0, 101, 10)],
                  20, gold, cap_ends=False)
    vis.rotation_euler = (math.radians(90), 0, 0)    # dome apex to the front (-Y); it opens toward the back
    vis.location = (0, -0.02, 1.72)
    P(vis, 'head')
    P(C.torus('halo', 0.168, 0.022, (0, 0.0, 1.78), normal=(0, 0.35, 1), segments=22, tube=6, material_=white, scale_xy=(1.0, 1.05)), 'head')
    for side, sx in (('L', 1), ('R', -1)):
        P(C.rbox(f'lamp_pod.{side}', (0.05, 0.08, 0.05), (0.17*sx, -0.06, 1.79), radius=0.01, material_=white), 'head')
        P(C.cylinder(f'lamp_lens.{side}', 0.016, 0.006, (0.17*sx, -0.102, 1.79), (math.radians(90), 0, 0), segments=12, material_=lamp), 'head')
    P(C.rbox('halo_camera', (0.05, 0.05, 0.035), (0, -0.07, 1.905), radius=0.008, material_=grey), 'head')
    P(C.cylinder('halo_camera_lens', 0.012, 0.008, (0, -0.097, 1.905), (math.radians(90), 0, 0), segments=10, material_=dark), 'head')

    # ---------------- arms
    for side, sx in (('L', 1), ('R', -1)):
        ua_h, ua_t = B(f'upper_arm.{side}')
        fa_h, fa_t = B(f'forearm.{side}')
        h_h, h_t = B(f'hand.{side}')
        P(C.sphere(f'shoulder_cap.{side}', 0.10, (0.25*sx, 0.0, 1.47), segments=14, rings=8, material_=orange, scale=(1, 1, 0.95)), f'upper_arm.{side}')
        P(C.torus(f'shoulder_bearing.{side}', 0.088, 0.016, (0.30*sx, 0.0, 1.45), normal=(sx, 0, 0.35), segments=18, tube=6, material_=bearing), f'upper_arm.{side}')
        P(C.limb_folds(f'upper_arm.{side}', ua_h+Vector((0, 0, -0.02)), ua_t, [0.085, 0.082, 0.078, 0.074], 12, orange,
                         folds=[(0.0, 0.2, 2, 0.06), (0.74, 1.0, 3, 0.08)]), f'upper_arm.{side}')
        mid = ua_h.lerp(ua_t, 0.35)
        P(C.torus(f'arm_bearing.{side}', 0.083, 0.012, mid, normal=ua_t-ua_h, segments=16, tube=5, material_=bearing), f'upper_arm.{side}')
        P(C.torus(f'arm_band.{side}', 0.080, 0.010, ua_h.lerp(ua_t, 0.7), normal=ua_t-ua_h, segments=16, tube=5, material_=white), f'upper_arm.{side}')
        P(C.limb_folds(f'forearm.{side}', fa_h, fa_t, [0.075, 0.072, 0.066, 0.06], 12, orange,
                         folds=[(0.0, 0.26, 3, 0.08)]), f'forearm.{side}')
        P(C.sphere(f'elbow_patch.{side}', 0.06, fa_h+Vector((0, 0.045, 0.0)), segments=12, rings=6, material_=grey, scale=(1.05, 0.55, 1.1)), f'forearm.{side}')
        for seg_name, (p0, p1, rr) in ((f'upper_arm.{side}', (ua_h+Vector((0, 0, -0.06)), ua_t, 0.08)), (f'forearm.{side}', (fa_h, fa_t, 0.07))):
            P(C.tube(f'arm_seam_{seg_name}', [p0+Vector((0, rr, 0)), p0.lerp(p1, 0.5)+Vector((0, rr+0.002, 0)), p1+Vector((0, rr*0.85, 0))], 0.004, 6, white), seg_name)
        P(C.torus(f'wrist_bearing.{side}', 0.058, 0.012, fa_t+(fa_h-fa_t).normalized()*0.02, normal=fa_t-fa_h, segments=16, tube=5, material_=bearing), f'forearm.{side}')
        # gauntlet cuff, palm, fingers and thumb
        cuff = C.lathe(f'gauntlet.{side}', [(0.058, 0.0), (0.066, 0.4), (0.074, 1.0)], 18, white, cap_ends=False)
        P(C.align(cuff, fa_t+(fa_t-fa_h).normalized()*0.005, fa_t+(fa_t-fa_h).normalized()*0.06), f'forearm.{side}')
        d = (h_t-h_h).normalized()
        palm_c = h_h+d*0.055
        palm = C.rbox(f'palm.{side}', (0.075, 0.035, 0.09), (0, 0, 0), radius=0.014, material_=white)
        palm.rotation_euler = d.to_track_quat('Z', 'Y').to_euler()
        palm.location = palm_c
        P(palm, f'hand.{side}')
        P(C.rbox(f'glove_back.{side}', (0.06, 0.008, 0.06), palm_c+Vector((0, 0.02, 0)), radius=0.004, material_=grey), f'hand.{side}')
        for k in range(4):                           # fingers: two segments each, curled slightly forward
            x = (-0.027+k*0.018)*sx
            base = palm_c+d*0.045+Vector((x, -0.004, 0))
            mid_ = base+d*0.032+Vector((0, -0.008, 0))
            tip = mid_+d*0.026+Vector((0, -0.014, 0))
            P(C.tube(f'finger{k}a.{side}', [base, mid_], 0.0085, 6, white), f'hand.{side}')
            P(C.tube(f'finger{k}b.{side}', [mid_, tip], 0.008, 6, grey), f'hand.{side}')
            P(C.sphere(f'fingertip{k}.{side}', 0.0088, tip, segments=8, rings=5, material_=grey), f'hand.{side}')
        tb = palm_c+Vector((0.04*sx, -0.02, 0.02))
        P(C.tube(f'thumb.{side}', [tb, tb+Vector((0.012*sx, -0.025, -0.03)), tb+Vector((0.005*sx, -0.04, -0.05))], 0.0095, 6, white), f'hand.{side}')

    # ---------------- legs and boots
    for side, sx in (('L', 1), ('R', -1)):
        th_h, th_t = B(f'thigh.{side}')
        sh_h, sh_t = B(f'shin.{side}')
        P(C.limb_folds(f'thigh.{side}', th_h+Vector((0, 0, 0.03)), th_t, [0.112, 0.108, 0.10, 0.092], 12, orange,
                         folds=[(0.0, 0.14, 2, 0.05), (0.80, 1.0, 3, 0.08)]), f'thigh.{side}')
        P(C.torus(f'thigh_band.{side}', 0.104, 0.012, th_h.lerp(th_t, 0.45), normal=th_t-th_h, segments=16, tube=5, material_=white), f'thigh.{side}')
        P(C.torus(f'thigh_bearing.{side}', 0.102, 0.012, th_h.lerp(th_t, 0.2), normal=th_t-th_h, segments=16, tube=5, material_=bearing), f'thigh.{side}')
        P(C.limb_folds(f'shin.{side}', sh_h, sh_t+Vector((0, 0, 0.04)), [0.09, 0.088, 0.082, 0.078], 12, orange,
                         folds=[(0.0, 0.24, 3, 0.08)]), f'shin.{side}')
        P(C.sphere(f'knee_patch.{side}', 0.072, sh_h+Vector((0, -0.065, 0.0)), segments=12, rings=6, material_=grey, scale=(1.05, 0.5, 1.15)), f'shin.{side}')
        P(C.torus(f'knee_band.{side}', 0.088, 0.011, sh_h.lerp(sh_t, 0.3), normal=sh_t-sh_h, segments=16, tube=5, material_=white), f'shin.{side}')
        # AxEMU-style outer leg panel with piping on both edges, and an A7L-style thigh cargo pocket
        for seg, (a_, b_, rad) in (('thigh', (th_h+Vector((0, 0, -0.05)), th_t+Vector((0, 0, 0.09)), 0.118)),
                                   ('shin', (sh_h+Vector((0, 0, -0.09)), sh_t+Vector((0, 0, 0.10)), 0.097))):
            off = Vector((sx*rad, 0, 0))
            P(C.strip(f'leg_panel_{seg}.{side}', a_, b_, 0.05, 0.012, blue, offset=off), f'{seg}.{side}')
            for e in (-1, 1):
                P(C.tube(f'leg_piping_{seg}{e}.{side}', [a_+off+Vector((sx*0.002, e*0.027, 0)), b_+off+Vector((sx*0.002, e*0.027, 0))],
                         0.0045, 6, white), f'{seg}.{side}')
        pk = th_h.lerp(th_t, 0.55)+Vector((sx*0.075, -0.07, 0))
        P(C.rbox(f'thigh_pocket.{side}', (0.03, 0.11, 0.13), pk, radius=0.012, material_=orange, rotation=(0, 0, math.radians(-sx*35))), f'thigh.{side}')
        P(C.rbox(f'pocket_flap.{side}', (0.034, 0.115, 0.03), pk+Vector((0, 0, 0.065)), radius=0.008, material_=white, rotation=(0, 0, math.radians(-sx*35))), f'thigh.{side}')
        # boot: ankle bearing, shell, toe cap, thick sole with tread
        P(C.torus(f'ankle_bearing.{side}', 0.082, 0.012, (0.12*sx, 0.01, 0.16), segments=16, tube=5, material_=bearing), f'foot.{side}')
        cuffb = C.lathe(f'boot_cuff.{side}', [(0.086, 0.0), (0.09, 0.03), (0.086, 0.06)], 20, white, cap_ends=False)
        cuffb.location = (0.12*sx, 0.01, 0.10)
        P(cuffb, f'foot.{side}')
        P(C.rbox(f'boot_shell.{side}', (0.15, 0.30, 0.12), (0.12*sx, -0.04, 0.095), radius=0.045, segments=2, material_=white), f'foot.{side}')
        P(C.sphere(f'toe_cap.{side}', 0.07, (0.12*sx, -0.165, 0.07), segments=16, rings=8, material_=grey, scale=(1.05, 0.9, 0.62)), f'foot.{side}')
        P(C.rbox(f'sole.{side}', (0.16, 0.32, 0.04), (0.12*sx, -0.045, 0.02), radius=0.012, material_=C.material('sole_blue_grey', (0.62, 0.68, 0.74, 1), roughness=.8)), f'foot.{side}')
        for k in range(6):
            P(C.rbox(f'tread{k}.{side}', (0.15, 0.012, 0.008), (0.12*sx, -0.17+k*0.05, 0.002), radius=0.002, material_=dark), f'foot.{side}')
    C.apply_transforms(parts)
    body = C.join(parts, 'Astronaut')
    C.box_uv(body, 0.45)          # for the fabric normal map (and any future textures)
    return body
