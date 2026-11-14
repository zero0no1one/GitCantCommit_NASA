# First Light — MINT equipment

Generated 2026-11-14 using MINT MCP.

Source: https://mint.gg/chat/ph7a56r724acgkjk0z7nx6y33d8j7x87

Astronaut source: https://mint.gg/chat/ph76t3z9jc18ekehjxhyjyrcjd8j64qm

## Files

- `models/lunar_rover.glb`: static rover visual, 6,275 vertices, one mesh/material.
- `models/survey_beacon.glb`: static survey beacon visual, 6,588 vertices, one mesh/material.
- `models/astronaut.glb`: fictional orange-white astronaut, 6,457 vertices, one mesh/material, 3,864,968 bytes. Static T-pose; no skeleton or animation clips.
- `scenes/lunar_rover.tscn`: bottom-aligned rover, chosen visual height approximately 1.2 m.
- `scenes/survey_beacon.tscn`: bottom-aligned beacon, chosen visual height approximately 1.4 m.
- `scenes/equipment_preview.tscn`: standalone orbit-camera inspection scene.
- `scenes/astronaut.tscn`: bottom-aligned astronaut visual, chosen display height approximately 1.85 m.
- `scenes/astronaut_preview.tscn`: orbit-camera astronaut inspection scene.
- `astronaut-preview.png`: actual Godot Compatibility-renderer capture.
- `equipment-preview.png`: actual Godot Compatibility-renderer capture.

## Godot use

Copy this folder into the game's Assets directory, preserving its internal structure. Let Godot import the GLBs, then drag either equipment scene into your existing 3D scene. External resource paths are relative to each scene, so the folder can be relocated together.

Open `scenes/equipment_preview.tscn` and use Run Current Scene (F6) to inspect both props. Drag to orbit, scroll to zoom, and press R or Reset view to reset. Single-finger dragging also orbits.

Open `scenes/astronaut_preview.tscn` and press F6 to inspect the astronaut. Instance `scenes/astronaut.tscn` as the character's visual child. Rigging, animation, and a character controller remain separate integration steps. The 1.85 m display height is an artistic choice, not measured astronaut or suit data.

These are fictional static visual props, not flight-hardware replicas. Their chosen dimensions do not specify panel height, rover performance, or scientific instrument properties. Configure scientific observers independently from these visuals. No terrain, sunlight result, collisions, physics, animations, or communication model is supplied by these assets.

## Verification

Both GLBs passed binary header and declared-length checks. Godot 4.7.2 imported the assets successfully. A rendered run of the inspection scene loaded both equipment meshes and the floor, captured a 1280x720 image, and exited with code 0 without reported script errors. Browser and physical-phone performance remain untested. The active NASA workspace contained no existing Godot project, so mission integration remains pending.

The astronaut subsequently passed GLB header and length checks and Godot 4.7.2 import. A fresh rendered run loaded both inspection scenes without reported errors and captured 1280x720 images. Bounds checks confirmed the astronaut's 1.85 m display height and floor alignment within 0.01 m. The updated shared viewer preserved the equipment preview's three expected meshes. Animation and browser validation have not been performed.

## Movement position study

Open `scenes/astronaut_motion_preview.tscn` and press F6. Select a reference pose, left/right 90-degree turn, 2 m translation, or ideal lunar hop. Play/pause or scrub the normalized timeline to inspect intermediate positions. Translation and turns use chosen demonstration speeds; they are not modeled astronaut gaits. The limbs retain their static T-pose.

MINT Basic Movement rigging/animation was requested for idle, walking, running, jumping, and turns. The provider rejected all six clips with `model_animation_provider_rejected`, and repeating the request returned the same failed batch. No rig or animation artifacts were delivered. The local position study is an explicitly labeled fallback. Skeletal movement remains pending.

The hop uses y(t) = v0*t - g*t*t/2, g = 1.62 m/s² and an assumed v0 = 1 m/s. It represents an ideal point trajectory over a flat surface, not a validated human biomechanical simulation. Duration is 2*v0/g and apex height v0²/(2*g). Source for gravity: https://www1.grc.nasa.gov/beginners-guide-to-aeronautics/moon/

Godot imported and rendered the new scene successfully. Automated checks exercised all five modes, midpoint seeking, one-shot completion, and playback stopping. Numeric checks verified turn angles, translation distance, hop apex, and landing height. Captured `astronaut-motion-preview.png` shows the hop at its apex. Browser and physical input checks remain pending.

## Sun and Earth

Source: https://mint.gg/chat/ph7a9jtqb5ks4geb0tpvcafsb18j6zdp

- `models/sun.glb`: 2,826 vertices, one mesh/material, 691,484 bytes.
- `models/earth.glb`: 2,957 vertices, one mesh/material, 3,038,200 bytes.
- `scenes/sun.tscn` and `scenes/earth.tscn`: centered reusable visual scenes, normalized to a maximum bounding-box diameter of 2 Godot units on instantiation.
- `scenes/celestial_preview.tscn`: Sun on the left and Earth on the right, with equal inspection sizes. Run Current Scene (F6), drag to orbit, and scroll to zoom.
- `sun-earth-preview.png`: actual Godot Compatibility-renderer capture.

The Sun visual uses an unshaded material and does not itself illuminate the terrain. A separate directional light must be driven by the Sun direction. Earth keeps its surface texture with neutral nonmetallic material settings.

Both are generated illustrative assets. Earth's continents, clouds, orientation, and lighting are not authoritative observations. Their silhouettes are generated meshes, not exact scientific spheres. Do not use their triangles to score solar clearance, eclipses, or Earth visibility. Equal inspection sizes and positions are unrelated to physical or apparent size. Runtime scene roots are centered on each body, which allows the game to place visuals from the independent observer geometry.

Integration with `Assets/Science/apollo11_sky_sample.json` remains pending. Use Horizons directions and angular diameters for sky placement, separately validated orientation/phase for Earth, and analytical disks for visibility calculations. Keep the reference-altitude and coarse-sampling limitations of that dataset visible.

Verification: GLB headers and declared lengths passed. Godot 4.7.2 imported both models without reported errors. Rendered checks verified textures, centered bounds, 2-unit display diameters, and the Sun's unshaded material. Captured a 1280×720 preview and exited with code 0. Browser performance and scientific sky integration have not been tested.
