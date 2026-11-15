extends Node3D
## Opening screen: the Moon with the two study sites as pixel-art pins, and the two ways in:
## PLAY CHANGE OF PLANS (the featured mission) and COMPARE SITES (the free comparison tool).
## Drag to turn the globe; tap a pin to read about the site.

const Starfield := preload("res://scenes/common/starfield.gd")
const LABEL_FONT := preload("res://assets/fonts/ChakraPetch-SemiBold.ttf")
const PIN_PX := 0.0085			# globe units per pin pixel (the Moon's radius is 1)
const PICK_RADIUS := 44.0		# px: how close a tap must land to a pin

## Change of Plans, as seeded from the data (see tests/test_moon_map.gd): the slot planned at Tranquility Base
## moves to a time that is locked. 6 h of continuous full-disc sunlight is the surface task's requirement.
const COP_SITE := "apollo-11"
const COP_ALT_SITE := "sl3"
const COP_PLANNED := "2028-03-13T02:00:00"
const COP_LOCKED := "2028-03-16T23:00:00"
const COP_NEED_S := 21600

const PIN_ART := [		# k outline, c colour, h highlight, d shade, w centre
	"..kkkkk..",
	".kchhcck.",
	"kchccccdk",
	"kccwwwcdk",
	"kccwwwcdk",
	"kccwwwcdk",
	"kcccccddk",
	".kccccdk.",
	".kccccdk.",
	"..kccdk..",
	"..kccdk..",
	"...kdk...",
	"....k....",
]

var _yaw := deg_to_rad(20.0)		# start over the near side, Tranquility Base in view
var _pitch := deg_to_rad(-42.0)		# tilted so the south pole shows too
var _dist := 4.2
var _dragging := false
var _drag_moved := 0.0
var _camera: Camera3D
var _globe: Node3D
var _pins := {}			# site id -> {node: Node3D, sprite: Sprite3D, normal: Vector3}
var _selected := ""
var _t := 0.0

var _layout_box: BoxContainer
var _top: VBoxContainer			# logo and tagline
var _side: VBoxContainer			# actions, card, menu
var _side_gap: Control
var _card: PanelContainer
var _card_body: VBoxContainer
var _ui_layer: CanvasLayer
var _sound_btn: Button


func _ready() -> void:
	_build_world()
	_build_ui()
	Game.orientation_changed.connect(_on_orientation)
	_on_orientation(Game.portrait)
	_show_welcome()
	Sfx.music("menu")


# ---------------------------------------------------------------- world

func _build_world() -> void:
	var bg := CanvasLayer.new()
	bg.layer = -1
	add_child(bg)
	bg.add_child(Starfield.new())
	var env := Environment.new()
	env.background_mode = Environment.BG_CANVAS
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color(0.12, 0.1, 0.25)
	env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	env.glow_enabled = true
	env.glow_hdr_threshold = 0.9
	var we := WorldEnvironment.new()
	we.environment = env
	add_child(we)
	_globe = Models.scene("moon_globe").instantiate()
	add_child(_globe)
	var earth: Node3D = Models.team("earth").instantiate()
	earth.scale = Vector3.ONE * 0.16
	earth.position = Vector3(-3.2, 1.7, -4.5)
	add_child(earth)
	_camera = Camera3D.new()
	_camera.fov = 38.0
	add_child(_camera)
	var sun := DirectionalLight3D.new()
	sun.light_energy = 1.5
	sun.rotation = Vector3(deg_to_rad(-20), deg_to_rad(-55), 0)
	_camera.add_child(sun)		# the lit side follows the view, so every site stays readable
	for id: String in Mission.site_ids:
		_add_pin(id)


func _add_pin(id: String) -> void:
	var s: Dictionary = Mission.sites[id]
	var n := _unit(s.lat, s.lon)
	var pin := Node3D.new()
	pin.position = n * 1.02		# clear of the globe's relief
	add_child(pin)
	var sprite := Sprite3D.new()
	sprite.texture = _pin_texture(Game.SUN)
	sprite.pixel_size = PIN_PX
	sprite.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	sprite.texture_filter = BaseMaterial3D.TEXTURE_FILTER_NEAREST
	sprite.alpha_cut = SpriteBase3D.ALPHA_CUT_DISCARD
	sprite.shaded = false
	sprite.no_depth_test = true		# drawn over the globe's bulge near the limb; far-side pins are hidden instead
	sprite.render_priority = 1
	sprite.offset = Vector2(0, PIN_ART.size() / 2.0)		# the pin's tip sits on the surface
	pin.add_child(sprite)
	var label := Label3D.new()
	label.text = Texts.site_info(id).title.to_upper()
	label.font = LABEL_FONT
	label.font_size = 40
	label.outline_size = 12
	label.outline_modulate = Game.SPACE
	label.modulate = Game.INK
	label.pixel_size = 0.0016
	label.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	label.position = Vector3(0, 0, 0)
	label.offset = Vector2(0, 92)
	label.texture_filter = BaseMaterial3D.TEXTURE_FILTER_LINEAR_WITH_MIPMAPS
	label.no_depth_test = true
	label.render_priority = 2
	pin.add_child(label)
	_pins[id] = {"node": pin, "sprite": sprite, "label": label, "normal": n}


