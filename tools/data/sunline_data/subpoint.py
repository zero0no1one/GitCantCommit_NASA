"""Coarse Sun and Earth positions from the hourly sub-solar / sub-Earth table (2026–2030).

Adapted from Echo-Path's `echo_path/ephemeris.py` and `conditions.sky_position`. The table
(source/ephemeris_moon_2026_2030.csv.gz) was built from JPL Horizons (DE441): target 301 seen from Earth's centre,
quantities 14 and 15 in the MOON_ME frame. Sunline uses it only to search for a good 30-day window quickly and as an
independent cross-check of the topocentric Horizons data; the game itself uses topocentric Horizons (horizons.py).
"""
import csv
import gzip
from functools import lru_cache
import numpy as np
from .constants import SOURCE, MOON_RADIUS_M

EPOCH = np.datetime64('2026-01-01T00:00', 's')


@lru_cache(maxsize=1)
def table():
    with gzip.open(SOURCE/'ephemeris_moon_2026_2030.csv.gz', 'rt', newline='') as f:
        rows = list(csv.reader(f))[1:]
    t = np.array([np.datetime64(r[0][:-1], 's') for r in rows])
    v = np.array([[float(x) for x in r[1:]] for r in rows])
    earth_lon, earth_lat, sun_lon, sun_lat, dist = v.T
    return {'unix': (t-np.datetime64('1970-01-01T00:00', 's')).astype(np.int64),
            'earth_lon': np.unwrap(earth_lon, period=360.), 'earth_lat': earth_lat,
            'sun_lon': np.unwrap(sun_lon, period=360.), 'sun_lat': sun_lat, 'earth_distance_km': dist}


def at(unix):
    t = table()
    unix = np.asarray(unix, float)
    if unix.min() < t['unix'][0] or unix.max() > t['unix'][-1]:
        raise ValueError('time outside the 2026–2030 table')
    out = {k: np.interp(unix, t['unix'], t[k]) for k in ('earth_lon', 'earth_lat', 'sun_lon', 'sun_lat', 'earth_distance_km')}
    out['earth_lon'] %= 360.
    out['sun_lon'] %= 360.
    return out


def _unit(lat, lon):
    la, lo = np.radians(lat), np.radians(lon)
    return np.stack([np.cos(la)*np.cos(lo), np.cos(la)*np.sin(lo), np.sin(la)], axis=-1)


def sky_position(site_lat, site_lon, body_lat, body_lon, distance_radii=None):
    """True-compass azimuth and elevation (degrees) of a body over (body_lat, body_lon), seen from the site."""
    site = _unit(site_lat, site_lon)
    body = _unit(body_lat, body_lon)
    if distance_radii is not None:
        body = body*np.asarray(distance_radii)[..., None]-site
        body /= np.linalg.norm(body, axis=-1, keepdims=True)
    la, lo = np.radians(site_lat), np.radians(site_lon)
    east = np.array([-np.sin(lo), np.cos(lo), 0.])
    north = np.array([-np.sin(la)*np.cos(lo), -np.sin(la)*np.sin(lo), np.cos(la)])
    elevation = np.degrees(np.arcsin(np.clip(body@site, -1, 1)))
    azimuth = np.degrees(np.arctan2(body@east, body@north)) % 360
    return azimuth, elevation


def sun_earth(site_lat, site_lon, unix):
    """Coarse (sun_az, sun_el, earth_az, earth_el, earth_radius_deg) at the site."""
    e = at(unix)
    sun_az, sun_el = sky_position(site_lat, site_lon, e['sun_lat'], e['sun_lon'])
    radii = e['earth_distance_km']*1000/MOON_RADIUS_M
    earth_az, earth_el = sky_position(site_lat, site_lon, e['earth_lat'], e['earth_lon'], radii)
    earth_r = np.degrees(np.arcsin(6378.137/e['earth_distance_km']))
    return sun_az, sun_el, earth_az, earth_el, earth_r


def sun_earth_separation(unix):
    """Angle (degrees) between the Sun and Earth directions seen from the Moon's centre; small means an eclipse."""
    e = at(unix)
    s = _unit(e['sun_lat'], e['sun_lon'])
    g = _unit(e['earth_lat'], e['earth_lon'])
    return np.degrees(np.arccos(np.clip(np.sum(s*g, axis=-1), -1, 1)))
