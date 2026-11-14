"""Sunline preliminary VFX: ballistic dust flipbooks and emissive effect meshes.

Realism rules (from the Echo-Path film notes): the Moon has no air, so dust does not billow or drift. Every grain
flies a parabola p = p0 + v0 t + ½ g t² with g = 1.62 m/s² and stops when it lands. No sound.

Flipbooks: frames are rendered here from a side-on orthographic camera with a transparent background into
blender/vfx/frames/<effect>/, then packed into 4x4 sheets (512 px) at assets/vfx/<effect>_4x4.png by
tools/pack_flipbooks.py (needs Pillow). Grain trajectories are seeded, so re-running gives the same sheets.
Meshes (assets/models/vfx_meshes.glb): ScannerBeam (cone, apex at origin, 1 m long toward Godot +Z),
Reticle (ring, radius 1 m, facing Godot +Z), BeaconPulse (flat ground ring, radius 1 m). Godot scales and fades them.
Each effect's numbers are in blender/vfx/<effect>.md so Godot's CPUParticles3D can match them.
"""
import json
import math
import sys
from pathlib import Path
import bpy
import bmesh
import numpy as np

sys.path.insert(0, str(Path(r'C:\dev\godot\new-game-project\blender\scripts')))
import importlib
import sunline_common as C
importlib.reload(C)

G = 1.62
FRAMES = 16
FRAME_PX = 128
DRAW_SCALE = 3.0     # grains are drawn 3x their physical size so they read at sprite resolution
FX_DIR = C.BLEND_DIR/'vfx'

EFFECTS = {
    # name: grains, lifetime s, speed range m/s, elevation range deg, azimuth centre/spread deg, size range m, ortho width m
    'footstep_dust': dict(n=48, life=1.2, speed=(0.4, 1.2), elev=(15, 55), az=(0, 90), size=(0.006, 0.02), width=1.6,
                          origin_r=0.08, use='astronaut footfalls (lunar_lope contact frames, walk_slow steps)'),
    'wheel_dust': dict(n=64, life=1.6, speed=(0.5, 1.5), elev=(20, 60), az=(180, 25), size=(0.006, 0.018), width=2.6,
                       origin_r=0.06, use='each rover wheel while drive_loop plays; spray goes backward'),
    'touchdown_spray': dict(n=220, life=1.0, speed=(5.0, 20.0), elev=(2, 12), az=(0, 180), size=(0.01, 0.05), width=12.0,
                            origin_r=0.6, use='lander touchdown: engine plume sweeps grains outward, low and fast; '
                                              'most leave the frame (real ranges reach tens of metres)'),
}


def trajectories(spec, seed):
    rng = np.random.default_rng(seed)
    n = spec['n']
    v = rng.uniform(*spec['speed'], n)
    el = np.radians(rng.uniform(*spec['elev'], n))
    az = np.radians(spec['az'][0]+rng.uniform(-spec['az'][1], spec['az'][1], n))
    r0 = spec['origin_r']*np.sqrt(rng.uniform(0, 1, n))
    a0 = rng.uniform(0, 2*np.pi, n)
    p0 = np.stack([r0*np.cos(a0), r0*np.sin(a0), np.full(n, 0.005)], 1)
    v0 = np.stack([v*np.cos(el)*np.sin(az), v*np.cos(el)*np.cos(az), v*np.sin(el)], 1)
    size = rng.uniform(*spec['size'], n)
    return p0, v0, size


def position(p0, v0, t):
    t_land = 2*v0[:, 2]/G
    tt = np.minimum(t, t_land)[:, None]
    p = p0+v0*tt+0.5*np.array([0, 0, -G])*tt**2
    p[:, 2] = np.maximum(p[:, 2], 0.0)
    return p