## A map pin drawn from PIN_ART in the given colour (pixel art, nearest-filtered).
static func _pin_texture(c: Color) -> ImageTexture:
	var img := Image.create(PIN_ART[0].length(), PIN_ART.size(), false, Image.FORMAT_RGBA8)
	var colours := {"k": Color("0b0820"), "c": c, "h": c.lightened(0.45), "d": c.darkened(0.35), "w": Color("fff8e1")}
	for y in PIN_ART.size():
		var row: String = PIN_ART[y]
		for x in row.length():
			if colours.has(row[x]):
				img.set_pixel(x, y, colours[row[x]])
	return ImageTexture.create_from_image(img)


static func _unit(lat: float, lon: float) -> Vector3:
	var p := deg_to_rad(lat)
	var l := deg_to_rad(lon)
	return Vector3(cos(p) * cos(l), sin(p), -cos(p) * sin(l))


func _process(delta: float) -> void:
	_t += delta
	if not _dragging and _selected == "":
		_yaw += delta * 0.03
	var dir := Vector3(cos(_pitch) * cos(_yaw), sin(_pitch), -cos(_pitch) * sin(_yaw))
	_camera.position = dir * _dist
	_camera.look_at(Vector3.ZERO, Vector3.UP if absf(dir.y) < 0.99 else Vector3.FORWARD)
	for id: String in _pins:
		var p: Dictionary = _pins[id]
		var facing: bool = (p.normal as Vector3).dot(_camera.position.normalized()) > 0.12
		p.label.visible = facing
		p.sprite.visible = facing
		# the selected pin bobs; the others sit still
		var bob := 0.5 + 0.5 * sin(_t * 4.0) if id == _selected else 0.0
		p.sprite.offset.y = PIN_ART.size() / 2.0 + roundf(bob * 2.0)


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouse and event.device == InputEvent.DEVICE_ID_EMULATION:
		return		# touches arrive as ScreenTouch/ScreenDrag
	var press := false
	var release := false
	var at := Vector2.ZERO
	if event is InputEventMouseButton and (event as InputEventMouseButton).button_index == MOUSE_BUTTON_LEFT:
		press = event.pressed
		release = not event.pressed
		at = event.position
	elif event is InputEventScreenTouch:
		press = event.pressed
		release = not event.pressed
		at = event.position
	if press:
		_dragging = true
		_drag_moved = 0.0
	elif release:
		_dragging = false
		if _drag_moved < 8.0:
			_pick(at)
	elif _dragging and (event is InputEventScreenDrag or event is InputEventMouseMotion):
		var rel: Vector2 = event.relative
		_drag_moved += rel.length()
		_yaw -= rel.x * 0.006
		_pitch = clampf(_pitch + rel.y * 0.006, deg_to_rad(-85), deg_to_rad(85))


## Select the visible pin nearest a tap, if any is close enough.
func _pick(at: Vector2) -> void:
	var best := ""
	var best_d := PICK_RADIUS
	for id: String in _pins:
		var p: Dictionary = _pins[id]
		if not p.label.visible:
			continue
		var tip: Vector3 = p.node.global_position + _camera.global_basis.y * (PIN_ART.size() * PIN_PX * 0.5)
		var d := _camera.unproject_position(tip).distance_to(at)
		if d < best_d:
			best_d = d
			best = id
	if best != "":
		Sfx.play("click")
		_select_site(best)


func _turn_to(n: Vector3) -> void:
	var y0 := _yaw
	var p0 := _pitch
	var ty := atan2(-n.z, n.x) if absf(n.y) < 0.95 else _yaw
	var tp := clampf(asin(n.y) * 0.8, deg_to_rad(-70), deg_to_rad(70))
	create_tween().set_trans(Tween.TRANS_SINE).tween_method(func(f: float) -> void:
		_yaw = lerp_angle(y0, ty, f)
		_pitch = lerpf(p0, tp, f), 0.0, 1.0, 0.7)


# ---------------------------------------------------------------- UI

