# Last Light Operations — implementation and validation

Mission 2 is a new flow at `scenes/last_light/last_light.tscn`. The campaign's existing `sunset-operations` identifier routes to it; the older six-hour operations screen remains available to the Moon map comparison and Earth Link. It does not share the new mission's assessment or claims.

## Reproduce

- Generate science: `python tools/data/build_last_light.py` (NumPy, SciPy, rasterio; cached source files required).
- Mission tests: `Godot --headless --path . --script res://tests/test_last_light.gd`.
- Rendered layout checks: omit `--headless`. Captures go to `user://last-light-WIDTHxHEIGHT.png`.
- Play directly: `Godot --path . res://scenes/last_light/last_light.tscn`.
- Browser: export the Web preset, serve `build/web` on localhost, choose Training Missions → Last Light Operations → Plan Operations.
- Mission Logs persist to `user://last_light_log.json`, including the submitted plan, comparison, source hashes, verdicts and recommendation. Browser storage is local to the browser and origin.

## Generated teaching scenarios

Dates were selected by searching the computed variants, not supplied as winning inputs. Both scenarios use Tranquility Base, 0.674° N, 23.473° E, Moon mean-Earth/polar-axis frame, at a fixed 1 m height above the modeled ground. Dates are hypothetical training dates.

| Scenario | Setup start UTC | Setup end UTC | Observation end UTC | Illumination |
|---|---|---|---|---|
| Initial, already interrupted | 2028-03-16 12:14:16 | 12:29:16 | 13:14:16 | Misses across all evaluated variants |
| Revised date/time | 2028-03-16 10:22:16 | 10:37:16 | 11:22:16 | Meets across all evaluated variants; bonus supported |

The nominal full-to-partial transition is **2028-03-16 11:57:16 UTC**, bearing **271.2944°**, solar center elevation **1.5336°**, apparent radius **0.26762°**, skyline **1.26606°**. Thus terrain interrupts full sunlight while the entire solar disk would still clear a level horizon. The revised plan has a **1,390 s (23 min 10 s) minimum margin across evaluated variants**. The initial plan is deliberately after the interruption; the red event remains visible and Inspect Limit reveals the preceding terrain transition. Starts crossing the nominal event are never classified Meets, even if total sunlight on either side would sum to an hour.

## Science package and calculations

