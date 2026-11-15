"""Generate AI-sculpted meshes with the local Hunyuan3D-2 server (shape only) and save the raw GLBs.

Server: C:\\dev\\toolchains\\Hunyuan3D-2\\sunline_shape_server.py on http://127.0.0.1:8080 (Tencent Hunyuan3D-2mini
turbo shape model; Tencent Hunyuan 3D 2.0 Community License — not for use in the EU, UK or South Korea).
Inputs: blender/references/hy_input_<asset>.png (renders of the procedural models, or crops of the Apollo photos).
Outputs: blender/hunyuan/raw/<asset>_s<seed>.glb plus a JSON log of the exact request parameters, so every sculpt is
reproducible. Run with the system Python:  python blender/scripts/hunyuan_generate.py astronaut rock ... [--seeds 1 2]
"""
import argparse
import base64
import json
import time
from pathlib import Path

import requests

REPO = Path(__file__).resolve().parents[2]
REFS = REPO/'blender'/'references'
RAW = REPO/'blender'/'hunyuan'/'raw'
URL = 'http://127.0.0.1:8080/generate'
DEFAULTS = dict(octree_resolution=256, num_inference_steps=5, guidance_scale=5.0, num_chunks=8000, face_count=0)


def generate(asset, seed, **over):
    params = dict(DEFAULTS, seed=seed, **over)
    image = (REFS/f'hy_input_{asset}.png').read_bytes()
    t0 = time.time()
    r = requests.post(URL, json=dict(params, image=base64.b64encode(image).decode()), timeout=1800)
    if r.status_code != 200:
        raise RuntimeError(f'{asset}: {r.status_code} {r.text[:300]}')
    RAW.mkdir(parents=True, exist_ok=True)
    out = RAW/f'{asset}_s{seed}.glb'
    out.write_bytes(r.content)
    log = dict(asset=asset, input=f'blender/references/hy_input_{asset}.png', seconds=round(time.time()-t0, 1),
               model='tencent/Hunyuan3D-2mini hunyuan3d-dit-v2-mini-turbo', **params)
    (RAW/f'{asset}_s{seed}.json').write_text(json.dumps(log, indent=1))
    return out, log


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('assets', nargs='+')
    ap.add_argument('--seeds', nargs='+', type=int, default=[1234])
    ap.add_argument('--octree', type=int, default=DEFAULTS['octree_resolution'])
    ap.add_argument('--steps', type=int, default=DEFAULTS['num_inference_steps'])
    a = ap.parse_args()
    for asset in a.assets:
        for seed in a.seeds:
            try:
                out, log = generate(asset, seed, octree_resolution=a.octree, num_inference_steps=a.steps)
                print(f'{asset} seed {seed}: {out.name} in {log["seconds"]} s, {out.stat().st_size/1e6:.1f} MB', flush=True)
            except Exception as e:
                print(f'{asset} seed {seed}: FAILED {e}', flush=True)
