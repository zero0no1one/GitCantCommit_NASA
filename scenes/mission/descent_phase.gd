extends Node
## DESCENT: an arcade lunar-lander run, side-on, into the landing ring.
## Thrust (Space / W / ↑, or hold the right side on touch) fights lunar gravity; steer with A/D (←/→, or the left
## side). Touch down slower than 2.2 m/s vertically and 1.6 m/s sideways. Time of day is frozen at the committed
## touchdown, and the ring is far too small to change the skyline, so the plan's result holds wherever you land.

signal landed(result: Dictionary)

const G := 1.62
const THRUST := 3.4
const STEER := 1.8
const FUEL_BURN := 6.5
const STEER_BURN := 2.5
const RING_R := 12.0
const SAFE_VY := 2.2
const SAFE_VX := 1.6
const START := Vector2(-75, 70)		# x offset from the target, height above the target ground

var host: Node
var world: SiteWorld
var lander: Node3D

var _cam: Camera3D
var _pos := Vector2.ZERO			# (x, y) in world metres along the approach line (z = 0)
var _vel := Vector2.ZERO
var _fuel := 100.0
var _active := false
var _thrusting := false
var _touch_thrust := false
var _touch_steer := 0.0
var _flame: MeshInstance3D
var _flame_light: OmniLight3D
var _dust: CPUParticles3D
var _shake := 0.0
var _attempts := 0
var _ground0 := 0.0

var _ui: Control
var _alt: Label
var _vs: Label
var _hs: Label
var _fuel_bar: ProgressBar
var _target: Label
var _banner: Label
var _retry: Button


func setup(p_host: Node, p_world: SiteWorld) -> void:
	host = p_host
	world = p_world


func _ready() -> void:
	_ground0 = world.ground_y(Vector2.ZERO)
	_cam = Camera3D.new()
	_cam.fov = 50.0
	_cam.keep_aspect = Camera3D.KEEP_WIDTH if Game.portrait else Camera3D.KEEP_HEIGHT	# phones: keep the approach in frame
	_cam.far = 7000.0
	world.add_child(_cam)
	_cam.make_current()
	lander = Models.scene("lander").instantiate()
	world.add_child(lander)
	_build_effects()
	_build_ui()
	_reset()


func _exit_tree() -> void:
	if is_instance_valid(_cam):
		_cam.queue_free()
	for n in [_flame, _flame_light, _dust]:		# the lander stays in the world for the next phase; its engine doesn't
		if is_instance_valid(n):
			n.queue_free()
	Sfx.loop("thrust", false)


func _glow(c: Color, e: float) -> StandardMaterial3D:
	var m := StandardMaterial3D.new()
	m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	m.albedo_color = c
	m.emission_enabled = true
	m.emission = c
	m.emission_energy_multiplier = e
	return m


func _build_effects() -> void:
	# target ring + a tall beacon beam you can steer toward from anywhere
	var ring := MeshInstance3D.new()
	var torus := TorusMesh.new()
	torus.inner_radius = RING_R - 0.6
	torus.outer_radius = RING_R
	ring.mesh = torus
	ring.material_override = _glow(Game.CYAN, 2.0)
	ring.position = Vector3(0, _ground0 + 0.3, 0)
	add_child(ring)
	var beam := MeshInstance3D.new()
	var cyl := CylinderMesh.new()
	cyl.top_radius = 0.25
	cyl.bottom_radius = 0.6
	cyl.height = 90.0
	beam.mesh = cyl
	var bm := _glow(Color(Game.CYAN, 0.35), 1.5)
	bm.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	bm.blend_mode = BaseMaterial3D.BLEND_MODE_ADD
	beam.material_override = bm
	beam.position = Vector3(0, _ground0 + 45.0, 0)
	beam.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(beam)
	var fill := DirectionalLight3D.new()		# artistic fill from the camera side so the lander reads at dawn
	fill.light_energy = 0.35
	fill.light_color = Color(0.7, 0.8, 1.0)
	fill.rotation = Vector3(deg_to_rad(-25), 0, 0)
	add_child(fill)
	_flame = MeshInstance3D.new()
	var cone := CylinderMesh.new()
	cone.top_radius = 0.9
	cone.bottom_radius = 0.0
	cone.height = 3.0
	_flame.mesh = cone
	var fm := StandardMaterial3D.new()
	fm.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	fm.albedo_color = Color(0.6, 0.95, 1, 0.8)
	fm.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	fm.blend_mode = BaseMaterial3D.BLEND_MODE_ADD
	fm.emission_enabled = true
	fm.emission = Game.CYAN
	fm.emission_energy_multiplier = 3.0
	_flame.material_override = fm
	_flame.position = Vector3(0, -0.2, 0)
	_flame.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	lander.add_child(_flame)
	_flame_light = OmniLight3D.new()
	_flame_light.light_color = Game.CYAN
	_flame_light.omni_range = 18.0
	_flame_light.position = Vector3(0, -1.0, 0)
	lander.add_child(_flame_light)
	_dust = CPUParticles3D.new()
	_dust.emitting = false
	_dust.amount = 60
	_dust.lifetime = 2.2
	_dust.one_shot = false
	_dust.explosiveness = 0.0
	_dust.direction = Vector3(0, 0.25, 0)
	_dust.spread = 85.0
	_dust.initial_velocity_min = 6.0
	_dust.initial_velocity_max = 14.0
	_dust.gravity = Vector3(0, -G, 0)		# vacuum: ballistic arcs, no billowing
	_dust.scale_amount_min = 0.6
	_dust.scale_amount_max = 1.6
	var quad := QuadMesh.new()
	quad.size = Vector2(1.2, 1.2)
	var dm := StandardMaterial3D.new()
	dm.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	dm.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	dm.billboard_mode = BaseMaterial3D.BILLBOARD_PARTICLES
	dm.albedo_texture = load("res://assets/vfx/touchdown_spray_4x4.png")
	dm.particles_anim_h_frames = 4
	dm.particles_anim_v_frames = 4
	dm.vertex_color_use_as_albedo = true
	quad.material = dm
	_dust.mesh = quad
	_dust.anim_speed_min = 1.0
	_dust.anim_speed_max = 1.0
	_dust.color = Color(0.75, 0.72, 0.68, 0.8)
	world.add_child(_dust)


