# Sunline 3D assets (Blender first)

Every 3D asset is modelled, rigged, animated and given its preliminary VFX in Blender, then exported to `assets/models/*.glb` for Godot. Each asset is built by one script, so re-running the script rebuilds that asset exactly. Godot ignores this folder (`.gdignore`).

## Rebuild

Open Blender 5.2, then run a script, either from the Text Editor or through the Blender MCP:

```python
exec(open(r'C:\dev\godot\new-game-project\blender\scripts\build_astronaut.py', encoding='utf-8').read())
```

Each script writes `blender/<asset>.blend` and `assets/models/<asset>.glb`.

| Script | Builds |
|---|---|
| `build_astronaut.py` | `astronaut.glb` (with the scanner on `scanner_socket`) and `scanner.glb` |
| `build_rover.py` | `rover.glb` |
| `build_beacon.py` | `beacon.glb` |
| `build_lander.py` | `lander.glb`, from the team's Echo-Path lander (`NASA_GITCANTCOMMIT`, `web/public/models/lander.glb`) |
| `build_site_terrain.py` | `terrain_<site>.glb`. It needs `blender/data/terrain_<site>.json` from `tools/data/export_site_terrain.py` |
| `build_sky_props.py` | `moon_globe.glb`, `earth.glb`, `sun_disc.glb`, `site_pin.glb`, `fp_rig.glb` |
| `build_vfx.py` | VFX frames and `vfx_meshes.glb`. Then run `python tools/pack_flipbooks.py` for `assets/vfx/*.png` |
| `preview_animations.py` | Review renders in `assets/previews/` |

`sunline_common.py` holds the shared helpers: materials, primitives, rigid skinning, rigs, keyed poses, export and preview.

## Conventions

- **Units and axes:** metres, Blender +Z up, exported as glTF +Y up.
- **Characters and vehicles:** face Blender −Y, which becomes Godot +Z (`MODEL_FRONT`). The origin is on the ground.
- **Terrain:** Blender +X east, +Y north. In Godot that's +X east and −Z north. The origin is the site, on the ground.
- **Moon globe:** a point at latitude φ, longitude λ is at `(cos φ cos λ, sin φ, −cos φ sin λ)` in Godot, with radius 1.
- **Animations:** 24 fps. There's no root motion, because Godot moves the bodies. Actions export as named glTF animations.
- **Skinning:** rigid, one suit or vehicle part per bone. IK controls exist on the astronaut for hand-animating in Blender. The scripted actions are FK, and IK is muted during export.
- **Materials:** plain Principled BSDF (colour, metallic, roughness, emission), all safe for Godot's Compatibility renderer. Only the globe, Earth and lander have image textures, each 1024 px or smaller.

## Reference-first workflow

Before any geometry is scripted, at least two reference images of the real object (ideally front and side) are viewed and analysed for proportions, components and materials. The references for each asset are listed in its build script's docstring.

| Asset | References |
|---|---|
| Astronaut | **The team's turnaround sheet** (v3). The earlier v2 used NASA xEMU and Axiom AxEMU photos |
| Scanner | Pistol-grip handheld XRF analysers (Wikimedia Commons: "Handheld RXF analyzer gun.jpg", "Niton XL3t GOLDD Plus on rock") |
| Rover | NASA VIPER (Commons "VIPER lunar rover.jpg", NASA jsc2024e013783 mast, GRC-2021-C-00710 mobility platform) |
| Beacon | Geodetic survey stations (Commons "Round prism and laser plummet on tripod.jpg", "GNSS receiver at dusk among eucalyptus trees.jpg") |
| Lander | NASA CLPS renders (Peregrine, Nova-C, Blue Ghost) and the Blue Ghost mockup |
| Rocks | Apollo 17 Station 6 boulder (AS17-146-22294) and an Apollo 16 block (AS16-107-17573) |
| Regolith texture | Apollo 17 and Apollo 16 photos above |
| Suit soft goods | Aldrin's Apollo 11 A7L (Commons) and the AxEMU flight cover (axemu-axiom-suitcover-20230621-dgb-axp00653) |
| Foil texture | VIPER references |
| Distant hills | Apollo 15 Hadley Delta (AS15-87-11748) and Mount Hadley (AS15-90-12187) |
| Earth | Apollo 8 Earthrise (AS08-14-2383) and Artemis II Earthrise (art002e021278) |

## Assets

