extends Node3D
## Campaign select: the Moon with the two landing sites, a strip of mission nodes, and the selected mission's card.
## Drag to turn the globe. Picking a mission swings the globe to its site.

const Starfield := preload("res://scenes/common/starfield.gd")
const MissionNode := preload("res://scenes/campaign/mission_node.gd")
const PIN_SCALE := 0.1

var _yaw := deg_to_rad(20.0)
var _pitch := deg_to_rad(-32.0)
var _dist := 3.6
var _dragging := false
var _camera: Camera3D
var _pins := {}
var _nodes := {}
var _selected := ""

var _layout_box: BoxContainer
var _card: PanelContainer
var _card_body: VBoxContainer


func _ready() -> void:
	_build_world()
	_build_ui()
	Game.orientation_changed.connect(_on_orientation)
	_on_orientation(Game.portrait)
	_select(Game.mission_id if Game.mission_id != "" and Campaign.unlocked(Game.mission_id) else Campaign.next_up())
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
	add_child(Models.scene("moon_globe").instantiate())
	_camera = Camera3D.new()
	_camera.fov = 38.0
	add_child(_camera)
	var sun := DirectionalLight3D.new()
	sun.light_energy = 1.5
	sun.rotation = Vector3(deg_to_rad(-20), deg_to_rad(-55), 0)
	_camera.add_child(sun)
	var pin_scene := Models.scene("site_pin")
	for id in Mission.site_ids:
		var s: Dictionary = Mission.sites[id]
		var n := _unit(s.lat, s.lon)
		var pin: Node3D = pin_scene.instantiate()
		add_child(pin)
		var side := n.cross(Vector3.UP if absf(n.y) < 0.95 else Vector3.RIGHT).normalized()
		pin.transform = Transform3D(Basis(side, n, side.cross(n)).orthonormalized().scaled(Vector3.ONE * PIN_SCALE), n)
		_pins[id] = {"node": pin, "normal": n}


static func _unit(lat: float, lon: float) -> Vector3:
	var p := deg_to_rad(lat)
	var l := deg_to_rad(lon)
	return Vector3(cos(p) * cos(l), sin(p), -cos(p) * sin(l))


func _tint(pin: Node, c: Color, energy: float) -> void:
	var mat := StandardMaterial3D.new()
	mat.albedo_color = c
	mat.emission_enabled = true
	mat.emission = c
	mat.emission_energy_multiplier = energy
	for mi in pin.find_children("*", "MeshInstance3D", true, false):
		(mi as MeshInstance3D).material_override = mat


func _process(delta: float) -> void:
	if not _dragging:
		_yaw += delta * 0.03
	var dir := Vector3(cos(_pitch) * cos(_yaw), sin(_pitch), -cos(_pitch) * sin(_yaw))
	_camera.position = dir * _dist
	_camera.look_at(Vector3.ZERO, Vector3.UP if absf(dir.y) < 0.99 else Vector3.FORWARD)


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouse and event.device == InputEvent.DEVICE_ID_EMULATION:
		return
	if event is InputEventMouseButton and event.button_index == MOUSE_BUTTON_LEFT:
		_dragging = event.pressed
	elif event is InputEventScreenTouch:
		_dragging = event.pressed
	elif event is InputEventScreenDrag or (event is InputEventMouseMotion and _dragging):
		_yaw -= event.relative.x * 0.006
		_pitch = clampf(_pitch + event.relative.y * 0.006, deg_to_rad(-85), deg_to_rad(85))


# ---------------------------------------------------------------- UI