func _build_ui() -> void:
	_ui_layer = CanvasLayer.new()
	add_child(_ui_layer)
	var root := UIKit.full_rect(UIKit.margin(24))
	root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_ui_layer.add_child(root)
	_layout_box = BoxContainer.new()
	_layout_box.mouse_filter = Control.MOUSE_FILTER_IGNORE
	root.add_child(_layout_box)

	_side = UIKit.vbox(12)
	_side.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_layout_box.add_child(_side)
	var globe_room := UIKit.spacer()		# the Moon shows through here, whichever way the box runs
	globe_room.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_layout_box.add_child(globe_room)

	_top = UIKit.vbox(8)
	_top.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_side.add_child(_top)
	var logo := Control.new()		# a magenta "shadow" behind the yellow logo
	logo.custom_minimum_size = Vector2(0, 84)
	logo.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_top.add_child(logo)
	var back := UIKit.display("MOONWARD", 72, Game.MAGENTA)
	back.position = Vector2(5, 5)
	logo.add_child(back)
	logo.add_child(UIKit.display("MOONWARD", 72, Game.SUN))
	_top.add_child(UIKit.label("PLAN THE LIGHT  ·  READ THE SKY  ·  MAKE THE CALL", 16, Game.CYAN, true))

	var play := UIKit.button("PLAY CHANGE OF PLANS", _show_change_of_plans, 26, "primary")
	play.custom_minimum_size = Vector2(0, 64)
	_side.add_child(play)
	var compare := UIKit.button("COMPARE SITES", _open_compare, 22)
	compare.custom_minimum_size = Vector2(0, 54)
	_side.add_child(compare)
	play.focus_mode = Control.FOCUS_ALL		# keyboard: Tab between the two, Enter to go
	compare.focus_mode = Control.FOCUS_ALL
	play.grab_focus.call_deferred()

	_card = UIKit.panel("card")
	_side.add_child(_card)
	_card_body = UIKit.vbox(8)
	_card.add_child(_card_body)

	_side_gap = UIKit.spacer()
	_side.add_child(_side_gap)
	var more := HFlowContainer.new()
	more.add_theme_constant_override("h_separation", 8)
	more.add_theme_constant_override("v_separation", 8)
	_side.add_child(more)
	more.add_child(UIKit.button("TRAINING MISSIONS", func() -> void: Game.goto("campaign"), 15))
	more.add_child(UIKit.button("SCIENCE LOG", func() -> void:
		UIKit.overlay(_ui_layer, "SCIENCE LOG", Texts.science_log()), 15))
	more.add_child(UIKit.button("CREDITS", func() -> void:
		UIKit.overlay(_ui_layer, "CREDITS", Texts.credits()), 15))
	_sound_btn = UIKit.button("", _toggle_sound, 15)
	more.add_child(_sound_btn)
	_update_sound_label()
	_side.add_child(UIKit.label("NASA Space Apps Challenge 2026  ·  hypothetical 2028 analysis window", 13, Game.MUTED, true))
	var i := 0
	for c in [logo, play, compare]:
		UIKit.pop_in(c, i * 0.08)
		i += 1


## Landscape: one column on the left (logo, actions, card, menu), the Moon on the right.
## Portrait: the logo on top, the Moon in the middle, the actions and card at the bottom.
func _on_orientation(portrait: bool) -> void:
	_layout_box.vertical = portrait
	_top.get_parent().remove_child(_top)
	if portrait:
		_layout_box.add_child(_top)
		_layout_box.move_child(_top, 0)
		_layout_box.move_child(_side, 2)
	else:
		_side.add_child(_top)
		_side.move_child(_top, 0)
		_layout_box.move_child(_side, 0)
	_side_gap.visible = not portrait
	_side.custom_minimum_size.x = 0 if portrait else 440
	for l in _top.get_child(0).get_children():
		(l as Label).add_theme_font_size_override("font_size", 60 if portrait else 72)
	_dist = 7.2 if portrait else 4.2
	_camera.keep_aspect = Camera3D.KEEP_WIDTH if portrait else Camera3D.KEEP_HEIGHT
	_camera.h_offset = 0.0 if portrait else -0.8
	_camera.v_offset = -2.3 if portrait else 0.0
	for id: String in _pins:		# pins and labels keep their on-screen size when the Moon is further away
		_pins[id].sprite.pixel_size = PIN_PX * _dist / 4.2
		_pins[id].label.pixel_size = 0.0016 * _dist / 4.2


func _clear_card() -> void:
	for c in _card_body.get_children():
		c.queue_free()


func _show_welcome() -> void:
	_clear_card()
	_card_body.add_child(UIKit.label("THE JOB", 15, Game.MAGENTA))
	_card_body.add_child(UIKit.label("You plan surface work on the Moon. Pick a site and a start time, read when the Sun "
		+ "and Earth are above the real skyline, and make a call you can defend.", 17, Game.INK, true))
	_card_body.add_child(UIKit.label("Tap a pin to read about a site.", 15, Game.MUTED, true))


