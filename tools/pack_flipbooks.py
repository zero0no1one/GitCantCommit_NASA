"""Pack the VFX frames rendered by blender/scripts/build_vfx.py into 4x4 sprite sheets, and draw the visor glint.

Run from the repo root after build_vfx.py: python tools/pack_flipbooks.py   (needs Pillow and numpy)
Outputs: assets/vfx/<effect>_4x4.png (512 px, frame order left-to-right, top-to-bottom) and assets/vfx/visor_glint.png
(256 px: soft core with four thin spikes, additive; shown when the Sun is near the view centre in first person).
"""
from pathlib import Path
import numpy as np
from PIL import Image

REPO = Path(__file__).resolve().parents[1]
FRAMES = REPO/'blender'/'vfx'/'frames'
OUT = REPO/'assets'/'vfx'


def pack(effect_dir, cols=4, rows=4):
    files = sorted(effect_dir.glob('*.png'))
    if len(files) != cols*rows:
        raise SystemExit(f'{effect_dir.name}: expected {cols*rows} frames, found {len(files)}')
    w, h = Image.open(files[0]).size
    sheet = Image.new('RGBA', (cols*w, rows*h), (0, 0, 0, 0))
    for i, f in enumerate(files):
        sheet.paste(Image.open(f).convert('RGBA'), ((i % cols)*w, (i//cols)*h))
    path = OUT/f'{effect_dir.name}_{cols}x{rows}.png'
    sheet.save(path)
    return path


def glint(size=256):
    y, x = np.mgrid[-1:1:size*1j, -1:1:size*1j]
    r = np.hypot(x, y)
    core = np.exp(-(r/0.08)**2)+0.35*np.exp(-(r/0.30)**2)
    spikes = np.exp(-(np.abs(x)/0.012)**2)*np.exp(-(np.abs(y)/0.9)**2)+np.exp(-(np.abs(y)/0.012)**2)*np.exp(-(np.abs(x)/0.9)**2)
    a = np.clip(core+0.6*spikes, 0, 1)
    img = np.zeros((size, size, 4))
    img[..., :3] = 1.0
    img[..., 3] = a
    path = OUT/'visor_glint.png'
    Image.fromarray((img*255).astype('uint8'), 'RGBA').save(path)
    return path


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for d in sorted(p for p in FRAMES.iterdir() if p.is_dir()):
        print(pack(d))
    print(glint())


if __name__ == '__main__':
    main()
