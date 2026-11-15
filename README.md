# Moonward (Godot)

The existing game design and UI are preserved: startup opens the original title scene, followed by the existing campaign and mission screens. This repository uses Godot 4.7.2 and bundled JSON, with no runtime NASA requests or login.

Missions 2 (Sunset Operations) and 3 (Earth Link) include COMPARE and REVIEW actions inside their existing operations HUD. Compare pins two to four site/date options, links UTC starts optionally, and accepts 10–1440 minute intervals. Select USE PLAN / EXPLORE to apply an option. Review saves session-only evidence briefs and reopens them without changing current inputs. The selected plan persists between these two missions.

The operating-sequence lessons retain their six-hour training rule. Other comparison durations, uncovered intervals and all 16 exploration-preview records receive unknown mission assessments. Original-model Apollo 11 and sl3 plans drive the existing survey/first/third-person scene and replay. New site/window surface scenes remain unavailable; operational claims remain unknown.

Run `Godot --path .`; export locally with `Godot --headless --path . --export-release Web build/web/index.html`. Serve `build/web` over localhost. No public deployment is authorized by this work.

See [Navigator implementation status](NAVIGATOR.md), [scientific validation](tools/data/VALIDATION.md), and [exploration data limitations](data/exploration/README.md). The implementation and expanded scientific validation are still incomplete.
