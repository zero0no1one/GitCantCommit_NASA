# Sunline — credits and licences

Sunline is a NASA Space Apps Challenge 2026 entry (Lunar Landing Site Navigator) by team GitCantCommit.

## Data
| Source | Use | Reference |
|---|---|---|
| NASA JPL Horizons (DE441), topocentric observer on the Moon | Sun and Earth direction, elevation and angular size from each site, every 10 minutes | https://ssd.jpl.nasa.gov/horizons/ |
| LRO LOLA LDEM_4 global elevation (PDS) | Distant terrain for skylines; Moon globe textures | doi:10.1029/2010GL043751 |
| LRO LOLA LDEM 118 m global mosaic (USGS Astrogeology) | Tranquility Base skyline | doi:10.1029/2010GL043751 |
| NASA GSFC PGDA LOLA 80 m south polar mosaic | South-polar skyline | https://pgda.gsfc.nasa.gov/products/90 · doi:10.3847/PSJ/acf3e1 |
| NASA GSFC PGDA south pole landing sites | Polar site location | https://pgda.gsfc.nasa.gov/products/78 · doi:10.1016/j.pss.2020.105119 |
| NSSDC Apollo landing sites | Tranquility Base location | https://nssdc.gsfc.nasa.gov/planetary/lunar/apolloland.html |

How the data is processed and checked: `tools/data/README.md` and `tools/data/VALIDATION.md`.
The sampling-hour requirements (2, 6, 8 h) are fictional mission rules; all sunlight timing comes from the data.

## 3D models
| Model | Made by | Notes |
|---|---|---|
| Astronaut, lunar rover, survey beacon, Sun, Earth (`assets/team/`) | Our team, generated with MINT (https://mint.gg) | The astronaut is rigged to the Sunline skeleton and animated by `blender/scripts/rig_team_astronaut.py`. Sun and Earth are illustrative visuals: their positions and sizes in the sky come from the Horizons data, never from the meshes. |
| Lander, rocks, terrain, skyline ring, Moon globe, first-person rig (`assets/models/`) | Our team, built procedurally in Blender 5.2 (`blender/scripts/`) | Terrain and skyline ring are built from the same skyline that scores the mission. |

**MINT terms (checked 2026-11-14, https://docs.mint.gg/terms-of-service, last updated 2026-05-07).**
Section 4 assigns the rights in generated output to the user, subject to the terms, payment and third-party rights.
No attribution requirement and no territory restriction were found. Section 6 says Mint does not guarantee a GLB is free
of third-party rights. The models are credited here anyway.

The Hunyuan3D-2 sculpt experiments (`blender/hunyuan/`, `assets/models/*.glb` sculpt versions) are **not** used in the
web build: the Tencent Hunyuan 3D 2.0 Community License does not cover the EU, UK or South Korea.

## Fonts
- Russo One — SIL Open Font License 1.1 (`assets/fonts/RussoOne-OFL.txt`)
- Chakra Petch — SIL Open Font License 1.1 (`assets/fonts/ChakraPetch-OFL.txt`)

## Sound
All sound effects and music are synthesised in the game at start-up (`scripts/sfx.gd`); no audio files are used.

## Software
- Godot Engine 4.7 (MIT)
- Blender 5.2 (GPL; the assets made with it are ours)
- Python with NumPy, SciPy, rasterio, requests (data pipeline)

## AI use
Code, data-pipeline scripts and several 3D models were made with help from AI tools (an AI coding assistant; MINT for
the team models). Every science claim in the game is checked against the data by the automated tests in `tools/data/tests`
and `tests/`.
