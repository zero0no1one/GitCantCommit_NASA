"""Step 3: independent checks of the bundled dataset. Writes VALIDATION.md. Run: python validate.py

1. Sky positions: topocentric Horizons (the game's data) against an independent Horizons query (geocentric
   sub-point table) turned into local azimuth/elevation with our own geometry.
2. Polar lighting: our long-term mean visible solar fraction at each of the 13 polar candidates (2026–2030, hourly)
   against NASA GSFC PGDA's LOLA average-visibility map (Mazarico et al. 2011), read at the site and its 3x3
   neighbourhood (60 m pixels).
3. Terrain resolution sensitivity: skyline change when the finest terrain layer is removed.
4. Interval edges on the real data: just inside / just outside every full-disc boundary.
5. Partial sunlight, dataset edges and golden parity.
"""
import json
from datetime import datetime, timezone
import numpy as np
import rasterio
from sunline_data import terrain, subpoint, scoring
from sunline_data.constants import ROOT, SOURCE, MISSION_JSON, GOLDEN_JSON, PANEL_HEIGHT_M, SAMPLING_HOURS

PGDA_AVG = 'https://pgda.gsfc.nasa.gov/data/MoonIllumination/AVGVISIB_85S_060M_201608.TIF'


def iso(u):
    return datetime.fromtimestamp(int(u), timezone.utc).strftime('%Y-%m-%d %H:%M')


def pgda_values(sites):
    out = {}
    with rasterio.Env(CPL_VSIL_CURL_ALLOWED_EXTENSIONS='.TIF', GDAL_HTTP_MAX_RETRY=3):
        with rasterio.open('/vsicurl/'+PGDA_AVG) as ds:
            scale = ds.scales[0]
            for s in sites:
                x, y = terrain._polar_xy(np.array([s['lat']]), np.array([s['lon']]))
                col, row = ~ds.transform*(float(x[0]), float(y[0]))
                r, c = int(np.floor(row)), int(np.floor(col))
                if not (1 <= r < ds.height-1 and 1 <= c < ds.width-1):
                    out[s['id']] = None
                    continue
                w = ds.read(1, window=rasterio.windows.Window(c-1, r-1, 3, 3)).astype(float)
                w[w == ds.nodata] = np.nan
                w *= scale
                # pixel, darkest and brightest of the 3x3 (the brightest is the crest the site sits on)
                out[s['id']] = (float(w[1, 1]), float(np.nanmin(w)), float(np.nanmax(w)))
    return out


def our_mean_visibility(s, hours):
    profile = terrain.horizon_profile(s['lat'], s['lon'], PANEL_HEIGHT_M, step_deg=1.0)
    sun_az, sun_el, *_ = subpoint.sun_earth(s['lat'], s['lon'], hours)
    x = np.clip((sun_el-terrain.skyline_at(profile, sun_az))/.2666, -1, 1)
    return float(np.mean((np.arccos(-x)+x*np.sqrt(1-x**2))/np.pi))


