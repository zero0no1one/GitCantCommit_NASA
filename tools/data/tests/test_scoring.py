"""Unit tests for the Sunline pipeline. Run from tools/data: python -m unittest discover -s tests -v"""
import json
import sys
import unittest
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sunline_data import scoring, horizons                       # noqa: E402
from sunline_data.constants import MISSION_JSON, GOLDEN_JSON, SAMPLING_HOURS   # noqa: E402

H = 3600
NEED = int(SAMPLING_HOURS*H)


def flat_track(sun_el, n=6*24+1, step=600, sun_r=.25, skyline=0., earth_el=-30., earth_az=180.):
    """Sun moving east->west at a fixed or scripted elevation over a level skyline."""
    t = np.arange(n)*step
    el = sun_el(t) if callable(sun_el) else np.full(n, float(sun_el))
    return scoring.Track(t, np.linspace(90, 270, n), el, np.full(n, sun_r),
                         np.full(n, earth_az), np.full(n, earth_el), np.full(n, .95), np.full(3600, skyline))


class Intervals(unittest.TestCase):
    def test_crossings_found_to_the_second(self):
        f = lambda t: np.where((t >= 1000) & (t <= 5000), 1., -1.)
        self.assertEqual(scoring.intervals(f, 0, 10000), [[1000, 5000]])

    def test_short_gap_between_samples_is_caught(self):
        # a 5-minute dip inside one 10-minute sample step must still split the interval
        f = lambda t: np.where((t >= 3010) & (t < 3310), -1., 1.)
        self.assertEqual(scoring.intervals(f, 0, 6000), [[0, 3009], [3310, 6000]])

    def test_open_at_both_edges(self):
        self.assertEqual(scoring.intervals(lambda t: np.ones_like(t), 0, 7200), [[0, 7200]])
        self.assertEqual(scoring.intervals(lambda t: -np.ones_like(t), 0, 7200), [])


