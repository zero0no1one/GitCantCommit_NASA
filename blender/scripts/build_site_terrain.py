"""Sunline site terrain: the walkable ground around each site plus a distant skyline ring, from the mission data.

Inputs: blender/data/terrain_<site>.json (tools/data/export_site_terrain.py), which carries the local height grid and
the SAME 0.1° skyline that scores the mission (data/mission.json).
Frame: Blender +X = east, +Y = north, +Z = up; origin on the ground at the site. After glTF export: Godot +X east,
-Z north, +Y up.

- SkylineRing: a wall RING_RADIUS_M away whose top edge sits, for each 0.1° of azimuth, exactly at the scoring
  skyline elevation seen from the panel height (1.0 m above the origin). What the player sees on the horizon is the
  skyline the game scores against.
- Terrain: the 1.2 km x 1.2 km local surface. Any vertex that would rise above the skyline (as seen from the panel)
  is lowered to 0.05° below it, so near ground can never hide or add to the scored skyline. Small craters and
  roughness are added for readability and are ILLUSTRATIVE (seeded, < 0.6 m), not data.
Outputs: blender/terrain_<site>.blend, assets/models/terrain_<site>.glb
"""
import json
import math
import zlib
import sys
from pathlib import Path
import bpy
import bmesh
import numpy as np
from mathutils import Vector

sys.path.insert(0, str(Path(r'C:\dev\godot\new-game-project\blender\scripts')))
import importlib
import sunline_common as C
importlib.reload(C)

RING_RADIUS_M = 1500.0
RING_DEPTH_M = 400.0
CLEARANCE_DEG = 0.05
TILE_M = 2.0


def skyline_at(sky, step, az):
    n = len(sky)
    x = (np.asarray(az) % 360)/step
    i0 = np.floor(x).astype(int) % n
    f = x-np.floor(x)
    return sky[i0]*(1-f)+sky[(i0+1) % n]*f


def illustrative_detail(X, Y, seed):
    rng = np.random.default_rng(seed)
    z = np.zeros_like(X)
    for _ in range(40):                                   # small bowl craters 4–30 m across
        cx, cy = rng.uniform(-560, 560, 2)
        r = rng.uniform(2, 15)
        d = np.hypot(X-cx, Y-cy)/r
        z += np.where(d < 1, -0.12*r*(1-d**2), np.where(d < 1.4, .03*r*(1.4-d)/.4, 0))
    z += .15*np.sin(X/37+1.3)*np.sin(Y/29+.4)+.08*np.sin(X/11)*np.cos(Y/13)
    return np.clip(z, -0.6, 0.6)

COARSE_STEP_DEG = 0.5      # azimuth step of the slope rings (the crest ring keeps the full 0.1° skyline)
HILL_RINGS = 14
HILL_INNER_M = 540.0       # hills start under the walkable ground...
GROUND_R = 590.0           # ...which ends on this circle (no straight square edge on the horizon)
UNDER_M = 0.15             # hills sit this far below the ground where they overlap (no z-fighting, step invisible)
SMOOTH_DEG = 1.0           # skyline smoothing used only for shading normals


def grid_height(X, Y, Z, step, half, x, y):
    """Bilinear height of the local grid at (x, y), clamped to the grid."""
    n = Z.shape[0]
    c = min(max((x+half)/step, 0), n-1.001)
    r = min(max((y+half)/step, 0), n-1.001)
    c0, r0 = int(c), int(r)
    fc, fr = c-c0, r-r0
    return (Z[r0, c0]*(1-fc)*(1-fr)+Z[r0, c0+1]*fc*(1-fr)+Z[r0+1, c0]*(1-fc)*fr+Z[r0+1, c0+1]*fc*fr)