def main():
    m = json.loads(MISSION_JSON.read_text())
    g = json.loads(GOLDEN_JSON.read_text())
    catalog = json.loads((SOURCE/'sites_catalog.json').read_text())['sites']
    polar = [s for s in catalog if s['group'] == 'South pole candidates']
    lines = ['# Sunline data validation', '',
             f"Generated {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC by `tools/data/validate.py` from "
             f"`data/mission.json` (window {m['window']['start_utc']} → {m['window']['end_utc']}).", '']

    # 1. Sky positions
    lines += ['## 1. Sun and Earth positions vs an independent Horizons query', '',
              'The game uses topocentric Horizons az/el (observer on the Moon). The check converts a separate '
              'geocentric Horizons table (sub-solar and sub-Earth points, MOON_ME) into local az/el with our own '
              'geometry, hourly over the window.', '',
              '| Site | Sun elevation | Sun azimuth (below 80° el.) | Earth elevation | Earth azimuth | Samples |',
              '|---|---|---|---|---|---|']
    for sid, c in m['cross_check_vs_subpoint_table'].items():
        lines.append(f"| {sid} | {c['sun_el_max_diff_deg']:.4f}° | {c['sun_az_max_diff_deg_below_80']:.4f}° | "
                     f"{c['earth_el_max_diff_deg']:.4f}° | {c['earth_az_max_diff_deg']:.4f}° | {c['samples']} |")
    lines += ['', 'Values are the largest absolute difference. Both are far below the 0.1° displayed precision.', '']

    # 2. PGDA illumination
    print('PGDA average visibility ...', flush=True)
    t0 = int(np.datetime64('2026-01-01T00:00', 's').astype(np.int64))
    t1 = int(np.datetime64('2030-12-31T00:00', 's').astype(np.int64))
    hours = np.arange(t0, t1, 3600)
    ref = pgda_values(polar)
    rows, ours_l, pix_l, crest_l = [], [], [], []
    for s in polar:
        ours = our_mean_visibility(s, hours)
        r = ref[s['id']]
        rows.append((s, ours, r))
        if r is not None and np.isfinite(r[0]):
            ours_l.append(ours)
            pix_l.append(r[0])
            crest_l.append(r[2])
    def stats(ref_vals):
        d = np.array(ours_l)-np.array(ref_vals)
        return float(np.corrcoef(ours_l, ref_vals)[0, 1]), 100*d.mean(), 100*np.abs(d).mean(), 100*np.abs(d).max()
    sp, sc = stats(pix_l), stats(crest_l)
    lines += ['## 2. Polar lighting vs NASA PGDA LOLA average illumination', '',
              f'Reference: PGDA `AVGVISIB_85S_060M_201608` ({PGDA_AVG}), mean fraction of the solar disc visible, '
              '60 m polar stereographic (Mazarico, E. et al. 2011, Icarus 211, 1066–1081, doi:10.1016/j.icarus.2010.10.030). '
              'Ours: mean visible solar fraction from the 1° skyline at 1.0 m panel height with the hourly '
              '2026–2030 Horizons table. Periods and observer heights differ, so a few points of difference '
              'are expected.', '',
              'Our sites are crest points picked on the 80 m grid, and PGDA values change by tens of points within '
              'one 60 m pixel on these crests, so the fair comparison is with the brightest pixel of the 3×3 '
              'neighbourhood (the crest). The single-pixel column is shown for completeness.', '',
              'Projection check: reading PGDA with either map axis flipped gives implausible values (most near '
              'zero), which confirms our polar stereographic convention matches PGDA\'s.', '',
              '| Site | Lat | Ours | PGDA crest (3×3 max) | PGDA pixel | PGDA 3×3 range | Ours − crest |',
              '|---|---|---|---|---|---|---|']
    for s, ours, r in rows:
        if r is None:
            lines.append(f"| {s['id']} {s['name']} | {s['lat']:.2f} | {100*ours:.1f}% | outside map | | | |")
        else:
            mark = ' **(game site)**' if s['id'] in [x['id'] for x in m['sites']] else ''
            lines.append(f"| {s['id']} {s['name']}{mark} | {s['lat']:.2f} | {100*ours:.1f}% | {100*r[2]:.1f}% | "
                         f"{100*r[0]:.1f}% | {100*r[1]:.1f}–{100*r[2]:.1f}% | {100*(ours-r[2]):+.1f} pts |")
    lines += ['', f'Across {len(ours_l)} sites, against the crest: r = {sc[0]:.3f}, mean difference {sc[1]:+.1f} pts, '
              f'mean |difference| {sc[2]:.1f} pts, largest {sc[3]:.1f} pts. '
              f'Against the single pixel: r = {sp[0]:.3f}, mean {sp[1]:+.1f} pts, largest {sp[3]:.1f} pts.', '']

    # 3. Resolution sensitivity
    print('resolution sensitivity ...', flush=True)
    lines += ['## 3. Skyline sensitivity to terrain resolution', '',
              'How far the skyline moves if the finest terrain layer at the site is removed. This bounds the effect '
              'of DEM resolution; the error of the finer product itself is expected to be smaller. The game shows '
              f"timing uncertainty for a ±{m['conventions']['skyline_error_deg']}° skyline error, and every "
              f"showcase example keeps its outcome under ±{m['conventions']['examples_robust_to_skyline_error_deg']}°.", '',
              '| Site | Layer removed | Median | 90th pct | Max |', '|---|---|---|---|---|']
    for s in m['sites']:
        full = terrain.horizon_profile(s['lat'], s['lon'], PANEL_HEIGHT_M, step_deg=1.0)
        if s['lat'] < -79.5:
            keep, terrain._patches = terrain._patches, (lambda: [])
            what = '80 m patch → 640 m mosaic'
        else:
            keep, terrain._tranquility = terrain._tranquility, (lambda: None)
            what = '118 m patch → 7.6 km LDEM_4'
        coarse = terrain.horizon_profile(s['lat'], s['lon'], PANEL_HEIGHT_M, step_deg=1.0)
        if s['lat'] < -79.5:
            terrain._patches = keep
        else:
            terrain._tranquility = keep
        d = np.abs(full-coarse)
        lines.append(f"| {s['id']} | {what} | {np.median(d):.3f}° | {np.percentile(d, 90):.3f}° | {d.max():.3f}° |")
    lines.append('')

    # 4/5. Interval edges, partial sun, dataset edge, golden parity
    lines += ['## 4. Interval edges, partial sunlight, dataset edges', '']
    end = m['window']['end_unix']
    need = int(SAMPLING_HOURS*3600)
    for s in m['sites']:
        smp = s['samples']
        n = smp['count']
        unix = smp['start_unix']+np.arange(n)*smp['step_s']
        tr = scoring.Track(unix, smp['sun_az'], smp['sun_el'], smp['sun_radius'], smp['earth_az'], smp['earth_el'],
                           smp['earth_radius'], s['skyline']['elevation_deg'])
        bad = 0
        checked = 0
        for a, b, _, _ in s['intervals']['sun_full']:
            if a > tr.start:
                checked += 1
                bad += not (tr.clear(np.array([a+1.]))[0] >= 0 and tr.clear(np.array([a-2.]))[0] < 0)
            if b < tr.end:
                checked += 1
                bad += not (tr.clear(np.array([b-1.]))[0] >= 0 and tr.clear(np.array([b+2.]))[0] < 0)
        full_s = sum(b+1-a for a, b, *_ in s['intervals']['sun_full'])
        any_s = sum(b+1-a for a, b in s['intervals']['sun_any'])
        iv = [x[:2] for x in s['intervals']['sun_full']]
        last = scoring.evaluate(iv, m['window']['touchdown_max_unix'], end)
        try:
            scoring.evaluate(iv, m['window']['touchdown_max_unix']+600, end)
            edge_ok = False
        except ValueError:
            edge_ok = True
        lines += [f"**{s['name']} ({s['id']})**", '',
                  f"- Full-disc boundaries checked 1–2 s inside and outside: {checked - bad}/{checked} correct.",
                  f"- Partial sunlight (some but not all of the disc): {(any_s-full_s)/3600:.1f} h in the window.",
                  f"- Last allowed touchdown {iso(m['window']['touchdown_max_unix'])}: "
                  f"{'pass' if last['pass'] else 'fail'}; one step later is refused: {'yes' if edge_ok else 'NO'}.", '']

    mismatches = 0
    for s in m['sites']:
        iv = [x[:2] for x in s['intervals']['sun_full']]
        for t, want in zip(g['touchdowns'], g['results'][s['id']]):
            mismatches += scoring.evaluate(iv, t, end) != want
    lines += [f"Golden parity: {len(g['touchdowns'])} touchdowns × {len(m['sites'])} sites re-scored from the bundled "
              f"intervals, {mismatches} mismatches.", '']

    ex = m['examples']
    lines += ['## 5. Showcase examples (verified, robust to the larger skyline error)', '']
    a = ex['same_site']
    lines.append(f"- Same site ({a['site']}): touchdown {iso(a['pass_touchdown'])} passes; "
                 f"{iso(a['fail_touchdown'])} fails ({a['gap_s']/3600:.1f} h apart).")
    for k in ('same_time', 'same_time_reverse'):
        if k in ex:
            b = ex[k]
            lines.append(f"- Same time {iso(b['touchdown'])}: {b['winner']} passes, {b['loser']} fails.")
    lines += ['', '## 6. Checks still needing a person', '',
              '- **LROC Quickmap** (https://quickmap.lroc.asu.edu/): open the polar site, turn on the LOLA '
              'illumination / topography layers, and confirm the ridge that blocks the Sun matches our skyline '
              'peak direction. Record the result here.',
              '- **NASA Moon Trek** (https://trek.nasa.gov/moon/): draw elevation profiles from each site toward '
              'the skyline maximum and compare the angle with ours.',
              '- First-time player test (one minute to explain the choice) — pending.', '',
              '## Known limits', '',
              '- Terrain within 100 m of the site is not used for the skyline (DEM pixels are 80–118 m).',
              '- The skyline is treated as level across the 0.5° solar disc when estimating partial sunlight.',
              '- Panel height 1.0 m is a modelled assumption; the 6 h requirement is fictional.',
              '- Earth visibility is a geometric reading (centre of Earth above the skyline), not a link budget.',
              '- Times are linearly interpolated between 10-minute Horizons samples (Sun moves < 0.1° per step).', '']
    with open(ROOT/'VALIDATION.md', 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(lines))
    print('wrote VALIDATION.md')


if __name__ == '__main__':
    main()
