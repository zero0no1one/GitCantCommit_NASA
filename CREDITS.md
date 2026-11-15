# Moonward — credits, data sources and licences

Moonward — Mission Control Adventure is a NASA Space Apps Challenge 2026 entry (Lunar Landing Site Navigator) by team GitCantCommit.
It started as *Sunline*; some code and file names still use that name.

## 1. Data behind the game's results
Bundled in `data/mission.json` (the original modeled study sites), `data/last_light.json` (Last Light Operations and evaluated sensitivity variants), and `data/exploration/*.json` (provisional previews). Last Light provenance and remaining scientific limits are recorded in `LAST_LIGHT_VALIDATION.md`.
Every sunlight and Earth-visibility result in the game is computed from these.

| Data | Product | Use in the game | Reference |
|---|---|---|---|
| Sun and Earth positions | NASA JPL Horizons System (DE441), observer standing on the Moon at each site (`coord@301`), every 10 minutes. https://ssd.jpl.nasa.gov/horizons/ | Sun and Earth direction, elevation and angular size from each site | Giorgini, J. D. et al., JPL Horizons On-Line Ephemeris System |
| South-polar terrain, 80 m | NASA GSFC Planetary Geodesy Data Archive (PGDA), LOLA `LDEM_80S_80MPP_ADJ`. https://pgda.gsfc.nasa.gov/products/90 | Connecting Ridge skyline (plus a 640 m average of the same mosaic for distant terrain); polar preview sites | Barker, M. K. et al. (2023), PSJ 4, 183, doi:10.3847/PSJ/acf3e1 |
| Polar site list | NASA GSFC PGDA, south pole landing-site LOLA DEMs. https://pgda.gsfc.nasa.gov/products/78 | Polar site locations: Connecting Ridge (sl3) and the Shackleton rim, peak near Shackleton and de Gerlache rim previews | Barker, M. K. et al. (2021), PSS 203, 105119, doi:10.1016/j.pss.2020.105119 |
| Tranquility terrain, 118 m | LRO LOLA LDEM 256 px/deg global mosaic, USGS Astrogeology. https://planetarymaps.usgs.gov/mosaic/Lunar_LRO_LOLA_Global_LDEM_118m_Mar2014.tif | Tranquility Base skyline | Smith, D. E. et al. (2010), GRL 37, L18204, doi:10.1029/2010GL043751 |
| Global terrain, 7.6 km | LRO LOLA `LDEM_4`, PDS Geosciences Node. https://pds-geosciences.wustl.edu/lro/lro-l-lola-3-rdr-v1/lrolol_1xxx/data/lola_gdr/cylindrical/img/ | Distant terrain on every skyline; the Apollo 17 preview (coarse only); Moon globe textures | Smith et al. (2010), as above |
| Apollo landing sites | NASA NSSDC. https://nssdc.gsfc.nasa.gov/planetary/lunar/apolloland.html | Apollo 11 (Tranquility Base) and Apollo 17 coordinates; Moon mean-Earth/polar-axis convention | — |
| Ephemeris cross-check | Horizons hourly sub-solar and sub-Earth points, 2026–2030 (`tools/data/source/ephemeris_moon_2026_2030.csv.gz`, from the team's Echo-Path project) | Choosing analysis windows; checking the topocentric Horizons samples | Derived from JPL Horizons |

**Analysis windows.** All dates are hypothetical 30-day planning windows chosen from the data, not NASA launch or landing
dates. The validated sites use 2028-02-18 to 2028-03-19 UTC. The preview packs also use 2027-11-15 to 2027-12-15 and
2028-10-15 to 2028-11-14 (see §3).

**Preview records are provisional.** The 16 exploration-preview records (`data/exploration/`) have not passed full
independent terrain or event validation, and the game gives them only "unknown" assessments
(`data/exploration/README.md`).

**Rules, not data.** Sampling-hour and task-duration requirements (2, 6, 8 h; the 30-minute Earth Link contact) are
fictional mission rules and training objectives. Earth "in view" means the centre of Earth's disc is above the skyline: geometry only, with no
claim about radio contact.

How the data is processed and checked: `tools/data/README.md` and `tools/data/VALIDATION.md`.

## 2. References used to check our numbers
These are compared with our results; they do not feed any result.

| Reference | Check | Citation |
|---|---|---|
| NASA GSFC PGDA, LOLA average polar illumination `AVGVISIB_85S_060M_201608`. https://pgda.gsfc.nasa.gov/products/69 | Our polar sunlight fraction vs PGDA's (`tools/data/VALIDATION.md` §2) | Mazarico, E. et al. (2011), Icarus 211, 1066–1081, doi:10.1016/j.icarus.2010.10.030 |
| LROC QuickMap. https://quickmap.lroc.asu.edu/ | Skyline cross-check by hand (pending, `VALIDATION.md` §6); exploration, not a numerical source | Arizona State University / LRO Camera team |
| NASA Moon Trek. https://trek.nasa.gov/moon/ | Elevation profiles toward each skyline maximum (pending, `VALIDATION.md` §6) | NASA JPL Solar System Treks |

## 3. Context references
Cited in the game or docs for context. No values in the game come from them.

| Reference | Why it is cited |
|---|---|
| NASA, VIPER delivery. https://www.nasa.gov/news-release/nasa-selects-blue-origin-to-deliver-viper-rover-to-moons-south-pole/ | Late-2027 context for the "VIPER era" preview window |
| NASA, Artemis IV. https://www.nasa.gov/mission/artemis-iv/ | Early-2028 context for the "Artemis IV era" window |
| NASA, Artemis V. https://www.nasa.gov/event/artemis-v/ | Late-2028 context for the "Artemis V era" window |
| Surveyor battery report, NASA NTRS 19700010014. https://ntrs.nasa.gov/citations/19700010014 | Robotic-lander reference in the operations missions; its flight configuration is not yet verified, so no battery values are used |
| DSN 810-005, module 301M, Coverage and Geometry. https://deepspace.jpl.nasa.gov/dsndocs/810-005/301/301M.pdf | Earth Link: station geometry context; no link or contact-window claims are made |
| NASA, Blue Ghost end-of-mission briefing. https://www.nasa.gov/news-release/nasa-firefly-invite-media-to-discuss-end-of-blue-ghost-moon-mission/ | Educational context on post-sunset operations (not used for any lander performance) |
| Canadian Space Agency, Moon exploration. https://www.asc-csa.gc.ca/eng/astronomy/moon-exploration/ | Context |

## 4. Visual and physics references
| Reference | Use |
|---|---|
| NASA, Spacewalk spacesuit basics. https://www.nasa.gov/centers-and-facilities/johnson/spacewalk-spacesuit-basics/ | Colour reference for the 3D EVA suit (white fabric, red accents, gold visor); stylised, not a flight-hardware replica |
| NASA Glenn Research Center, Beginner's Guide to Aeronautics: the Moon. https://www1.grc.nasa.gov/beginners-guide-to-aeronautics/moon/ | Lunar surface gravity, 1.62 m/s², used for walking, hops and the descent |

## 5. Art
### Pixel art
| Sprite | Made by | Notes |
|---|---|---|
| Astronaut (`assets/pixel/astronaut/`) | Our team: the eight standing views were generated with PixelLab (https://pixellab.ai); the idle and walk frames are drawn from those pixels by `tools/pixel/build_astronaut_sheet.gd` (no new colours) | Shown as a four-view sprite in the 3D world (`scenes/common/pixel_astronaut.gd`). |
| Moon map pins (`scenes/map/map.gd`) | Our team, drawn in code | — |

### 3D models
| Model | Made by | Notes |
|---|---|---|
| Lunar rover, survey beacon, Sun, Earth (`assets/team/`) | Our team, generated with MINT (https://mint.gg) | Sun and Earth are illustrative visuals: their positions and sizes in the sky come from the Horizons data, never from the meshes. The MINT astronaut (rigged by `blender/scripts/rig_team_astronaut.py`) is kept in the repository but no longer shown. |
| Lander, rocks, terrain, skyline ring, Moon globe, first-person rig, procedural suit and rover (`assets/models/`) | Our team, built procedurally in Blender 5.2 (`blender/scripts/`) | Terrain and skyline ring are built from the same skyline that scores the mission. |

**MINT terms (checked 2026-11-14, https://docs.mint.gg/terms-of-service, last updated 2026-05-07).**
Section 4 assigns the rights in generated output to the user, subject to the terms, payment and third-party rights.
No attribution requirement and no territory restriction were found. Section 6 says Mint does not guarantee a GLB is free
of third-party rights. The models are credited here anyway.

**PixelLab terms:** https://pixellab.ai/termsofservice. The astronaut was generated on a trial account; the terms for
trial-account output have not been checked yet.

The Hunyuan3D-2 sculpt experiments (`blender/hunyuan/`, `assets/models/*.glb` sculpt versions) are **not** used in the
web build: the Tencent Hunyuan 3D 2.0 Community License does not cover the EU, UK or South Korea.

## 6. Fonts
- Russo One — SIL Open Font License 1.1 (`assets/fonts/RussoOne-OFL.txt`)
- Chakra Petch — SIL Open Font License 1.1 (`assets/fonts/ChakraPetch-OFL.txt`)

## 7. Sound
All sound effects and music are synthesised in the game at start-up (`scripts/sfx.gd`); no audio files are used.

## 8. Software
- Godot Engine 4.7 (MIT)
- Blender 5.2 (GPL; the assets made with it are ours)
- Python with NumPy, SciPy, rasterio, requests (data pipeline)
- Code adapted from the team's Echo-Path engine: `tools/data/sunline_data/terrain.py`, `subpoint.py` and parts of
  `scoring.py`

## 9. AI use
Code, data-pipeline scripts, several 3D models and the astronaut sprite were made with help from AI tools (an AI coding
assistant; MINT for the team models; PixelLab for the astronaut's standing views). Every science claim in the game is
checked against the data by the automated tests in `tools/data/tests` and `tests/`.