func _select_site(id: String) -> void:
	_selected = id
	for k: String in _pins:
		_pins[k].sprite.texture = _pin_texture(Game.SUN if k == id else Game.MUTED)
	_turn_to(_pins[id].normal)
	var info := Texts.site_info(id)
	_clear_card()
	_card_body.add_child(UIKit.label(info.where.to_upper(), 14, Game.MAGENTA, true))
	_card_body.add_child(UIKit.display(info.title.to_upper(), 28, Game.SUN))
	_card_body.add_child(UIKit.label(info.text, 16, Game.INK, true))
	UIKit.pop_in(_card)


## The featured mission's brief, with the verdicts computed from the data.
func _show_change_of_plans() -> void:
	Sfx.play("confirm")
	_select_site(COP_SITE)
	var cop := change_of_plans()
	_clear_card()
	_card_body.add_child(UIKit.label("FEATURED MISSION", 14, Game.MAGENTA))
	_card_body.add_child(UIKit.display("CHANGE OF PLANS", 28, Game.SUN))
	_card_body.add_child(UIKit.label(("Your crew was set to start a %s surface task at %s on %s. The landing slot has moved: "
		+ "the new start is %s, and it is locked.") % [Scoring.duration_label(COP_NEED_S), Texts.site_info(COP_SITE).title,
		Mission.utc_label(cop.planned), Mission.utc_label(cop.locked)], 16, Game.INK, true))
	_card_body.add_child(UIKit.label("The task needs the whole Sun above the skyline the entire time. Keep the site, move "
		+ "the site, or hold for better evidence?", 16, Game.CYAN, true))
	var go := UIKit.button("COMPARE THE OPTIONS", func() -> void: _open_compare(cop.locked, [COP_SITE, COP_ALT_SITE]), 20, "primary")
	_card_body.add_child(go)
	_card_body.add_child(UIKit.label("Next build: lock in your recommendation (A, B, both, neither or hold) and get Mission "
		+ "Control's response.", 13, Game.MUTED, true))
	UIKit.pop_in(_card)


## The scenario's times and each option's verdict, from the bundled data.
static func change_of_plans() -> Dictionary:
	var planned := Time.get_unix_time_from_datetime_string(COP_PLANNED)
	var locked := Time.get_unix_time_from_datetime_string(COP_LOCKED)
	return {"planned": planned, "locked": locked, "need_s": COP_NEED_S,
		"planned_keep": verdict(COP_SITE, planned, COP_NEED_S),
		"locked_keep": verdict(COP_SITE, locked, COP_NEED_S),
		"locked_move": verdict(COP_ALT_SITE, locked, COP_NEED_S)}


## "meets", "misses" or "unknown" for continuous full-disc sunlight from `t` for `need_s`, across the skyline
## uncertainty: each sun_full interval is [start, end, start uncertainty, end uncertainty] in seconds.
static func verdict(site: String, t: int, need_s: int) -> String:
	if t + need_s > int(Mission.data.window.end_unix):
		return "unknown"		# the data ends before the task would
	for iv: Array in Mission.sites[site].intervals.sun_full:
		var a := int(iv[0])
		var b := int(iv[1]) + 1
		var ua := int(iv[2]) if iv.size() > 2 else 0
		var ub := int(iv[3]) if iv.size() > 3 else 0
		if t + need_s <= b + ub and t >= a - ua:		# could fit inside this interval
			return "meets" if t >= a + ua and t + need_s <= b - ub else "unknown"
		if t >= a - ua and t < b + ub:					# starts in this interval but outlasts even its latest end
			return "misses"
	return "misses"


func _open_compare(start := -1, sites: Array = []) -> void:
	Sfx.play("confirm")
	if start >= 0:
		Navigator.same_time = true
		while Navigator.cards.size() < sites.size():
			Navigator.cards.append(Navigator.cards[0].duplicate(true))
		for i in sites.size():
			Navigator.cards[i].merge({"key": "artemis-iv-era/" + str(sites[i]), "start": start, "duration": COP_NEED_S}, true)
		Navigator.active_index = 0
		Navigator.mission_plan_initialized = true
	Game.open_compare = true
	Game.return_to = "map"
	Game.mission_id = "sunset-operations"
	Game.goto("operations")


func _toggle_sound() -> void:
	Sfx.set_muted(not Sfx.muted)
	_update_sound_label()


func _update_sound_label() -> void:
	_sound_btn.text = "SOUND: OFF" if Sfx.muted else "SOUND: ON"