func _build_ui() -> void:
	var layer := CanvasLayer.new()
	add_child(layer)
	var root := UIKit.full_rect(UIKit.margin(20))
	root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	layer.add_child(root)
	var col := UIKit.vbox(10)
	col.mouse_filter = Control.MOUSE_FILTER_IGNORE
	root.add_child(col)

	var head := UIKit.hbox(12)
	col.add_child(head)
	head.add_child(UIKit.button("‹ TITLE", func() -> void:
		Sfx.play("back")
		Game.goto("title"), 17))
	var title := UIKit.display("MISSIONS", 34, Game.SUN)
	title.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	head.add_child(title)
	head.add_child(UIKit.stars(1, 1, 24))
	head.add_child(UIKit.label("%d / %d" % [Campaign.total_stars(), Campaign.missions.size() * 3], 20, Game.SUN))

	_layout_box = BoxContainer.new()
	_layout_box.size_flags_vertical = Control.SIZE_EXPAND_FILL
	_layout_box.mouse_filter = Control.MOUSE_FILTER_IGNORE
	col.add_child(_layout_box)
	_layout_box.add_child(UIKit.spacer(false))
	_card = UIKit.panel("card")
	_card.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	_layout_box.add_child(_card)
	_card_body = UIKit.vbox(10)
	_card.add_child(_card_body)

	# the mission strip
	var strip_panel := UIKit.panel("hud")
	col.add_child(strip_panel)
	var scroll := ScrollContainer.new()
	scroll.vertical_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	scroll.custom_minimum_size.y = 90
	strip_panel.add_child(scroll)
	var strip := UIKit.hbox(4)
	strip.alignment = BoxContainer.ALIGNMENT_CENTER
	strip.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	scroll.add_child(strip)
	for m: Dictionary in Campaign.missions:
		var node := MissionNode.new()
		node.id = m.id
		node.number = m.number
		node.stars = Campaign.stars(m.id)
		node.locked = not Campaign.unlocked(m.id)
		node.picked.connect(_select)
		strip.add_child(node)
		_nodes[m.id] = node


func _on_orientation(portrait: bool) -> void:
	_layout_box.vertical = portrait
	_layout_box.move_child(_card, 1)
	_card.custom_minimum_size.x = 0 if portrait else 470
	_dist = 4.6 if portrait else 3.6
	_camera.keep_aspect = Camera3D.KEEP_WIDTH if portrait else Camera3D.KEEP_HEIGHT
	_camera.h_offset = 0.0 if portrait else -0.9
	_camera.v_offset = 0.55 if portrait else 0.0


func _select(id: String) -> void:
	_selected = id
	Game.mission_id = id
	for k in _nodes:
		_nodes[k].selected = k == id
		_nodes[k].queue_redraw()
	var m: Dictionary = Campaign.by_id[id]
	for pid in _pins:
		var on: bool = pid in m.sites
		_tint(_pins[pid].node, Game.SUN if on else Game.MUTED, 2.0 if on else 0.2)
	# swing toward the (first) site
	var n: Vector3 = _pins[m.sites[0]].normal
	var y0 := _yaw
	var p0 := _pitch
	var ty := atan2(-n.z, n.x) if absf(n.y) < 0.95 else _yaw
	var tp := clampf(asin(n.y) * 0.75, deg_to_rad(-62), deg_to_rad(62))
	create_tween().set_trans(Tween.TRANS_SINE).tween_method(func(f: float) -> void:
		_yaw = lerp_angle(y0, ty, f)
		_pitch = lerpf(p0, tp, f), 0.0, 1.0, 0.7)
	_fill_card(m)


func _fill_card(m: Dictionary) -> void:
	for c in _card_body.get_children():
		c.queue_free()
	_card_body.add_child(UIKit.label("MISSION %d" % m.number, 15, Game.MAGENTA))
	_card_body.add_child(UIKit.display(m.title.to_upper(), 30, Game.SUN))
	_card_body.add_child(UIKit.label(m.tagline, 17, Game.CYAN, true))
	var where := " or ".join(m.sites.map(func(s: String) -> String: return Texts.site_info(s).title))
	_card_body.add_child(UIKit.label(where, 15, Game.MUTED, true))
	var goals := UIKit.vbox(6)
	_card_body.add_child(goals)
	goals.add_child(_goal("Hold %d h of unbroken sunlight" % int(m.need_s / 3600), true))
	goals.add_child(_goal("Bonus: " + str(m.bonus.text), true))
	goals.add_child(_goal("Beat par: %d points" % int(m.par), true))
	var row := UIKit.hbox(12)
	_card_body.add_child(row)
	row.add_child(UIKit.stars(Campaign.stars(m.id), 3, 26))
	var best := Campaign.best(m.id)
	row.add_child(UIKit.label("BEST %d" % best if best > 0 else "NOT FLOWN YET", 16, Game.MUTED))
	var go := UIKit.button("LAUNCH  ▶", func() -> void:
		Sfx.play("confirm")
		Game.play_mission(m.id), 26, "primary")
	go.custom_minimum_size.y = 62
	_card_body.add_child(go)
	UIKit.pop_in(_card)


func _goal(text: String, on: bool) -> Control:
	var h := UIKit.hbox(10)
	var dot := UIKit.label("▶", 14, Game.CYAN if on else Game.MUTED)
	h.add_child(dot)
	var l := UIKit.label(text, 17, Game.INK, true)
	l.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	h.add_child(l)
	return h