def render_effect(name, spec, seed):
    C.new_scene()
    s = bpy.context.scene
    s.render.engine = 'BLENDER_EEVEE'
    s.render.film_transparent = True
    s.render.resolution_x = s.render.resolution_y = FRAME_PX
    s.view_settings.view_transform = 'Standard'
    w = bpy.data.worlds.new('W')
    s.world = w
    w.use_nodes = True
    w.node_tree.nodes['Background'].inputs['Color'].default_value = (0, 0, 0, 1)
    grain = C.material('grain', (0.62, 0.60, 0.57, 1), roughness=1.0)
    p0, v0, size = trajectories(spec, seed)
    grains = []
    for i in range(spec['n']):
        bm = bmesh.new()
        bmesh.ops.create_icosphere(bm, subdivisions=1, radius=float(size[i])*DRAW_SCALE)
        grains.append(C.mesh_object(f'g{i}', bm, grain))
    cam = C.link(bpy.data.objects.new('cam', bpy.data.cameras.new('cam')))
    cam.data.type = 'ORTHO'
    cam.data.ortho_scale = spec['width']
    # side-on, across the main spray direction (local +Y forward / -Y back), ground near the bottom of the frame
    cam.location = (20, 0, spec['width']*0.35)
    cam.rotation_euler = (math.radians(90), 0, math.radians(90))
    s.camera = cam
    sun = C.link(bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN')))
    sun.data.energy = 6
    sun.rotation_euler = (math.radians(60), 0, math.radians(90))     # light from the camera side (+X)
    frames_dir = FX_DIR/'frames'/name
    frames_dir.mkdir(parents=True, exist_ok=True)
    for f in range(FRAMES):
        t = spec['life']*f/(FRAMES-1)
        p = position(p0, v0, t)
        for g, q in zip(grains, p):
            g.location = q.tolist()
        s.render.filepath = str(frames_dir/f'{f:02d}.png')
        bpy.ops.render.render(write_still=True)
    return frames_dir


def write_spec(name, spec):
    flight = 2*spec['speed'][1]*math.sin(math.radians(spec['elev'][1]))/G
    reach = max(v**2*math.sin(2*math.radians(e))/G for v in spec['speed'] for e in spec['elev'])
    md = f"""# {name}

Used for: {spec['use']}.

| Parameter | Value |
|---|---|
| Gravity | (0, -{G}, 0) m/s² in Godot (lunar; no drag, no damping) |
| Grains | {spec['n']} per burst (one-shot) |
| Lifetime | {spec['life']} s (longest flight here {flight:.2f} s) |
| Launch speed | {spec['speed'][0]}–{spec['speed'][1]} m/s |
| Launch elevation | {spec['elev'][0]}–{spec['elev'][1]}° above the ground |
| Direction | azimuth {spec['az'][0]}° ± {spec['az'][1]}° in the effect's local frame (0° = forward) |
| Grain size | {spec['size'][0]*1000:.0f}–{spec['size'][1]*1000:.0f} mm |
| Spawn | disc of radius {spec['origin_r']} m on the ground |
| Max reach | {reach:.1f} m |
| Flipbook | `assets/vfx/{name}_4x4.png`, 4×4 frames of {FRAME_PX} px, {FRAMES} frames over the lifetime, side view, transparent; grains drawn {DRAW_SCALE:g}× size for readability |

Godot (Compatibility renderer): `CPUParticles3D`, one_shot, explosiveness 1, `gravity = Vector3(0, -{G}, 0)`,
`damping = 0`, initial velocity {spec['speed'][0]}–{spec['speed'][1]}, spread from the elevation/azimuth ranges above,
quad mesh with the grain colour (or the flipbook as a single billboard for distant/cheap use).
Grains must stop on landing (no bounce, no drift): use a short `lifetime` after landing or a ground collision.
Preliminary values; tune in the game.
"""
    (FX_DIR/f'{name}.md').write_text(md, encoding='utf-8')


def build_meshes():
    C.new_scene()
    cyan = C.mat('scanner_cyan', emission=C.PALETTE['scanner_cyan'], strength=4.0)
    # scanner beam: open cone, apex at origin, 1 m toward Blender -Y (= Godot +Z, the scanner's front)
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=False, segments=20, radius1=0.0, radius2=0.05, depth=1.0)
    bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=__import__('mathutils').Matrix.Rotation(math.radians(90), 3, 'X'))
    bmesh.ops.translate(bm, verts=bm.verts, vec=(0, -0.5, 0))
    beam = C.mesh_object('ScannerBeam', bm, cyan, smooth=True)
    # reticle: ring of radius 1 with four ticks, facing Godot +Z
    bm = bmesh.new()
    seg = 64
    inner, outer = [], []
    for i in range(seg):
        a = 2*math.pi*i/seg
        inner.append(bm.verts.new((0.94*math.cos(a), 0, 0.94*math.sin(a))))
        outer.append(bm.verts.new((1.0*math.cos(a), 0, 1.0*math.sin(a))))
    for i in range(seg):
        bm.faces.new((inner[i], outer[i], outer[(i+1) % seg], inner[(i+1) % seg]))
    for a in (0, 90, 180, 270):
        r = math.radians(a)
        c, s_ = math.cos(r), math.sin(r)
        q = [bm.verts.new((x*c-z*s_, 0, x*s_+z*c)) for x, z in ((1.05, -.03), (1.3, -.03), (1.3, .03), (1.05, .03))]
        bm.faces.new(q)
    reticle = C.mesh_object('Reticle', bm, cyan, smooth=False)
    # beacon pulse: flat ring on the ground, radius 1
    bm = bmesh.new()
    inner, outer = [], []
    for i in range(seg):
        a = 2*math.pi*i/seg
        inner.append(bm.verts.new((0.9*math.cos(a), 0.9*math.sin(a), 0.01)))
        outer.append(bm.verts.new((1.0*math.cos(a), 1.0*math.sin(a), 0.01)))
    for i in range(seg):
        bm.faces.new((inner[i], outer[i], outer[(i+1) % seg], inner[(i+1) % seg]))
    pulse = C.mesh_object('BeaconPulse', bm, cyan, smooth=False)
    C.export_glb('vfx_meshes', [beam, reticle, pulse], animations=False)
    C.save_blend('vfx')
    for name, use in (('scanner_beam', 'ScannerBeam: scale z to the scan range, fade alpha with distance; additive, unshaded'),
                      ('reticle', 'Reticle: place on the scanned point facing the camera; scale with distance'),
                      ('beacon_pulse', 'BeaconPulse: every 2 s scale 0.2→3 m over 1.2 s while alpha 1→0, synced to pulse_idle')):
        (FX_DIR/f'{name}.md').write_text(f'# {name}\n\nMesh in `assets/models/vfx_meshes.glb`. {use}.\n'
                                         'Material: scanner cyan (0.20, 0.92, 0.95), emission; in Godot use an unshaded '
                                         'additive StandardMaterial3D (Compatibility renderer safe). Preliminary.\n',
                                         encoding='utf-8')
    return C.triangles([beam, reticle, pulse])


def main():
    FX_DIR.mkdir(parents=True, exist_ok=True)
    out = {}
    for i, (name, spec) in enumerate(EFFECTS.items()):
        render_effect(name, spec, seed=1000+i)
        write_spec(name, spec)
        out[name] = str(FX_DIR/'frames'/name)
    out['mesh_tris'] = build_meshes()
    (FX_DIR/'effects.json').write_text(json.dumps({k: {kk: vv for kk, vv in v.items()} for k, v in EFFECTS.items()}, indent=1))
    return out


result = main()
