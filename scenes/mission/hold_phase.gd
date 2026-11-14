extends Node
## HOLD THE LIGHT: the sampling block plays as a time-lapse with the real Sun. While the rover drills, sample
## canisters pop out: carry them (2 at a time) to the lander. Scan the glowing rocks for bonus points.
## If the plan fails, the Sun really does slip behind the terrain at the data's interruption time: an alarm gives
## a last 30 seconds to deliver what you carry. Whatever happens, the outcome comes from Scoring.

signal finished(stats: Dictionary)

const Astronaut := preload("res://scenes/mission/astronaut.gd")
const HOLD_SECONDS := 75.0			# real seconds for the whole block
const CANISTERS := 6
const SCAN_TARGETS := 4
const CARRY_MAX := 2
const WARN_SECONDS := 30.0

var host: Node
var world: SiteWorld
var mission: Dictionary
var touchdown := 0
var lander_pos := Vector3.ZERO
var result := {}

var _player: Astronaut
var _t := 0.0
var _end := 0
var _speed := 1.0
var _running := false
var _warned := false
var _spawned := 0
var _canisters: Array[Node3D] = []
var _carried := 0
var _delivered := 0
var _scans: Array[Node3D] = []
var _scanned := 0
var _scan_busy := false

var _ui: Control
var _bar: ProgressBar
var _clock_label: Label
var _sun_pill: Label
var _carry_label: Label
var _prompt: Label
var _alarm: Label
var _scan_btn: Button


func setup(p_host: Node, p_world: SiteWorld, p_mission: Dictionary, p_touchdown: int, p_lander_pos: Vector3) -> void:
	host = p_host
	world = p_world
	mission = p_mission
	touchdown = p_touchdown
	lander_pos = p_lander_pos


func _ready() -> void:
	result = Game.evaluate(world.site, touchdown, int(mission.need_s))
	_end = int(result.sampling_end) if result.pass else int(result.interruption)
	_speed = float(mission.need_s) / HOLD_SECONDS
	_t = touchdown
	world.set_time(_t)
	world.spawn_props(Vector2(lander_pos.x, lander_pos.z) + Vector2(4, 10))
	_player = Astronaut.new()
	world.add_child(_player)
	_player.position = lander_pos + Vector3(-4, 1.5, 6)
	var sd := world.sun_dir(_t)
	_player.face(atan2(-sd.x, -sd.z))		# start looking at the Sun
	_player.camera.make_current()
	_build_scan_targets()
	_build_ui()
	_drive_rover()
	if world.rover_anim and world.rover_anim.has_animation("sample_drill_cycle"):
		world.rover_anim.get_animation("sample_drill_cycle").loop_mode = Animation.LOOP_LINEAR
	host.banner("HOLD THE LIGHT", Game.SUN)
	await get_tree().create_timer(1.2).timeout
	if result.sampled_s == 0:
		_alarm.text = "NO FULL SUNLIGHT AT TOUCHDOWN"
		_alarm.visible = true
		Sfx.play("fail")
		await get_tree().create_timer(3.0).timeout
		_finish()
		return
	_running = true
	if world.rover_anim and world.rover_anim.has_animation("sample_drill_cycle"):
		world.rover_anim.play("sample_drill_cycle")


func _exit_tree() -> void:
	if is_instance_valid(_player):
		_player.queue_free()


# ---------------------------------------------------------------- objects

func _glow_mat(c: Color, energy := 2.5) -> StandardMaterial3D:
	var m := StandardMaterial3D.new()
	m.albedo_color = c
	m.emission_enabled = true
	m.emission = c
	m.emission_energy_multiplier = energy
	return m


func _build_scan_targets() -> void:
	var rng := RandomNumberGenerator.new()
	rng.seed = hash(mission.id)
	for i in SCAN_TARGETS:
		var a := rng.randf() * TAU
		var r := rng.randf_range(14.0, 34.0)
		var xz := Vector2(lander_pos.x, lander_pos.z) + Vector2(cos(a), sin(a)) * r
		var rock := MeshInstance3D.new()
		rock.mesh = world.rock_mesh(i + 3)
		rock.material_override = _glow_mat(Game.MAGENTA, 1.6)
		world.put(rock, xz, rng.randf() * TAU, 0.7)
		var light := OmniLight3D.new()
		light.light_color = Game.MAGENTA
		light.light_energy = 1.5
		light.omni_range = 4.0
		light.position.y = 0.8
		rock.add_child(light)
		_scans.append(rock)


