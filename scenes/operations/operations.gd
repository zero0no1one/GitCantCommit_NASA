extends Node3D
## The preview is presentation only. Its debrief always evaluates the saved plan.

const Astronaut := preload("res://scenes/mission/astronaut.gd")
const MissionNavigatorUI := preload("res://scenes/operations/mission_navigator.gd")
var navigator_ui: RefCounted
var site := "apollo-11"
var start := 0
var at := 0.0
var previewing := false
var result: Dictionary = {}
var world: SiteWorld
var camera: Camera3D
var inspector: CharacterBody3D
var body: VBoxContainer
var readout: Label
var clock_label: Label
var slider: HSlider
var schedule: Array = []
var phase := "plan"
var view_index := 0
var _tick := -1
var _generation := 0

func _ready() -> void:
	if not Game.mission_id in ["sunset-operations", "earth-link"]:
		Game.mission_id = "sunset-operations"
	# Near the bundled equatorial sunset, useful for the electrical-endurance lesson.
	start = floori((float(Mission.sites[site].intervals.sun_full[0][1]) - 10800.0) / 600.0) * 600
	if not Navigator.mission_plan_initialized:
		Navigator.set_card(0, "artemis-iv-era/" + site, start, Operations.DURATION_S)
		Navigator.mission_plan_initialized = true
	var card: Dictionary = Navigator.cards[Navigator.active_index]
	var initial_key := str(card.key)
	start = int(card.start)
	var record: Dictionary = Navigator.records[card.key]
	if record.verified:
		site = str(record.site.id)
	at = start
	navigator_ui = MissionNavigatorUI.new(self)
	for activity in ["Observation request", "Telemetry request", "Standby request"]:
		schedule.append({"activity": activity, "duration_s": 7200})
	_build_ui()
	Game.orientation_changed.connect(_fit_camera)
	_change_site(site)
	# A preview must not borrow the last original site's surface or sky.
	if not record.verified:
		Navigator.cards[Navigator.active_index].key = initial_key
		world.visible = false
	_plan()
	if Game.open_compare:		# arrived from the Moon map's COMPARE SITES / Change of Plans
		Game.open_compare = false
		navigator_ui.compare()
	Sfx.music("mission")

func _build_ui() -> void:
	var layer := CanvasLayer.new()
	add_child(layer)
	var root := UIKit.full_rect(UIKit.margin(16))
	root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	layer.add_child(root)
	var col := UIKit.vbox(8)
	col.mouse_filter = Control.MOUSE_FILTER_IGNORE
	root.add_child(col)
	var top := UIKit.hbox(12)
	col.add_child(top)
	top.add_child(_button("MAP" if Game.return_to == "map" else "MISSIONS", func() -> void: Game.goto(Game.return_to)))
	var heading := "MOONWARD / COMPARE SITES" if Game.return_to == "map" else "MOONWARD / " + str(Campaign.by_id[Game.mission_id].title).to_upper()
	var title := UIKit.label(heading, 23, Game.SUN, true)
	title.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	top.add_child(title)
	top.add_child(_button("VIEW", _cycle_view))
	col.add_child(UIKit.label("Exploration-era planning scenario / Surveyor robotic reference / validation pending", 16, Game.CYAN, true))
	col.add_child(UIKit.spacer())
	var panel := UIKit.panel("hud")
	col.add_child(panel)
	var scroll := ScrollContainer.new()
	scroll.custom_minimum_size.y = 345
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	panel.add_child(scroll)
	body = UIKit.vbox(8)
	body.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	scroll.add_child(body)

func _button(text: String, action: Callable) -> Button:
	var b := UIKit.button(text, action, 18)
	b.focus_mode = Control.FOCUS_ALL
	b.tree_entered.connect(func() -> void:
		if b.is_inside_tree():
			b.grab_focus())
	return b

func _clear() -> void:
	for child in body.get_children():
		body.remove_child(child)
		child.queue_free()
	readout = null
	clock_label = null

func _text(text: String, color: Color = Game.INK) -> Label:
	var label := UIKit.label(text, 17, color, true)
	body.add_child(label)
	return label

