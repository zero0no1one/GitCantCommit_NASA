extends Node3D
## Debug viewer: the in-game astronaut from the side (same angle as the Blender check: camera on +X, the
## astronaut faces screen-left), holding one animation frame so it can be compared with Blender frame by frame.
## Keys: 1 walk_slow, 2 lunar_lope, 3 idle, Space play/pause, Left/Right step one frame (24 fps).

var anim: AnimationPlayer
var clip := "walk_slow"
var frame := 1
var playing := false
var _label: Label


func _ready() -> void:
	var env := Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = Color(0.22, 0.22, 0.24)
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color(0.5, 0.5, 0.55)
	var we := WorldEnvironment.new()
	we.environment = env
	add_child(we)
	var sun := DirectionalLight3D.new()
	sun.rotation = Vector3(deg_to_rad(-40), deg_to_rad(40), 0)
	add_child(sun)
	var model: Node3D = Models.scene("astronaut_team").instantiate()
	add_child(model)
	anim = model.find_children("*", "AnimationPlayer", true, false)[0]
	var cam := Camera3D.new()
	cam.position = Vector3(4.2, 0.95, 0)
	add_child(cam)
	cam.look_at(Vector3(0, 0.95, 0))
	cam.fov = 40
	var layer := CanvasLayer.new()
	add_child(layer)
	_label = Label.new()
	_label.position = Vector2(20, 20)
	layer.add_child(_label)
	_show()


func _show() -> void:
	if not anim.has_animation(clip):
		return
	anim.play(clip)
	anim.seek((frame - 1) / 24.0, true)
	if not playing:
		anim.pause()
	_label.text = "%s  frame %d  (%s)" % [clip, frame, "playing" if playing else "paused"]
	_dump.call_deferred()


## Print key bone head positions in Blender coordinates (x, y, z) = Godot (x, -z, y), for comparison.
func _dump() -> void:
	var sk: Skeleton3D = anim.get_parent().find_children("*", "Skeleton3D", true, false)[0]
	var out := PackedStringArray()
	for b in ["hips", "foot.L", "foot.R", "forearm.L", "hand.L", "forearm.R", "hand.R", "head"]:
		var i := sk.find_bone(b)
		if i < 0:
			continue
		var p := sk.global_transform * sk.get_bone_global_pose(i).origin
		out.append("%s=(%.3f, %.3f, %.3f)" % [b, p.x, -p.z, p.y])
	print("BONES %s f%d %s" % [clip, frame, " ".join(out)])


func _unhandled_input(e: InputEvent) -> void:
	if not (e is InputEventKey and e.pressed):
		return
	match (e as InputEventKey).keycode:
		KEY_1: clip = "walk_slow"; frame = 1
		KEY_2: clip = "lunar_lope"; frame = 1
		KEY_3: clip = "idle"; frame = 1
		KEY_SPACE: playing = not playing
		KEY_RIGHT: frame += 1
		KEY_LEFT: frame = maxi(1, frame - 1)
	_show()


## Called from tests/tools: show a given clip and frame.
func show_frame(c: String, f: int) -> void:
	clip = c
	frame = f
	playing = false
	_show()
