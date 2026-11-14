extends CharacterBody3D
## The player on the surface: lunar-gravity movement, third-person (default) or first-person view with the visor
## and cyan scanner, mouse/touch look, a left-thumb stick on touch screens. Input via the Game actions.

signal view_changed(first_person: bool)

const EYE_H := 1.62
const WALK := 0.9		# = WALK_NATIVE: the walk plays at exactly its Blender timing
const LOPE := 2.3		# = LOPE_NATIVE: the lope plays at exactly its Blender timing
const HOP := 2.2
const PLAY_RADIUS := 380.0
const WALK_NATIVE := 0.9		# m/s the walk_slow cycle is authored at (blender/scripts/animate_astronaut_locomotion.py)
const LOPE_NATIVE := 2.3		# m/s the lunar_lope cycle is authored at

var frozen := false
var first_person := false
var camera: Camera3D
var model: Node3D
var anim: AnimationPlayer
var scanning := false

var _yaw := 0.0
var _pitch := deg_to_rad(-12.0)
var _cam_yaw: Node3D
var _cam_pitch: Node3D
var _arm: SpringArm3D
var _fp_rig: Node3D
var _stick_index := -1
var _stick_origin := Vector2.ZERO
var _stick_vec := Vector2.ZERO
var _look_index := -1
var _mouse_look := false
var _overlay: Control
var _visor: ColorRect
var _dust: CPUParticles3D
var _was_floor := true


func _ready() -> void:
	var col := CollisionShape3D.new()
	var cap := CapsuleShape3D.new()
	cap.radius = 0.35
	cap.height = 1.8
	col.shape = cap
	col.position.y = 0.9
	add_child(col)
	collision_layer = 2
	floor_snap_length = 0.6
	floor_max_angle = deg_to_rad(42)

	# the teammate's astronaut, rigged to the Sunline skeleton by blender/scripts/rig_team_astronaut.py
	model = Models.scene("astronaut_team").instantiate()
	add_child(model)
	SiteWorld.tame_emission(model, 0.7)
	anim = SiteWorld.find_anim(model)
	if anim:
		for a in ["idle", "lunar_lope", "walk_slow", "scan_sweep"]:
			if anim.has_animation(a):
				anim.get_animation(a).loop_mode = Animation.LOOP_LINEAR
		anim.play("idle")

	_cam_yaw = Node3D.new()
	_cam_yaw.position.y = EYE_H
	add_child(_cam_yaw)
	_cam_pitch = Node3D.new()
	_cam_yaw.add_child(_cam_pitch)
	_arm = SpringArm3D.new()
	var sph := SphereShape3D.new()
	sph.radius = 0.2
	_arm.shape = sph
	_arm.collision_mask = 1
	_cam_pitch.add_child(_arm)
	camera = Camera3D.new()
	camera.near = 0.05
	camera.far = 6500.0
	camera.fov = 70.0
	_arm.add_child(camera)
	_fit_camera(Game.portrait)
	Game.orientation_changed.connect(_fit_camera)
	_fp_rig = Models.scene("fp_rig").instantiate()
	camera.add_child(_fp_rig)
	SiteWorld.tame_emission(_fp_rig, 0.7)
	var fa := SiteWorld.find_anim(_fp_rig)
	if fa and fa.has_animation("fp_idle"):
		fa.get_animation("fp_idle").loop_mode = Animation.LOOP_LINEAR
		fa.play("fp_idle")
	_dust = SiteWorld.dust(14, 0.35, 0.4, 1.1, 1.3)
	_dust.position = Vector3(0, 0.05, 0)
	add_child(_dust)
	_build_overlay()
	set_view(false)


## Phones held upright: keep a wide horizontal view instead of a tall narrow one.
func _fit_camera(portrait: bool) -> void:
	camera.keep_aspect = Camera3D.KEEP_WIDTH if portrait else Camera3D.KEEP_HEIGHT
	camera.fov = 80.0 if portrait else 70.0


func face(yaw: float) -> void:
	_yaw = yaw
	model.rotation.y = yaw + PI		# the astronaut model faces +Z (Blender -Y); the camera looks along -Z


func set_view(fp: bool) -> void:
	first_person = fp
	_arm.spring_length = 0.0 if fp else 5.5
	_cam_pitch.position = Vector3.ZERO if fp else Vector3(0.5, 0.4, 0)
	model.visible = not fp
	_fp_rig.visible = fp
	_visor.visible = fp
	view_changed.emit(fp)


## Horizontal direction the camera looks along.
func look_dir() -> Vector3:
	var f := -camera.global_basis.z
	return Vector3(f.x, 0, f.z).normalized()


func _build_overlay() -> void:
	var layer := CanvasLayer.new()
	layer.layer = 1
	add_child(layer)
	_overlay = UIKit.full_rect(Control.new())
	_overlay.mouse_filter = Control.MOUSE_FILTER_IGNORE
	layer.add_child(_overlay)
	_visor = ColorRect.new()
	_visor.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var sh := Shader.new()
	sh.code = """shader_type canvas_item;
uniform vec2 aspect = vec2(1.777, 1.0);
void fragment() {
	vec2 p = (UV - 0.5) * 2.0 * aspect;
	vec2 q = abs(p) - (aspect - vec2(0.42));
	float d = length(max(q, 0.0)) / 0.42;
	float edge = smoothstep(0.55, 1.05, d);
	COLOR = vec4(0.02, 0.02, 0.05, edge * 0.94) + vec4(0.18, 0.95, 1.0, 0.05) * smoothstep(0.4, 0.55, d) * (1.0 - edge);
}"""
	var smat := ShaderMaterial.new()
	smat.shader = sh
	_visor.material = smat
	_overlay.add_child(UIKit.full_rect(_visor))
	_overlay.draw.connect(_draw_stick)


