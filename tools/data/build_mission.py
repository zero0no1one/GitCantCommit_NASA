"""Step 2: build data/mission.json (bundled with the game) and golden_results.json (for the Godot tests).

Uses the best window from window_search.json (or --site/--start), then:
1. topocentric JPL Horizons Sun and Earth at both sites, 10-minute steps (horizons.py, cached in raw/);
2. 0.1° skylines from the panel height (terrain.py);
3. full-disc sunlight, any-disc sunlight and Earth-up intervals to the second (scoring.py), plus how much each
   boundary moves if the whole skyline is SKYLINE_ERROR_DEG higher or lower (the displayed uncertainty);
4. the mission result for every touchdown on the 10-minute grid, for both sites;
5. two showcase examples that keep their outcome under that skyline error:
   (a) same site, nearby touchdown times, different outcome; (b) same touchdown time, the two sites differ.
Run: python build_mission.py
"""
import argparse
import json
from datetime import datetime, timezone
import numpy as np
from sunline_data import horizons, scoring, terrain, subpoint
from sunline_data.constants import (ROOT, SOURCE, MISSION_JSON, GOLDEN_JSON, PANEL_HEIGHT_M, SAMPLING_HOURS,
                                    STEP_MIN, WINDOW_DAYS, SKYLINE_STEP_DEG, MOON_RADIUS_M)

SKYLINE_ERROR_DEG = 0.1      # skyline uncertainty behind the displayed timing bands (see VALIDATION.md)
ROBUST_ERROR_DEG = 0.3       # showcase examples must keep their outcome under this larger skyline error
EDGE_MARGIN_S = 12*3600      # keep showcase touchdowns away from the window edges


