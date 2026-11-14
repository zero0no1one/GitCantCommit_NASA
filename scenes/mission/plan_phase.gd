extends Node
## PLAN: pick the touchdown time in the 3D world.
##  - SUN SCOPE view (default): a telescope view from the site toward the Sun and the ridge; drag anywhere to
##    move the Sun along its real path (scrubs time). SITE view: orbit the landing site; drag the Sun to scrub.
##  - The sun-path ribbon shows the next hours (gold clear / coral blocked); the Sunlight Clock shows how long
##    unbroken sunlight lasts from the chosen time; the dial scrubs the decision window in 10-minute steps.
##  - FORECAST lights the passing touchdowns on the dial for a score penalty.

signal committed(touchdown: int, forecast_used: bool)
signal site_switch(site_id: String)

const TimeDial := preload("res://scenes/mission/widgets/time_dial.gd")
const SunlightClock := preload("res://scenes/mission/widgets/sunlight_clock.gd")
const SunRibbon := preload("res://scenes/mission/widgets/sun_ribbon.gd")
const FORECAST_COST := 200

var host: Node
var mission: Dictionary
var world: SiteWorld
var t := 0

var _cam: Camera3D
var _scope := true
var _orbit_yaw := 0.0
var _orbit_pitch := deg_to_rad(-22.0)
var _orbit_dist := 55.0
var _aim := Vector3.FORWARD
var _aim_target := Vector3.FORWARD
var _fov_target := 12.0
var _drag := ""				# "", "sun", "orbit"
var _ribbon: Node3D
var _ring: MeshInstance3D
var _ghost: Node3D
var _forecast := false
var _window_dirs: Array = []	# [time, dir] across the window, for dragging the Sun

var _ui: Control
var _dial: TimeDial
var _clock: SunlightClock
var _time_label: Label
var _status: Label
var _view_btn: Button
var _forecast_btn: Button
var _bottom: BoxContainer
var _row: BoxContainer


func setup(p_host: Node, p_mission: Dictionary, p_world: SiteWorld, start_t: int) -> void:
	host = p_host
	mission = p_mission
	world = p_world
	t = start_t


func _ready() -> void:
	_cam = Camera3D.new()
	_cam.far = 7000.0
	_cam.near = 0.5
	world.add_child(_cam)
	_cam.make_current()
	_ribbon = SunRibbon.new()
	world.add_child(_ribbon)
	_build_site_markers()
	_cache_window()
	_build_ui()
	Game.orientation_changed.connect(_layout)
	_layout(Game.portrait)
	_orbit_yaw = _yaw_toward_sun()
	_apply_time(true)
	_cam.fov = _fov_target
	_aim = _aim_target
	Sfx.music("mission")


func _exit_tree() -> void:
	for n in [_cam, _ribbon, _ring, _ghost]:
		if is_instance_valid(n):
			n.queue_free()


# ---------------------------------------------------------------- 3D

func _build_site_markers() -> void:
	var g := world.ground_y(Vector2.ZERO)
	_ring = MeshInstance3D.new()
	var torus := TorusMesh.new()
	torus.inner_radius = 11.4
	torus.outer_radius = 12.0
	_ring.mesh = torus
	var rm := StandardMaterial3D.new()
	rm.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	rm.albedo_color = Game.CYAN
	rm.emission_enabled = true
	rm.emission = Game.CYAN
	rm.emission_energy_multiplier = 2.0
	_ring.material_override = rm
	_ring.position = Vector3(0, g + 0.3, 0)
	world.add_child(_ring)
	_ghost = Models.scene("lander").instantiate()
	var gm := StandardMaterial3D.new()
	gm.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	gm.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	gm.albedo_color = Color(Game.CYAN, 0.25)
	for mi in _ghost.find_children("*", "MeshInstance3D", true, false):
		(mi as MeshInstance3D).material_override = gm
		(mi as MeshInstance3D).cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	_ghost.position = Vector3(0, g + 14, 0)
	world.add_child(_ghost)


func _cache_window() -> void:
	_window_dirs.clear()
	var w: Dictionary = mission.window
	var tt := int(w.start)
	while tt <= int(w.end):
		_window_dirs.append([tt, world.sun_dir(tt)])
		tt += int(w.step)


func _yaw_toward_sun() -> float:
	var d := world.sun_dir(t)
	return atan2(-d.x, -d.z)		# camera sits opposite the Sun, looking at it over the site


