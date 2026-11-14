extends Node
## Game flow, palette and screen transitions. Registered as the `Game` autoload (after `Mission` and `Campaign`).
##
## Keeps the UI readable on phones: in portrait the UI base is 560x996 instead of 1280x720.

signal orientation_changed(portrait: bool)

const SCREENS := {
	"title": "res://scenes/title/title.tscn",
	"campaign": "res://scenes/campaign/campaign.tscn",
	"mission": "res://scenes/mission/mission.tscn",
}

# Palette: bold arcade sci-fi (shared with web/shell.html)
const SPACE := Color("0b0820")
const PANEL := Color("161040")
const INK := Color("e9f1ff")
const MUTED := Color("9a9cc9")
const CYAN := Color("2ef2ff")
const SUN := Color("ffd23f")
const CORAL := Color("ff5a36")
const LIME := Color("7dff6a")
const MAGENTA := Color("ff3df2")
const EARTH := Color("4aa8ff")

const LUNAR_G := 1.62	# m/s², also physics/3d/default_gravity

var mission_id := ""		# mission being played (campaign.json id)
var portrait := false

var _fade: ColorRect
var _busy := false


const ACTIONS := {
	"thrust": [KEY_SPACE, KEY_W, KEY_UP],
	"steer_left": [KEY_A, KEY_LEFT],
	"steer_right": [KEY_D, KEY_RIGHT],
	"move_forward": [KEY_W, KEY_UP],
	"move_back": [KEY_S, KEY_DOWN],
	"move_left": [KEY_A, KEY_LEFT],
	"move_right": [KEY_D, KEY_RIGHT],
	"hop": [KEY_SPACE],
	"run": [KEY_SHIFT],		# lunar lope
	"scan": [KEY_E, KEY_F],
	"view": [KEY_V],
	"commit": [KEY_ENTER, KEY_KP_ENTER],
	"pause": [KEY_ESCAPE, KEY_P],
}


func _ready() -> void:
	for action in ACTIONS:		# keyboard bindings in one place (touch controls call the same actions)
		if not InputMap.has_action(action):
			InputMap.add_action(action)
		for key in ACTIONS[action]:
			var ev := InputEventKey.new()
			ev.physical_keycode = key
			InputMap.action_add_event(action, ev)
	get_window().size_changed.connect(_fit_orientation)
	_fit_orientation()
	var layer := CanvasLayer.new()
	layer.layer = 128
	add_child(layer)
	_fade = ColorRect.new()
	_fade.color = SPACE
	_fade.color.a = 0.0
	_fade.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_fade.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	layer.add_child(_fade)


## Fade to black, change scene, fade back in.
func goto(screen: String) -> void:
	if _busy:
		return
	_busy = true
	_fade.mouse_filter = Control.MOUSE_FILTER_STOP
	var tw := create_tween()
	tw.tween_property(_fade, "color:a", 1.0, 0.22)
	await tw.finished
	get_tree().change_scene_to_file(SCREENS[screen])
	await get_tree().process_frame
	await get_tree().process_frame
	tw = create_tween()
	tw.tween_property(_fade, "color:a", 0.0, 0.3)
	await tw.finished
	_fade.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_busy = false


func play_mission(id: String) -> void:
	mission_id = id
	goto("mission")


func evaluate(site: String, t: int, need_s := Scoring.SAMPLING_S) -> Dictionary:
	return Scoring.evaluate(Mission.sites[site].intervals.sun_full, t, int(Mission.data.window.end_unix), need_s)


func _fit_orientation() -> void:
	var size := get_window().size
	var p := size.y > size.x
	# phones: a narrower base keeps text near 11-12 css px on a 375 px wide screen
	get_window().content_scale_size = Vector2i(560, 996) if p else Vector2i(1280, 720)
	if p != portrait:
		portrait = p
		orientation_changed.emit(p)
