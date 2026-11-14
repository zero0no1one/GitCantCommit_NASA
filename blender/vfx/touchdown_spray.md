# touchdown_spray

Used for: lander touchdown: engine plume sweeps grains outward, low and fast; most leave the frame (real ranges reach tens of metres).

| Parameter | Value |
|---|---|
| Gravity | (0, -1.62, 0) m/s² in Godot (lunar; no drag, no damping) |
| Grains | 220 per burst (one-shot) |
| Lifetime | 1.0 s (longest flight here 5.13 s) |
| Launch speed | 5.0–20.0 m/s |
| Launch elevation | 2–12° above the ground |
| Direction | azimuth 0° ± 180° in the effect's local frame (0° = forward) |
| Grain size | 10–50 mm |
| Spawn | disc of radius 0.6 m on the ground |
| Max reach | 100.4 m |
| Flipbook | `assets/vfx/touchdown_spray_4x4.png`, 4×4 frames of 128 px, 16 frames over the lifetime, side view, transparent; grains drawn 3× size for readability |

Godot (Compatibility renderer): `CPUParticles3D`, one_shot, explosiveness 1, `gravity = Vector3(0, -1.62, 0)`,
`damping = 0`, initial velocity 5.0–20.0, spread from the elevation/azimuth ranges above,
quad mesh with the grain colour (or the flipbook as a single billboard for distant/cheap use).
Grains must stop on landing (no bounce, no drift): use a short `lifetime` after landing or a ground collision.
Preliminary values; tune in the game.
