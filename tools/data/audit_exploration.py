"""Offline integrity audit only; never promotes scientific validation flags."""
import hashlib
import json
import math
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def audit():
    rows = []
    for path in sorted((REPO / 'data/exploration').glob('*.json')):
        pack = json.loads(path.read_text())
        assert pack['validated'] is False
        for site in pack['sites']:
            s = site['samples']
            assert s['count'] == 4321 and s['step_s'] == 600
            for key in ('sun_az', 'sun_el', 'sun_radius', 'earth_az', 'earth_el', 'earth_radius'):
                assert len(s[key]) == s['count'] and all(map(math.isfinite, s[key]))
            assert len(site['skyline']['elevation_deg']) == 3600
            assert all(map(math.isfinite, site['skyline']['elevation_deg']))
            end = s['start_unix'] + (s['count'] - 1)*s['step_s']
            for key in ('sun_full', 'sun_any', 'earth_up'):
                previous = s['start_unix'] - 1
                for iv in site['intervals'][key]:
                    assert previous < iv[0] <= iv[1] <= end
                    previous = iv[1]
            rows.append({'window': pack['scenario_id'], 'site': site['id'],
                         'samples_per_body': s['count'], 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                         'generator_reported_cross_check_not_rerun': pack['cross_checks'][site['id']],
                         'scientifically_validated': False})
    assert len(rows) == 16
    output = REPO / 'tools/data/exploration-audit.json'
    output.write_text(json.dumps({'scope': 'Offline structure, finite samples, skyline length and ordered interval bounds only. Independent ephemeris/terrain/event validation NOT completed.', 'records': rows}, indent=2))
    print('16 provisional records: structure audit passed; scientific validation remains false')


if __name__ == '__main__':
    audit()
