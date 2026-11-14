"""Build data/campaign.json: the Sunline mission campaign, checked against the bundled mission data.

Each mission is a site (or a choice of sites), a decision window for touchdown, the sunlight hours needed (the 6 h
rule is FICTIONAL; mission 8 asks for 8 h and says so), a bonus goal and a par score. Windows are hand-picked from the
real intervals in data/mission.json (see README.md, "Campaign"); this script only scores them and refuses to write a
mission that is not fair:
  - at least one touchdown passes in the window, and one of them still passes when every interval edge is moved
    against the player by its listed skyline uncertainty (a "robust" pass);
  - the mission has something to get wrong: some touchdown fails, or the bonus is not met everywhere;
  - a data bonus (margin, early touchdown, Earth up) can be met together with a pass.
Scores use the same evaluate() as the game (Godot's port is checked against it in tests/test_campaign.gd).

Run from tools/data:  python build_campaign.py
"""
import datetime as dt
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sunline_data import scoring                                  # noqa: E402
from sunline_data.constants import MISSION_JSON                   # noqa: E402

CAMPAIGN_JSON = MISSION_JSON.parent/'campaign.json'
H = 3600


def utc(s):
    """'03-01 19:00' -> unix seconds in the 2028 window."""
    return int(dt.datetime.strptime('2028-'+s, '%Y-%m-%d %H:%M').replace(tzinfo=dt.timezone.utc).timestamp())


# id, title, tagline, sites, need_h, window (UTC) or fixed example, bonus, par, brief
MISSIONS = [
    dict(id='first-light', title='First Light', tagline='Catch the sunrise at Tranquility Base.',
         sites=['apollo-11'], need_h=2, window=('03-01 08:00', '03-02 12:00'),
         bonus=dict(type='touchdown_before', utc='03-01 22:00', text='Land within 3 hours of sunrise'), par=1800,
         brief='Night is ending at Tranquility Base. Drag the Sun along its path and find the moment it clears the '
               'horizon. Your rover only needs 2 hours of light for this test run.'),
    dict(id='before-sunset', title='Before Sunset', tagline='Two weeks of daylight are almost over.',
         sites=['apollo-11'], need_h=6, window=('03-15 00:00', '03-16 12:00'),
         bonus=dict(type='margin', hours=12, text='Keep 12 h of sunlight in reserve'), par=2600,
         brief='The long lunar day at Tranquility is ending. Land early enough that the Sun is still up for the whole '
               '6-hour sample. Too late and the rover freezes in the dark.'),
    dict(id='ridge-runner', title='Ridge Runner', tagline='At the pole, the Sun skims the mountains.',
         sites=['sl3'], need_h=6, window=('03-08 12:00', '03-10 00:00'),
         bonus=dict(type='margin', hours=6, text='Keep 6 h of sunlight in reserve'), par=2800,
         brief='Near the south pole the Sun never climbs high. It circles the horizon and slips behind distant peaks. '
               'Find the gap where it stays clear of the ridges for 6 hours.'),
    dict(id='two-sites', title='Two Sites, One Clock', tagline='Same time. Which site has the Sun?',
         sites=['apollo-11', 'sl3'], need_h=6, fixed='same_time_reverse',
         bonus=dict(type='landing', offset_m=6, text='Land within 6 m of the target'), par=2800,
         brief='The launch is fixed: touchdown time cannot move. You can still choose where to land. One site has '
               '6 hours of sunlight ahead, the other is in darkness.'),
    dict(id='ten-minutes', title='Ten Minutes Matter', tagline='A narrow gap at the ridge.',
         sites=['sl3'], need_h=6, window=('03-12 03:00', '03-12 13:00'),
         bonus=dict(type='touchdown_before', utc='03-12 08:30', text='Land within about an hour of first light'),
         par=3000,
         brief='The Sun is about to climb out from behind a peak. Land too early and the panel sits in shadow. Land '
               'right after it clears for the best run.'),
    dict(id='earthrise', title='Earthrise', tagline='Land with the Earth in view.',
         sites=['sl3'], need_h=6, window=('02-21 00:00', '02-23 00:00'),
         bonus=dict(type='earth_up', text='Earth above the skyline at touchdown'), par=3000,
         brief='From the pole, Earth hides behind the horizon for weeks. It is about to rise over the ridge. Land in '
               'sunlight with Earth in the sky. (Earth in view is geometry only: no radio claim.)'),
    dict(id='long-day', title='Long Day', tagline='Squeeze out every hour of light.',
         sites=['sl3'], need_h=6, window=('03-10 18:00', '03-13 18:00'),
         bonus=dict(type='margin', hours=24, text='Keep 24 h of sunlight in reserve'), par=3200,
         brief='Short windows and one long one. Any 6 hours will do the job; a full day of spare sunlight earns the '
               'bonus.'),
    dict(id='endurance', title='Endurance', tagline='8 hours. One window.',
         sites=['sl3'], need_h=8, window=('03-14 18:00', '03-16 12:00'),
         bonus=dict(type='landing', offset_m=4, text='Land within 4 m of the target'), par=3500,
         brief='The upgraded drill needs 8 hours of unbroken sunlight (a made-up requirement, like the 6 h one). '
               'There is exactly one window that fits.'),
]


