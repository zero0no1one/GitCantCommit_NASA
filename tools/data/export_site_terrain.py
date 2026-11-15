"""Sample the terrain around each mission site into a local grid for Blender (blender/scripts/build_site_terrain.py).

Local frame: x = east, y = north, z = up, metres, origin on the ground at the site. Heights include the drop of the
lunar sphere (d²/2R), so the grid is the true surface seen from the site. Heights come from the same terrain layers
the skyline uses (sunline_data.terrain.height): 80 m PGDA patch at the pole, 118 m LOLA patch at Tranquility.
Output: blender/data/terrain_<site>.json  (run: python export_site_terrain.py)
"""
import json
import numpy as np
from scipy.ndimage import gaussian_filter
from sunline_data import terrain
from sunline_data.constants import MISSION_JSON, REPO, MOON_RADIUS_M

HALF_M = 600.0      # grid half-width (the playable surface; distant terrain is the skyline ring)
STEP_M = 20.0
SMOOTH_CELLS = 1.0     # Gaussian sigma in grid cells (20 m), display smoothing only


def main():
    m = json.loads(MISSION_JSON.read_text())
    out_dir = REPO/'blender'/'data'
    out_dir.mkdir(parents=True, exist_ok=True)
    xs = np.arange(-HALF_M, HALF_M+STEP_M/2, STEP_M)
    X, Y = np.meshgrid(xs, xs)                       # X east, Y north
    dist = np.hypot(X, Y)
    az = np.degrees(np.arctan2(X, Y)) % 360
    for s in m['sites']:
        lat, lon = s['lat'], s['lon']
        la, lo = terrain._destination(lat, lon, az, np.maximum(dist, 1e-6))
        h = terrain.height(la, lo)
        h0 = float(terrain.height(lat, lon))
        z = (h-h0)-dist**2/(2*MOON_RADIUS_M)        # relative height, curvature included
        # Bilinear sampling of the 80 m DEM makes flat facets whose edges read as straight lines on a near ridge
        # silhouette; a light 20 m Gaussian removes the facets without changing the landform. Display only: the
        # scoring skyline uses the raw DEM, and Blender still clamps this ground below that skyline.
        z = gaussian_filter(z, SMOOTH_CELLS, mode='nearest')
        z -= z[len(xs)//2, len(xs)//2]                 # keep the site itself at height 0
        path = out_dir/f"terrain_{s['id']}.json"
        path.write_text(json.dumps({
            'site': s['id'], 'name': s['name'], 'step_m': STEP_M, 'size': len(xs), 'half_m': HALF_M,
            'frame': 'x east, y north, z up, metres, origin at the site on the ground',
            'source': s['terrain_source'], 'z': np.round(z, 2).tolist(),
            'panel_height_m': s['panel_height_m'],
            'skyline_step_deg': s['skyline']['azimuth_step_deg'], 'skyline_deg': s['skyline']['elevation_deg']}))
        print(f"{path.name}: {len(xs)}x{len(xs)}, relief {z.min():.1f}..{z.max():.1f} m")


if __name__ == '__main__':
    main()