func _process(delta: float) -> void:
	if _ghost:
		_ghost.rotate_y(delta * 0.3)
		_ghost.position.y += sin(Time.get_ticks_msec() * 0.002) * delta * 0.3
	var eye := Vector3(0, world.ground_y(Vector2.ZERO) + 2.0, 0)
	_ring.visible = not _scope		# from inside the ring it would fill the bottom of the scope view
	_ghost.visible = not _scope
	if _scope:
		if _drag != "sun":
			_aim = _aim.slerp(_aim_target, minf(1.0, delta * 4.0)).normalized()
			_cam.fov = lerpf(_cam.fov, _fov_target, minf(1.0, delta * 4.0))
		_cam.global_position = eye
		_cam.look_at(eye + _aim, Vector3.UP if absf(_aim.y) < 0.98 else Vector3.FORWARD)
	else:
		_cam.fov = lerpf(_cam.fov, 60.0, minf(1.0, delta * 4.0))
		var dir := Vector3(sin(_orbit_yaw) * cos(_orbit_pitch), -sin(_orbit_pitch), cos(_orbit_yaw) * cos(_orbit_pitch))
		_cam.global_position = eye + dir * _orbit_dist
		_cam.look_at(eye + Vector3.UP * 4.0)


func _scope_aim() -> void:
	# aim between the Sun's path over the block and the skyline under it; widen until both fit
	var need := int(mission.need_s)
	var mid := t + need / 2
	var az := Mission.sample(world.site, "sun_az", mid)
	var el := Mission.sample(world.site, "sun_el", mid)
	var sky := Mission.skyline(world.site, az)
	var lo := minf(sky, minf(Mission.sample(world.site, "sun_el", t), el)) - 1.0
	var hi := maxf(sky, maxf(Mission.sample(world.site, "sun_el", t + need), el)) + 1.5
	var aim_el := clampf((lo + hi) * 0.5, -10.0, 80.0)
	_aim_target = SiteWorld.sky_dir(az, aim_el)
	if Game.portrait:
		# tall screen, horizontal FOV fixed: the view is ~1.8x taller than wide, and the plan panel covers the
		# lower ~45%, so frame the content in the upper half
		var vp := get_viewport().get_visible_rect().size
		var tall := vp.y / maxf(1.0, vp.x)
		_fov_target = clampf((hi - lo) * 1.35, 5.0, 60.0)		# horizontal (KEEP_WIDTH)
		var fov_v := _fov_target * tall
		_aim_target = SiteWorld.sky_dir(az, clampf(hi - fov_v * 0.42, -20.0, 85.0))	# top of content ~8% from the top
	else:
		_fov_target = clampf((hi - lo) * 1.5, 7.0, 75.0)
		# the plan panel covers the lower part of the screen: aim lower so the Sun and ridge sit in the upper half
		_aim_target = SiteWorld.sky_dir(az, clampf(aim_el - _fov_target * 0.22, -20.0, 85.0))


func _apply_time(rebuild := true) -> void:
	world.set_time(t)
	if rebuild:
		_ribbon.build(world, t, int(mission.need_s))
	_scope_aim()
	_update_readouts()


# ---------------------------------------------------------------- input: drag the Sun / orbit

func _sun_screen() -> Vector2:
	var p := world.sun_disc.global_position
	if _cam.is_position_behind(p):
		return Vector2.INF
	return _cam.unproject_position(p)


func _unhandled_input(event: InputEvent) -> void:
	if host.paused:
		return
	if event is InputEventMouse and event.device == InputEvent.DEVICE_ID_EMULATION:
		return
	var press := false
	var release := false
	var pos := Vector2.ZERO
	if event is InputEventMouseButton and event.button_index == MOUSE_BUTTON_LEFT:
		press = event.pressed
		release = not event.pressed
		pos = event.position
	elif event is InputEventScreenTouch and event.index == 0:
		press = event.pressed
		release = not event.pressed
		pos = event.position
	elif event is InputEventMouseButton and event.pressed and not _scope:
		if event.button_index == MOUSE_BUTTON_WHEEL_UP:
			_orbit_dist = maxf(18.0, _orbit_dist * 0.9)
		elif event.button_index == MOUSE_BUTTON_WHEEL_DOWN:
			_orbit_dist = minf(160.0, _orbit_dist * 1.1)
		return
	if press:
		var s := _sun_screen()
		var near_sun := s != Vector2.INF and s.distance_to(pos) < 90.0
		_drag = "sun" if (_scope or near_sun) and not mission.fixed_touchdown else ("orbit" if not _scope else "")
		if _drag == "sun":
			Sfx.play("click", 1.3)
		_drag_to(pos)
	elif release:
		if _drag == "sun":
			_apply_time(true)
		_drag = ""
	elif (event is InputEventMouseMotion or event is InputEventScreenDrag) and _drag != "":
		if _drag == "orbit":
			_orbit_yaw -= event.relative.x * 0.006
			_orbit_pitch = clampf(_orbit_pitch - event.relative.y * 0.004, deg_to_rad(-70), deg_to_rad(-3))
		else:
			_drag_to(event.position)


