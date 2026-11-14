"""Sunline handheld scanner (imported by build_astronaut.py and reused by build_sky_props.py via scanner.glb).

References viewed before modelling (Wikimedia Commons):
- "Handheld RXF analyzer gun.jpg": side profile of a pistol-grip XRF analyser: wedge-shaped upper body tapering
  to a metal measuring nose, grip raked back ~15° with a dark rubber overmould, trigger-guard loop.
- "Niton XL3t GOLDD Plus on rock 800-600.jpg": 3/4 view in use: grey shell with a dark side panel, flip-up screen
  hinged at the rear top (~40°), nose window pressed to rock, dark grip bumpers, wrist strap. Body ~24 cm long,
  ~8 cm wide; grip ~12 cm.
Sunline version: scaled for a pressurised EVA glove (grip 15 cm x 5 cm, bigger guard), white shell to match the
suit, cyan flip-up screen and cyan lens ring (the game's scanner colour), lanyard ring, stub antenna.
Frame: origin at the middle of the grip (where the glove closes), forward = -Y (Godot +Z), up = +Z.
"""
import math
from mathutils import Vector
import sunline_common as C


def build_scanner():
    white = C.mat('suit_white', roughness=.5)
    dark = C.mat('suit_dark', roughness=.55)
    rubber = C.mat('rubber', roughness=.9)
    metal = C.material('bearing_metal', (0.55, 0.56, 0.58, 1), metallic=.85, roughness=.3)
    cyan = C.mat('scanner_cyan', emission=C.PALETTE['scanner_cyan'], strength=3.0)
    glass = C.material('sensor_window', (0.05, 0.06, 0.07, 1), metallic=.2, roughness=.05)
    p = []
    # wedge body: built as a lathe-free extruded profile (side view) then given width
    import bmesh
    prof = [(0.07, 0.035), (0.07, 0.105), (0.02, 0.118), (-0.10, 0.112), (-0.17, 0.095), (-0.20, 0.075),
            (-0.20, 0.045), (-0.16, 0.035)]            # (y, z) side outline, nose at -y
    bm = bmesh.new()
    half = 0.042
    left = [bm.verts.new((-half, y, z)) for y, z in prof]
    right = [bm.verts.new((half, y, z)) for y, z in prof]
    n = len(prof)
    for i in range(n):
        j = (i+1) % n
        bm.faces.new((left[i], left[j], right[j], right[i]))
    bm.faces.new(list(reversed(left)))
    bm.faces.new(right)
    bmesh.ops.bevel(bm, geom=bm.edges[:], offset=0.008, segments=2, affect='EDGES', profile=0.5)
    body = C.mesh_object('scanner_body', bm, white)
    body.data.set_sharp_from_angle(angle=math.radians(40))
    p.append(body)
    for sx in (1, -1):                                 # dark side panels
        p.append(C.rbox(f'side_panel{sx}', (0.004, 0.17, 0.035), (0.044*sx, -0.06, 0.07), radius=0.002, material_=dark))
    # nose: metal collar, cyan lens ring, dark sensor window
    p.append(C.cylinder('nose_collar', 0.030, 0.03, (0, -0.212, 0.06), (math.radians(90), 0, 0), segments=16, material_=metal))
    p.append(C.torus('lens_ring', 0.024, 0.0045, (0, -0.229, 0.06), normal=(0, -1, 0), segments=18, tube=6, material_=cyan))
    p.append(C.cylinder('sensor_window', 0.019, 0.004, (0, -0.228, 0.06), (math.radians(90), 0, 0), segments=16, material_=glass))
    # flip-up screen hinged at the rear top, tilted ~40°
    hinge = Vector((0, 0.05, 0.118))
    p.append(C.cylinder('screen_hinge', 0.007, 0.07, hinge, (0, math.radians(90), 0), segments=8, material_=dark))
    tilt = math.radians(40)
    centre = hinge+Vector((0, -0.045*math.cos(tilt), 0.045*math.sin(tilt)+0.004))
    bezel = C.rbox('screen_bezel', (0.075, 0.095, 0.010), centre, radius=0.004, material_=dark, rotation=(-tilt, 0, 0))
    # the cyan face sits on the user-facing (rear, upper) side of the bezel
    screen = C.rbox('screen', (0.062, 0.078, 0.003), centre+Vector((0, 0.006*math.sin(tilt), 0.006*math.cos(tilt))),
                    radius=0.001, material_=cyan, rotation=(-tilt, 0, 0))
    p += [bezel, screen]
    # buttons on the top deck in front of the screen
    for k, y in enumerate((-0.05, -0.075, -0.10)):
        p.append(C.cylinder(f'button{k}', 0.007, 0.006, (0, y, 0.115-0.006*k), segments=10, material_=dark))
    # pistol grip raked back 15°, rubber overmould, trigger and guard sized for a glove
    rake = math.radians(15)
    gtop, gbot = Vector((0, 0.025, 0.04)), Vector((0, 0.025+0.15*math.sin(rake), 0.04-0.15*math.cos(rake)))
    grip = C.rbox('grip', (0.046, 0.052, 0.15), (gtop+gbot)/2, radius=0.016, material_=white, rotation=(rake, 0, 0))
    over = C.rbox('grip_rubber', (0.05, 0.03, 0.12), (gtop+gbot)/2+Vector((0, 0.016, -0.005)), radius=0.012, material_=rubber, rotation=(rake, 0, 0))
    p += [grip, over]
    p.append(C.rbox('grip_foot', (0.056, 0.07, 0.022), gbot+Vector((0, 0.002, -0.004)), radius=0.008, material_=rubber, rotation=(rake, 0, 0)))
    p.append(C.rbox('trigger', (0.016, 0.018, 0.04), (0, -0.002, 0.014), radius=0.005, material_=dark, rotation=(rake, 0, 0)))
    p.append(C.tube('trigger_guard', [(0, -0.01, 0.036), (0, -0.058, 0.032), (0, -0.062, -0.02), (0, -0.03, -0.052), (0, 0.012, -0.062), (0, 0.032, -0.064)], 0.006, 8, white))
    p.append(C.torus('lanyard_ring', 0.012, 0.003, gbot+Vector((0, 0.03, -0.01)), normal=(1, 0, 0), segments=12, tube=5, material_=metal))
    p.append(C.cylinder('antenna', 0.0035, 0.06, (0.03, 0.06, 0.135), segments=6, material_=dark))
    # shift so the origin sits at the middle of the grip (where the glove closes)
    grip_mid = (gtop+gbot)/2
    for o in p:
        o.location = Vector(o.location)-grip_mid
    C.apply_transforms(p)
    return C.join(p, 'Scanner')