func _reset() -> void:
	_attempts += 1
	_pos = Vector2(START.x, _ground0 + START.y)
	_vel = Vector2(4.2, -2.4)
	_fuel = 130.0
	_active = true
	lander.rotation = Vector3.ZERO
	lander.visible = true
	_banner.text = "BRING HER DOWN IN THE RING" if _attempts == 1 else "ATTEMPT %d" % _attempts
	_banner.add_theme_color_override("font_color", Game.CYAN)
	_retry.visible = false
	_place()


func _place() -> void:
	lander.global_position = Vector3(_pos.x, _pos.y, 0)


func _physics_process(delta: float) -> void:
	_shake = maxf(0.0, _shake - delta * 2.0)
	if not _active or host.paused:
		_thrusting = false
		_update_flame(delta)
		return
	var thrust := (Input.is_action_pressed("thrust") or _touch_thrust) and _fuel > 0.0
	var steer := Input.get_axis("steer_left", "steer_right") + _touch_steer
	steer = clampf(steer, -1.0, 1.0) if _fuel > 0.0 else 0.0
	_thrusting = thrust
	var acc := Vector2(steer * STEER, -G + (THRUST if thrust else 0.0))
	_vel += acc * delta
	_pos += _vel * delta
	_fuel = maxf(0.0, _fuel - (FUEL_BURN if thrust else 0.0) * delta - absf(steer) * STEER_BURN * delta)
	lander.rotation.z = lerpf(lander.rotation.z, -steer * 0.18, minf(1.0, delta * 4.0))
	var gy := world.ground_y(Vector2(_pos.x, 0))
	if _pos.y <= gy:
		_pos.y = gy
		_touchdown(gy)
	elif absf(_pos.x) > 220.0 or _pos.y > _ground0 + 220.0:
		_crash("LOST CONTROL")
	_place()
	_update_flame(delta)
	_dust.global_position = Vector3(_pos.x, gy, 0)
	_dust.emitting = thrust and _pos.y - gy < 14.0
	Sfx.loop("thrust", thrust, -6.0)
	# HUD
	var dx := -_pos.x
	_alt.text = "ALT %5.1f m" % (_pos.y - gy)
	_vs.text = "V/S %+5.1f" % _vel.y
	_vs.add_theme_color_override("font_color", Game.LIME if _vel.y > -SAFE_VY else Game.CORAL)
	_hs.text = "H/S %+5.1f" % _vel.x
	_hs.add_theme_color_override("font_color", Game.LIME if absf(_vel.x) < SAFE_VX else Game.CORAL)
	_fuel_bar.value = _fuel
	_target.text = ("TARGET  %s %.0f m" % ["▶" if dx > 0 else "◀", absf(dx)]) if absf(dx) > RING_R else "OVER THE RING"
	_target.add_theme_color_override("font_color", Game.LIME if absf(dx) <= RING_R else Game.SUN)