def robust_pass(iv, t, need):
    """Pass even when every interval is shrunk by its listed uncertainty at both ends."""
    return any(a+ua <= t and t+need <= b+1-ub for a, b, ua, ub in iv)


def robust_fail(iv, t, need, end):
    """Fail even when every interval is grown by its listed uncertainty at both ends."""
    grown = [[a-ua, b+ub] for a, b, ua, ub in iv]
    return not scoring.evaluate(grown, t, end+H*48, need/H)['pass']


def bonus_met(m, site, t, r, mission):
    b = m['bonus']
    if b['type'] == 'margin':
        return r['pass'] and r['margin_s'] >= b['hours']*H
    if b['type'] == 'touchdown_before':
        return r['pass'] and t <= utc(b['utc'])
    if b['type'] == 'earth_up':
        return r['pass'] and any(a <= t <= e for a, e, *_ in site['intervals']['earth_up'])
    return None                                          # landing bonuses depend on the player, not the data


def build():
    mission = json.loads(MISSION_JSON.read_text(encoding='utf-8'))
    sites = {s['id']: s for s in mission['sites']}
    w = mission['window']
    end, step = w['end_unix'], w['touchdown_step_s']
    out = []
    for n, m in enumerate(MISSIONS, 1):
        need = m['need_h']*H
        if 'fixed' in m:
            t0 = t1 = mission['examples'][m['fixed']]['touchdown']
        else:
            t0, t1 = utc(m['window'][0]), utc(m['window'][1])
        assert t0 >= w['touchdown_min_unix'] and t1+need <= end, f"{m['id']}: window outside the data"
        stats = {}
        for sid in m['sites']:
            iv = sites[sid]['intervals']['sun_full']
            rows = []
            for t in range(t0, t1+1, step):
                r = scoring.evaluate([x[:2] for x in iv], t, end, need/H)
                rows.append(dict(t=t, ok=r['pass'], margin=r['margin_s'], robust_ok=robust_pass(iv, t, need),
                                 robust_fail=robust_fail(iv, t, need, end), bonus=bonus_met(m, sites[sid], t, r, m)))
            passes = [x for x in rows if x['ok']]
            stats[sid] = dict(touchdowns=len(rows), passes=len(passes),
                              robust_passes=sum(x['robust_ok'] for x in rows),
                              robust_fails=sum(x['robust_fail'] for x in rows),
                              first_pass=passes[0]['t'] if passes else None,
                              last_pass=passes[-1]['t'] if passes else None,
                              best_margin_s=max((x['margin'] for x in passes), default=None),
                              bonus_touchdowns=None if m['bonus']['type'] == 'landing' else sum(bool(x['bonus']) for x in rows),
                              example_pass=next((x['t'] for x in rows if x['robust_ok']), None),
                              example_fail=next((x['t'] for x in rows if x['robust_fail']), None))
        any_robust = any(s['robust_passes'] for s in stats.values())
        any_fail = any(s['robust_fails'] for s in stats.values())
        bonus_partial = any(s['bonus_touchdowns'] is not None and 0 < s['bonus_touchdowns'] < s['touchdowns']
                            for s in stats.values())
        if not any_robust:
            raise SystemExit(f"{m['id']}: no robust passing touchdown")
        if not (any_fail or bonus_partial):
            raise SystemExit(f"{m['id']}: nothing to get wrong")
        if m['bonus']['type'] != 'landing' and not any(s['bonus_touchdowns'] for s in stats.values()):
            raise SystemExit(f"{m['id']}: bonus cannot be met")
        bonus = dict(m['bonus'])
        if 'utc' in bonus:
            bonus['unix'] = utc(bonus.pop('utc'))
        out.append(dict(id=m['id'], number=n, title=m['title'], tagline=m['tagline'], brief=m['brief'],
                        sites=m['sites'], need_s=need, window=dict(start=t0, end=t1, step=step),
                        fixed_touchdown='fixed' in m, bonus=bonus, par=m['par'], stats=stats))
    doc = dict(schema='sunline-campaign/1', generated_utc=dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds'),
               source='data/mission.json', note='Sampling hours are fictional mission requirements; all sunlight '
               'timing comes from the bundled Horizons + LOLA data.', missions=out)
    CAMPAIGN_JSON.write_text(json.dumps(doc, indent=1), encoding='utf-8', newline='\n')
    return doc


if __name__ == '__main__':
    doc = build()
    for m in doc['missions']:
        print(f"{m['number']}. {m['title']:<22}", {k: (v['passes'], v['robust_passes'], v['robust_fails'], v['bonus_touchdowns'])
                                                    for k, v in m['stats'].items()})
    print('wrote', CAMPAIGN_JSON)
