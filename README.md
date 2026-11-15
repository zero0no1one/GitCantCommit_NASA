# Moonward — Mission Control Adventure

Startup opens the Moon map; Training Missions opens the campaign and mission screens. This repository uses Godot 4.7.2 and bundled JSON, with no runtime NASA requests or login.

Mission 2, **Last Light Operations**, now has its own planner: a fixed-observer Horizon View, draggable UTC activity bracket, two comparison cards, prediction, skippable astronaut replay and persistent Mission Log. Its data-driven training sequence is 15 minutes setup plus 45 minutes observation, with a supported 15-minute margin bonus. Assessments compare 13 evaluated science variants; electrical endurance and thermal survival remain Unknown. Open Training Missions → Last Light Operations, or run `Godot --path . res://scenes/last_light/last_light.tscn`. See [scenario values, provenance and scientific limits](LAST_LIGHT_VALIDATION.md). The old six-hour comparison screen remains available from the Moon map and for Earth Link.

Mission 1, Science Outpost, uses the original `first-light` save identity and two-hour sunlight challenge. Choose Tranquility Base or Connecting Ridge, plan and land, then collect canisters near the rover and return them to the lander. Face glowing rocks and press E or tap SCAN. The outpost checklist asks for three delivered samples and two scans; the debrief reports these separately from the existing arcade stars. Activities and equipment are illustrative, without electrical or thermal survival claims. Run `--headless --path . --script res://tests/test_science_outpost.gd` with Godot for the mission flow check.

Mission 1 uses site-specific planning dates: March 1–2, 2028 at Tranquility Base, and March 8–10 at Connecting Ridge. Switching sites updates the time dial and bonus: the ridge asks for six hours of spare sunlight rather than the Tranquility sunrise deadline. Both sites retain the two-hour primary requirement and have passing plans outside the listed boundary uncertainty.

Missions 2 (Sunset Operations) and 3 (Earth Link) include COMPARE and REVIEW actions inside their existing operations HUD. Compare pins two to four site/date options, links UTC starts optionally, and accepts 10–1440 minute intervals. Select USE PLAN / EXPLORE to apply an option. Review saves session-only evidence briefs and reopens them without changing current inputs. The selected plan persists between these two missions.

The operating-sequence lessons retain their six-hour training rule. Other comparison durations, uncovered intervals and all 16 exploration-preview records receive unknown mission assessments. Original-model Apollo 11 and sl3 plans drive the existing survey/first/third-person scene and replay. New site/window surface scenes remain unavailable; operational claims remain unknown.

Run `Godot --path .`; export locally with `Godot --headless --path . --export-release Web build/web/index.html`. Serve `build/web` over localhost. No public deployment is authorized by this work.

See [Navigator implementation status](NAVIGATOR.md), [scientific validation](tools/data/VALIDATION.md), and [exploration data limitations](data/exploration/README.md). The implementation and expanded scientific validation are still incomplete.