func _plan() -> void:
	phase = "plan"
	previewing = false
	at = start
	if is_instance_valid(inspector):
		inspector.frozen = true
	_clear()
	_text("1 / CHOOSE SITE AND UTC START", Game.SUN)
	var actions := HFlowContainer.new()
	body.add_child(actions)
	actions.add_child(_button("INSPECT", _inspect))
	actions.add_child(_button("PREVIEW / 720x", _preview))
	actions.add_child(_button("ASSESS", _assess))
	actions.add_child(_button("COMPARE", func() -> void: navigator_ui.compare()))
	actions.add_child(_button("REVIEW", func() -> void: navigator_ui.review()))
	var sites := UIKit.hbox(12)
	body.add_child(sites)
	for sid: String in Mission.site_ids:
		var b := _button(Texts.site_info(sid).title, func() -> void: _change_site(sid))
		sites.add_child(b)
		if sid == site:
			b.grab_focus()
	_text("Navigator plan: " + str(Navigator.cards[Navigator.active_index].key), Game.CYAN)
	clock_label = _text(Mission.utc_label(start))
	slider = HSlider.new()
	var selected_samples: Dictionary = Navigator.records[Navigator.cards[Navigator.active_index].key].site.samples
	slider.min_value = selected_samples.start_unix
	slider.max_value = int(selected_samples.start_unix) + (int(selected_samples.count)-1)*int(selected_samples.step_s)
	slider.step = 600
	slider.value = start
	body.add_child(slider)
	slider.value_changed.connect(func(value: float) -> void:
		start = int(value)
		at = value
		navigator_ui.sync_plan()
		_refresh())
	_text("Bundled coverage: " + Mission.utc_label(selected_samples.start_unix) + " to " + Mission.utc_label(int(selected_samples.start_unix)+(int(selected_samples.count)-1)*int(selected_samples.step_s)), Game.MUTED)
	_text("The operating-sequence lesson uses a six-hour training interval. Compare accepts 10 minutes to 24 hours; other durations and preview records receive an unknown mission assessment.", Game.MUTED)
	readout = _text("")
	_text("2 / REQUEST AN OPERATING SEQUENCE (three two-hour blocks)", Game.SUN)
	_text("Activities below are planning requests, not verified Surveyor hardware modes. No low-power mode or free panel rotation is offered.", Game.MUTED)
	for i in schedule.size():
		var row := UIKit.hbox(10)
		body.add_child(row)
		row.add_child(UIKit.label("+%d to +%d h" % [i * 2, (i + 1) * 2], 18))
		var choice := OptionButton.new()
		for activity in ["Observation request", "Telemetry request", "Standby request"]:
			choice.add_item(activity)
		choice.select(["Observation request", "Telemetry request", "Standby request"].find(schedule[i].activity))
		choice.item_selected.connect(func(index: int) -> void: schedule[i].activity = choice.get_item_text(index))
		row.add_child(choice)
	var telemetry := OptionButton.new()
	telemetry.add_item("Telemetry: UNKNOWN")
	telemetry.clip_text = true
	telemetry.tooltip_text = "No verified Surveyor 1 telemetry configuration is available."
	telemetry.disabled = true
	body.add_child(telemetry)
	body.add_child(_button("EVIDENCE AND ASSUMPTIONS", _evidence))
	body.add_child(_button("HINT", func() -> void: _text("Compare the Sun's direction with the array indicator. A favorable sky position is only one input: array pointing, electrical demand and stored energy also matter. For Earth Link, ask which of the three conditions is actually supported.", Game.CYAN)))
	_refresh()

func _change_site(sid: String) -> void:
	Navigator.set_card(Navigator.active_index, "artemis-iv-era/" + sid, start, int(Navigator.cards[Navigator.active_index].duration))
	_generation += 1
	var generation := _generation
	site = sid
	if is_instance_valid(world):
		remove_child(world)
		world.queue_free()
	world = SiteWorld.new(site)
	add_child(world)
	world.set_time(at)
	camera = Camera3D.new()
	camera.far = 6500
	camera.keep_aspect = Camera3D.KEEP_WIDTH if Game.portrait else Camera3D.KEEP_HEIGHT
	world.add_child(camera)
	camera.position = Vector3(12, 8, 16)
	camera.look_at(Vector3(0, 2, 0))
	camera.v_offset = -4.0
	camera.current = true
	view_index = 0
	inspector = null
	await get_tree().physics_frame
	if generation != _generation or not is_inside_tree():
		return
	var ground := world.ground_y(Vector2.ZERO)
	var inspection_light := OmniLight3D.new()
	inspection_light.position = Vector3(0, ground + 8, 0)
	inspection_light.omni_range = 30
	inspection_light.light_energy = 1.5
	world.add_child(inspection_light)
	_marker("ASSESSMENT ORIGIN", Vector3(0, ground + 1.4, 0), Game.CYAN)
	var ring := MeshInstance3D.new()
	var mesh := TorusMesh.new()
	mesh.inner_radius = 1.7
	mesh.outer_radius = 2.0
	ring.mesh = mesh
	ring.position = Vector3(0, ground + 0.15, 0)
	world.add_child(ring)
	var lander: Node3D = Models.scene("lander").instantiate()
	world.put(lander, Vector2(5, -4))
	_marker("ROBOTIC REFERENCE", lander.position + Vector3(0, 6, 0), Game.SUN)
	_marker("ARRAY: UNVERIFIED", lander.position + Vector3(-5, 4, 0), Game.SUN)
	_marker("ANTENNA: UNVERIFIED", lander.position + Vector3(6, 3, 0), Game.CYAN)
	_marker("INSTRUMENT", Vector3(-6, ground + 1, -3), Game.LIME)
	for direction in [["N", Vector3(0, 0, -15)], ["E", Vector3(15, 0, 0)], ["S", Vector3(0, 0, 15)], ["W", Vector3(-15, 0, 0)]]:
		_marker(direction[0], direction[1] + Vector3(0, ground + 1, 0), Game.INK)
	camera.position += Vector3(0, ground, 0)
	inspector = Astronaut.new()
	world.add_child(inspector)
	inspector.position = Vector3(0, ground + 1, 8)
	inspector.frozen = true
	camera.make_current()
	_refresh()

