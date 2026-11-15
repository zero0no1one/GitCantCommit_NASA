"""Tileable surface textures for Sunline: regolith ground (albedo + normal) and a rock detail normal map.

Based on the Apollo references viewed for the rock set (NASA AS17-146-22294, AS16-107-17573): fine grey granular
regolith with a faint brown cast, cohesive clods, and scattered angular pebbles 1–5 cm across; rock surfaces are
granular and pitted. Albedo only (no baked lighting, no shadows) so the game's Sun does the shading.

Everything is periodic (FFT-filtered noise, pebbles stamped with wrap-around), so the tiles repeat seamlessly.
Regolith tile = 2 m x 2 m at 1024 px (~2 mm per pixel). Run: python tools/make_surface_textures.py
Outputs: assets/textures/regolith_albedo.png, regolith_normal.png, rock_detail_normal.png
"""
from pathlib import Path
import numpy as np
from PIL import Image

OUT = Path(__file__).resolve().parents[1]/'assets'/'textures'
N = 1024
TILE_M = 2.0


def fbm(n, seed, octaves, falloff=1.0):
    """Periodic fractal noise from filtered white noise; octaves = list of (wavelength_px, weight)."""
    rng = np.random.default_rng(seed)
    f = np.fft.fftfreq(n)
    k = np.sqrt(f[None, :]**2+f[:, None]**2)
    out = np.zeros((n, n))
    for wl, w in octaves:
        white = np.fft.fft2(rng.normal(size=(n, n)))
        band = np.exp(-((k*wl-1.0)**2)/0.5) if wl > 0 else 1.0
        layer = np.real(np.fft.ifft2(white*band))
        layer /= layer.std()+1e-9
        out += w*layer
    return out/np.abs(out).max()


