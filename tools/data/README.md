# Sunline data pipeline

Builds `data/mission.json`, the dataset bundled with the game. The game makes no live NASA requests; every number it shows comes from this file.

## What it produces

| File | What it is |
|---|---|
| `../../data/mission.json` (~0.5 MB) | Both sites, their 0.1° skylines, Sun and Earth positions every 10 min, scored intervals, showcase examples, conventions and sources |
| `golden_results.json` | Mission result for every 10-minute touchdown at both sites. The Godot tests compare against it |
| `window_search.json` | Top 100 candidate windows from the coarse search |
| `VALIDATION.md` | Independent checks and their measured results |

## The mission rule

> Your rover needs six continuous hours of direct sunlight after touchdown to collect a sample.

- **Six hours is a fictional instrument requirement.**
- A plan **passes** when the **entire apparent solar disc** stays above the local terrain skyline for the whole block [touchdown, touchdown + 6 h). The skyline is seen from the rover's panel at **1.0 m** (a modelled assumption), and Earth must not overlap the Sun.
- Partial sunlight, where only part of the disc is visible, does not count.
- The Earth row is a geometric reading only: the centre of Earth's disc is above the skyline. It makes no communications claim.

## Chosen sites and window

The data picked these sites and dates; nobody hand-chose them.

- **Tranquility Base:** Apollo 11, 0.674° N 23.473° E (NSSDC, mean-Earth/polar-axis frame).
- **Connecting ridge extension (sl3):** 89.3168° S 114.0411° W. This is one of NASA GSFC PGDA's surveyed south-pole landing-site regions. The point is the local crest on the 80 m map, not an official landing point.
- **Window:** 2028-02-18 to 2028-03-19 UTC.
  - Touchdown can be anywhere from the window start to 6 h before its end, in 10-minute steps.
  - No eclipse occurs: Sun and Earth stay at least 2.6° apart.
- **Showcase examples:** listed in `VALIDATION.md`. Each one keeps its outcome even if the whole skyline is 0.3° higher or lower.

## Conventions

| Item | Convention |
|---|---|
| Frame | Moon mean-Earth/polar-axis (MEAN_ME = MOON_ME), east longitude positive. Horizons reports its lunar observer frame as `MEAN_ME`, so no conversion is needed |
| Elevation datum | Heights above a 1,737.4 km sphere. LOLA heights and Horizons site altitudes use the same sphere |
| Azimuth | True compass bearing: 0° toward the lunar north pole, clockwise |
| Refraction | None (airless) |
| Time | UTC, stored as unix seconds |
| Interval `[a, b]` | Full-disc sunlight for whole seconds a..b, i.e. the span [a, b+1) |
| Uncertainty | Interval edges carry how far they move for a ±0.1° skyline error. Show times to the minute with that band |

## How it works

1. **`search_windows.py`** (seconds, offline)
   - Scores every 30-day window from 2027 to 2030 for all 13 polar sites against Tranquility.
   - Uses the hourly Horizons sub-point table and 1° skylines.
   - Rejects windows within 3° of an eclipse.
   - A window qualifies when touchdown time changes the outcome at the polar site, the two sites disagree in both directions, and Earth rises and sets at the polar site.
2. **`build_mission.py`** (needs network on first run; responses are cached in `raw/`)
   - Fetches topocentric JPL Horizons Sun and Earth positions at both sites, every 10 minutes.
   - Builds 0.1° skylines (3,600 rays, 100 m to 400 km, sphere geometry).
   - Rounds everything to the bundled precision, then scores. The game's numbers and the scored intervals are therefore identical.
   - Finds crossings at 1-minute sub-steps, refined to 1 s by bisection.
   - Picks robust showcase examples and writes the outputs.
3. **`validate.py`** writes `VALIDATION.md`. It needs network access to read about 1 MB from the PGDA map.
4. **`fetch_tranquility_dem.py`** cuts the 2°×2° 118 m Tranquility patch.
   - It is already in `source/`, so you only re-run it to rebuild from scratch.
   - It range-reads about 94 MB from USGS.

## Run it

```bash
cd tools/data
pip install -r requirements.txt
python search_windows.py
python build_mission.py
python -m unittest discover -s tests -v
python validate.py
```

Re-running is offline as long as `raw/` holds the cached Horizons responses.

## Sources

| Data | Product | Reference |
|---|---|---|
| Sun and Earth positions | NASA JPL Horizons (DE441), observer `coord@301`. https://ssd.jpl.nasa.gov/horizons/ | Giorgini, J. D. et al., JPL Horizons |
| Window search and cross-check | Horizons sub-solar and sub-Earth points, hourly 2026–2030 (`source/ephemeris_moon_2026_2030.csv.gz`, from the team's Echo-Path project) | |
| Polar terrain, 80 m | NASA GSFC PGDA `LDEM_80S_80MPP_ADJ`, https://pgda.gsfc.nasa.gov/products/90 | Barker, M. K. et al. (2023), PSJ 4, 183, doi:10.3847/PSJ/acf3e1 |
| Polar terrain, 640 m | Same mosaic, averaged | as above |
| Polar site list | PGDA south pole landing-site DEMs, https://pgda.gsfc.nasa.gov/products/78 | Barker, M. K. et al. (2021), PSS 203, 105119, doi:10.1016/j.pss.2020.105119 |
| Tranquility terrain, 118 m | LOLA LDEM 256 px/deg global mosaic, USGS Astrogeology, https://planetarymaps.usgs.gov/mosaic/Lunar_LRO_LOLA_Global_LDEM_118m_Mar2014.tif | Smith, D. E. et al. (2010), GRL 37, L18204, doi:10.1029/2010GL043751 |
| Global terrain, 7.6 km | LOLA `LDEM_4`, PDS Geosciences Node | Smith et al. (2010) |
| Illumination check | PGDA `AVGVISIB_85S_060M_201608`, https://pgda.gsfc.nasa.gov/products/69 | Mazarico, E. et al. (2011), Icarus 211, 1066, doi:10.1016/j.icarus.2010.10.030 |
| Apollo 11 coordinates | NSSDC, https://nssdc.gsfc.nasa.gov/planetary/lunar/apolloland.html | |

- **Reused code:** `sunline_data/terrain.py`, `subpoint.py` and parts of `scoring.py` are adapted from the team's Echo-Path engine (`NASA_GITCANTCOMMIT`, `NASA Project/echo_path/`).
- **Official challenge resources:** LROC Quickmap and NASA Moon Trek are the remaining cross-checks, which need a person. See `VALIDATION.md` §6.
