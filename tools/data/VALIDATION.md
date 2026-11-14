# Sunline data validation

Generated 2026-11-13 16:06 UTC by `tools/data/validate.py` from `data/mission.json` (window 2028-02-18T00:00:00Z → 2028-03-19T00:00:00Z).

## 1. Sun and Earth positions vs an independent Horizons query

The game uses topocentric Horizons az/el (observer on the Moon). The check converts a separate geocentric Horizons table (sub-solar and sub-Earth points, MOON_ME) into local az/el with our own geometry, hourly over the window.

| Site | Sun elevation | Sun azimuth (below 80° el.) | Earth elevation | Earth azimuth | Samples |
|---|---|---|---|---|---|
| apollo-11 | 0.0009° | 0.0085° | 0.0058° | 0.0038° | 721 |
| sl3 | 0.0008° | 0.0003° | 0.0006° | 0.0061° | 721 |

Values are the largest absolute difference. Both are far below the 0.1° displayed precision.

## 2. Polar lighting vs NASA PGDA LOLA average illumination

Reference: PGDA `AVGVISIB_85S_060M_201608` (https://pgda.gsfc.nasa.gov/data/MoonIllumination/AVGVISIB_85S_060M_201608.TIF), mean fraction of the solar disc visible, 60 m polar stereographic (Mazarico, E. et al. 2011, Icarus 211, 1066–1081, doi:10.1016/j.icarus.2010.10.030). Ours: mean visible solar fraction from the 1° skyline at 1.0 m panel height with the hourly 2026–2030 Horizons table. Periods and observer heights differ, so a few points of difference are expected.

Our sites are crest points picked on the 80 m grid, and PGDA values change by tens of points within one 60 m pixel on these crests, so the fair comparison is with the brightest pixel of the 3×3 neighbourhood (the crest). The single-pixel column is shown for completeness.

Projection check: reading PGDA with either map axis flipped gives implausible values (most near zero), which confirms our polar stereographic convention matches PGDA's.

| Site | Lat | Ours | PGDA crest (3×3 max) | PGDA pixel | PGDA 3×3 range | Ours − crest |
|---|---|---|---|---|---|---|
| site01 Connecting ridge | -89.44 | 84.5% | 75.5% | 44.3% | 44.3–75.5% | +9.1 pts |
| sl3 Connecting ridge extension **(game site)** | -89.32 | 76.8% | 79.4% | 74.9% | 23.6–79.4% | -2.7 pts |
| site04 Shackleton rim | -89.49 | 62.0% | 71.4% | 61.7% | 47.3–71.4% | -9.5 pts |
| site07 Peak near Shackleton | -88.81 | 82.4% | 86.0% | 71.7% | 48.9–86.0% | -3.6 pts |
| site06 Nobile rim 1 | -85.23 | 63.6% | 57.8% | 55.6% | 52.9–57.8% | +5.8 pts |
| dm2 Nobile rim 2 | -84.10 | 50.4% | 51.9% | 46.6% | 46.6–51.9% | -1.5 pts |
| site11 de Gerlache rim | -88.66 | 80.9% | 82.7% | 82.7% | 38.3–82.7% | -1.8 pts |
| site42 de Gerlache-Kocher massif | -85.46 | 33.1% | 42.3% | 39.3% | 11.7–42.3% | -9.2 pts |
| site20 Leibnitz Beta plateau | -85.40 | 60.4% | 64.0% | 49.7% | 49.6–64.0% | -3.6 pts |
| site23 Malapert massif | -85.99 | 60.6% | 60.4% | 55.6% | 48.9–60.4% | +0.2 pts |
| haworth Haworth | -86.36 | 60.5% | 63.1% | 49.3% | 41.3–63.1% | -2.5 pts |
| dm1 Amundsen rim | -84.56 | 51.5% | outside map | | | |
| lm7 Faustini rim A | -87.77 | 65.4% | 63.7% | 62.9% | 44.8–63.7% | +1.7 pts |

Across 12 sites, against the crest: r = 0.933, mean difference -1.5 pts, mean |difference| 4.3 pts, largest 9.5 pts. Against the single pixel: r = 0.654, mean +7.2 pts, largest 40.2 pts.

## 3. Skyline sensitivity to terrain resolution

How far the skyline moves if the finest terrain layer at the site is removed. This bounds the effect of DEM resolution; the error of the finer product itself is expected to be smaller. The game shows timing uncertainty for a ±0.1° skyline error, and every showcase example keeps its outcome under ±0.3°.

| Site | Layer removed | Median | 90th pct | Max |
|---|---|---|---|---|
| apollo-11 | 118 m patch → 7.6 km LDEM_4 | 0.243° | 0.491° | 0.845° |
| sl3 | 80 m patch → 640 m mosaic | 0.049° | 4.003° | 5.152° |

## 4. Interval edges, partial sunlight, dataset edges

**Apollo 11 (apollo-11)**

- Full-disc boundaries checked 1–2 s inside and outside: 2/2 correct.
- Partial sunlight (some but not all of the disc): 2.1 h in the window.
- Last allowed touchdown 2028-03-18 18:00: fail; one step later is refused: yes.

**Connecting ridge extension (sl3)**

- Full-disc boundaries checked 1–2 s inside and outside: 12/12 correct.
- Partial sunlight (some but not all of the disc): 103.6 h in the window.
- Last allowed touchdown 2028-03-18 18:00: pass; one step later is refused: yes.

Golden parity: 4285 touchdowns × 2 sites re-scored from the bundled intervals, 0 mismatches.

## 5. Showcase examples (verified, robust to the larger skyline error)

- Same site (sl3): touchdown 2028-03-12 09:40 passes; 2028-03-12 05:20 fails (4.3 h apart).
- Same time 2028-02-18 12:00: sl3 passes, apollo-11 fails.
- Same time 2028-03-01 19:40: apollo-11 passes, sl3 fails.

## 6. Checks still needing a person

- **LROC Quickmap** (https://quickmap.lroc.asu.edu/): open the polar site, turn on the LOLA illumination / topography layers, and confirm the ridge that blocks the Sun matches our skyline peak direction. Record the result here.
- **NASA Moon Trek** (https://trek.nasa.gov/moon/): draw elevation profiles from each site toward the skyline maximum and compare the angle with ours.
- First-time player test (one minute to explain the choice) — pending.

## Known limits

- Terrain within 100 m of the site is not used for the skyline (DEM pixels are 80–118 m).
- The skyline is treated as level across the 0.5° solar disc when estimating partial sunlight.
- Panel height 1.0 m is a modelled assumption; the 6 h requirement is fictional.
- Earth visibility is a geometric reading (centre of Earth above the skyline), not a link budget.
- Times are linearly interpolated between 10-minute Horizons samples (Sun moves < 0.1° per step).