def far_hills(sky, sstep, eye, X, Y, Z, step, half, material_, seed):
    """Sloped hills from the walkable ground's circular edge to a crest RING_RADIUS_M away.

    References (Apollo 15 AS15-87-11748 Hadley Delta, AS15-90-12187 Mount Hadley): smooth rounded mountains with
    layered foothills, rising from the plain without a hard edge, crisp silhouette against black sky.
    The crest sits EXACTLY on the scoring skyline (0.1° azimuth). Every slope vertex is held at least CLEARANCE_DEG
    below the skyline as seen from the panel, so the visible horizon is the scoring skyline and nothing else.
    Shading normals come from the same height function evaluated on a slightly smoothed skyline, so lighting
    follows the hill shape rather than the triangle layout (no banding from the 0.5°-to-0.1° stitch).
    """
    rng = np.random.default_rng(seed)
    phase = rng.uniform(0, 2*np.pi, 4)
    win = int(round(SMOOTH_DEG/sstep))
    kernel = np.ones(2*win+1)/(2*win+1)
    sky_s = np.convolve(np.concatenate([sky[-win:], sky, sky[:win]]), kernel, mode='valid')

    def height(d, az, skyline):
        a = math.radians(az)
        x, y = d*math.sin(a), d*math.cos(a)
        el = float(skyline_at(skyline, sstep, az))
        crest = eye+RING_RADIUS_M*math.tan(math.radians(el))
        sight = eye+d*math.tan(math.radians(el-CLEARANCE_DEG))
        if d <= GROUND_R:
            return min(grid_height(X, Y, Z, step, half, x, y)-UNDER_M, sight)
        edge = min(grid_height(X, Y, Z, step, half, GROUND_R*math.sin(a), GROUND_R*math.cos(a))-UNDER_M, crest)
        u = (d-GROUND_R)/(RING_RADIUS_M-GROUND_R)
        h = edge+(crest-edge)*u**1.7                                         # rises toward the mountains
        h += 0.03*(d-GROUND_R)*(0.6+0.4*math.sin(3*a+phase[0]))*math.sin(math.pi*u*2.0+phase[1])             * (0.5+0.5*math.sin(7*a+phase[2]))*(1-u)                         # foothill ridges, fading at the crest
        return min(h, sight)

    def normal(d, az):
        dd, da = 6.0, 0.4
        a = math.radians(az)
        dh_dd = (height(min(d+dd, RING_RADIUS_M), az, sky_s)-height(d-dd, az, sky_s))/(min(d+dd, RING_RADIUS_M)-(d-dd))
        dh_da = (height(d, az+da, sky_s)-height(d, az-da, sky_s))/math.radians(2*da)
        r_hat = Vector((math.sin(a), math.cos(a), 0))
        t_hat = Vector((math.cos(a), -math.sin(a), 0))
        g = r_hat*dh_dd+t_hat*(dh_da/max(d, 1.0))
        return Vector((-g.x, -g.y, 1.0)).normalized()

    bm = bmesh.new()
    uv = bm.loops.layers.uv.new('UVMap')
    normals = []
    n_c = int(round(360/COARSE_STEP_DEG))
    ratio = int(round(COARSE_STEP_DEG/sstep))
    t = np.linspace(0, 1, HILL_RINGS+1)[:-1]
    radii = HILL_INNER_M+(RING_RADIUS_M-HILL_INNER_M)*(1-(1-t)**1.6)       # denser toward the crest
    rings = []
    for d in radii:
        ring = []
        for j in range(n_c):
            az = j*COARSE_STEP_DEG
            a = math.radians(az)
            ring.append(bm.verts.new((d*math.sin(a), d*math.cos(a), height(d, az, sky))))
            normals.append(normal(d, az))
        rings.append(ring)
    crest_ring = []
    for i in range(len(sky)):
        az = i*sstep
        a = math.radians(az)
        crest_ring.append(bm.verts.new((RING_RADIUS_M*math.sin(a), RING_RADIUS_M*math.cos(a),
                                        eye+RING_RADIUS_M*math.tan(math.radians(float(sky[i]))))))
        normals.append(normal(RING_RADIUS_M, az))
    def face(vs):
        f = bm.faces.new(vs)
        for loop in f.loops:
            loop[uv].uv = (loop.vert.co.x/TILE_M, loop.vert.co.y/TILE_M)    # same 2 m tile as the ground
    for k in range(len(rings)-1):
        for j in range(n_c):
            jj = (j+1) % n_c
            face((rings[k][j], rings[k+1][j], rings[k+1][jj], rings[k][jj]))
    last = rings[-1]
    for j in range(n_c):                                                    # stitch 0.5° ring to the 0.1° crest
        jj = (j+1) % n_c
        for i in range(ratio):
            face((last[j], crest_ring[(j*ratio+i) % len(sky)], crest_ring[(j*ratio+i+1) % len(sky)]))
        face((last[j], crest_ring[(jj*ratio) % len(sky)], last[jj]))
    bm.normal_update()
    if sum(f.normal.z for f in bm.faces) < 0:                               # the slope must face up
        bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
    ob = C.mesh_object('SkylineRing', bm, material_, smooth=True)
    ob.data.normals_split_custom_set_from_vertices([tuple(n) for n in normals])
    return ob


