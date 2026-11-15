"""Offline Last Light package from cached Horizons/LOLA, with explicit model variants.
Run with the scientific Python environment: python tools/data/build_last_light.py.
No winning dates are specified: examples are selected only after variant evaluation.
"""
import hashlib
import json
from pathlib import Path
from datetime import datetime, timezone
import numpy as np
from sunline_data import terrain, scoring

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'data/mission.json'
OUT = ROOT / 'data/last_light.json'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def iso(t):
    return datetime.fromtimestamp(t, timezone.utc).isoformat()

def track(site, sky, stride=1):
    s = site['samples']
    indices = np.unique(np.append(np.arange(0, s['count'], stride), s['count']-1))
    unix = s['start_unix'] + indices * s['step_s']
    arrays = [np.array(s[k])[indices] for k in ['sun_az', 'sun_el', 'sun_radius', 'earth_az', 'earth_el', 'earth_radius']]
    return scoring.Track(unix, *arrays, sky)

def fit(intervals, start, need):
    return next((iv for iv in intervals if iv[0] <= start and start+need <= iv[1]+1), None)

def verdict(record, start, need):
    outcomes = [fit(v['full'], start, need) is not None for v in record['variants']]
    return 'Meets' if all(outcomes) else ('Misses' if not any(outcomes) else 'Unknown')

def build():
    source = json.loads(SOURCE.read_text())
    records = []
    for site in source['sites']:
        print('Checking', site['id'], flush=True)
        sky = np.array(site['skyline']['elevation_deg'])
        variants = []
        profiles = [('nominal', sky), ('skyline +0.1 deg', sky+.1), ('skyline -0.1 deg', sky-.1)]
        for height in [.5, 2.]:
            profiles.append((f'observer {height} m', terrain.horizon_profile(site['lat'], site['lon'], height)))
        # Pixel registration perturbations, not certified positional error bounds.
        for bearing in [0, 90, 180, 270]:
            lat, lon = terrain._destination(site['lat'], site['lon'], bearing, 40.)
            profiles.append((f'registration 40 m bearing {bearing}', terrain.horizon_profile(float(lat), float(lon), 1.)))
        saved_patches, saved_tq = terrain._patches, terrain._tranquility
        try:
            terrain._patches = lambda: []
            terrain._tranquility = lambda: None
            profiles.append(('fine terrain removed', terrain.horizon_profile(site['lat'], site['lon'], 1.)))
        finally:
            terrain._patches, terrain._tranquility = saved_patches, saved_tq
        base = track(site, sky)
        for name, profile in profiles:
            tr = track(site, profile)
            variants.append({'name': name, 'full': scoring.intervals(tr.clear, tr.start, tr.end, substep=30),
                             'skyline_max_delta_deg': float(np.max(np.abs(profile-sky)))})
        coarse = track(site, sky, 2)
        variants.append({'name': '1200 s ephemeris cadence', 'full': scoring.intervals(coarse.clear, coarse.start, coarse.end, substep=30)})
        variants.append({'name': '15 s boundary search', 'full': scoring.intervals(base.clear, base.start, base.end, substep=15)})
        # +/-1 s around refined crossings prevents a rounded endpoint yielding a stable pass.
        variants.append({'name': '1 s adverse event rounding', 'full': [[a+(a>base.start), b-(b<base.end)] for a,b in variants[0]['full']]})
        any_sun = scoring.intervals(base.partial_margin, base.start, base.end, substep=15)
        events = []
        for kind, intervals in [('Full to partial', variants[0]['full']), ('Partial to blocked', any_sun)]:
            for a,b in intervals:
                if b < base.end:
                    t = b+1
                    p = base.at(float(t))
                    events.append({'kind': kind, 'unix': t, 'utc': iso(t), 'sun_az_deg': float(p['sun_az']),
                                   'sun_el_deg': float(p['sun_el']), 'sun_radius_deg': float(p['sun_r']),
                                   'skyline_deg': float(terrain.skyline_at(sky, p['sun_az'])),
                                   'boundary_check': {'before_margin_deg': float(base.clear(float(t-1)) if kind == 'Full to partial' else base.partial_margin(float(t-1))),
                                                      'after_margin_deg': float(base.clear(float(t)) if kind == 'Full to partial' else base.partial_margin(float(t)))}})
        records.append({'id': site['id'], 'site': site, 'variants': variants, 'sun_any': any_sun, 'events': events,
                        'coverage': [base.start, base.end], 'status': 'Evaluated model sensitivity; incomplete physical uncertainty budget',
                        'observer': {'height_m': 1., 'frame': source['conventions']['frame'], 'datum': source['conventions']['elevation_datum']},
                        'limits': ['Terrain within 100 m excluded; rays stop at 400 km.', 'Skyline approximated as level across solar disk.',
                                   '40 m registration and 0.5–2 m height are sensitivity probes, not certified errors.',
                                   '600/1200 s cadence comparison is not an independent finer Horizons query.',
                                   'QuickMap decisive-ridge and Moon Trek profile review pending.']})
    # Prefer a polar ridge loss with the Sun still above a level horizon.
    candidates = []
    for record in reversed(records):
        for event in record['events']:
            if event['kind'] != 'Full to partial' or event['sun_el_deg'] <= event['sun_radius_deg']:
                continue
            loss = event['unix']
            for start in range(loss-3540, min(loss+43200,record['coverage'][1]-3600), 60):
                if verdict(record, start, 3600) == 'Misses':
                    for earlier in range(loss-4500, max(record['coverage'][0], loss-172800), -600):
                        fits = [fit(v['full'], earlier, 4500) for v in record['variants']]
                        if all(fits):
                            candidates.append({'site': record['id'], 'initial_start': start, 'alternative_start': earlier,
                                               'loss': loss, 'loss_utc': iso(loss), 'initial_utc': iso(start), 'alternative_utc': iso(earlier),
                                               'alternative_margin_lower_s': min(iv[1]+1-earlier-3600 for iv in fits),
                                               'event': event})
                            break
                    if candidates:
                        break
            if candidates:
                break
        if candidates:
            break
    if not candidates:
        raise RuntimeError('No stable teaching pair found; do not publish predetermined dates')
    package = {'schema': 'moonward-last-light/1', 'requirements': {'setup_s': 900, 'observation_s': 2700, 'bonus_margin_s': 900, 'training_only': True},
               'source': {'path': 'res://data/mission.json', 'sha256': sha(SOURCE), 'conventions': source['conventions'], 'references': source['sources'],
                          'raw_horizons': [{'path': str(p.relative_to(ROOT)), 'sha256': sha(p)} for p in sorted((ROOT/'tools/data/raw').glob('horizons_10_*.txt'))],
                          'terrain_files': [{'path': str(p.relative_to(ROOT)), 'sha256': sha(p)} for p in sorted((ROOT/'tools/data/source').glob('*')) if p.suffix in ['.npz','.tif','.img','.lbl']],
                          'generator': 'tools/data/build_last_light.py'},
               'featured': candidates[0], 'records': records,
               'validation': {'variant_count_per_site': len(records[0]['variants']), 'independent_source_audit': 'pending', 'bound_scope': 'evaluated model variants only',
                              'prior_horizons_crosscheck': source['cross_check_vs_subpoint_table'], 'terrain_registration': 'spherical MEAN_ME transforms and 40 m perturbations; absolute registration not certified'}}
    OUT.write_text(json.dumps(package, separators=(',',':')), encoding='utf-8')
    print(json.dumps(package['featured'], indent=2))
    print('Wrote', OUT, flush=True)

if __name__ == '__main__':
    build()