func _draw_stick() -> void:
	if _stick_index >= 0:
		_overlay.draw_arc(_stick_origin, 70, 0, TAU, 40, Color(Game.CYAN, 0.5), 3.0)
		_overlay.draw_circle(_stick_origin + _stick_vec * 70, 28, Color(Game.CYAN, 0.35))


func _process(_delta: float) -> void:
	_cam_yaw.rotation.y = _yaw
	_cam_pitch.rotation.x = _pitch
	var vp := get_viewport().get_visible_rect().size
	(_visor.material as ShaderMaterial).set_shader_parameter("aspect",
		Vector2(vp.x / vp.y, 1.0) if vp.x > vp.y else Vector2(1.0, vp.y / vp.x))


func _physics_process(delta: float) -> void:
	var input := Input.get_vector("move_left", "move_right", "move_forward", "move_back")
	input = (input + _stick_vec).limit_length(1.0)
	if frozen:
		input = Vector2.ZERO
	var wish := Basis(Vector3.UP, _yaw) * Vector3(input.x, 0, input.y)
	# walk by default (the Blender walk cycle at its native speed); Shift, or a full push of the touch stick = lope
	var bounding := Input.is_action_pressed("run") or _stick_vec.length() > 0.85
	var speed := LOPE if bounding else WALK
	var v := velocity
	var horiz := Vector3(v.x, 0, v.z)
	var accel := 7.0 if is_on_floor() else 1.2
	horiz = horiz.move_toward(wish * speed, accel * delta * speed)
	v.x = horiz.x
	v.z = horiz.z
	if not is_on_floor():
		v.y -= Game.LUNAR_G * delta
	elif Input.is_action_just_pressed("hop") and not frozen:
		v.y = HOP
	velocity = v
	move_and_slide()
	var flat := Vector2(position.x, position.z)
	if flat.length() > PLAY_RADIUS:
		flat = flat.limit_length(PLAY_RADIUS)
		position = Vector3(flat.x, position.y, flat.y)
	if position.y < -250:
		position = Vector3(0, 10, 0)
		velocity = Vector3.ZERO
	if horiz.length() > 0.2:
		model.rotation.y = lerp_angle(model.rotation.y, atan2(horiz.x, horiz.z), 8.0 * delta)	# +Z toward travel
	# footstep dust while moving on the ground, and a puff when landing from a hop
	_dust.emitting = is_on_floor() and horiz.length() > 0.6
	if is_on_floor() and not _was_floor:
		_dust.restart()
		_dust.emitting = true
	_was_floor = is_on_floor()
	if anim:
		_animate(horiz.length())


## Pick the gait from the actual ground speed and play it at the matching rate, so planted feet don't skate.
## Native speeds were measured from the planted foot in Blender (walk_slow 0.9 m/s; lunar_lope is a bounding
## gait that is mostly airborne, tuned to ~2.6 m/s). In the air (hops) the current pose is held.
func _animate(spd: float) -> void:
	var want := "idle"
	var rate := 1.0
	if scanning:
		want = "scan_sweep"
	elif not is_on_floor() and anim.current_animation != "":
		want = anim.current_animation
		rate = anim.speed_scale
	elif spd > 1.4:
		want = "lunar_lope"
		rate = clampf(spd / LOPE_NATIVE, 0.7, 1.6)
	elif spd > 0.3:
		want = "walk_slow"
		rate = clampf(spd / WALK_NATIVE, 0.5, 2.2)
	anim.speed_scale = rate
	if anim.current_animation != want and anim.has_animation(want):
		anim.play(want, 0.25)


func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("view"):
		set_view(not first_person)
	if event is InputEventMouse and event.device == InputEvent.DEVICE_ID_EMULATION:
		return		# touches are handled as ScreenTouch/ScreenDrag below
	if event is InputEventMouseButton:
		var mb := event as InputEventMouseButton
		if mb.button_index == MOUSE_BUTTON_LEFT:
			_mouse_look = mb.pressed
		elif mb.button_index == MOUSE_BUTTON_WHEEL_UP and not first_person:
			_arm.spring_length = maxf(2.5, _arm.spring_length - 0.5)
		elif mb.button_index == MOUSE_BUTTON_WHEEL_DOWN and not first_person:
			_arm.spring_length = minf(14.0, _arm.spring_length + 0.5)
	elif event is InputEventMouseMotion and _mouse_look:
		_look((event as InputEventMouseMotion).relative)
	elif event is InputEventScreenTouch:
		var st := event as InputEventScreenTouch
		var vp := get_viewport().get_visible_rect().size
		if st.pressed:
			if st.position.x < vp.x * 0.45 and st.position.y > vp.y * 0.3 and _stick_index < 0:
				_stick_index = st.index
				_stick_origin = st.position
				_stick_vec = Vector2.ZERO
			elif _look_index < 0:
				_look_index = st.index
		else:
			if st.index == _stick_index:
				_stick_index = -1
				_stick_vec = Vector2.ZERO
			elif st.index == _look_index:
				_look_index = -1
		_overlay.queue_redraw()
	elif event is InputEventScreenDrag:
		var sd := event as InputEventScreenDrag
		if sd.index == _stick_index:
			_stick_vec = ((sd.position - _stick_origin) / 70.0).limit_length(1.0)
			_overlay.queue_redraw()
		elif sd.index == _look_index:
			_look(sd.relative * 1.4)


func _look(rel: Vector2) -> void:
	_yaw -= rel.x * 0.0045
	_pitch = clampf(_pitch - rel.y * 0.0045, deg_to_rad(-80), deg_to_rad(70))