func _marker(text: String, position_: Vector3, color: Color) -> void:
	var label := Label3D.new()
	label.text = text
	label.font_size = 36
	label.pixel_size = 0.016
	label.modulate = color
	label.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	label.position = position_
	world.add_child(label)

func _cycle_view() -> void:
	if not navigator_ui.surface_available():
		return
	if not is_instance_valid(inspector):
		return
	view_index = (view_index + 1) % 3
	inspector.frozen = view_index == 0 or phase != "inspect"
	if view_index == 0:
		camera.make_current()
	else:
		inspector.set_view(view_index == 2)
		inspector.camera.make_current()

func _fit_camera(portrait: bool) -> void:
	if is_instance_valid(camera):
		camera.keep_aspect = Camera3D.KEEP_WIDTH if portrait else Camera3D.KEEP_HEIGHT

func _inspect() -> void:
	if not navigator_ui.surface_available():
		navigator_ui.review()
		return
	phase = "inspect"
	_clear()
	_text("SURFACE INSPECTION / SURVEY, THIRD PERSON, FIRST PERSON", Game.SUN)
	_text("VIEW cycles cameras. WASD moves the virtual inspector; drag to look. The cyan assessment marker remains the calculation origin. Surveyor 1 was robotic, not crewed.")
	_text("Inspect the array, antenna and instrument labels. Inspection lighting is artificial. Rendered orientation and shadows are illustrative; they do not provide hardware pointing limits or scientific evidence.", Game.MUTED)
	readout = _text("")
	body.add_child(_button("RETURN TO PLAN", _plan))
	body.add_child(_button("PREVIEW / 720x", _preview))
	if is_instance_valid(inspector):
		inspector.frozen = view_index == 0
	_refresh()

func _refresh() -> void:
	if navigator_ui != null and not navigator_ui.surface_available():
		if is_instance_valid(world):
			world.visible = false
		if is_instance_valid(readout):
			readout.text = navigator_ui.card_text(Navigator.cards[Navigator.active_index]) + "\nSurface inspection unavailable for this site/window."
		return
	if not is_instance_valid(world):
		return
	world.set_time(at)
	world.visible = true
	if is_instance_valid(clock_label):
		clock_label.text = Mission.utc_label(at)
	if not is_instance_valid(readout):
		return
	var s: Dictionary = Mission.sites[site]
	var sun_state := Operations.illumination(s.intervals, int(at))
	var earth_az := Mission.sample(site, "earth_az", at)
	var earth_el := Mission.sample(site, "earth_el", at)
	var obstruction := Mission.skyline(site, earth_az)
	var margin := earth_el - obstruction
	var sensitivity := float(Mission.data.conventions.skyline_error_deg)
	var visibility := "UNKNOWN (near skyline)" if absf(margin) <= sensitivity else ("VISIBLE" if margin > 0 else "BLOCKED")
	var block := clampi(int((at - start) / 7200), 0, schedule.size() - 1)
	readout.text = "%s / %s\nSun: %s | az %.1f deg / el %.1f deg\nEarth centre: %s | az %.1f deg / el %.1f deg | terrain %.1f deg\nSolar output: UNKNOWN | demand: UNKNOWN | battery: UNKNOWN\nDSS-14 contact intervals: UNKNOWN | range and radio performance: UNKNOWN\nArray and antenna pointing: UNKNOWN | remaining %.2f h\nSource: bundled Horizons + LOLA, 10-minute samples; skyline sensitivity +/-%.1f deg (not an accuracy guarantee).\nActivity: %s (hardware mapping unverified)" % [
		Texts.site_info(site).title, Mission.utc_label(at), sun_state, Mission.sample(site, "sun_az", at), Mission.sample(site, "sun_el", at),
		visibility, earth_az, earth_el, obstruction, maxf(0, start + Operations.DURATION_S - at) / 3600.0, sensitivity, schedule[block].activity]