| GLB | Triangles | Animations | Notes |
|---|---|---|---|
| astronaut | 17,050 (14,622 suit + 2,428 scanner) | idle, lunar_lope, walk_slow, turn_in_place, scan_raise, scan_sweep, kneel_sample | **v3, built to the team's turnaround sheet**; see notes below |
| rocks | 2,422 for 9 variants | — | Cobbles (0.1–0.2 m), rocks (0.3–0.5 m), blocks (0.6–1.3 m) and a split boulder (3.5 m) with slabs at its foot. Fracture facets come from hull and plane cuts, with a pitted detail normal map. **Illustrative** scatter, kept below the scoring skyline like the terrain |
| scanner | 2,428 | — | Pistol-grip XRF-style body, cyan flip-up screen facing the user, cyan lens ring, glove-sized grip and guard. The grip is at the origin |
| rover | 10,620 | drive_loop, steer_turn, sample_drill_cycle, mast_look | VIPER-style; see notes below |
| beacon | 3,188 | deploy (legs open to 22°, feet stay planted), pulse_idle (reflector spins) | Survey tripod; see notes below. Godot drives the light's brightness |
| lander | 11,728 | touchdown | Echo-Path CLPS lander, already matching the references. Foil materials were retuned so the gold reads in direct sun. The body sinks the 8 cm leg stroke and settles, and the bell gimbals |

**Astronaut details (v3, `astronaut_body_v3.py`)**
- Built to the team's turnaround sheet: a slim, fitted orange coverall.
- **Helmet:** white hard helmet with a big round visor, round ear pods, side windows and a back panel. **All the glass is glossy black** (visor, its edge and the side windows); the sheet's light blue is reflected light. White neck ring over a navy collar. White neck ring over a navy collar.
- **Chest:** light-blue gauges with rims, a central hose, a zip and a yoke seam.
- **Harness:** navy straps over the shoulders to a navy belt with a buckle, and a V seam across the back.
- **Backpack:** compact, rounded and white.
- **Arms:** flag patches on both shoulders, navy wrist cuffs, chunky royal-blue gloves.
- **Legs:** white knee pads, horizontal shin ribbing, a blue flap pocket on the left thigh and an outlined pocket on the right, chunky royal-blue boots with navy soles.
- The rig and all animations are unchanged. The first-person arm uses the same navy cuff and royal-blue glove.
- The earlier AxEMU-style body (`astronaut_body_v2.py`) is kept for reference.

**Rover details**
- Silver-foil body on a gold frame, with a crumpled-foil normal map.
- **Vertical solar panels on the left, right and back, centred at exactly 1.0 m**, the skyline's panel height.
- Four wheels, each with a swing arm, steering drive, double rim, spokes, 16 chevron grousers and a gold hub. One wheel turn covers 1.57 m.
- Stereo-camera mast with lamp bars.
- TRIDENT-style drill on a vertical carriage, which replaces the earlier scoop arm and `panel_settle`.

**Beacon details**
- White telescoping legs with orange clamp bands, pointed shoes and foot pegs.
- Tribrach with three levelling knobs.
- Ring of eight retro-prisms.
- Clear dome lamp with a cyan core and a rotating reflector.
| terrain_apollo-11 / terrain_sl3 | 5,448 ground + 23,040 hills each | — | Walkable ground (round, 590 m radius) plus sloped hills (Apollo 15 Hadley references) whose crest at 1.5 km sits on the scoring skyline within 0.05°. Hill normals come from the hill shape, so there's no banding. The near-ground display grid is lightly smoothed (20 m) to remove 80 m DEM facets. No ground or hill vertex rises above the skyline (tested). Small craters and roughness are **illustrative** and stable across rebuilds |
| moon_globe | 9,024 | — | LOLA colour and normal maps |
| earth | 3,968 + limb quad | — | NASA Blue Marble NG with clouds, plus an added atmospheric blue over the oceans and low specular (Apollo 8 / Artemis II Earthrise references). `AtmosphereLimb` is a camera-facing quad with a soft pale-blue rim (`assets/textures/earth_limb.png`). In Godot: billboard, unshaded, additive, faded on the night side by Sun direction |
| sun_disc, site_pin, vfx_meshes | small | — | Sizes and tints are set in Godot |
| fp_rig | 2,820 | fp_idle, fp_scan_raise, fp_scan_hold | First-person forearm, glove and the new scanner. The visor frame is a Godot overlay |

All models total about 15 MB as GLB files. Each terrain GLB embeds its own copy of the regolith textures (about 4.5 MB per site). In Godot, use the shared textures in `assets/textures/` so they're imported once.

## Surface textures

`tools/make_surface_textures.py` generates these. All are tileable, and all are albedo or normal only, with no baked lighting.

| Texture | Size | What it shows |
|---|---|---|
| `regolith_albedo.png`, `regolith_normal.png` | 1024 px | A 2 m tile of granular speckle, clods, and 1–5 cm angular pebbles, with a faint brown cast |
| `rock_detail_normal.png` | 512 px | Pitting for the rocks |
| `suit_fabric_normal.png` | 512 px | Weave and wrinkles for the suit fabric |
| `mli_crinkle_normal.png` | 512 px | Crumpled-foil facets and creases for the rover body |
| `earth_limb.png` | 512 px | Earth's thin atmospheric rim |

| Script | Builds |
|---|---|
| `astronaut_body_v2.py` | The detailed suit |
| `scanner_v2.py` | The scanner |