func _update_flame(delta: float) -> void:
	var on := _thrusting and _active
	var s := lerpf(_flame.scale.y, 1.0 + randf() * 0.25 if on else 0.0, minf(1.0, delta * 12.0))
	_flame.scale = Vector3(1, maxf(0.001, s), 1)
	_flame.visible = s > 0.02
	_flame_light.light_energy = 3.0 * s


func _process(_delta: float) -> void:
	# side-on camera that keeps both the lander and the ring in frame, closing in as you get near
	var mid := Vector3(_pos.x * 0.5, (_pos.y + _ground0) * 0.5 + 2.0, 0)
	var sep := Vector2(_pos.x, _pos.y - _ground0).length()
	var dist := clampf(sep * 1.35, 28.0, 150.0)
	var desired := mid + Vector3(0, dist * 0.12, dist)
	_cam.global_position = _cam.global_position.lerp(desired, 0.08) if _cam.global_position != Vector3.ZERO else desired
	_cam.look_at(mid)
	if _shake > 0.0:
		_cam.global_position += Vector3(randf_range(-1, 1), randf_range(-1, 1), 0) * _shake * 0.6


func _touchdown(gy: float) -> void:
	var vy := -_vel.y
	var vx := absf(_vel.x)
	if vy > SAFE_VY or vx > SAFE_VX:
		_crash("TOO FAST  (%.1f m/s)" % maxf(vy, vx))
		return
	_active = false
	Sfx.loop("thrust", false)
	Sfx.play("touchdown")
	_shake = 1.0
	_burst()
	var a := SiteWorld.find_anim(lander)
	if a and a.has_animation("touchdown"):
		a.play("touchdown")
	var offset := absf(_pos.x)
	var precision := int(round(500.0 * clampf(1.0 - offset / RING_R, 0.0, 1.0)))
	var soft := int(round(300.0 * clampf(1.0 - vy / SAFE_VY, 0.0, 1.0)))
	_banner.text = "BULLSEYE!" if offset < 3.0 else ("TOUCHDOWN!" if offset <= RING_R else "DOWN, OFF TARGET")
	_banner.add_theme_color_override("font_color", Game.LIME if offset <= RING_R else Game.SUN)
	UIKit.pop_in(_banner)
	host.popup("+%d PRECISION" % precision, Game.CYAN)
	await get_tree().create_timer(0.5).timeout
	host.popup("+%d SOFT LANDING" % soft, Game.CYAN)
	await get_tree().create_timer(1.6).timeout
	landed.emit({"offset_m": offset, "vy": vy, "precision": precision, "soft": soft, "attempts": _attempts,
		"x": _pos.x, "ground": gy, "auto": false})


func _crash(why: String) -> void:
	_active = false
	Sfx.loop("thrust", false)
	Sfx.play("crash")
	_shake = 2.0
	_burst()
	lander.rotation.z = randf_range(-0.9, 0.9)
	_banner.text = "CRASHED — " + why
	_banner.add_theme_color_override("font_color", Game.CORAL)
	UIKit.pop_in(_banner)
	_retry.visible = true


func _burst() -> void:
	var b := _dust.duplicate() as CPUParticles3D
	world.add_child(b)
	b.global_position = Vector3(_pos.x, world.ground_y(Vector2(_pos.x, 0)), 0)
	b.one_shot = true
	b.explosiveness = 0.9
	b.amount = 80
	b.emitting = true
	get_tree().create_timer(4.0).timeout.connect(b.queue_free)


## Skip the minigame: land on target automatically, with no landing points.
func _auto_land() -> void:
	if not _active and not _retry.visible:
		return
	_active = false
	Sfx.loop("thrust", false)
	_pos = Vector2(0, world.ground_y(Vector2.ZERO))
	lander.rotation = Vector3.ZERO
	_place()
	Sfx.play("touchdown")
	_burst()
	landed.emit({"offset_m": 0.0, "vy": 0.0, "precision": 0, "soft": 0, "attempts": _attempts, "x": 0.0,
		"ground": _pos.y, "auto": true})


# ---------------------------------------------------------------- UI

