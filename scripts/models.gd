class_name Models
## Resolves which version of a 3D model to load.
##
## The astronaut, scanner, rover, beacon, lander and rocks exist in two versions:
##   - assets/models/<name>.glb             sculpted with Tencent Hunyuan3D-2 (editor and local review only)
##   - assets/models/procedural/<name>.glb  built procedurally in Blender (blender/scripts/build_*.py)
## The public web build ships the procedural versions only: the Hunyuan 3D 2.0 Community License does not
## cover the EU, UK or South Korea, and a public site is shown there. The Web export preset sets the
## `procedural_models` feature tag and leaves the sculpted files out of the pack (see export_presets.cfg).
## Every other model (terrain, Moon, Earth, Sun, pins, first-person rig, VFX meshes) has a single version.
##
## Always load these models through Models.scene() / Models.path(), never by a hard-coded path.

const DIR := "res://assets/models/"
const SCULPTED := ["astronaut", "scanner", "rover", "beacon", "lander", "rocks"]


static func use_procedural() -> bool:
	return OS.has_feature("procedural_models")


static func path(model: String) -> String:
	if model in SCULPTED and use_procedural():
		return DIR + "procedural/" + model + ".glb"
	return DIR + model + ".glb"


static func scene(model: String) -> PackedScene:
	return load(path(model)) as PackedScene


## Teammate models (assets/team/, made with MINT; see assets/team/README.md): lunar_rover, survey_beacon,
## astronaut (static T-pose, no rig yet), sun, earth. Each scene is bottom-aligned (props) or centred (bodies).
static func team(model: String) -> PackedScene:
	return load("res://assets/team/scenes/%s.tscn" % model) as PackedScene
