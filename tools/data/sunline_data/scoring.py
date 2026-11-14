"""Sunlight and Earth-visibility intervals, and the mission rule, from sampled sky positions and a skyline.

Mission rule (the 6 h requirement is FICTIONAL): after touchdown the rover needs SAMPLING_HOURS of continuous
sunlight in which the ENTIRE apparent solar disc is above the local terrain skyline, seen from the panel height.

- Sun margin m(t) = sun elevation - sun angular radius - skyline elevation toward the sun's azimuth (degrees).
  Full disc clear when m >= 0. Partly hidden when -2r < m < 0. Hidden when m <= -2r.
  The skyline is treated as level across the 0.5° disc; at 0.1° skyline steps that is the documented approximation.
- Earth occulting the Sun (a lunar eclipse seen from the Moon) also breaks full-disc sunlight: any overlap of the
  two discs counts as not clear.
- Earth reading (geometric only, no comms claim): Earth is "up" when the centre of its disc is above the skyline.

Positions are linearly interpolated between the 10-minute Horizons samples (azimuth unwrapped). Each 10-minute step
is checked at 1-minute sub-steps, and every sign change is refined by bisection to 1 second, so a ridge crossed
between samples is still caught.
"""
import numpy as np
from .terrain import skyline_at
from .constants import SAMPLING_HOURS, SUBSTEP_S


class Track:
    """Sky positions of the Sun and Earth over one site, with interpolation in time."""

    def __init__(self, unix, sun_az, sun_el, sun_r, earth_az, earth_el, earth_r, skyline):
        self.unix = np.asarray(unix, np.int64)
        self.t = self.unix.astype(float)
        self.sun_az = np.unwrap(np.asarray(sun_az, float), period=360.)
        self.sun_el = np.asarray(sun_el, float)
        self.sun_r = np.asarray(sun_r, float)
        self.earth_az = np.unwrap(np.asarray(earth_az, float), period=360.)
        self.earth_el = np.asarray(earth_el, float)
        self.earth_r = np.asarray(earth_r, float)
        self.skyline = np.asarray(skyline, float)

    @property
    def start(self):
        return int(self.unix[0])

    @property
    def end(self):
        return int(self.unix[-1])

    def at(self, t):
        t = np.asarray(t, float)
        f = lambda v: np.interp(t, self.t, v)
        return {'sun_az': f(self.sun_az) % 360, 'sun_el': f(self.sun_el), 'sun_r': f(self.sun_r),
                'earth_az': f(self.earth_az) % 360, 'earth_el': f(self.earth_el), 'earth_r': f(self.earth_r)}

    def sun_margin(self, t, skyline_offset=0.):
        p = self.at(t)
        return p['sun_el']-p['sun_r']-(skyline_at(self.skyline, p['sun_az'])+skyline_offset)

    def eclipse_margin(self, t):
        """Angular gap between the Sun's and Earth's discs (degrees); negative means they overlap."""
        p = self.at(t)
        def vec(az, el):
            az, el = np.radians(az), np.radians(el)
            return np.stack([np.cos(el)*np.sin(az), np.cos(el)*np.cos(az), np.sin(el)], axis=-1)
        sep = np.degrees(np.arccos(np.clip(np.sum(vec(p['sun_az'], p['sun_el'])*vec(p['earth_az'], p['earth_el']), axis=-1), -1, 1)))
        return sep-p['sun_r']-p['earth_r']

    def clear(self, t, skyline_offset=0.):
        """Full-disc sunlight margin: positive when the whole disc is above the skyline and not behind Earth."""
        return np.minimum(self.sun_margin(t, skyline_offset), self.eclipse_margin(t))

    def sun_visible_fraction(self, t):
        p = self.at(t)
        x = np.clip((p['sun_el']-skyline_at(self.skyline, p['sun_az']))/p['sun_r'], -1, 1)
        return (np.arccos(-x)+x*np.sqrt(1-x**2))/np.pi

    def earth_margin(self, t, skyline_offset=0.):
        p = self.at(t)
        return p['earth_el']-(skyline_at(self.skyline, p['earth_az'])+skyline_offset)

    def partial_margin(self, t):
        """Positive while any part of the solar disc is above the skyline."""
        p = self.at(t)
        return p['sun_el']+p['sun_r']-skyline_at(self.skyline, p['sun_az'])


def intervals(fn, start, end, substep=SUBSTEP_S):
    """[[a, b], ...] (unix seconds) where fn(t) >= 0 between start and end, crossings refined to 1 s."""
    grid = np.arange(start, end+1, substep, dtype=float)
    if grid[-1] != end:
        grid = np.append(grid, float(end))
    ok = fn(grid) >= 0
    out, open_at = [], (int(start) if ok[0] else None)
    for i in np.flatnonzero(ok[1:] != ok[:-1]):
        lo, hi = grid[i], grid[i+1]
        want = ok[i]                      # state on the left of the crossing
        while hi-lo > 1:
            mid = np.floor((lo+hi)/2)
            if (fn(np.array([mid]))[0] >= 0) == want:
                lo = mid
            else:
                hi = mid
        if want:                          # interval closes at the last second still clear
            out.append([open_at, int(lo)])
            open_at = None
        else:                             # interval opens at the first clear second
            open_at = int(hi)
    if open_at is not None:
        out.append([open_at, int(end)])
    return out


def evaluate(sun_intervals, touchdown, data_end, hours=SAMPLING_HOURS):
    """Mission result for a touchdown time, using the precomputed full-disc intervals.

    Time convention: an interval [a, b] means full-disc sunlight for whole seconds a..b, i.e. the span [a, b+1).
    The sampling block is [touchdown, touchdown + 6 h). It must fit inside the dataset: touchdown + 6 h <= data_end.

    Returns dict(pass, touchdown, sampling_end, interruption, sampled_s, remaining_s, margin_s, margin_open).
    - pass: full-disc sunlight for the whole sampling block.
    - interruption: first second without full-disc sunlight inside the block (None on pass).
    - sampled_s: continuous sampling done before the interruption; remaining_s: what was still needed.
    - margin_s: on pass, verified sunlight left after sampling ends; margin_open=True when sunlight continues to the
      end of the dataset, so the true margin is at least margin_s.
    """
    need = int(round(hours*3600))
    finish = touchdown+need
    if finish > data_end:
        raise ValueError('touchdown too late: the dataset ends before the sampling block does')
    for a, b in sun_intervals:
        if a <= touchdown <= b:
            if b+1 >= finish:
                open_end = b >= data_end
                margin = (data_end if open_end else b+1)-finish
                return {'pass': True, 'touchdown': touchdown, 'sampling_end': finish, 'interruption': None,
                        'sampled_s': need, 'remaining_s': 0, 'margin_s': margin, 'margin_open': open_end}
            done = b+1-touchdown
            return {'pass': False, 'touchdown': touchdown, 'sampling_end': finish, 'interruption': b+1,
                    'sampled_s': done, 'remaining_s': need-done, 'margin_s': None, 'margin_open': False}
    return {'pass': False, 'touchdown': touchdown, 'sampling_end': finish, 'interruption': touchdown,
            'sampled_s': 0, 'remaining_s': need, 'margin_s': None, 'margin_open': False}
