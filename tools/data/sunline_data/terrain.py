"""Terrain height anywhere on the Moon and the skyline (horizon profile) seen from a point.

Adapted from Echo-Path's `echo_path/horizon.py`. Changes for Sunline:
- an extra 118 m (256 px/deg) LOLA patch around Tranquility Base (source/tranquility_ldem256.npz);
- configurable azimuth resolution (Sunline uses 0.1°, 3600 rays);
- the observer height is the rover's panel height (constants.PANEL_HEIGHT_M).

Heights are metres above the 1,737.4 km reference sphere in the Moon's mean-Earth/polar-axis (MEAN_ME) frame.
Sources, finest first: 80 m PGDA patches around the south-pole sites, the 118 m Tranquility patch, the 640 m
south polar mosaic (poleward of 79.5° S) and the global LDEM_4 map (about 7.6 km). Rays follow great circles from
100 m to 400 km with log spacing; the elevation angle to each sample uses exact sphere geometry, so curvature is
included (Sunline starts rays at 100 m; see DISTANCES_M). There is no atmosphere, so no refraction. Azimuth is a true compass bearing: 0° toward the north pole,
90° east, clockwise.
"""
from functools import lru_cache
import numpy as np
from scipy.ndimage import map_coordinates
from .constants import MOON_RADIUS_M, SOURCE, SKYLINE_STEP_DEG

# 100 m (just over one 80 m DEM pixel) to 400 km. Starting at 100 m instead of Echo-Path's 300 m matched NASA PGDA's
# average-illumination map better across the 13 polar sites (see VALIDATION.md).
DISTANCES_M = np.geomspace(100., 400_000., 340)


@lru_cache(maxsize=1)
def _global():
    z = np.fromfile(SOURCE/'ldem_4.img', '<i2').reshape(720, 1440).astype(np.float32)*.5
    return np.pad(np.concatenate([z[:, -1:], z, z[:, :1]], axis=1), ((1, 1), (0, 0)), mode='edge')


@lru_cache(maxsize=1)
def _polar():
    import rasterio
    with rasterio.open(SOURCE/'lola_south_pole_surround_640m.tif') as ds:
        z = ds.read(1, masked=True).astype(np.float32).filled(np.nan)*ds.scales[0]+ds.offsets[0]
        return z, ds.transform


@lru_cache(maxsize=1)
def _patches():
    with np.load(SOURCE/'site_patches_80m.npz') as f:
        return [(str(i), float(x), float(y), float(d), np.where(z == -32768, np.nan, z).astype(np.float32))
                for i, (x, y, d), z in zip(f['ids'], f['origins'], f['z'])]


@lru_cache(maxsize=1)
def _tranquility():
    path = SOURCE/'tranquility_ldem256.npz'
    if not path.exists():
        return None
    with np.load(path) as f:
        return float(f['north_lat']), float(f['west_lon']), float(f['ppd']), f['z'].astype(np.float32)


def _polar_xy(lat, lon):
    rho = 2*MOON_RADIUS_M*np.tan(np.radians(90+lat)/2)
    return rho*np.sin(np.radians(lon)), rho*np.cos(np.radians(lon))


