class_name PixelAstronaut
extends Node3D
## The HD-2D astronaut: a pixel-art sprite standing upright in the 3D world.
## It shows one of four views (front, back, left, right) chosen from where it faces relative to the camera,
## and plays idle or walk frames from assets/pixel/astronaut/astronaut_sheet.png
## (built by tools/pixel/build_astronaut_sheet.gd from the PixelLab rotations).

const SHEET := preload("res://assets/pixel/astronaut/astronaut_sheet.png")
const COLS := 6				# idle0, idle1, walk0..walk3
const ROWS := ["south", "east", "north", "west"]		# sheet row order
const HEIGHT := 1.8			# metres from sole to helmet top
const ART_TOP := 3			# first and last opaque rows of the 64 px art
const ART_SOLE := 60
const IDLE_FPS := 1.6
const WALK_FPS := 6.0		# at rate 1.0: one 4-frame cycle (two steps) every 0.67 s
const HYSTERESIS := deg_to_rad(8.0)

## World-space horizontal direction the astronaut faces.
var facing := Vector3.FORWARD
## "idle", "walk", "air" or "scan".
var state := "idle"
## Walk speed multiplier (1.0 = the authored cadence).
var rate := 1.0
var sprite: Sprite3D
var view := "south"

var _t := 0.0
var _shadow: Sprite3D
var _sun: DirectionalLight3D


func _ready() -> void:
	sprite = Sprite3D.new()
	sprite.texture = SHEET
	sprite.hframes = COLS
	sprite.vframes = ROWS.size()
	sprite.pixel_size = HEIGHT / float(ART_SOLE - ART_TOP + 1)
	sprite.billboard = BaseMaterial3D.BILLBOARD_FIXED_Y		# stays upright, turns to face the camera
	sprite.texture_filter = BaseMaterial3D.TEXTURE_FILTER_NEAREST
	sprite.alpha_cut = SpriteBase3D.ALPHA_CUT_DISCARD
	sprite.shaded = false
	sprite.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	# put the soles (row ART_SOLE) on the node's origin
	sprite.position.y = float(ART_SOLE + 1 - 32) * sprite.pixel_size
	add_child(sprite)
	# An invisible copy turned square to the Sun casts the shadow, so the silhouette falls on the ground
	# (the visible sprite faces the camera and would cast only a sliver).
	_shadow = sprite.duplicate() as Sprite3D
	_shadow.billboard = BaseMaterial3D.BILLBOARD_DISABLED
	_shadow.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_SHADOWS_ONLY
	add_child(_shadow)


## Set what the astronaut is doing. `new_rate` scales the walk cadence.
func play(new_state: String, new_rate := 1.0) -> void:
	if new_state != state and not (new_state == "air" and state == "walk"):
		_t = 0.0
	state = new_state
	rate = new_rate


func _process(delta: float) -> void:
	var cam := get_viewport().get_camera_3d()
	if cam:
		view = _pick_view(cam)
	_t += delta
	var col := 0
	match state:
		"walk":
			col = 2 + int(_t * WALK_FPS * rate) % 4
		"air":
			col = 2		# legs apart while airborne
		"scan":
			col = 0
		_:
			col = int(_t * IDLE_FPS) % 2
	sprite.frame = ROWS.find(view) * COLS + col
	_aim_shadow()


func _aim_shadow() -> void:
	if not is_instance_valid(_sun):
		var lights := get_tree().root.find_children("*", "DirectionalLight3D", true, false)
		if lights.is_empty():
			return
		_sun = lights[0] as DirectionalLight3D
		for l: DirectionalLight3D in lights:		# the shadow-casting light is the Sun; others are fills
			if l.shadow_enabled:
				_sun = l
				break
	var d := -_sun.global_basis.z		# direction the light travels
	if Vector2(d.x, d.z).length_squared() < 1e-6:
		return		# Sun overhead: any orientation casts the same small shadow
	_shadow.global_rotation = Vector3(0, atan2(d.x, d.z), 0)
	_shadow.frame = sprite.frame


## Which of the four drawn views the camera sees, with a little hysteresis so it doesn't flicker on a diagonal.
func _pick_view(cam: Camera3D) -> String:
	var fwd := -cam.global_basis.z
	fwd.y = 0.0
	if fwd.length_squared() < 1e-6 or facing.length_squared() < 1e-6:
		return view
	fwd = fwd.normalized()
	var right := Vector3(-fwd.z, 0, fwd.x)
	var f := Vector3(facing.x, 0, facing.z).normalized()
	# angle of the facing direction seen from the camera: 0 = walking away (back view), +90 = to screen right
	var a := atan2(f.dot(right), f.dot(fwd))
	var current := {"north": 0.0, "east": PI / 2, "south": PI, "west": -PI / 2}[view] as float
	if absf(angle_difference(a, current)) < PI / 4 + HYSTERESIS:
		return view
	var i := posmod(roundi(a / (PI / 2)), 4)
	return ["north", "east", "south", "west"][i]