class DiscRule(unittest.TestCase):
    def test_full_disc_needs_lower_limb_above_skyline(self):
        r = .25
        tr = flat_track(sun_el=r+.01)                       # lower limb 0.01° above a level skyline
        self.assertTrue(np.all(tr.clear(tr.t) > 0))
        tr = flat_track(sun_el=r-.01)                       # lower limb clipped: partial, not full
        self.assertTrue(np.all(tr.clear(tr.t) < 0))
        self.assertTrue(np.all(tr.partial_margin(tr.t) > 0))

    def test_half_disc_fraction(self):
        tr = flat_track(sun_el=0.)
        self.assertAlmostEqual(float(tr.sun_visible_fraction(np.array([0.]))[0]), .5, places=6)

    def test_earth_over_sun_is_not_clear(self):
        tr = flat_track(sun_el=10., earth_el=10.)
        t = np.array([tr.t[len(tr.t)//2]])                  # Sun passes azimuth 180°, where Earth sits
        self.assertLess(float(tr.eclipse_margin(t)[0]), 0)
        self.assertLess(float(tr.clear(t)[0]), 0)

    def test_ridge_crossing_between_samples(self):
        # Sun sinks through the lower-limb threshold 0.25° between two 10-minute samples
        tr = flat_track(sun_el=lambda t: 1.0-t/(4*H))       # 0.25° per hour
        iv = scoring.intervals(tr.clear, tr.start, tr.end)
        self.assertEqual(len(iv), 1)
        self.assertAlmostEqual(iv[0][1], 3*H, delta=2)      # 1.0-0.25 = 0.75 → 3 h


class MissionRule(unittest.TestCase):
    def test_exact_six_hours_passes(self):
        # clear for seconds 0..NEED-1 = exactly the block [0, NEED)
        r = scoring.evaluate([[0, NEED-1]], 0, 10*H)
        self.assertTrue(r['pass'])
        self.assertEqual(r['margin_s'], 0)

    def test_one_second_short_fails(self):
        r = scoring.evaluate([[0, NEED-2]], 0, 10*H)
        self.assertFalse(r['pass'])
        self.assertEqual(r['interruption'], NEED-1)
        self.assertEqual(r['sampled_s'], NEED-1)
        self.assertEqual(r['remaining_s'], 1)

    def test_pass_margin_counts_seconds_after_block(self):
        r = scoring.evaluate([[0, NEED+599]], 0, 10*H)
        self.assertTrue(r['pass'])
        self.assertEqual(r['margin_s'], 600)
        self.assertFalse(r['margin_open'])

    def test_touchdown_in_darkness(self):
        r = scoring.evaluate([[5*H, 20*H]], H, 30*H)
        self.assertFalse(r['pass'])
        self.assertEqual(r['interruption'], H)
        self.assertEqual(r['sampled_s'], 0)
        self.assertEqual(r['remaining_s'], NEED)

    def test_dataset_edge(self):
        self.assertTrue(scoring.evaluate([[0, 10*H]], 4*H, 10*H)['pass'])
        self.assertTrue(scoring.evaluate([[0, 10*H]], 4*H, 10*H)['margin_open'])
        with self.assertRaises(ValueError):
            scoring.evaluate([[0, 10*H]], 4*H+1, 10*H)


class HorizonsParse(unittest.TestCase):
    def test_parse_row(self):
        text = ('header\n$$SOE\n 2027-Mar-01 00:00, ,i,  271.002129217,     -27.950112007,  1937.327,  '
                '0.99026270266505, -0.4536606,\n$$EOE\n')
        p = horizons.parse(text)
        self.assertEqual(int(p['unix'][0]), 1803859200)     # 2027-03-01T00:00:00Z
        self.assertAlmostEqual(float(p['az'][0]), 271.002129217)
        self.assertAlmostEqual(float(p['radius'][0]), 1937.327/7200)
        self.assertAlmostEqual(float(p['range_km'][0]), 0.99026270266505*horizons.AU_KM)


@unittest.skipUnless(MISSION_JSON.exists() and GOLDEN_JSON.exists(), 'run build_mission.py first')
class BundledData(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = json.loads(MISSION_JSON.read_text())
        cls.g = json.loads(GOLDEN_JSON.read_text())

    def track(self, s):
        smp = s['samples']
        unix = smp['start_unix']+np.arange(smp['count'])*smp['step_s']
        return scoring.Track(unix, smp['sun_az'], smp['sun_el'], smp['sun_radius'], smp['earth_az'],
                             smp['earth_el'], smp['earth_radius'], s['skyline']['elevation_deg'])

    def test_window_leaves_room_for_the_block(self):
        w = self.m['window']
        self.assertLessEqual(w['touchdown_max_unix']+NEED, w['end_unix'])
        self.assertEqual(w['touchdown_min_unix'], w['start_unix'])

    def test_shapes(self):
        for s in self.m['sites']:
            self.assertEqual(len(s['skyline']['elevation_deg']), 3600)
            n = s['samples']['count']
            for k in ('sun_az', 'sun_el', 'sun_radius', 'earth_az', 'earth_el', 'earth_radius'):
                self.assertEqual(len(s['samples'][k]), n)

    def test_bundled_samples_reproduce_bundled_intervals(self):
        # the game's numbers and the scored intervals must come from the same data
        for s in self.m['sites']:
            tr = self.track(s)
            got = scoring.intervals(tr.clear, tr.start, tr.end)
            self.assertEqual(got, [x[:2] for x in s['intervals']['sun_full']])

    def test_no_eclipse_in_window(self):
        for s in self.m['sites']:
            self.assertGreater(s['min_sun_earth_gap_deg'], 0)

    def test_golden_matches_bundled_intervals(self):
        end = self.m['window']['end_unix']
        for s in self.m['sites']:
            iv = [x[:2] for x in s['intervals']['sun_full']]
            for t, want in zip(self.g['touchdowns'][::7], self.g['results'][s['id']][::7]):
                self.assertEqual(scoring.evaluate(iv, t, end), want)

    def test_examples_hold(self):
        ex, end = self.m['examples'], self.m['window']['end_unix']
        sites = {s['id']: [x[:2] for x in s['intervals']['sun_full']] for s in self.m['sites']}
        a = ex['same_site']
        self.assertTrue(scoring.evaluate(sites[a['site']], a['pass_touchdown'], end)['pass'])
        self.assertFalse(scoring.evaluate(sites[a['site']], a['fail_touchdown'], end)['pass'])
        for key in ('same_time', 'same_time_reverse'):
            if key in ex:
                b = ex[key]
                self.assertTrue(scoring.evaluate(sites[b['winner']], b['touchdown'], end)['pass'])
                self.assertFalse(scoring.evaluate(sites[b['loser']], b['touchdown'], end)['pass'])


if __name__ == '__main__':
    unittest.main()