## The rover rolls off from beside the lander to its drilling spot, throwing wheel dust (illustrative).
func _drive_rover() -> void:
	var rover := world.rover
	if rover == null:
		return
	var goal := rover.position
	var start := lander_pos + (goal - lander_pos).normalized() * 4.0
	var dir := Vector3(goal.x - start.x, 0, goal.z - start.z).normalized()
	rover.rotation.y = atan2(dir.x, dir.z)		# model front is +Z
	var dusts: Array[CPUParticles3D] = []
	for side in [-0.75, 0.75]:					# rear wheels, kicked back and up
		var d := SiteWorld.dust(18, 0.5, 0.8, 1.8, 1.4, "res://assets/vfx/wheel_dust_4x4.png")
		d.direction = Vector3(0, 0.6, -1)
		d.spread = 35.0
		d.position = Vector3(side, 0.15, -0.9)
		rover.add_child(d)
		d.emitting = true
		dusts.append(d)
	var dur := 5.0
	var step := func(f: float) -> void:
		var p := start.lerp(goal, f)
		p.y = world.ground_y(Vector2(p.x, p.z))
		rover.position = p
		rover.rotation.z = sin(f * 40.0) * 0.015		# a little suspension jiggle
	var tw := create_tween()
	tw.tween_method(step, 0.0, 1.0, dur).set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
	tw.tween_callback(func() -> void:
		rover.rotation.z = 0.0
		for d in dusts:
			d.emitting = false)


func _spawn_canister() -> void:
	var c := MeshInstance3D.new()
	var cyl := CylinderMesh.new()
	cyl.top_radius = 0.16
	cyl.bottom_radius = 0.16
	cyl.height = 0.5
	c.mesh = cyl
	c.material_override = _glow_mat(Game.CYAN, 3.0)
	var base: Vector3 = world.rover.global_position if world.rover else lander_pos
	var a := randf() * TAU
	world.add_child(c)
	c.global_position = base + Vector3(cos(a) * 2.2, 0.6, sin(a) * 2.2)
	c.global_position.y = world.ground_y(Vector2(c.global_position.x, c.global_position.z)) + 0.6
	_canisters.append(c)
	Sfx.play("pickup", 0.7)
	host.popup("SAMPLE READY", Game.CYAN)


# ---------------------------------------------------------------- loop

func _process(delta: float) -> void:
	if host.paused:
		return
	var ms := Time.get_ticks_msec() * 0.001
	for c in _canisters:
		c.rotation.y += delta * 2.0
		c.position.y += sin(ms * 3.0 + c.position.x) * delta * 0.15
	for r in _scans:
		if r.has_meta("done"):
			continue
		(r.material_override as StandardMaterial3D).emission_energy_multiplier = 1.2 + 0.8 * sin(ms * 4.0)
	if not _running:
		return
	_t = minf(_t + delta * _speed, float(_end))
	world.set_time(_t)
	var done := _t - touchdown
	# canisters at fixed fractions of the block (the last one leaves time to deliver)
	while _spawned < CANISTERS and done >= float(mission.need_s) * (_spawned + 1) / (CANISTERS + 1.0):
		_spawned += 1
		_spawn_canister()
	_pickups()
	_update_hud(done)
	if not result.pass and not _warned and (_end - _t) / _speed <= WARN_SECONDS:
		_warned = true
		_alarm.text = "SHADOW INCOMING — DELIVER YOUR SAMPLES!"
		_alarm.visible = true
		UIKit.pulse(_alarm, 0.3, 0.5)
		Sfx.play("alarm")
	if _t >= _end:
		_running = false
		if world.rover_anim:
			world.rover_anim.stop()
		if result.pass:
			Sfx.play("win")
			host.banner("SAMPLING COMPLETE", Game.LIME)
		else:
			Sfx.play("fail")
			host.banner("SUNLIGHT LOST", Game.CORAL)
		await get_tree().create_timer(2.2).timeout
		_finish()


func _pickups() -> void:
	var p := _player.global_position
	for c in _canisters.duplicate():
		if _carried < CARRY_MAX and p.distance_to(c.global_position) < 1.8:
			_canisters.erase(c)
			c.queue_free()
			_carried += 1
			Sfx.play("pickup")
			host.popup("GOT IT  (%d/%d)" % [_carried, CARRY_MAX], Game.CYAN)
	if _carried > 0 and Vector2(p.x - lander_pos.x, p.z - lander_pos.z).length() < 5.0:
		for i in _carried:
			_delivered += 1
			host.add_score("samples", 300)
			host.popup("+300 SAMPLE DELIVERED", Game.LIME)
		_carried = 0
		Sfx.play("deliver")
	var target := _scan_target()
	_prompt.visible = target != null and not _scan_busy
	_scan_btn.disabled = target == null or _scan_busy


func _scan_target() -> Node3D:
	var p := _player.global_position
	var f: Vector3 = _player.look_dir()
	for r in _scans:
		if r.has_meta("done"):
			continue
		var d := r.global_position - p
		d.y = 0
		if d.length() < 8.0 and f.dot(d.normalized()) > 0.55:
			return r
	return null


func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("scan"):
		_scan()


