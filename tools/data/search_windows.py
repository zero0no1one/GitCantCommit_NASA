"""Step 1: pick the south-polar site and the 30-day window that make the clearest puzzle.

Coarse and fast: hourly sub-point ephemeris (source/ephemeris_moon_2026_2030.csv.gz, from JPL Horizons) and 1°
skylines. The chosen window is then rebuilt at full detail by build_mission.py from topocentric Horizons.

A window qualifies when, over its touchdown times:
- no lunar eclipse is anywhere near (Sun-Earth separation seen from the Moon > 3°);
- the polar site both passes and fails, switching several times (changing touchdown changes the outcome);
- the two sites disagree in both directions at some shared touchdown times;
- Earth rises and sets at the polar site (so the Earth row is not trivially all-up or all-down).
Output: window_search.json (top 100 windows, best first). Run: python search_windows.py
"""
import json
import numpy as np
from sunline_data import subpoint, terrain
from sunline_data.constants import ROOT, PANEL_HEIGHT_M, SAMPLING_HOURS, WINDOW_DAYS, SOURCE

SEARCH_FROM = np.datetime64('2027-01-01T00:00', 's')
SEARCH_TO = np.datetime64('2030-12-01T00:00', 's')
SUN_R = .2666
ECLIPSE_CLEARANCE_DEG = 3.0


def unix(dt):
    return int((dt-np.datetime64('1970-01-01T00:00', 's'))/np.timedelta64(1, 's'))


def coarse_pass(lat, lon, hours):
    profile = terrain.horizon_profile(lat, lon, PANEL_HEIGHT_M, step_deg=1.0)
    sun_az, sun_el, earth_az, earth_el, _ = subpoint.sun_earth(lat, lon, hours)
    clear = sun_el-SUN_R >= terrain.skyline_at(profile, sun_az)
    earth = earth_el >= terrain.skyline_at(profile, earth_az)
    n = int(SAMPLING_HOURS)+1                      # samples spanning the 6 h block, both ends included
    run = np.lib.stride_tricks.sliding_window_view(clear, n).all(axis=1)
    return run, earth[:len(run)], clear


def transitions(flags):
    return int(np.count_nonzero(flags[1:] != flags[:-1]))


def main():
    sites = json.loads((SOURCE/'sites_catalog.json').read_text())['sites']
    tq = next(s for s in sites if s['id'] == 'apollo-11')
    polar = [s for s in sites if s['group'] == 'South pole candidates']
    hours = np.arange(unix(SEARCH_FROM), unix(SEARCH_TO)+1, 3600)
    sep = subpoint.sun_earth_separation(hours)
    tq_pass, _, _ = coarse_pass(tq['lat'], tq['lon'], hours)
    W = WINDOW_DAYS*24
    results = []
    for s in polar:
        p_pass, p_earth, _ = coarse_pass(s['lat'], s['lon'], hours)
        print(f"{s['id']:9s} pass {100*p_pass.mean():5.1f}%  earth up {100*p_earth.mean():5.1f}%")
        for d0 in range(0, len(p_pass)-W, 24):
            span = slice(d0, d0+W)
            if sep[d0:d0+W+int(SAMPLING_HOURS)+1].min() < ECLIPSE_CLEARANCE_DEG:
                continue
            pp, tp, pe = p_pass[span], tq_pass[span], p_earth[span]
            flips = transitions(pp)
            polar_only = float(np.mean(pp & ~tp))
            tq_only = float(np.mean(~pp & tp))
            earth_flips = transitions(pe)
            if flips < 4 or min(polar_only, tq_only) < .05 or earth_flips < 2 or not (.15 < pp.mean() < .85):
                continue
            score = (min(flips, 20)/20 + 4*min(polar_only, tq_only) + (1-2*abs(pp.mean()-.5))
                     + min(earth_flips, 8)/8 + (1-2*abs(pe.mean()-.5)))
            results.append({'site': s['id'], 'name': s['name'], 'lat': s['lat'], 'lon': s['lon'],
                            'start_unix': int(hours[d0]), 'start': str(SEARCH_FROM+np.timedelta64(int(hours[d0]-hours[0]), 's'))+'Z',
                            'score': round(score, 4), 'polar_pass_pct': round(100*pp.mean(), 1),
                            'tq_pass_pct': round(100*tp.mean(), 1), 'polar_flips': flips,
                            'polar_only_pct': round(100*polar_only, 1), 'tq_only_pct': round(100*tq_only, 1),
                            'earth_up_pct': round(100*pe.mean(), 1), 'earth_flips': earth_flips,
                            'min_sun_earth_sep_deg': round(float(sep[d0:d0+W].min()), 2)})
    results.sort(key=lambda r: -r['score'])
    (ROOT/'window_search.json').write_text(json.dumps(results[:100], indent=1))  # top 100 kept
    print(f'{len(results)} qualifying windows; best:')
    for r in results[:10]:
        print({k: r[k] for k in ('site', 'start', 'score', 'polar_pass_pct', 'tq_pass_pct', 'polar_flips',
                                 'polar_only_pct', 'tq_only_pct', 'earth_up_pct', 'earth_flips')})
    if not results:
        raise SystemExit('No window qualifies: relax the criteria or widen the search.')


if __name__ == '__main__':
    main()
