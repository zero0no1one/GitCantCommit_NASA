# First Light: Phase 2 implementation status

Navigator is integrated into Missions 2 and 3 through COMPARE and REVIEW actions in the existing operations HUD. The original title/campaign design remains. Shared site/date options, immutable session briefs, source evidence and preview gates reuse the current UI styling and existing inspection/replay flow. Original-model covered six-hour plans can run the lessons; other comparison intervals and exploration previews receive unknown mission assessments. New exploration packs remain unverified. See `NAVIGATOR.md` for checks and outstanding science gates. Existing mission IDs and save identity remain unchanged.

Status: playable evidence-gated foundation; scientific completion criteria are not met.

The active project is `GitCantCommit_NASA` (Godot application name: Sunline). Its runtime mission catalog now presents Science Outpost, Sunset Operations, Earth Link, and the non-playable Polar Ice Scout roadmap card. The generated eight-mission arcade dataset remains intact for regression checks; existing introductory save identity is retained.

## Implemented

- Both new missions start with site and UTC time selection at Tranquility Base or Connecting Ridge.
- Use the existing February 18–March 19, 2028 numerical coverage, with starts limited to leave six complete hours. The user authorized choosing dates appropriate to the game. These are hypothetical training dates, not relabeled 2026 data or a Surveyor reconstruction.
- Three two-hour blocks express observation, telemetry or standby **requests**. They are not claims of verified flight modes. Flight telemetry selection is disabled until supported configurations exist.
- Surface inspection offers survey, third-person and first-person cameras. The labeled assessment origin remains fixed when the virtual astronaut walks. Equipment geometry and inspection lighting are illustrative.
- A 720x preview takes 30 seconds for six simulated hours. Skip and completion show the same immutable plan assessment.
- Debriefs separate met, violated and unknown criteria, explain causes, identify evidence and offer revision. Unknown never awards scientific points or becomes an automatic failure.
- Full/partial/blocked solar illumination uses bundled intervals. Earth-centre visibility is distinct from station geometry and radio feasibility. Values near the skyline sensitivity band are labeled unknown.

## Evidence boundary

No battery capacity, array wattage, load, charge/discharge efficiency, state of charge, temperature limit, antenna gain, telemetry threshold or station contact window was invented. In particular, there is no generic rechargeable battery simulation and no signal-strength bar.

Engineering readouts remain **unknown** because flight-configuration-specific inputs have not been verified. Six hours is the specified training objective; a continuous 30-minute contact within the plan is an explicitly chosen training objective for Earth Link. The existing skyline sensitivity is not a complete uncertainty budget. Terrain sampling resolution is not positional accuracy.

References linked in the game include the [Surveyor battery report](https://ntrs.nasa.gov/citations/19700010014), [DSN geometry module 301M](https://deepspace.jpl.nasa.gov/dsndocs/810-005/301/301M.pdf), bundled numerical-product provenance, and educational exploration resources. Blue Ghost's post-sunset operations are context only, not a source for Surveyor constants. Surveyor telecommunications and power-system report sections still need identification and flight-specific review.

## Required before scientifically scored release

1. Extract and independently check the Surveyor 1 flight electrical configuration, initial conditions, allowed modes, array pointing limits and battery behavior against exact report pages and test conditions.
2. Implement and validate the configuration-specific power/energy integration and operating-limit assessment, including unknown propagation, environmental limits and conservative numerical uncertainty.
3. Produce DSS-14 geometry with station horizon/pointing constraints; separately verify the selected historical Surveyor telemetry signal against applicable receiver/reception criteria and link losses. Generate continuous contact intervals with uncertainty.
4. Replace activity requests with verified hardware modes, and bind array/antenna indicators to validated attitudes. Add validated success and failure scenarios. Do not enable scores solely from geometry or example constants.
5. Validate the selected surface terrain coverage, observer height and error budget for each scored result. The existing terrain and ephemeris checks are described in `tools/data/VALIDATION.md`.

## Verification

- `tests/test_operations.gd`: deterministic assessment, coverage boundaries, evidence gates, catalog and preview-state independence.
- `tests/test_operations_flow.gd`: mission flow, camera selection, fixed observer under movement, preview/skip equality and site switching. With a graphics display it saves `user://phase2-planning-WIDTHxHEIGHT.png` at desktop, portrait and ultrawide sizes.
- `tests/test_campaign.gd`: preserved generated arcade dataset regression.
- Compile checker: `.agents/skills/godot-gdscript/assets/check_scripts_compile.gd`.

The mission preview does not establish lunar-night thermal survival, certified landing suitability, or actual DSN scheduling/service availability.

Verified on Godot 4.7.2: 16 model checks, 14 rendered flow/layout checks, 33 legacy campaign checks, and 197 scripts compiled without broken scripts. Planning screenshots were inspected at 1280x720, 560x996 and 2560x1080. The editor import reported a GitPlugin DLL-copy error with another editor open; game tests did not depend on that plugin. Some rendered shutdowns reported two ObjectDB instances remaining; no script/runtime errors were reported in the final flow check.
