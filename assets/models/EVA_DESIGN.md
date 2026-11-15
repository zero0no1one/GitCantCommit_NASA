# EVA suit appearance

The title and playable astronaut share `Models.astronaut()`, which uses the
existing procedural rig with per-instance material overrides. White fabric,
red seam accents, dark joint fittings and a gold visor draw on NASA's EVA
spacesuit reference: https://www.nasa.gov/centers-and-facilities/johnson/spacewalk-spacesuit-basics/

This is a stylized NASA-inspired game suit, not an exact flight-hardware replica.
The visual changes do not change the scientific observer or scoring geometry.

The title astronaut blends between idle and scan_sweep. The title rover uses the
procedural rig's mast_look animation at reduced speed. Both remain stationary
on the globe; wheels do not spin while parked. Gameplay retains idle, walking,
lunar lope, hopping and scanning behavior on the shared astronaut rig.
