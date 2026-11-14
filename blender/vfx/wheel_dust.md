# wheel_dust

Used for: each rover wheel while drive_loop plays; spray goes backward.

| Parameter | Value |
|---|---|
| Gravity | (0, -1.62, 0) m/s² in Godot (lunar; no drag, no damping) |
| Grains | 64 per burst (one-shot) |
| Lifetime | 1.6 s (longest flight here 1.60 s) |
| Launch speed | 0.5–1.5 m/s |
| Launch elevation | 20–60° above the ground |
| Direction | azimuth 180° ± 25° in the effect's local frame (0° = forward) |
| Grain size | 6–18 mm |
| Spawn | disc of radius 0.06 m on the ground |
| Max reach | 1.2 m |
| Flipbook | `assets/vfx/wheel_dust_4x4.png`, 4×4 frames of 128 px, 16 frames over the lifetime, side view, transparent; grains drawn 3× size for readability |

Godot (Compatibility renderer): `CPUParticles3D`, one_shot, explosiveness 1, `gravity = Vector3(0, -1.62, 0)`,
`damping = 0`, initial velocity 0.5–1.5, spread from the elevation/azimuth ranges above,
quad mesh with the grain colour (or the flipbook as a single billboard for distant/cheap use).
Grains must stop on landing (no bounce, no drift): use a short `lifetime` after landing or a ground collision.
Preliminary values; tune in the game.