func _preview() -> void:
	if not navigator_ui.training_available():
		_assess()
		return
	phase = "preview"
	at = start
	_tick = -1
	result = Operations.assess(Mission.data, site, start, Game.mission_id, schedule)
	result["navigator_plan"] = Navigator.cards[Navigator.active_index].duplicate(true)
	_clear()
	_text("OPERATIONS PREVIEW / ACCELERATED TIME 720x", Game.SUN)
	_text("Six simulated hours in 30 seconds. Watching and skipping use the same saved plan and assessment.")
	clock_label = _text("")
	readout = _text("")
	body.add_child(_button("SKIP TO DEBRIEF", _debrief))
	body.add_child(_button("REVISE PLAN", _plan))
	if is_instance_valid(inspector):
		inspector.frozen = true
	previewing = true
	_refresh()

func _process(delta: float) -> void:
	if not previewing:
		return
	at = minf(at + delta * 720.0, start + Operations.DURATION_S)
	world.set_time(at)
	var tick := int((at - start) / 60)
	if tick != _tick:
		_tick = tick
		_refresh()
	if at >= start + Operations.DURATION_S:
		_debrief()

func _assess() -> void:
	result = navigator_ui.mission_assessment()
	_debrief()

func _debrief() -> void:
	previewing = false
	phase = "debrief"
	_clear()
	_text("DEBRIEF / " + str(result.state).to_upper() + " / NOT SCIENTIFICALLY SCORED", Game.SUN)
	for state in ["met", "violated", "unknown"]:
		_text(state.to_upper(), Game.CYAN)
		var found := false
		for c: Dictionary in result.criteria:
			if c.state == state:
				found = true
				_text(c.name + ": " + c.cause + "\nEvidence: " + c.evidence)
		if not found:
			_text("None.", Game.MUTED)
	_text("WHAT TO CHANGE", Game.SUN)
	_text("Compare the other site, shift the UTC start, or revise activity requests. Sunlight does not guarantee adequate power; darkness does not imply immediate electrical failure. Visible Earth does not prove station access or signal reception.")
	_text("Unknown is useful information, not a penalty. This assessment establishes neither lunar-night thermal survival nor a certified landing recommendation. Earth Link never books DSN service.", Game.MUTED)
	body.add_child(_button("REVISE PLAN", _plan))
	body.add_child(_button("SOURCES AND ASSUMPTIONS", _evidence))
	body.add_child(_button("REVIEW COMPARISON", func() -> void: navigator_ui.review()))
	(body.get_child(body.get_child_count() - 2) as Button).grab_focus()

func _evidence() -> void:
	previewing = false
	phase = "evidence"
	if is_instance_valid(inspector):
		inspector.frozen = true
	_clear()
	_text("EVIDENCE / CONFIGURATION READINESS", Game.SUN)
	if not navigator_ui.surface_available():
		_text(navigator_ui.card_text(Navigator.cards[Navigator.active_index]))
		body.add_child(_button("BACK TO PLAN", _plan))
		return
	_text("Available: bundled topocentric Sun/Earth geometry, terrain skyline and illumination intervals. No Surveyor 1 flight power or radio configuration is validated here. Initial battery energy and temperature, charging limits, equipment loads, panel pointing, antenna pattern and reception thresholds are UNKNOWN.")
	var s: Dictionary = Mission.sites[site]
	_text("Fixed observer: %.5f deg latitude, %.5f deg east longitude; %.1f m above terrain.\nTerrain product: %s\nSampling resolution is not positional accuracy. Near-field decoration, equipment shadows and inspection lighting are not measurements." % [s.lat, s.lon, s.panel_height_m, str(s.terrain_source)])
	_text("The bundled skyline sensitivity is not a complete error budget. See tools/data/VALIDATION.md for terrain-resolution sensitivity and independent geometry comparisons. Results close to boundaries require further evidence.")
	_text("Six hours and the 30-minute downlink are training objectives. This 2028 scenario uses a historical robotic reference, not a reconstruction. Blue Ghost provides educational context only; its performance is not copied into Surveyor.")
	for source: Dictionary in Mission.data.sources:
		body.add_child(UIKit.rich("[url=%s]%s[/url]" % [source.url, source.name], 16))
	for source: Array in Operations.SOURCES:
		body.add_child(UIKit.rich("[url=%s]%s[/url]" % [source[1], source[0]], 16))
	_text("Outstanding: identify and review the Surveyor 1 telecommunications and power-system report sections before enabling flight mode controls or scored engineering results.", Game.CYAN)
	body.add_child(_button("BACK TO PLAN", _plan))