def iso(u):
    return datetime.fromtimestamp(int(u), timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def hstamp(u):
    return datetime.fromtimestamp(int(u), timezone.utc).strftime('%Y-%m-%d %H:%M')


def boundary_uncertainty(nominal, variants, horizon_s=48*3600):
    """For each nominal interval edge, the largest shift to the matching edge in the variant interval lists."""
    out = []
    for a, b in nominal:
        ua = ub = 0
        for v in variants:
            starts = np.array([x[0] for x in v]) if v else np.array([])
            ends = np.array([x[1] for x in v]) if v else np.array([])
            for edge, pool, idx in ((a, starts, 0), (b, ends, 1)):
                if len(pool) == 0:
                    continue
                d = int(np.min(np.abs(pool-edge)))
                d = min(d, horizon_s)
                if idx == 0:
                    ua = max(ua, d)
                else:
                    ub = max(ub, d)
        out.append([int(a), int(b), ua, ub])
    return out


def build_site(site, start, end):
    lat, lon = site['lat'], site['lon']
    ground = float(terrain.height(lat, lon))
    alt_km = (ground+PANEL_HEIGHT_M)/1000
    print(f"{site['id']}: ground {ground:.1f} m, skyline 0.1° ...", flush=True)
    # Round to the precision bundled in mission.json BEFORE scoring, so the game's numbers and the scored
    # intervals come from exactly the same data.
    sky = np.round(terrain.horizon_profile(lat, lon, PANEL_HEIGHT_M, step_deg=SKYLINE_STEP_DEG), 3)
    print(f"{site['id']}: Horizons ...", flush=True)
    sun, earth = horizons.site_series(lon, lat, alt_km, hstamp(start), hstamp(end), STEP_MIN)
    for body in (sun, earth):
        body['az'] = np.round(body['az'], 4)
        body['el'] = np.round(body['el'], 4)
        body['radius'] = np.round(body['radius'], 5)
    tr = scoring.Track(sun['unix'], sun['az'], sun['el'], sun['radius'],
                       earth['az'], earth['el'], earth['radius'], sky)
    t0, t1 = tr.start, tr.end
    full = scoring.intervals(tr.clear, t0, t1)
    full_hi = scoring.intervals(lambda t: tr.clear(t, SKYLINE_ERROR_DEG), t0, t1)
    full_lo = scoring.intervals(lambda t: tr.clear(t, -SKYLINE_ERROR_DEG), t0, t1)
    full_rhi = scoring.intervals(lambda t: tr.clear(t, ROBUST_ERROR_DEG), t0, t1)
    full_rlo = scoring.intervals(lambda t: tr.clear(t, -ROBUST_ERROR_DEG), t0, t1)
    any_sun = scoring.intervals(tr.partial_margin, t0, t1)
    earth_up = scoring.intervals(tr.earth_margin, t0, t1)
    earth_hi = scoring.intervals(lambda t: tr.earth_margin(t, SKYLINE_ERROR_DEG), t0, t1)
    earth_lo = scoring.intervals(lambda t: tr.earth_margin(t, -SKYLINE_ERROR_DEG), t0, t1)
    ecl = tr.eclipse_margin(np.arange(t0, t1+1, 600, dtype=float))
    return {
        'site': site, 'ground_m': ground, 'skyline': sky, 'track': tr, 'sun': sun, 'earth': earth,
        'full': full, 'full_hi': full_hi, 'full_lo': full_lo, 'full_rhi': full_rhi, 'full_rlo': full_rlo,
        'any': any_sun, 'earth_up': earth_up,
        'full_unc': boundary_uncertainty(full, [full_hi, full_lo]),
        'earth_unc': boundary_uncertainty(earth_up, [earth_hi, earth_lo]),
        'min_eclipse_gap_deg': float(ecl.min()),
    }


def results_grid(b, touchdowns, data_end):
    nominal = [scoring.evaluate(b['full'], int(t), data_end) for t in touchdowns]
    hi = [scoring.evaluate(b['full_rhi'], int(t), data_end)['pass'] for t in touchdowns]
    lo = [scoring.evaluate(b['full_rlo'], int(t), data_end)['pass'] for t in touchdowns]
    robust = [n['pass'] == h == l for n, h, l in zip(nominal, hi, lo)]
    return nominal, np.array(robust)


def pick_examples(tq, po, touchdowns, rq, rp, robq, robp):
    inner = (touchdowns >= touchdowns[0]+EDGE_MARGIN_S) & (touchdowns <= touchdowns[-1]-EDGE_MARGIN_S)
    robq, robp = robq & inner, robp & inner
    passq = np.array([r['pass'] for r in rq])
    passp = np.array([r['pass'] for r in rp])
    ex = {}
    # (a) same polar site, two nearby touchdowns with different robust outcomes; prefer the closest pair.
    best = None
    for i in np.flatnonzero(robp & passp):
        for j in np.flatnonzero(robp & ~passp):
            gap = abs(int(touchdowns[j])-int(touchdowns[i]))
            if best is None or gap < best[0]:
                best = (gap, i, j)
    if best is None:
        raise SystemExit('No robust same-site example: choose another window.')
    _, i, j = best
    ex['same_site'] = {'site': po['site']['id'], 'pass_touchdown': int(touchdowns[i]), 'fail_touchdown': int(touchdowns[j]),
                       'gap_s': int(best[0]), 'pass_result': rp[i], 'fail_result': rp[j]}
    # (b) same touchdown time, sites differ, robust for both; prefer polar passing while Tranquility fails,
    # choosing the time with the largest pass margin.
    both = robq & robp
    cand_pole = np.flatnonzero(both & passp & ~passq)
    cand_tq = np.flatnonzero(both & ~passp & passq)
    if len(cand_pole) == 0 and len(cand_tq) == 0:
        raise SystemExit('No robust same-time example: choose another window.')
    def strongest(idx, results):
        return max(idx, key=lambda k: results[k]['margin_s'] or 0)
    if len(cand_pole):
        k = strongest(cand_pole, rp)
        ex['same_time'] = {'touchdown': int(touchdowns[k]), 'winner': po['site']['id'], 'loser': tq['site']['id'],
                           'results': {po['site']['id']: rp[k], tq['site']['id']: rq[k]}}
    if len(cand_tq):
        k = strongest(cand_tq, rq)
        ex['same_time_reverse'] = {'touchdown': int(touchdowns[k]), 'winner': tq['site']['id'], 'loser': po['site']['id'],
                                   'results': {po['site']['id']: rp[k], tq['site']['id']: rq[k]}}
    return ex


def cross_check(b):
    """Topocentric Horizons vs the sub-point table (independent Horizons query + our geometry), hourly."""
    tr = b['track']
    hours = np.arange(tr.start, tr.end+1, 3600)
    s = b['site']
    sa, se, ea, ee, _ = subpoint.sun_earth(s['lat'], s['lon'], hours)
    p = tr.at(hours.astype(float))
    daz = lambda x, y: np.abs((x-y+180) % 360-180)
    # Near the zenith azimuth is ill-defined, so compare it only below 80° elevation.
    ok = p['sun_el'] < 80
    return {'sun_el_max_diff_deg': float(np.max(np.abs(p['sun_el']-se))),
            'sun_az_max_diff_deg_below_80': float(np.max(daz(p['sun_az'], sa)[ok])),
            'earth_el_max_diff_deg': float(np.max(np.abs(p['earth_el']-ee))),
            'earth_az_max_diff_deg': float(np.max(daz(p['earth_az'], ea))), 'samples': int(len(hours))}


def site_json(b):
    tr, s = b['track'], b['site']
    r4 = lambda a: [round(float(x), 4) for x in a]
    return {
        'id': s['id'], 'name': s['name'], 'lat': s['lat'], 'lon': s['lon'], 'coordinate_source': s['source'],
        'ground_elevation_m': round(b['ground_m'], 1), 'panel_height_m': PANEL_HEIGHT_M,
        'terrain_source': terrain.source_at(s['lat'], s['lon']),
        'skyline': {'azimuth_step_deg': SKYLINE_STEP_DEG, 'elevation_deg': [round(float(x), 3) for x in b['skyline']],
                    'max_deg': round(float(b['skyline'].max()), 3), 'min_deg': round(float(b['skyline'].min()), 3)},
        'samples': {'start_unix': tr.start, 'step_s': STEP_MIN*60, 'count': int(len(tr.unix)),
                    'sun_az': r4(b['sun']['az']), 'sun_el': r4(b['sun']['el']),
                    'sun_radius': [round(float(x), 5) for x in b['sun']['radius']],
                    'earth_az': r4(b['earth']['az']), 'earth_el': r4(b['earth']['el']),
                    'earth_radius': [round(float(x), 5) for x in b['earth']['radius']]},
        'intervals': {
            'sun_full': b['full_unc'], 'sun_any': b['any'], 'earth_up': b['earth_unc'],
            'format': 'sun_full and earth_up: [start_unix, end_unix, start_uncertainty_s, end_uncertainty_s]; '
                      'sun_any: [start_unix, end_unix]. Ends are the last second inside the interval.'},
        'min_sun_earth_gap_deg': round(b['min_eclipse_gap_deg'], 3),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--site')
    ap.add_argument('--start', help='window start, e.g. 2028-02-20T00:00')
    a = ap.parse_args()
    sites = {s['id']: s for s in json.loads((SOURCE/'sites_catalog.json').read_text())['sites']}
    if a.site and a.start:
        polar_id, start = a.site, int(np.datetime64(a.start, 's').astype(np.int64))
    else:
        best = json.loads((ROOT/'window_search.json').read_text())[0]
        polar_id, start = best['site'], best['start_unix']
    end = start+WINDOW_DAYS*86400
    tq = build_site(sites['apollo-11'], start, end)
    po = build_site(sites[polar_id], start, end)
    for b in (tq, po):
        if b['min_eclipse_gap_deg'] <= 0:
            raise SystemExit(f"Earth covers the Sun at {b['site']['id']} in this window: choose another.")
    data_end = min(tq['track'].end, po['track'].end)
    need = int(SAMPLING_HOURS*3600)
    touchdowns = np.arange(start, data_end-need+1, STEP_MIN*60)
    rq, robq = results_grid(tq, touchdowns, data_end)
    rp, robp = results_grid(po, touchdowns, data_end)
    examples = pick_examples(tq, po, touchdowns, rq, rp, robq, robp)
    checks = {tq['site']['id']: cross_check(tq), po['site']['id']: cross_check(po)}

    mission = {
        'schema': 1, 'title': 'Sunline', 'generated_utc': iso(datetime.now(timezone.utc).timestamp()),
        'mission': {
            'brief': 'Your rover needs six continuous hours of direct sunlight after touchdown to collect a sample. '
                     'Choose a landing site and a touchdown time.',
            'sampling_hours': SAMPLING_HOURS, 'requirement_is_fictional': True,
            'rule': 'Pass when the entire apparent solar disc stays above the local terrain skyline (seen from the '
                    'panel height) and clear of Earth for the whole sampling block that starts at touchdown.',
            'hint': 'Follow the sampling block to its end. Does the Sun clear the ridge the whole time?'},
        'window': {'start_unix': int(start), 'end_unix': int(data_end), 'start_utc': iso(start), 'end_utc': iso(data_end),
                   'touchdown_min_unix': int(touchdowns[0]), 'touchdown_max_unix': int(touchdowns[-1]),
                   'touchdown_step_s': STEP_MIN*60},
        'conventions': {
            'frame': 'Moon mean-Earth/polar-axis (MEAN_ME / MOON_ME), east longitude positive',
            'elevation_datum': f'heights above a {MOON_RADIUS_M/1000:.1f} km sphere (LOLA and Horizons)',
            'azimuth': 'true compass bearing, 0° toward the lunar north pole, increasing clockwise (east = 90°)',
            'elevation': 'degrees above the local horizontal plane of the sphere; no refraction (airless)',
            'time': 'UTC, unix seconds',
            'sun_full': 'whole solar disc above the skyline and not overlapped by Earth',
            'earth_up': 'centre of Earth\'s disc above the skyline (a geometric reading; no communications claim)',
            'skyline_error_deg': SKYLINE_ERROR_DEG, 'examples_robust_to_skyline_error_deg': ROBUST_ERROR_DEG,
            'display_precision': 'show times to the minute with the listed uncertainty; angles to 0.1°'},
        'sites': [site_json(tq), site_json(po)],
        'examples': examples,
        'cross_check_vs_subpoint_table': checks,
        'sources': [
            {'name': 'NASA JPL Horizons System (DE441), topocentric observer on the Moon', 'url': 'https://ssd.jpl.nasa.gov/horizons/'},
            {'name': 'LRO LOLA LDEM_4 global elevation (PDS)', 'url': 'https://pds-geosciences.wustl.edu/lro/lro-l-lola-3-rdr-v1/lrolol_1xxx/data/lola_gdr/cylindrical/img/', 'doi': '10.1029/2010GL043751'},
            {'name': 'LRO LOLA LDEM 118 m global mosaic (USGS Astrogeology)', 'url': 'https://planetarymaps.usgs.gov/mosaic/Lunar_LRO_LOLA_Global_LDEM_118m_Mar2014.tif', 'doi': '10.1029/2010GL043751'},
            {'name': 'NASA GSFC PGDA LOLA 80 m south polar mosaic LDEM_80S_80MPP_ADJ', 'url': 'https://pgda.gsfc.nasa.gov/products/90', 'doi': '10.3847/PSJ/acf3e1'},
            {'name': 'NASA GSFC PGDA south pole landing site LOLA DEMs (site list)', 'url': 'https://pgda.gsfc.nasa.gov/products/78', 'doi': '10.1016/j.pss.2020.105119'},
            {'name': 'Apollo landing sites (NSSDC)', 'url': 'https://nssdc.gsfc.nasa.gov/planetary/lunar/apolloland.html'}],
    }
    MISSION_JSON.parent.mkdir(parents=True, exist_ok=True)
    MISSION_JSON.write_text(json.dumps(mission, separators=(',', ':')))
    golden = {'window': mission['window'], 'touchdowns': [int(t) for t in touchdowns],
              'results': {tq['site']['id']: rq, po['site']['id']: rp},
              'robust': {tq['site']['id']: robq.tolist(), po['site']['id']: robp.tolist()}}
    GOLDEN_JSON.write_text(json.dumps(golden, separators=(',', ':')))

    print(f'\nmission.json {MISSION_JSON.stat().st_size/1e6:.2f} MB, golden {GOLDEN_JSON.stat().st_size/1e6:.2f} MB')
    print('window', iso(start), '->', iso(data_end), 'touchdowns', len(touchdowns))
    for b, r, rob in ((tq, rq, robq), (po, rp, robp)):
        p = np.array([x['pass'] for x in r])
        unc = [max(x[2], x[3]) for x in b['full_unc']]
        print(f"{b['site']['id']}: pass {100*p.mean():.1f}%  robust {100*rob.mean():.1f}%  full-sun intervals {len(b['full'])}"
              f"  earth-up intervals {len(b['earth_up'])}  skyline max {b['skyline'].max():.2f}°  "
              f"min sun-earth gap {b['min_eclipse_gap_deg']:.1f}°  median edge uncertainty {np.median(unc)/60 if unc else 0:.0f} min")
    print(json.dumps({k: {kk: (iso(vv) if kk.endswith('touchdown') else vv) for kk, vv in v.items() if not isinstance(vv, dict)}
                      for k, v in examples.items()}, indent=1))
    print(json.dumps(checks, indent=1))


if __name__ == '__main__':
    main()