func _scan() -> void:
	var r := _scan_target()
	if r == null or _scan_busy or host.paused:
		return
	_scan_busy = true
	_player.scanning = true
	Sfx.play("scan")
	var beam := MeshInstance3D.new()
	var cyl := CylinderMesh.new()
	cyl.top_radius = 0.03
	cyl.bottom_radius = 0.12
	var from := _player.global_position + Vector3.UP * 1.3
	var to := r.global_position + Vector3.UP * 0.4
	cyl.height = from.distance_to(to)
	beam.mesh = cyl
	beam.material_override = _glow_mat(Game.CYAN, 4.0)
	world.add_child(beam)
	beam.global_position = (from + to) * 0.5
	beam.look_at(to, Vector3.UP)
	beam.rotate_object_local(Vector3.RIGHT, PI / 2)
	await get_tree().create_timer(0.9).timeout
	beam.queue_free()
	r.set_meta("done", true)
	(r.material_override as StandardMaterial3D).emission = Game.LIME
	(r.material_override as StandardMaterial3D).emission_energy_multiplier = 0.4
	for l in r.get_children():
		l.queue_free()
	_scanned += 1
	host.add_score("scans", 150)
	host.popup("+150 SCAN", Game.MAGENTA)
	_player.scanning = false
	_scan_busy = false


func _finish() -> void:
	finished.emit({"delivered": _delivered, "scanned": _scanned, "spawned": _spawned, "carried_lost": _carried})


# ---------------------------------------------------------------- HUD

func _build_ui() -> void:
	var layer := CanvasLayer.new()
	layer.layer = 2
	add_child(layer)
	_ui = UIKit.full_rect(Control.new())
	_ui.mouse_filter = Control.MOUSE_FILTER_IGNORE
	layer.add_child(_ui)
	var m := UIKit.full_rect(UIKit.margin(16))
	m.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_ui.add_child(m)
	var col := UIKit.vbox(8)
	col.mouse_filter = Control.MOUSE_FILTER_IGNORE
	m.add_child(col)

	var top := UIKit.hbox(10)
	top.mouse_filter = Control.MOUSE_FILTER_IGNORE
	col.add_child(top)
	var hud := UIKit.panel("hud")
	hud.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	top.add_child(hud)
	var hv := UIKit.vbox(4)
	hud.add_child(hv)
	var hr := UIKit.hbox(10)
	hv.add_child(hr)
	hr.add_child(UIKit.label("SAMPLING", 14, Game.MAGENTA))
	_clock_label = UIKit.label("", 16, Game.INK)
	_clock_label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	hr.add_child(_clock_label)
	_sun_pill = UIKit.label("", 16, Game.LIME)
	hr.add_child(_sun_pill)
	_bar = ProgressBar.new()
	_bar.max_value = float(mission.need_s)
	_bar.show_percentage = false
	_bar.custom_minimum_size.y = 14
	hv.add_child(_bar)
	_carry_label = UIKit.label("", 15, Game.CYAN)
	hv.add_child(_carry_label)
	top.add_child(UIKit.button("II", host.toggle_pause, 18))

	_alarm = UIKit.display("", 28, Game.CORAL)
	_alarm.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_alarm.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_alarm.visible = false
	col.add_child(_alarm)
	col.add_child(UIKit.spacer())
	_prompt = UIKit.label("PRESS E / TAP SCAN", 18, Game.MAGENTA)
	_prompt.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_prompt.visible = false
	col.add_child(_prompt)
	var bottom := UIKit.hbox(10)
	bottom.alignment = BoxContainer.ALIGNMENT_END
	col.add_child(bottom)
	var touch := DisplayServer.is_touchscreen_available()
	var hint := UIKit.label("LEFT THUMB: MOVE (PUSH FULLY: LOPE) · DRAG: LOOK" if touch else "MOVE: WASD (SHIFT: LOPE) · LOOK: DRAG · HOP: SPACE",
		13, Game.MUTED, true)
	hint.size_flags_horizontal = Control.SIZE_EXPAND_FILL		# takes the free width; wraps only on narrow screens
	hint.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	bottom.add_child(hint)
	if touch:
		bottom.add_child(UIKit.button("HOP", func() -> void:
			Input.action_press("hop")
			await get_tree().process_frame
			await get_tree().physics_frame
			Input.action_release("hop"), 16))
	bottom.add_child(UIKit.button("VIEW", func() -> void: _player.set_view(not _player.first_person), 16))
	_scan_btn = UIKit.button("SCAN", _scan, 20, "primary")
	_scan_btn.disabled = true
	bottom.add_child(_scan_btn)


func _update_hud(done: float) -> void:
	_bar.value = done
	_clock_label.text = "%s / %d H   ·   %s" % [Scoring.duration_label(int(done)), int(mission.need_s / 3600),
		Mission.utc_label(_t)]
	var frac := world.sun_fraction(_t)
	var full := Scoring.find(Mission.sites[world.site].intervals.sun_full, int(_t)) >= 0
	_sun_pill.text = "SUN CLEAR" if full else ("SUN FADING" if frac > 0.0 else "DARK")
	_sun_pill.add_theme_color_override("font_color", Game.LIME if full else Game.CORAL)
	_carry_label.text = "CARRYING %d/%d   ·   DELIVERED %d   ·   SCANS %d/%d" % [_carried, CARRY_MAX, _delivered,
		_scanned, SCAN_TARGETS]
