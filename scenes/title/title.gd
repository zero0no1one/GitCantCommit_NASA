extends Node3D
## Title screen: the lander drifting over the Moon, the SUNLINE logo and the main menu.

const Starfield := preload("res://scenes/common/starfield.gd")

var _lander: Node3D
var _moon: Node3D
var _camera: Camera3D
var _t := 0.0
var _col: VBoxContainer
var _logo: Control
var _sound_btn: Button
var _astronaut: Node3D
var _rover: Node3D
var _astronaut_anim: AnimationPlayer
var _rover_anim: AnimationPlayer
var _surveying: bool = false


func _ready() -> void:
	_build_world()
	_build_ui()
	Game.orientation_changed.connect(func(_p: bool) -> void: _layout())
	_layout()
	Sfx.music("menu")


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
	env.glow_intensity = 1.0
	env.glow_hdr_threshold = 0.9
	var we := WorldEnvironment.new()
	we.environment = env
	add_child(we)

	_moon = Models.scene("moon_globe").instantiate()
	_moon.scale = Vector3.ONE * 2.6
	_moon.position = Vector3(0, -3.1, -0.6)
	_moon.rotation.x = 1.15		# keep the texture's pole pinch away from the visible limb
	add_child(_moon)
	var earth: Node3D = Models.team("earth").instantiate()		# teammate's Earth (unit radius)
	earth.scale = Vector3.ONE * 0.22
	earth.position = Vector3(-2.6, 1.6, -5.0)
	add_child(earth)
	# the teammate's rover and astronaut riding along on the title screen
	var astro: Node3D = Models.astronaut()
	_astronaut = astro
	add_child(astro)
	var aa := SiteWorld.find_anim(astro)
	_astronaut_anim = aa
	if aa and aa.has_animation("idle"):
		aa.get_animation("idle").loop_mode = Animation.LOOP_LINEAR
		aa.play("idle")
	var rover: Node3D = (load("res://assets/models/procedural/rover.glb") as PackedScene).instantiate()
	_rover = rover
	add_child(rover)
	_rover_anim = SiteWorld.find_anim(rover)
	if _rover_anim and _rover_anim.has_animation("mast_look"):
		_rover_anim.get_animation("mast_look").loop_mode = Animation.LOOP_LINEAR
		_rover_anim.speed_scale = 0.45
		_rover_anim.play("mast_look")

	_lander = Models.scene("lander").instantiate()
	_lander.scale = Vector3.ONE * 0.09
	_lander.position = Vector3(0.7, 0.2, 0.5)
	add_child(_lander)
	var flame := OmniLight3D.new()		# engine glow under the lander
	flame.light_color = Game.CYAN
	flame.light_energy = 2.0
	flame.omni_range = 0.6
	flame.position = Vector3(0, -0.05, 0)
	_lander.add_child(flame)

	var sun := DirectionalLight3D.new()
	sun.light_energy = 1.6
	sun.shadow_enabled = true
	sun.directional_shadow_max_distance = 12.0
	sun.rotation = Vector3(deg_to_rad(-25), deg_to_rad(60), 0)
	add_child(sun)
	var rim := DirectionalLight3D.new()
	rim.light_color = Game.MAGENTA
	rim.light_energy = 0.5
	rim.rotation = Vector3(deg_to_rad(-10), deg_to_rad(-140), 0)
	add_child(rim)

	_camera = Camera3D.new()
	_camera.fov = 45.0
	_camera.position = Vector3(0, 0.35, 3.0)
	add_child(_camera)
	_camera.look_at(Vector3(0, -0.15, 0))


## A point on the title-screen Moon's surface (centre (0, -3.1, -0.6), radius 2.6).
func _on_moon(x: float, z: float) -> Vector3:
	var c := Vector3(0, -3.1, -0.6)
	var dz := z - c.z
	return Vector3(x, c.y + sqrt(maxf(0.0, 6.76 - x * x - dz * dz)), z)


## Place the display models tangent to the globe, with their feet/wheels on the surface.
func _place_surface_model(model: Node3D, x: float, z: float, model_scale: float, yaw: float) -> void:
	var surface: Vector3 = _on_moon(x, z)
	var normal: Vector3 = (surface - _moon.position).normalized()
	var right: Vector3 = Vector3.RIGHT.slide(normal).normalized()
	var surface_basis: Basis = Basis(right, normal, right.cross(normal))
	model.transform = Transform3D(surface_basis.rotated(normal, yaw).scaled(Vector3.ONE * model_scale), surface)
	# Imported models do not all share a bottom-centred origin.
	var bottom: float = INF
	for mesh: Node in model.find_children("*", "MeshInstance3D", true, false):
		var instance: MeshInstance3D = mesh as MeshInstance3D
		var relative: Transform3D = model.global_transform.affine_inverse() * instance.global_transform
		var bounds: AABB = relative * instance.get_aabb()
		bottom = minf(bottom, bounds.position.y)
	if is_finite(bottom):
		model.position -= normal * bottom * model_scale


