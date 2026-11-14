"""Campaign checks: data/campaign.json matches the mission data and every mission is fair.
Run from tools/data: python -m unittest discover -s tests -v"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sunline_data import scoring                                          # noqa: E402
from sunline_data.constants import MISSION_JSON                           # noqa: E402
import build_campaign                                                     # noqa: E402


class Campaign(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = json.loads(MISSION_JSON.read_text(encoding='utf-8'))
        cls.c = json.loads(build_campaign.CAMPAIGN_JSON.read_text(encoding='utf-8'))
        cls.sites = {s['id']: s for s in cls.m['sites']}

    def test_bundled_file_is_current(self):
        fresh = build_campaign.build()        # rebuilds the file; identical apart from the timestamp
        strip = lambda d: {k: v for k, v in d.items() if k != 'generated_utc'}
        self.assertEqual(strip(fresh), strip(self.c))

    def test_windows_inside_data(self):
        w = self.m['window']
        for mi in self.c['missions']:
            self.assertGreaterEqual(mi['window']['start'], w['touchdown_min_unix'])
            self.assertLessEqual(mi['window']['end']+mi['need_s'], w['end_unix'])
            self.assertEqual((mi['window']['start']-w['touchdown_min_unix']) % w['touchdown_step_s'], 0)

    def test_every_mission_is_fair(self):
        end = self.m['window']['end_unix']
        for mi in self.c['missions']:
            with self.subTest(mission=mi['id']):
                ok = fail = False
                for sid in mi['sites']:
                    iv = [x[:2] for x in self.sites[sid]['intervals']['sun_full']]
                    st = mi['stats'][sid]
                    if st['example_pass'] is not None:
                        self.assertTrue(scoring.evaluate(iv, st['example_pass'], end, mi['need_s']/3600)['pass'])
                        ok = True
                    if st['example_fail'] is not None:
                        self.assertFalse(scoring.evaluate(iv, st['example_fail'], end, mi['need_s']/3600)['pass'])
                        fail = True
                self.assertTrue(ok, 'no robust passing touchdown')
                partial_bonus = any(s['bonus_touchdowns'] is not None and 0 < s['bonus_touchdowns'] < s['touchdowns']
                                    for s in mi['stats'].values())
                self.assertTrue(fail or partial_bonus, 'nothing to get wrong')


if __name__ == '__main__':
    unittest.main()