`build_astronaut.py` imports both.

## VFX (preliminary)

| Effect | Files |
|---|---|
| Footstep dust, wheel dust, touchdown spray | `assets/vfx/<effect>_4x4.png` (512 px sheets). Spec in `blender/vfx/<effect>.md` |
| Scanner beam, reticle, beacon pulse | `vfx_meshes.glb` |
| Visor glint | `assets/vfx/visor_glint.png` |

- **Dust physics:** grains fly airless parabolas at 1.62 m/s² and stop on landing. Nothing billows.
- **Rebuilding in Godot:** use `CPUParticles3D` with the values in each spec note.

## Sources

| Asset | Source |
|---|---|
| Moon textures | Echo-Path `make_moon_textures.py`, from LRO LOLA LDEM_4 (NASA, public domain) |
| Earth | NASA Earth Observatory, Blue Marble Next Generation (Jan 2004) and Blue Marble clouds (public domain) |
| Terrain | LRO LOLA via `tools/data` (see `tools/data/README.md`) |
| Lander | The team's Echo-Path lander |

## AI-sculpted meshes (Hunyuan3D-2, local)

The astronaut, scanner, rover, beacon, lander and rocks are now **sculpted with Tencent Hunyuan3D-2**, run on this PC. Their procedural versions are kept in `assets/models/procedural/`.

**Setup**
- **Server:** `C:\dev\toolchains\Hunyuan3D-2`, an official Tencent checkout. It uses the `tencent/Hunyuan3D-2mini` turbo shape model, runs shape only (6 GB VRAM), and gives about one sculpt per minute on an RTX 4050 Laptop GPU.
- **Start it:** from that folder, run `.venv\Scripts\python.exe sunline_shape_server.py --port 8080`. This is a shape-only wrapper with the same API as Tencent's `api_server.py`. It's needed because Tencent's server imports the compiled texture modules, which aren't built here.
- **Version pins and one patch:** see `sunline_constraints.txt` and `sunline_patch.diff`. In short, `transformers<5`, `diffusers<0.36`, and a tuple index in `volume_decoders.py` so it works with PyTorch 2.9 and later.
- **In Blender:** the official add-on (sidebar → **Hunyuan3D-2**) is installed and points at `http://localhost:8080`. It's for making sculpts by hand.

**Pipeline**
1. **Inputs:** `render_hunyuan_inputs.py` renders 3/4 views of the procedural models. These were themselves built from the reference photos and the team's turnaround sheet. The rocks use a crop of the Apollo 16 photo.
2. **Generate:** `hunyuan_generate.py` produces the raw sculpts. They're saved to `blender/hunyuan/raw/` (not in git) alongside JSON logs of each exact request.
3. **Post-process:** `postprocess_sculpt.py` does the following:
   - fits each sculpt to the procedural model, with a fixed orientation; `FORCE_YAW` overrides it per asset (beacon 90°, scanner 270°);
   - decimates to the web budget;
   - takes materials by normal projection from the procedural model, then applies a majority filter;
   - takes skin weights from the procedural rig. They're smoothed for the suit; machines get rigid segments split at part boundaries, so wheels, drill and legs move without stretching;
   - exports.
4. **Rocks:** `build_rocks_sculpt.py` removes the photo-ground skirt, then scales, varies and decimates the rocks. The procedural cobbles are kept.

**Results**

| Asset | Triangles | Animations |
|---|---|---|
| Astronaut | 15k, plus a 4k sculpted scanner on the hand socket | All 7 |
| Rover | 15k | All 4 |
| Lander | 15k | All 4 |
| Beacon | 6k | All 4 |
| Rocks | 3k / 5k / 8k by size | — |

**Known issues**
- Colour borders on the astronaut are a little ragged on the chest gauges. The visor is clean: the mesh is cut exactly on the visor circle and everything inside it is black glass (`GLASS` in `postprocess_sculpt.py`). A couple of small notches remain where the sculpted helmet lip leaves the circle.
- Small gold points show at the rover's wheel hubs.
- Small rocks lose some pitting at 3k triangles.
- The lander uses plain colours sampled from its baked atlas.

**Licence.** These meshes are outputs of the Tencent Hunyuan 3D 2.0 Community License model:
- Tencent claims no rights in outputs.
- The licence does **not** apply in the EU, UK or South Korea, so the outputs may not be used or displayed there.
- Products with more than 1 million monthly users need a separate licence.

**What the public web build ships.** Because the site is public worldwide, the web build uses the **procedural** versions in `assets/models/procedural/`, not these sculpts:
- The Web export preset sets the `procedural_models` feature tag.
- It also leaves `assets/models/{astronaut,scanner,rover,beacon,lander,rocks}*` out of the pack.
- Game code loads these six models through `Models.scene(name)` (`scripts/models.gd`), which picks the procedural file when that tag is set.
- The sculpts stay available in the editor for review.
- Polishing the procedural versions is the path to better-looking web models.
