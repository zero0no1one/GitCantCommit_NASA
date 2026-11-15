# footstep_dust

Used for: astronaut footfalls (lunar_lope contact frames, walk_slow steps).

| Parameter | Value |
|---|---|
| Gravity | (0, -1.62, 0) m/s² in Godot (lunar; no drag, no damping) |
| Grains | 48 per burst (one-shot) |
| Lifetime | 1.2 s (longest flight here 1.21 s) |
| Launch speed | 0.4–1.2 m/s |
| Launch elevation | 15–55° above the ground |
| Direction | azimuth 0° ± 90° in the effect's local frame (0° = forward) |
| Grain size | 6–20 mm |
| Spawn | disc of radius 0.08 m on the ground |
| Max reach | 0.8 m |
| Flipbook | `assets/vfx/footstep_dust_4x4.png`, 4×4 frames of 128 px, 16 frames over the lifetime, side view, transparent; grains drawn 3× size for readability |

Godot (Compatibility renderer): `CPUParticles3D`, one_shot, explosiveness 1, `gravity = Vector3(0, -1.62, 0)`,
`damping = 0`, initial velocity 0.4–1.2, spread from the elevation/azimuth ranges above,
quad mesh with the grain colour (or the flipbook as a single billboard for distant/cheap use).
Grains must stop on landing (no bounce, no drift): use a short `lifetime` after landing or a ground collision.
Preliminary values; tune in the game.