def build(site_id):
    d = json.loads((C.BLEND_DIR/'data'/f'terrain_{site_id}.json').read_text())
    n, step, half = d['size'], d['step_m'], d['half_m']
    sky = np.array(d['skyline_deg'], float)
    sstep = d['skyline_step_deg']
    eye = d['panel_height_m']
    xs = np.arange(n)*step-half
    X, Y = np.meshgrid(xs, xs)                            # rows = north (y), cols = east (x)
    Z = np.array(d['z'], float)+illustrative_detail(X, Y, seed=zlib.crc32(site_id.encode()))   # stable across sessions (hash() is salted)
    dist = np.hypot(X, Y)
    az = np.degrees(np.arctan2(X, Y)) % 360
    limit = np.where(dist > 1, eye+dist*np.tan(np.radians(skyline_at(sky, sstep, az)-CLEARANCE_DEG)), np.inf)
    clamped = int(np.count_nonzero(Z > limit))
    Z = np.minimum(Z, limit)
    Z[n//2, n//2] = 0.0                                   # the site itself stays on the ground

    regolith = C.texture_material('regolith', (0.36, 0.35, 0.34, 1), albedo='regolith_albedo.png',
                                  normal='regolith_normal.png', roughness=0.97)   # 2 m tile, tools/make_surface_textures.py

    bm = bmesh.new()
    verts = [[bm.verts.new((float(X[r, c]), float(Y[r, c]), float(Z[r, c]))) for c in range(n)] for r in range(n)]
    uv = bm.loops.layers.uv.new('UVMap')
    for r in range(n-1):
        for c in range(n-1):
            if math.hypot((X[r, c]+X[r+1, c+1])/2, (Y[r, c]+Y[r+1, c+1])/2) > GROUND_R:
                continue                                  # round ground edge; the hills take over beyond it
            f = bm.faces.new((verts[r][c], verts[r][c+1], verts[r+1][c+1], verts[r+1][c]))
            for loop in f.loops:
                loop[uv].uv = (loop.vert.co.x/TILE_M, loop.vert.co.y/TILE_M)          # regolith tile repeats every 2 m
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
    terrain = C.mesh_object('Terrain', bm, regolith)

    ring = far_hills(sky, sstep, eye, X, Y, Z, step, half, regolith, zlib.crc32(site_id.encode()))

    C.export_glb(f'terrain_{site_id}', [terrain, ring], animations=False)
    C.save_blend(f'terrain_{site_id}')
    return {'site': site_id, 'clamped_vertices': clamped, 'terrain_tris': C.triangles([terrain]),
            'ring_tris': C.triangles([ring]), 'ring_radius_m': RING_RADIUS_M,
            'relief_m': [round(float(Z.min()), 1), round(float(Z.max()), 1)],
            'skyline_max': [round(float(sky.max()), 3), round(float(np.argmax(sky)*sstep), 1)]}


def main():
    out = []
    for f in sorted((C.BLEND_DIR/'data').glob('terrain_*.json')):
        C.new_scene()
        out.append(build(f.stem[len('terrain_'):]))
    return out


result = main()