func _process(delta: float) -> void:
	_t += delta
	# Survey the horizon, then settle back into a breathing idle. No sliding root motion.
	var survey: bool = fmod(_t, 14.0) >= 8.0
	if survey != _surveying and _astronaut_anim:
		_surveying = survey
		var clip: String = "scan_sweep" if survey else "idle"
		if _astronaut_anim.has_animation(clip):
			_astronaut_anim.get_animation(clip).loop_mode = Animation.LOOP_LINEAR
			_astronaut_anim.speed_scale = 0.65 if survey else 1.0
			_astronaut_anim.play(clip, 0.65)
	_lander.position.y = 0.2 + sin(_t * 0.8) * 0.05
	_lander.rotation = Vector3(sin(_t * 0.6) * 0.08, _t * 0.25, cos(_t * 0.5) * 0.06)


func _build_ui() -> void:
	var layer := CanvasLayer.new()
	add_child(layer)
	var root := UIKit.full_rect(UIKit.margin(36))
	root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	layer.add_child(root)
	_col = UIKit.vbox(12)
	_col.mouse_filter = Control.MOUSE_FILTER_IGNORE
	root.add_child(_col)

	var top := UIKit.hbox(8)
	_col.add_child(top)
	top.add_child(UIKit.spacer(false))
	_sound_btn = UIKit.button("", _toggle_sound, 15)
	top.add_child(_sound_btn)
	_update_sound_label()

	var logo := Control.new()		# two stacked labels: a magenta "shadow" behind the yellow logo
	_logo = logo
	logo.custom_minimum_size = Vector2(0, 112)
	logo.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_col.add_child(logo)
	var back := UIKit.display("SUNLINE", 96, Game.MAGENTA)
	back.position = Vector2(6, 6)
	logo.add_child(back)
	var front := UIKit.display("SUNLINE", 96, Game.SUN)
	logo.add_child(front)
	var tag := UIKit.label("HOLD THE LIGHT  ·  A LUNAR LANDING GAME", 18, Game.CYAN)
	_col.add_child(tag)
	_col.add_child(UIKit.label("Real Sun. Real terrain. Six hours to hold the light.", 17, Game.MUTED, true))

	_col.add_child(UIKit.spacer())

	var menu := UIKit.vbox(12)
	menu.size_flags_horizontal = Control.SIZE_SHRINK_BEGIN
	_col.add_child(menu)
	var play_text := "CONTINUE" if Campaign.has_progress() else "PLAY"
	var play := UIKit.button(play_text, func() -> void: Game.goto("campaign"), 30, "primary")
	play.custom_minimum_size = Vector2(320, 70)
	menu.add_child(play)
	if Campaign.has_progress():
		menu.add_child(_stars_line())
	for spec in [["HOW TO PLAY", func() -> void: UIKit.overlay(layer, "HOW TO PLAY", Texts.help())],
			["SCIENCE LOG", func() -> void: UIKit.overlay(layer, "SCIENCE LOG", Texts.science_log())],
			["CREDITS", func() -> void: UIKit.overlay(layer, "CREDITS", Texts.credits())]]:
		var b := UIKit.button(spec[0], spec[1], 19)
		b.custom_minimum_size.x = 260
		b.size_flags_horizontal = Control.SIZE_SHRINK_BEGIN
		menu.add_child(b)
	var i := 0
	for c in menu.get_children():
		UIKit.pop_in(c, 0.15 + i * 0.07)
		i += 1
	UIKit.pop_in(logo, 0.0)
	_col.add_child(UIKit.label("NASA Space Apps Challenge 2026", 13, Game.MUTED))


func _stars_line() -> Control:
	var h := UIKit.hbox(8)
	h.add_child(UIKit.stars(1, 1, 22))
	h.add_child(UIKit.label("%d / %d" % [Campaign.total_stars(), Campaign.missions.size() * 3], 18, Game.SUN))
	return h


func _layout() -> void:
	for l in _logo.get_children():
		(l as Label).add_theme_font_size_override("font_size", 76 if Game.portrait else 96)
	_lander.position.x = 0.35 if Game.portrait else 0.7
	_camera.position = Vector3(0, 0.1, 4.6) if Game.portrait else Vector3(0, 0.35, 3.0)
	_camera.h_offset = 0.0 if Game.portrait else -0.55
	_camera.look_at(Vector3(0, -0.15, 0))
	if Game.portrait:
		_place_surface_model(_astronaut, -0.38, 0.25, 0.24, deg_to_rad(-15))
		_place_surface_model(_rover, 0.38, 0.18, 0.18, deg_to_rad(-110))
	else:
		_place_surface_model(_astronaut, -0.18, 0.28, 0.27, deg_to_rad(-15))
		_place_surface_model(_rover, 0.57, 0.12, 0.19, deg_to_rad(-110))


func _toggle_sound() -> void:
	Sfx.set_muted(not Sfx.muted)
	_update_sound_label()


func _update_sound_label() -> void:
	_sound_btn.text = "SOUND: OFF" if Sfx.muted else "SOUND: ON"
