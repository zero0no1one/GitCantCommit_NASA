# Navigator implementation and validation status

**Current integration:** The original title/campaign presentation remains. Missions 2 and 3 now have COMPARE and REVIEW actions within their existing operations HUD, implemented in `scenes/operations/mission_navigator.gd`. They reuse UIKit panels, fonts, palette and keyboard focus. Two to four comparison cards cover all 18 site/window records; same-time linking and independent UTC inputs are available. Applying an option selects the existing scene's plan. Review snapshots inputs, source hashes, summaries and evidence; opening an attempt does not change the current plan. The shared decision persists when switching between Missions 2 and 3.

Only covered original-model six-hour options are eligible for the unchanged operations lesson/replay. Other durations and previews produce unknown assessments; preview surfaces are unavailable and never borrow another site's sky. Existing survey/third/first-person inspection remains in use. Navigator does not modify Mission 1. Science Outpost now has its own sample/scan checklist and debrief, retaining the original campaign/save identity and mission.json.

Integration verification: `tests/test_mission_navigator.gd` passed 17 rendered checks, including duration control, selected plan/surface, immutable saved inputs, saved-review independence, preview gating, endpoint gating, Mission 3 state retention and watched/skipped replay parity. Layout width checks passed at 1280×720 and 560×996; both screenshots were inspected. Existing operations-flow 11 checks passed. Compile checker reported 196 scripts and zero broken before the final documentation update. No new browser, physical-device or screen-reader validation is claimed for this integrated UI.

The sections below describe the earlier separate-UI prototype and scientific audit history. The separate Navigator scene, map UI and startup override were removed.

## Scope and evidence boundary

Work applies only to GitCantCommit_NASA. No files or data were read from or copied from the separate Three.js prototype. Existing mission.json and campaign/save identities were preserved. Pre-existing exploration packs and terrain.py modifications were retained.

The Navigator state loads 18 site/window records: two original-model records and 16 previews. It does not add previews to the Mission scoring catalog. Preview interval assessments and future events are unknown; raw az/el readouts are explicitly under the preview label. Incomplete coverage cannot produce supported results. Source-file SHA-256 hashes, input copies and uncertainty text are captured in session briefs. Operational claims have independent unknown gates.

## Implemented interactions

The startup scene presents a coordinate overview and keyboard-accessible six-point index, comparison controls and mission-free Review. Two default cards compare Apollo 11 and sl3 at the original window start; players can pin up to four. Each card selects a site/window, UTC start and duration. Same-time linking changes UTC starts together; disabling it allows same-site schedule comparisons. Playback is explicit, with no automatic camera movement. Original-model exploration reuses SiteWorld and the astronaut with first/third-person and survey cameras; scientific positions stay fixed when walking. New site/window surface scenes are unavailable until registered assets exist.

Eligible original-model six-hour plans seed Phase 2 operations. Other lessons retain their existing independent flows. Full shared-state migration of all guided lessons is unfinished. Returning through the operations Navigator button retains session state.

## Checks actually completed

- Godot 4.7.2 scoring: 18 checks, no failures; operations: 16; campaign: 33; operations flow (headless): 11. The existing flow check includes preview/skip assessment independence.
- New test_navigator.gd: 18 records, sample lengths, 16 preview gates, operational unknowns, coverage edges, no extrapolation, immutable snapshots, same-time and independent-date state checks passed.
- Python 3.14: all 24 existing pipeline tests passed. The first Python 3.12 attempt failed to import NumPy; it was rerun with the available 3.14 environment.
- audit_exploration.py passed structure/finite-value/interval-bounds checks on 16 records; exploration-audit.json stores hashes and copies of generator-reported comparisons. Those comparisons were NOT independently rerun by this audit.
- Godot compile checker: 196 scripts, zero broken at the recorded run. Headless Navigator startup had no script errors. Local Web export succeeded.
- Desktop Zen browser: local exported Navigator visibly loaded and two-site Review opened before any mission. Browser automation host was unavailable; native browser control was used. Narrow-browser, reduced-motion preference, screen-reader, and physical-device checks remain unverified. Final layout refinements have not had a repeated browser pass.

## Remaining scientific and product gates

No new record has been scientifically validated. Apollo 17 finer LOLA acquisition/integration is NOT completed. All terrain changes require regeneration and independent comparison. Required checks still include independent subpoint ephemeris recomputation for every new record, full/partial/blocked and Earth-center boundary checks with uncertainty, height/resolution/coverage sensitivity, recorded Quickmap/Moon Trek skyline review, robust examples, and new-pack golden parity. The ±0.1° sensitivity is not a complete uncertainty budget.

Product gaps: all-lessons shared-plan migration; richer horizon tracks; registered exploration scenes for additional sites/windows; map selection highlighting; fully synchronized visible playback controls; compact saved-brief presentation; narrow/touch and reduced-motion browser validation. Saved attempts currently reopen their immutable JSON evidence; current inputs remain unchanged. No overall suitability score exists.

## Source review (2026-11-15)

NASA's current pages were checked: [VIPER](https://www.nasa.gov/news-release/nasa-selects-blue-origin-to-deliver-viper-rover-to-moons-south-pole/) gives late-2027 context; [Artemis IV](https://www.nasa.gov/mission/artemis-iv/) says early 2028; [Artemis V](https://www.nasa.gov/event/artemis-v/) says by late 2028. These do not assign the hypothetical analysis dates or sites. The three labels in the bundled packs remain exploration-era planning scenarios.

NASA [Apollo landing table](https://nssdc.gsfc.nasa.gov/planetary/lunar/apolloland.html) confirms the repository's rounded Apollo 11 and Apollo 17 coordinates and DE421 ME/polar-axis convention. NASA [PGDA product 78](https://pgda.gsfc.nasa.gov/products/78) supplies polar-region context and high-resolution LOLA products; the repository's selected crest coordinates remain study points. Reviewing the product description does not validate their computed skylines.