def height(lat, lon):
    """Terrain height (m) above the reference sphere from the finest map covering each point."""
    lat, lon = np.broadcast_arrays(np.asarray(lat, float), np.asarray(lon, float))
    rows = (90-lat)*4-.5+1
    cols = (lon % 360)*4-.5+1
    z = map_coordinates(_global(), [rows.ravel(), cols.ravel()], order=1, mode='nearest').reshape(lat.shape)

    tq = _tranquility()
    if tq is not None:
        north, west, ppd, patch = tq
        r = (north-lat)*ppd
        c = (((lon-west+180) % 360)-180)*ppd
        inside = (r >= 0) & (c >= 0) & (r <= patch.shape[0]-1) & (c <= patch.shape[1]-1)
        if inside.any():
            fine = map_coordinates(patch, [r[inside], c[inside]], order=1, mode='nearest')
            z[inside] = np.where(np.isfinite(fine), fine, z[inside])

    south = lat < -79.5
    if south.any():
        polar, transform = _polar()
        x, y = _polar_xy(lat[south], lon[south])
        col, row = ~transform @ (x, y)
        fine = map_coordinates(polar, [np.asarray(row)-.5, np.asarray(col)-.5], order=1, mode='constant', cval=np.nan)
        best = np.where(np.isfinite(fine), fine, z[south])
        for _, sw_x, sw_y, step, patch in _patches():
            rp, cp = (y-sw_y)/step, (x-sw_x)/step
            inside = (rp >= 0) & (cp >= 0) & (rp <= patch.shape[0]-1) & (cp <= patch.shape[1]-1)
            if inside.any():
                sharp = map_coordinates(patch, [rp[inside], cp[inside]], order=1, mode='nearest')
                best[inside] = np.where(np.isfinite(sharp), sharp, best[inside])
        z[south] = best
    return z


def source_at(lat, lon):
    """Name of the finest terrain product used at a site, for the dataset's metadata."""
    if lat < -79.5:
        x, y = _polar_xy(np.array([lat]), np.array([lon]))
        for pid, sw_x, sw_y, step, patch in _patches():
            if 0 <= (y[0]-sw_y)/step <= patch.shape[0]-1 and 0 <= (x[0]-sw_x)/step <= patch.shape[1]-1:
                return f'PGDA LOLA 80 m south polar mosaic (patch {pid}), then 640 m mosaic, then LDEM_4'
        return 'PGDA LOLA 640 m south polar mosaic, then LDEM_4'
    tq = _tranquility()
    if tq is not None:
        north, west, ppd, patch = tq
        if 0 <= (north-lat)*ppd <= patch.shape[0]-1 and 0 <= (lon-west)*ppd <= patch.shape[1]-1:
            return 'LOLA LDEM 118 m (256 px/deg) patch, then LDEM_4 (7.6 km)'
    return 'LOLA LDEM_4 (7.6 km)'


def _destination(lat, lon, azimuth, distance):
    la, lo, az = np.radians(lat), np.radians(lon), np.radians(azimuth)
    d = distance/MOON_RADIUS_M
    la2 = np.arcsin(np.clip(np.sin(la)*np.cos(d)+np.cos(la)*np.sin(d)*np.cos(az), -1, 1))
    lo2 = lo+np.arctan2(np.sin(az)*np.sin(d)*np.cos(la), np.cos(d)-np.sin(la)*np.sin(la2))
    return np.degrees(la2), np.degrees(lo2)


def azimuths(step_deg=SKYLINE_STEP_DEG):
    return np.arange(0., 360., step_deg)


def horizon_profile(lat, lon, eye_m, step_deg=SKYLINE_STEP_DEG, offset_m=0., chunk=360):
    """Skyline elevation (degrees) toward each azimuth in azimuths(step_deg), seen from eye_m above the ground."""
    az_all = azimuths(step_deg)
    r0 = MOON_RADIUS_M+float(height(lat, lon))+eye_m
    gamma = DISTANCES_M/MOON_RADIUS_M
    out = np.empty(az_all.size)
    for i in range(0, az_all.size, chunk):
        az, dist = np.meshgrid(az_all[i:i+chunk], DISTANCES_M, indexing='ij')
        la, lo = _destination(lat, lon, az, dist)
        r1 = MOON_RADIUS_M+height(la, lo)+offset_m
        out[i:i+chunk] = np.degrees(np.arctan2(r1*np.cos(gamma)-r0, r1*np.sin(gamma))).max(axis=1)
    return out


def skyline_at(profile, azimuth):
    """Skyline elevation in any direction, interpolated linearly and wrapping at north."""
    step = 360./len(profile)
    grid = np.arange(len(profile)+1)*step
    return np.interp(np.asarray(azimuth) % 360, grid, np.append(profile, profile[0]))