func _build_ui() -> void:
	var layer := CanvasLayer.new()
	add_child(layer)
	_ui = UIKit.full_rect(Control.new())
	_ui.mouse_filter = Control.MOUSE_FILTER_IGNORE
	layer.add_child(_ui)

	# touch zones (only react to touches; mouse users have the keyboard)
	var left := _touch_zone(Vector2(0, 0.35), Vector2(0.45, 1.0))
	left.gui_input.connect(_on_steer_zone.bind(left))
	var right := _touch_zone(Vector2(0.55, 0.35), Vector2(1.0, 1.0))
	right.gui_input.connect(_on_thrust_zone.bind(right))
	if DisplayServer.is_touchscreen_available():
		var font := _ui.get_theme_default_font()
		left.draw.connect(func() -> void:
			left.draw_rect(Rect2(Vector2.ZERO, left.size), Color(Game.CYAN, 0.18), false, 2.0)
			left.draw_string(font, Vector2(0, left.size.y - 150), "◀  STEER  ▶", HORIZONTAL_ALIGNMENT_CENTER,
				left.size.x, 22, Color(Game.CYAN, 0.75)))
		right.draw.connect(func() -> void:
			right.draw_rect(Rect2(Vector2.ZERO, right.size), Color(Game.SUN, 0.25 if _touch_thrust else 0.05))
			right.draw_rect(Rect2(Vector2.ZERO, right.size), Color(Game.SUN, 0.4), false, 2.0)
			right.draw_string(font, Vector2(0, right.size.y - 150), "HOLD: THRUST", HORIZONTAL_ALIGNMENT_CENTER,
				right.size.x, 22, Color(Game.SUN, 0.85)))

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
	top.add_child(hud)
	var hv := UIKit.vbox(2)
	hud.add_child(hv)
	hv.add_child(UIKit.label("DESCENT", 13, Game.MAGENTA))
	_alt = UIKit.label("", 20, Game.INK)
	hv.add_child(_alt)
	_vs = UIKit.label("", 20, Game.INK)
	hv.add_child(_vs)
	_hs = UIKit.label("", 20, Game.INK)
	hv.add_child(_hs)
	var fr := UIKit.hbox(6)
	hv.add_child(fr)
	fr.add_child(UIKit.label("FUEL", 14, Game.MUTED))
	_fuel_bar = ProgressBar.new()
	_fuel_bar.show_percentage = false
	_fuel_bar.max_value = 130.0
	_fuel_bar.custom_minimum_size = Vector2(130, 12)
	_fuel_bar.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	fr.add_child(_fuel_bar)
	top.add_child(UIKit.spacer(false))
	var right_col := UIKit.vbox(8)
	top.add_child(right_col)
	right_col.add_child(UIKit.button("II", host.toggle_pause, 18))
	_target = UIKit.label("", 18, Game.SUN)
	col.add_child(_target)
	_target.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_banner = UIKit.display("", 34, Game.CYAN)
	_banner.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	col.add_child(_banner)
	col.add_child(UIKit.spacer())
	var bottom := UIKit.hbox(10)
	bottom.alignment = BoxContainer.ALIGNMENT_CENTER
	col.add_child(bottom)
	_retry = UIKit.button("RETRY DESCENT", _reset, 22, "primary")
	bottom.add_child(_retry)
	bottom.add_child(UIKit.button("AUTO-LAND (NO LANDING POINTS)", _auto_land, 14))
	var hint := UIKit.label("LEFT SIDE: STEER  ·  HOLD RIGHT SIDE: THRUST" if DisplayServer.is_touchscreen_available()
		else "THRUST: SPACE / W / ↑     STEER: A D / ← →", 14, Game.MUTED, true)
	hint.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	col.add_child(hint)


## Left zone: hold the left half to steer left, the right half to steer right. Accepts raw touches and the
## mouse events browsers emulate from them.
func _on_steer_zone(e: InputEvent, zone: Control) -> void:
	var down := -1		# -1 no change, 0 released, 1 pressed / dragged
	if e is InputEventScreenTouch or e is InputEventMouseButton:
		down = 1 if e.pressed else 0
	elif e is InputEventScreenDrag or (e is InputEventMouseMotion and e.button_mask & MOUSE_BUTTON_MASK_LEFT):
		down = 1
	if down < 0:
		return
	var x: float = e.position.x / zone.size.x
	_touch_steer = 0.0 if down == 0 else (-1.0 if x < 0.5 else 1.0)
	zone.queue_redraw()


func _on_thrust_zone(e: InputEvent, zone: Control) -> void:
	if e is InputEventScreenTouch or e is InputEventMouseButton:
		_touch_thrust = e.pressed
		zone.queue_redraw()


func _touch_zone(a: Vector2, b: Vector2) -> Control:
	var z := Control.new()
	z.anchor_left = a.x
	z.anchor_top = a.y
	z.anchor_right = b.x
	z.anchor_bottom = b.y
	z.mouse_filter = Control.MOUSE_FILTER_PASS if DisplayServer.is_touchscreen_available() else Control.MOUSE_FILTER_IGNORE
	_ui.add_child(z)
	return z