`data/last_light.json` records the source `data/mission.json` SHA256, raw Horizons cache hashes, terrain source hashes, coordinates, coordinate source, observer datum/frame, sampled solar bearing/elevation/radius, 0.1° directional skylines, nominal full/any sunlight intervals and refined loss events for both sites. The source data came from JPL Horizons DE441 observer geometry and LOLA terrain. See the [Horizons manual](https://ssd.jpl.nasa.gov/horizons/manual.html), [PGDA polar products](https://pgda.gsfc.nasa.gov/products/78), and `tools/data/sunline_data/terrain.py` for source conventions and transforms.

Full sunlight uses the lower apparent solar limb minus the terrain skyline, with the source model's eclipse exclusion. Positive clearance is full sunlight; an upper-limb-only clearance is partial; no disk clearance is blocked. Source eclipse separation is positive throughout these bundled site periods. Event times are refined to the first non-full whole second by bisection, with explicit half-open activity intervals. The analytical horizon view and timeline use the same package as assessment; no rendered mesh, shadow, camera or astronaut position enters a verdict.

Thirteen evaluated variants per site:

- Nominal skyline and uniform +0.1° / −0.1° skyline shifts.
- Recomputed terrain skylines for 0.5 m and 2 m observers (nominal 1 m).
- Recomputed skylines for four 40 m observer-registration perturbations at cardinal bearings.
- Finest terrain removed: Tranquility 118 m patch → global 7.6 km; ridge 80 m patch → 640 m mosaic with global fallback.
- Ephemeris samples decimated from 600 s to 1200 s, retaining endpoints.
- Boundary scan reduced from 30 s to 15 s, both refined to 1 s.
- Adverse one-second event rounding.

Maximum skyline changes for height 0.5 m / 2 m: Tranquility **0.0847° / 0.1346°**, ridge **0.2866° / 0.5724°**. Removing fine terrain changes the skyline by up to **0.8455°** and **5.1579°**, respectively. These are model sensitivity results, not certified accuracy bounds. All **13 nominal loss transitions** (2 equatorial, 11 polar, counting full-to-partial and partial-to-blocked) have nonnegative clearance at t−1 s and negative clearance at t.

Assessment requires the entire consecutive setup/observation interval to fit in one uninterrupted full-sun interval in every variant for Meets. No variant fits gives Misses; disagreement gives Unknown. Setup and observation are also reported independently. Bonus uses the lowest supported margin. If a variant's next loss lies beyond coverage, the margin is a lower bound and the upper bound/event time is not invented. Missing coverage, changed source version or unevaluated observer gives Unknown. Prediction, comparison editing, and replay never alter the saved submission.

## Verification

- `test_last_light.gd`: 26 model/flow checks; 29 with desktop, portrait and ultrawide layout checks. Includes boundary crossing, ambiguous timing, disjoint intervals, source edges, observer mismatch, configurable durations, both comparison invariants, restoration, uncovered previews, immutable briefs, hold filing, disk persistence, and complete/skip replay parity.
- 205 GDScripts compiled with zero broken scripts.
- Existing Science Outpost: 19 checks; operations: 16; legacy generated campaign: 33. Python science suite: 24 tests passed.
- Scene/resource checker: 512 files, zero errors or warnings.
- Web export completed. An initial editor import reported a GitPlugin DLL-copy error; a subsequent export completed without that error. The editor VCS extension is not used by the web runtime.
- Chrome/WebGL playthrough on localhost: Moon map → Training Missions → Mission 2 → planner; restored the generated alternative, edited the bracket with pointer/arrow controls and entered UTC, submitted the Meets/bonus plan, completed the replay, and filed the brief with Enter. No browser page exceptions or Godot script errors were observed. Chrome reported its usual audio-start user-gesture notice.
- Chrome/WebGL landing-practice check: Moon map → Training Missions → Mission 2 → Practice Landing → Auto-land returned to the planner with the original site, UTC start, and illumination verdict intact. No browser page exceptions or Godot script errors were observed. Manual piloting and touch controls were not exercised in this check.
- Headless teardown reports two ObjectDB instances for the new flow and nine in the existing Science Outpost check; the rendered Last Light run exits without this warning.

## Remaining scientific and usability limits

Meets means stable **within the explicitly evaluated model variants**, not a certified payload or landing-site determination. Absolute terrain registration, instrument placement, complete terrain error propagation, and independent finer-cadence Horizons event validation remain incomplete. Height and 40 m shifts are chosen probes, not measured mission uncertainty distributions. Terrain rays start at 100 m and end at 400 km; near-field occluders are omitted. The skyline is treated as level across the apparent solar disk. The original source cross-checks against a separate Horizons subpoint table are retained as prior evidence, not represented as newly rerun independent validation.

Decisive-ridge visual review in [QuickMap](https://quickmap.lroc.asu.edu/) with the recorded LOLA layer and independent [Moon Trek](https://trek.nasa.gov/moon/) profile review are still pending. A first-time human usability session and physical touchscreen testing remain pending.

Electrical endurance and thermal survival remain Unknown for every outcome. Missing electrical evidence includes validated array output/pointing, activity loads, storage and initial state, and limits. Missing thermal evidence includes material properties, coupling, initial temperatures, environment and operating limits. No invented capacities, wattages, temperature thresholds, power bar or survival model is used.

## Presentation provenance

The pixel astronaut reuses `assets/pixel/astronaut/astronaut_sheet.png`, assembled by the existing PixelLab sheet pipeline (`scenes/common/pixel_astronaut.gd`). SiteWorld reuses the existing exported terrain and analytical skyline ring; nearby meshes and inspection cameras are presentation only. Existing MINT Sun/Earth assets are documented in `assets/team/README.md` with their generation links. No callable MINT MCP was available for new assets in this session. The instrument is a locally authored primitive cylinder with an illustrative deployment animation, not flight hardware. The planner's locator map, timeline and Horizon View are locally drawn controls; the locator grid depicts coordinates rather than measured surface imagery.