## Pick the time in the window whose Sun lands closest to the pointer.
func _drag_to(pos: Vector2) -> void:
	if _drag != "sun":
		return
	var best := t
	var best_d := INF
	for td: Array in _window_dirs:
		var p: Vector3 = _cam.global_position + td[1] * 1000.0
		if _cam.is_position_behind(p):
			continue
		var d := _cam.unproject_position(p).distance_squared_to(pos)
		if d < best_d:
			best_d = d
			best = td[0]
	if best != t:
		_set_t(best, false)


func _set_t(v: int, rebuild_ribbon := true) -> void:
	var w: Dictionary = mission.window
	v = clampi(v, int(w.start), int(w.end))
	if v == t:
		return
	t = v
	_dial.set_value(t)
	world.set_time(t)
	_ribbon.build(world, t, int(mission.need_s))
	if _drag != "sun":
		_scope_aim()
	_update_readouts()
	if not rebuild_ribbon:
		Sfx.play("tick", 1.4, -10.0)


# ---------------------------------------------------------------- UI

func _build_ui() -> void:
	var layer := CanvasLayer.new()
	add_child(layer)
	_ui = UIKit.full_rect(Control.new())
	_ui.mouse_filter = Control.MOUSE_FILTER_IGNORE
	layer.add_child(_ui)
	var m := UIKit.full_rect(UIKit.margin(16))
	m.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_ui.add_child(m)
	var col := UIKit.vbox(10)
	col.mouse_filter = Control.MOUSE_FILTER_IGNORE
	m.add_child(col)

	var top := UIKit.hbox(10)
	top.mouse_filter = Control.MOUSE_FILTER_IGNORE
	col.add_child(top)
	var info := UIKit.panel("hud")
	top.add_child(info)
	var iv := UIKit.vbox(2)
	info.add_child(iv)
	iv.add_child(UIKit.label("MISSION %d · PLAN" % mission.number, 13, Game.MAGENTA))
	iv.add_child(UIKit.display(str(mission.title).to_upper(), 24, Game.SUN))
	iv.add_child(UIKit.label("Hold %d h of sunlight · %s" % [int(mission.need_s / 3600), Texts.site_info(world.site).title],
		15, Game.INK))
	iv.add_child(UIKit.label("Bonus: " + str(mission.bonus.text), 14, Game.CYAN))
	top.add_child(UIKit.spacer(false))
	top.add_child(UIKit.button("II", host.toggle_pause, 18))

	if mission.sites.size() > 1:		# "Two Sites, One Clock": choose where to land
		var pick := UIKit.hbox(8)
		pick.alignment = BoxContainer.ALIGNMENT_CENTER
		col.add_child(pick)
		pick.add_child(UIKit.label("LAND AT", 15, Game.MUTED))
		for sid: String in mission.sites:
			var b := UIKit.button(Texts.site_info(sid).title.to_upper(), func() -> void: site_switch.emit(sid), 16,
				"primary" if sid == world.site else "")
			pick.add_child(b)

	col.add_child(UIKit.spacer())

	_bottom = BoxContainer.new()
	_bottom.add_theme_constant_override("separation", 12)
	_bottom.mouse_filter = Control.MOUSE_FILTER_IGNORE
	col.add_child(_bottom)
	_clock = SunlightClock.new()
	_clock.need_s = int(mission.need_s)
	_clock.size_flags_vertical = Control.SIZE_SHRINK_END
	_bottom.add_child(_clock)

	var panel := UIKit.panel("card")
	panel.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_bottom.add_child(panel)
	var pv := UIKit.vbox(8)
	panel.add_child(pv)
	_row = BoxContainer.new()		# time + Sun status: side by side, stacked on phones
	_row.add_theme_constant_override("separation", 4)
	var row := _row
	pv.add_child(row)
	_time_label = UIKit.display("", 26, Game.INK)
	_time_label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	row.add_child(_time_label)
	_status = UIKit.label("", 15, Game.MUTED)
	row.add_child(_status)
	_dial = TimeDial.new()
	_dial.start = int(mission.window.start)
	_dial.end = int(mission.window.end)
	_dial.step = int(mission.window.step)
	_dial.value = t
	_dial.locked = mission.fixed_touchdown
	_dial.changed.connect(func(v: int) -> void: _set_t(v))
	pv.add_child(_dial)
	var btns := HFlowContainer.new()
	btns.add_theme_constant_override("h_separation", 8)
	btns.add_theme_constant_override("v_separation", 8)
	pv.add_child(btns)
	if not mission.fixed_touchdown:
		for spec in [["−1H", -3600], ["−10M", -600], ["+10M", 600], ["+1H", 3600]]:
			btns.add_child(UIKit.button(spec[0], func() -> void: _set_t(t + int(spec[1])), 16))
		_forecast_btn = UIKit.button("FORECAST −%d" % FORECAST_COST, _buy_forecast, 15)
		btns.add_child(_forecast_btn)
	_view_btn = UIKit.button("SITE VIEW", _toggle_view, 15)
	btns.add_child(_view_btn)
	var commit := UIKit.button("COMMIT LANDING  ▶", _commit, 22, "primary")
	commit.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	pv.add_child(commit)
	UIKit.pop_in(panel, 0.1)
	UIKit.pop_in(info, 0.0)


