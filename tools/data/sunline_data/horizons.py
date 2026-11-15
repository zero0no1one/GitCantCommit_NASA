"""Topocentric Sun and Earth positions at a lunar site from NASA JPL Horizons.

Query: target 10 (Sun) or 399 (Earth), observer CENTER='coord@301' (a point on the Moon), COORD_TYPE=GEODETIC with
SITE_COORD = east longitude, latitude, altitude above the 1,737.4 km sphere. Horizons reports this observer frame as
"MEAN_ME (high precision)", the same mean-Earth/polar-axis frame and sphere as the LOLA terrain, so no frame
conversion is needed. APPARENT='AIRLESS' (no refraction). Quantities: 4 (apparent azimuth and elevation, azimuth
measured from north through east), 13 (angular diameter, arcseconds) and 20 (range, au).

Every response is cached under raw/ with a name built from the query, so later runs are repeatable offline.
https://ssd.jpl.nasa.gov/horizons/  API docs: https://ssd-api.jpl.nasa.gov/doc/horizons.html
"""
import hashlib
import json
from datetime import datetime, timezone
import numpy as np
import requests
from .constants import RAW

API = 'https://ssd.jpl.nasa.gov/api/horizons.api'
AU_KM = 149_597_870.7
_MONTHS = {m: i+1 for i, m in enumerate('Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec'.split())}


def _params(target, lon, lat, alt_km, start, stop, step_min):
    return {'format': 'json', 'COMMAND': f"'{target}'", 'OBJ_DATA': "'NO'", 'MAKE_EPHEM': "'YES'",
            'EPHEM_TYPE': "'OBSERVER'", 'CENTER': "'coord@301'", 'COORD_TYPE': "'GEODETIC'",
            'SITE_COORD': f"'{lon:.6f},{lat:.6f},{alt_km:.6f}'", 'START_TIME': f"'{start}'", 'STOP_TIME': f"'{stop}'",
            'STEP_SIZE': f"'{step_min} m'", 'QUANTITIES': "'4,13,20'", 'ANG_FORMAT': "'DEG'", 'EXTRA_PREC': "'YES'",
            'CSV_FORMAT': "'YES'", 'APPARENT': "'AIRLESS'", 'TIME_DIGITS': "'MINUTES'"}


def fetch(target, lon, lat, alt_km, start, stop, step_min):
    """Raw Horizons text for one query, from the cache when available."""
    params = _params(target, lon, lat, alt_km, start, stop, step_min)
    key = hashlib.sha1(json.dumps(params, sort_keys=True).encode()).hexdigest()[:16]
    path = RAW/f'horizons_{target}_{key}.txt'
    if path.exists():
        return path.read_text(encoding='utf-8')
    RAW.mkdir(parents=True, exist_ok=True)
    r = requests.get(API, params=params, timeout=180)
    r.raise_for_status()
    body = r.json()
    if 'result' not in body:
        raise RuntimeError(f'Horizons error: {body}')
    text = body['result']
    if '$$SOE' not in text:
        raise RuntimeError('Horizons returned no ephemeris:\n'+text[-2000:])
    path.write_text(f'# query: {json.dumps(params, sort_keys=True)}\n'+text, encoding='utf-8')
    return text


def _unix(stamp):
    """'2027-Mar-01 00:10' -> unix seconds (UTC)."""
    y, mon, rest = stamp.strip().split('-', 2)
    d, hm = rest.split()
    h, m = hm.split(':')[:2]
    return int(datetime(int(y), _MONTHS[mon], int(d), int(h), int(m), tzinfo=timezone.utc).timestamp())


def parse(text):
    """Arrays: unix, azimuth, elevation (deg), angular radius (deg), range (km)."""
    body = text[text.index('$$SOE')+5:text.index('$$EOE')]
    rows = []
    for line in body.strip().splitlines():
        f = [x.strip() for x in line.split(',')]
        # date, solar-presence flag, lunar-presence flag, azimuth, elevation, angular diameter, delta, deldot
        rows.append((_unix(f[0]), float(f[3]), float(f[4]), float(f[5])/3600/2, float(f[6])*AU_KM))
    a = np.array(rows)
    return {'unix': a[:, 0].astype(np.int64), 'az': a[:, 1], 'el': a[:, 2], 'radius': a[:, 3], 'range_km': a[:, 4]}


def site_series(lon, lat, alt_km, start, stop, step_min):
    """Sun and Earth tables on the same time grid."""
    sun = parse(fetch(10, lon, lat, alt_km, start, stop, step_min))
    earth = parse(fetch(399, lon, lat, alt_km, start, stop, step_min))
    if not np.array_equal(sun['unix'], earth['unix']):
        raise RuntimeError('Sun and Earth tables are on different time grids')
    return sun, earth
