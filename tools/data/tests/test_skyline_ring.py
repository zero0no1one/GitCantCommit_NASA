"""The exported skyline ring (assets/models/terrain_<site>.glb) must match the scoring skyline in data/mission.json.

Reads the GLB directly (no extra packages): finds the `SkylineRing` mesh, takes the top vertex of every azimuth
column, converts it to an elevation angle seen from the panel (1.0 m above the origin) and compares it with the
bundled skyline. Also checks that no Terrain vertex rises above the skyline as seen from the panel.
glTF frame: +X east, +Y up, -Z north.
"""
import json
import struct
import sys
import unittest
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sunline_data.constants import MISSION_JSON, REPO          # noqa: E402

MODELS = REPO/'assets'/'models'
TOL_DEG = 0.05


def read_glb(path):
    data = path.read_bytes()
    _, _, length = struct.unpack_from('<III', data, 0)
    jlen, _ = struct.unpack_from('<II', data, 12)
    gltf = json.loads(data[20:20+jlen])
    blen, _ = struct.unpack_from('<II', data, 20+jlen)
    binary = data[28+jlen:28+jlen+blen]
    return gltf, binary


def positions(gltf, binary, node_name):
    node = next(n for n in gltf['nodes'] if n.get('name') == node_name)
    mesh = gltf['meshes'][node['mesh']]
    out = []
    for prim in mesh['primitives']:
        acc = gltf['accessors'][prim['attributes']['POSITION']]
        view = gltf['bufferViews'][acc['bufferView']]
        start = view.get('byteOffset', 0)+acc.get('byteOffset', 0)
        stride = view.get('byteStride', 12)
        arr = np.frombuffer(binary, dtype=np.uint8, count=stride*acc['count'], offset=start).reshape(acc['count'], stride)
        out.append(arr[:, :12].copy().view('<f4').reshape(-1, 3))
    p = np.vstack(out).astype(float)
    t = np.array(node.get('translation', [0, 0, 0]))
    return p+t


def skyline_at(sky, step, az):
    n = len(sky)
    x = (np.asarray(az) % 360)/step
    i0 = np.floor(x).astype(int) % n
    f = x-np.floor(x)
    return sky[i0]*(1-f)+sky[(i0+1) % n]*f


class SkylineRing(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = json.loads(MISSION_JSON.read_text())

    def test_ring_matches_scoring_skyline(self):
        for s in self.m['sites']:
            path = MODELS/f"terrain_{s['id']}.glb"
            if not path.exists():
                self.skipTest(f'{path.name} not exported yet')
            gltf, binary = read_glb(path)
            p = positions(gltf, binary, 'SkylineRing')
            eye = s['panel_height_m']
            az = np.round(np.degrees(np.arctan2(p[:, 0], -p[:, 2])) % 360, 3)
            sky = np.array(s['skyline']['elevation_deg'])
            step = s['skyline']['azimuth_step_deg']
            # The ring is now a sloped band (hills) whose crest is the skyline. For each azimuth the HIGHEST VIEWING
            # ANGLE must equal the skyline (not the highest point: where the skyline dips below horizontal, nearer
            # slope points sit higher in metres while still lower in angle).
            el_all = np.degrees(np.arctan2(p[:, 1]-eye, np.hypot(p[:, 0], p[:, 2])))
            worst = 0.0
            for a in np.unique(az):
                el = float(el_all[az == a].max())
                worst = max(worst, abs(el-float(skyline_at(sky, step, a))))
            above = el_all-skyline_at(sky, step, az)
            self.assertLessEqual(float(above.max()), 1e-3, f"{s['id']}: a hill vertex rises above the skyline")
            self.assertLess(worst, TOL_DEG, f"{s['id']}: ring differs from skyline by {worst:.4f}°")

    def test_terrain_never_above_skyline(self):
        for s in self.m['sites']:
            path = MODELS/f"terrain_{s['id']}.glb"
            if not path.exists():
                self.skipTest(f'{path.name} not exported yet')
            gltf, binary = read_glb(path)
            p = positions(gltf, binary, 'Terrain')
            eye = s['panel_height_m']
            d = np.hypot(p[:, 0], p[:, 2])
            far = d > 1
            el = np.degrees(np.arctan2(p[far, 1]-eye, d[far]))
            az = np.degrees(np.arctan2(p[far, 0], -p[far, 2])) % 360
            sky = skyline_at(np.array(s['skyline']['elevation_deg']), s['skyline']['azimuth_step_deg'], az)
            self.assertLessEqual(float(np.max(el-sky)), 1e-3, f"{s['id']}: terrain pokes above the skyline")


if __name__ == '__main__':
    unittest.main()