func _layout(portrait: bool) -> void:
	_bottom.vertical = portrait
	_row.vertical = portrait
	_cam.keep_aspect = Camera3D.KEEP_WIDTH if portrait else Camera3D.KEEP_HEIGHT
	if _dial:
		_scope_aim()
	_clock.custom_minimum_size = Vector2(130, 130) if portrait else Vector2(170, 170)
	_clock.size_flags_horizontal = Control.SIZE_SHRINK_CENTER if portrait else Control.SIZE_FILL


func _update_readouts() -> void:
	var d := Time.get_datetime_dict_from_unix_time(t)
	_time_label.text = "%s %d  %02d:%02d UTC" % [["", "JAN", "FEB", "MAR", "APR"][mini(d.month, 4)], d.day, d.hour, d.minute]
	var iv: Array = Mission.sites[world.site].intervals.sun_full
	var nc := Scoring.next_change(iv, t)
	if nc.inside:
		_clock.clear_s = int(nc.change) - t
		_clock.open_end = int(nc.change) >= int(Mission.data.window.end_unix)
	else:
		_clock.clear_s = 0
		_clock.wait_s = int(nc.change) - t if nc.change >= 0 else -1
	var margin := world.sun_margin(t)
	var earth := "  ·  EARTH UP" if world.earth_up(t) else ""
	_status.text = ("SUN %+.2f° ABOVE RIDGE" % margin if margin >= 0 else "SUN %.2f° BELOW RIDGE" % margin) + earth
	_status.add_theme_color_override("font_color", Game.LIME if margin >= 0 else Game.CORAL)


func _buy_forecast() -> void:
	if _forecast:
		return
	_forecast = true
	Sfx.play("scan")
	var spans := []
	var w: Dictionary = mission.window
	var a := -1
	var tt := int(w.start)
	while tt <= int(w.end) + int(w.step):
		var ok: bool = tt <= int(w.end) and Game.evaluate(world.site, tt, int(mission.need_s)).pass
		if ok and a < 0:
			a = tt
		elif not ok and a >= 0:
			spans.append([a, tt - int(w.step)])
			a = -1
		tt += int(w.step)
	_dial.forecast = spans
	_forecast_btn.disabled = true
	_forecast_btn.text = "FORECAST ON"


func _toggle_view() -> void:
	_scope = not _scope
	_view_btn.text = "SITE VIEW" if _scope else "SUN SCOPE"
	if not _scope:
		_orbit_yaw = _yaw_toward_sun()


func _commit() -> void:
	Sfx.play("confirm")
	committed.emit(t, _forecast)