def stamp_pebbles(height, albedo, rng, count, r_px, h_scale, tone):
    n = height.shape[0]
    yy, xx = np.mgrid[-r_px[1]*2:r_px[1]*2+1, -r_px[1]*2:r_px[1]*2+1]
    for _ in range(count):
        r = rng.uniform(*r_px)
        cx, cy = rng.integers(0, n, 2)
        ang = rng.uniform(0, np.pi)
        ex = rng.uniform(0.6, 1.0)
        xr = xx*np.cos(ang)+yy*np.sin(ang)
        yr = (-xx*np.sin(ang)+yy*np.cos(ang))/ex
        # irregular angular pebble: radius modulated by a few random lobes, then quantised into facets
        theta = np.arctan2(yr, xr)
        lobes = sum(rng.uniform(0.08, 0.22)*np.cos(k*theta+rng.uniform(0, 2*np.pi)) for k in (2, 3, 5))
        facets = rng.integers(5, 9)
        theta_q = np.round(theta/(2*np.pi/facets))*(2*np.pi/facets)
        rad = np.hypot(xr, yr)*np.cos(theta-theta_q)      # flat sides between facet corners
        d = rad/(1+lobes)
        bump = np.clip(1-d/r, 0, None)
        h = np.minimum(bump*3, 1.0)*h_scale*r
        rows = (np.arange(yy.shape[0])+cy-yy.shape[0]//2) % n
        cols = (np.arange(xx.shape[1])+cx-xx.shape[1]//2) % n
        sub = np.ix_(rows, cols)
        height[sub] = np.maximum(height[sub], h)
        a = albedo[sub]
        albedo[sub] = np.where(bump > 0, tone+rng.uniform(-0.03, 0.03), a)


def normal_map(height, strength):
    dx = (np.roll(height, -1, 1)-np.roll(height, 1, 1))*0.5*strength
    dy = (np.roll(height, -1, 0)-np.roll(height, 1, 0))*0.5*strength
    nrm = np.stack([-dx, dy, np.ones_like(dx)], -1)          # OpenGL convention (+Y up), as Godot expects
    nrm /= np.linalg.norm(nrm, axis=-1, keepdims=True)
    return ((nrm*0.5+0.5)*255).astype(np.uint8)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(7)
    px_per_cm = N/(TILE_M*100)
    # height: fine grain + clods + gentle undulation (all periodic)
    h = 0.45*fbm(N, 1, [(3, 1.0), (6, 0.6)])+0.35*fbm(N, 2, [(22, 1.0), (55, 0.4)])+0.3*fbm(N, 3, [(300, 1.0)])   # grains > clods > undulation
    h = (h-h.min())/(h.max()-h.min())*6.0                     # in pixel units of height for the normal map
    tone = (0.36+0.022*fbm(N, 4, [(250, 1.0), (60, 0.4)])    # large patches
            + 0.045*fbm(N, 8, [(2, 1.0), (3, 0.6)])            # granular speckle seen in the Apollo close-ups
            + 0.02*fbm(N, 9, [(14, 1.0)]))                     # clods
    albedo = tone.copy()
    stamp_pebbles(h, albedo, rng, 260, (0.5*px_per_cm, 1.2*px_per_cm), 1.4, 0.40)     # 1–2.4 cm grains
    stamp_pebbles(h, albedo, rng, 40, (1.5*px_per_cm, 2.5*px_per_cm), 1.2, 0.42)      # 3–5 cm pebbles
    rgb = np.stack([albedo*1.02, albedo*1.0, albedo*0.96], -1)                          # faint brown cast
    rgb = np.clip(rgb+0.015*fbm(N, 5, [(2, 1.0)])[..., None], 0, 1)
    Image.fromarray((rgb*255).astype(np.uint8)).save(OUT/'regolith_albedo.png')
    Image.fromarray(normal_map(h, 1.0)).save(OUT/'regolith_normal.png')
    # rock detail: granular pits and fine fractures, 512 px
    r = 0.5*fbm(512, 11, [(2, 1.0), (4, 0.7)])+0.5*fbm(512, 12, [(18, 1.0)])
    pits = fbm(512, 13, [(8, 1.0)])
    r -= 0.8*np.clip(pits-0.55, 0, None)
    Image.fromarray(normal_map(r*4.0, 1.0)).save(OUT/'rock_detail_normal.png')
    # suit fabric: fine weave plus soft wrinkles stretched along the limb (references: Apollo 11 A7L and AxEMU
    # cover close-ups show a wrinkled outer layer with a visible weave), 512 px, ~25 cm tile on the suit
    n = 512
    y, x = np.mgrid[0:n, 0:n]
    weave = 0.5*np.sin(2*np.pi*x/4)*np.sin(2*np.pi*y/4)
    wr = fbm(n, 21, [(40, 1.0), (16, 0.5)])
    wr_aniso = 0.6*np.real(np.fft.ifft2(np.fft.fft2(wr)*np.exp(-(np.fft.fftfreq(n)[:, None]*30)**2)))
    fabric = 0.25*weave+3.0*wr_aniso/np.abs(wr_aniso).max()
    Image.fromarray(normal_map(fabric, 1.0)).save(OUT/'suit_fabric_normal.png')
    # crinkled MLI foil (VIPER references: creased, faceted foil with sharp highlights): ridged noise gives creases
    m = 512
    c1 = fbm(m, 31, [(150, 1.0), (70, 0.45)])          # large crumple facets
    c2 = fbm(m, 32, [(30, 1.0)])                         # secondary creases
    crinkle = (1-np.abs(c1))**6+0.25*(1-np.abs(c2))**5  # sharp creases, smooth facets in between
    Image.fromarray(normal_map(crinkle*14.0, 1.0)).save(OUT/'mli_crinkle_normal.png')
    # Earth's atmospheric limb (references: Apollo 8 AS08-14-2383 Earthrise, Artemis II art002e021278): a thin pale-
    # blue rim ~1-2% of Earth's radius, brightest right at the limb. Drawn on a quad of half-width 1.04 Earth radii,
    # so radius 1.0 in Earth units sits at 1/1.04 of the half-width. Premultiplied-style RGBA, additive in Godot.
    q = 512
    yy, xx = np.mgrid[-1:1:q*1j, -1:1:q*1j]
    r = np.hypot(xx, yy)*1.04
    inner = np.clip((r-0.965)/0.04, 0, 1)**1.5            # soft fade-in over the outer 4% of the disc
    outer = np.exp(-np.clip(r-1.0, 0, None)/0.014)         # haze falls off over ~1-3% beyond the limb
    alpha = 0.75*np.clip(inner*outer, 0, 1)*np.clip((1.04-r)/0.01, 0, 1)
    limb = np.zeros((q, q, 4))
    limb[..., 0], limb[..., 1], limb[..., 2] = 0.62, 0.80, 1.0
    limb[..., 3] = alpha
    Image.fromarray((limb*255).astype(np.uint8), 'RGBA').save(OUT/'earth_limb.png')
    for f in sorted(OUT.glob('*.png')):
        print(f.name, Image.open(f).size, f'{f.stat().st_size/1e3:.0f} kB')


if __name__ == '__main__':
    main()
