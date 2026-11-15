class_name SiteWorld
extends Node3D
## One landing site, built from the mission data: terrain (with collision), the distant skyline ring (the same
## skyline that scores the mission), the Sun disc, sunlight and Earth placed from the Horizons samples at time
## `t`, and illustrative props. Shared by every phase of the mission scene.

const SKY_DIST := 4000.0

var site := ""
var t := 0.0

var env: Environment
var sun_light: DirectionalLight3D
var sun_disc: Node3D
var earth: Node3D
var rover: Node3D
var rover_anim: AnimationPlayer
var beacon: Node3D
var props_ready := false

var _rock_meshes: Array[Mesh] = []


func _init(site_id: String) -> void:
	site = site_id


func _ready() -> void:
	_build()


func _build() -> void:
	env = Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = Color(0, 0, 0)
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color(0.1, 0.1, 0.12)
	env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	env.tonemap_exposure = 1.1
	env.glow_enabled = true
	env.glow_intensity = 1.0
	env.glow_hdr_threshold = 1.1
	var we := WorldEnvironment.new()
	we.environment = env
	add_child(we)

	var terrain: Node3D = Models.scene("terrain_" + site).instantiate()
	add_child(terrain)
	for mi in terrain.find_children("*", "MeshInstance3D", true, false):
		var m := mi as MeshInstance3D
		if m.name.begins_with("Terrain"):
			m.create_trimesh_collision()
			# with the Sun a fraction of a degree up, a full-strength detail normal map makes only tiny sun-facing
			# bumps light up (sparkle). Soften it; the large-scale shading comes from the mesh.
			var tm := m.get_active_material(0)
			if tm is StandardMaterial3D:
				var t2: StandardMaterial3D = tm.duplicate()
				t2.normal_scale = 0.3
				t2.specular_mode = BaseMaterial3D.SPECULAR_DISABLED
				m.material_override = t2
		else:
			m.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF

	sun_light = DirectionalLight3D.new()
	sun_light.shadow_enabled = true
	sun_light.directional_shadow_max_distance = 140.0
	sun_light.shadow_blur = 0.6
	sun_light.shadow_bias = 0.15		# grazing Sun: generous biases stop shadow acne (worst on WebGL)
	sun_light.shadow_normal_bias = 3.0
	sun_light.directional_shadow_mode = DirectionalLight3D.SHADOW_PARALLEL_2_SPLITS
	add_child(sun_light)

	# Sun and Earth: the teammate's models (assets/team/scenes, unit radius, unshaded Sun). They are visuals
	# only: where they sit and how big they look comes from the Horizons samples in set_time(), and the
	# sunlight rule is scored from the data, never from these meshes.
	sun_disc = Models.team("sun").instantiate()
	add_child(sun_disc)
	sun_disc.add_child(_glare(10.0, Color(1, 0.92, 0.7)))		# cosmetic glare; the body itself is true size
	earth = Models.team("earth").instantiate()
	add_child(earth)
	for body in [sun_disc, earth]:		# their meshes exist once added (celestial_visual.gd builds them in _ready)
		for mi in body.find_children("*", "MeshInstance3D", true, false):
			(mi as MeshInstance3D).cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF

	var rocks: Node3D = Models.scene("rocks").instantiate()
	for mi in rocks.find_children("*", "MeshInstance3D", true, false):
		_rock_meshes.append((mi as MeshInstance3D).mesh)
	rocks.free()
	set_time(t)


## Additive radial glow quad (child of a node scaled in "radii").
static func _glare(size_r: float, c: Color) -> MeshInstance3D:
	var halo := MeshInstance3D.new()
	var quad := QuadMesh.new()
	quad.size = Vector2(size_r, size_r)
	halo.mesh = quad
	halo.position.z = -0.01
	var hm := StandardMaterial3D.new()
	hm.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	hm.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	hm.blend_mode = BaseMaterial3D.BLEND_MODE_ADD
	hm.cull_mode = BaseMaterial3D.CULL_DISABLED
	var grad := Gradient.new()
	grad.set_color(0, Color(c, 0.9))
	grad.set_color(1, Color(c, 0.0))
	grad.add_point(0.12, Color(c, 0.55))
	var gt := GradientTexture2D.new()
	gt.gradient = grad
	gt.fill = GradientTexture2D.FILL_RADIAL
	gt.fill_from = Vector2(0.5, 0.5)
	gt.fill_to = Vector2(1.0, 0.5)
	hm.albedo_texture = gt
	halo.material_override = hm
	halo.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	return halo


# ---------------------------------------------------------------- sky from the data

static func sky_dir(az: float, el: float) -> Vector3:
	var a := deg_to_rad(az)
	var e := deg_to_rad(el)
	return Vector3(cos(e) * sin(a), sin(e), -cos(e) * cos(a))


static func dir_to_az_el(d: Vector3) -> Vector2:
	return Vector2(fposmod(rad_to_deg(atan2(d.x, -d.z)), 360.0), rad_to_deg(asin(clampf(d.y, -1, 1))))


func sun_dir(at: float) -> Vector3:
	return sky_dir(Mission.sample(site, "sun_az", at), Mission.sample(site, "sun_el", at))


## Fraction of the solar disc above the skyline (same formula as scoring.py's sun_visible_fraction).
func sun_fraction(at: float) -> float:
	var az := Mission.sample(site, "sun_az", at)
	var x := clampf((Mission.sample(site, "sun_el", at) - Mission.skyline(site, az)) / Mission.sample(site, "sun_radius", at),
		-1.0, 1.0)
	return (acos(-x) + x * sqrt(1.0 - x * x)) / PI


## Lower edge of the Sun above (+) or below (-) the skyline, in degrees.
func sun_margin(at: float) -> float:
	var az := Mission.sample(site, "sun_az", at)
	return Mission.sample(site, "sun_el", at) - Mission.sample(site, "sun_radius", at) - Mission.skyline(site, az)


func earth_up(at: float) -> bool:
	var az := Mission.sample(site, "earth_az", at)
	return Mission.sample(site, "earth_el", at) > Mission.skyline(site, az)


func set_time(at: float) -> void:
	t = at
	var el := Mission.sample(site, "sun_el", t)
	var d := sun_dir(t)
	var up := Vector3.UP if absf(el) < 80.0 else Vector3.FORWARD
	sun_light.global_basis = Basis.looking_at(-d, up)
	var frac := sun_fraction(t)
	sun_light.light_energy = 2.3 * frac
	sun_light.visible = frac > 0.0
	sun_disc.position = d * SKY_DIST
	sun_disc.global_basis = Basis.looking_at(d, up).scaled(
		Vector3.ONE * SKY_DIST * tan(deg_to_rad(Mission.sample(site, "sun_radius", t))))
	var eel := Mission.sample(site, "earth_el", t)
	var ed := sky_dir(Mission.sample(site, "earth_az", t), eel)
	earth.position = ed * SKY_DIST
	earth.global_basis = Basis.looking_at(ed, Vector3.UP if absf(eel) < 80.0 else Vector3.FORWARD) \
		.scaled(Vector3.ONE * SKY_DIST * tan(deg_to_rad(Mission.sample(site, "earth_radius", t))))
	env.ambient_light_color = Color(0.17, 0.18, 0.22) if earth_up(t) else Color(0.1, 0.1, 0.11)


# ---------------------------------------------------------------- ground and props

func ground_y(xz: Vector2) -> float:
	var q := PhysicsRayQueryParameters3D.create(Vector3(xz.x, 300, xz.y), Vector3(xz.x, -400, xz.y))
	q.collision_mask = 1
	var hit := get_world_3d().direct_space_state.intersect_ray(q)
	return hit.position.y if hit else 0.0


func put(n: Node3D, xz: Vector2, yaw := 0.0, s := 1.0) -> Node3D:
	if n.get_parent() == null:
		add_child(n)
	n.position = Vector3(xz.x, ground_y(xz), xz.y)
	n.rotation.y = yaw
	n.scale = Vector3.ONE * s
	return n


## Rover, beacon and scattered rocks around `center` (call after one physics frame so rays hit the terrain).
## Rocks are illustrative and always far below the skyline.
func spawn_props(center: Vector2) -> void:
	# the teammate's rover and survey beacon (static visuals; see assets/team/README.md)
	rover = put(Models.team("lunar_rover").instantiate(), center + Vector2(7, -5), deg_to_rad(200), 1.4)
	rover_anim = find_anim(rover)
	beacon = put(Models.team("survey_beacon").instantiate(), center + Vector2(-9, -7), 0.4)
	# beacon light: a pulsing glow sprite on the antenna (no light source, so it never tints the ground)
	var pulse := MeshInstance3D.new()
	var q := QuadMesh.new()
	q.size = Vector2(0.6, 0.6)
	pulse.mesh = q
	var pm := StandardMaterial3D.new()
	pm.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	pm.billboard_mode = BaseMaterial3D.BILLBOARD_ENABLED
	pm.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	pm.blend_mode = BaseMaterial3D.BLEND_MODE_ADD
	var g := Gradient.new()
	g.set_color(0, Color(0.6, 1, 1, 1))
	g.set_color(1, Color(0.18, 0.95, 1, 0))
	var gt := GradientTexture2D.new()
	gt.gradient = g
	gt.fill = GradientTexture2D.FILL_RADIAL
	gt.fill_from = Vector2(0.5, 0.5)
	gt.fill_to = Vector2(1.0, 0.5)
	pm.albedo_texture = gt
	pulse.material_override = pm
	pulse.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	pulse.position.y = 1.45
	beacon.add_child(pulse)
	var tw := pulse.create_tween().set_loops()
	tw.tween_property(pulse, "scale", Vector3.ONE * 0.4, 0.8).set_trans(Tween.TRANS_SINE)
	tw.tween_property(pulse, "scale", Vector3.ONE * 1.1, 0.8).set_trans(Tween.TRANS_SINE)
	var rng := RandomNumberGenerator.new()
	rng.seed = hash(site)
	for i in 80:
		var r := rng.randf_range(8.0, 260.0)
		var a := rng.randf() * TAU
		var mesh: Mesh = _rock_meshes[rng.randi() % _rock_meshes.size()]
		if mesh.get_aabb().size.x > 2.5 and r < 35.0:
			continue
		var inst := MeshInstance3D.new()
		inst.mesh = mesh
		put(inst, center + Vector2(cos(a), sin(a)) * r, rng.randf() * TAU, rng.randf_range(0.6, 1.4))
	props_ready = true


func rock_mesh(i: int) -> Mesh:
	return _rock_meshes[i % _rock_meshes.size()]


## Lunar dust puffs from the baked flipbooks: ballistic arcs under 1.62 m/s², no billowing (no air).
static func dust(amount: int, size: float, v_min: float, v_max: float, lifetime := 1.4,
		sheet := "res://assets/vfx/footstep_dust_4x4.png") -> CPUParticles3D:
	var p := CPUParticles3D.new()
	p.emitting = false
	p.amount = amount
	p.lifetime = lifetime
	p.direction = Vector3(0, 1, 0)
	p.spread = 70.0
	p.initial_velocity_min = v_min
	p.initial_velocity_max = v_max
	p.gravity = Vector3(0, -1.62, 0)
	p.scale_amount_min = 0.6
	p.scale_amount_max = 1.3
	var quad := QuadMesh.new()
	quad.size = Vector2(size, size)
	var m := StandardMaterial3D.new()
	m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	m.billboard_mode = BaseMaterial3D.BILLBOARD_PARTICLES
	m.albedo_texture = load(sheet)
	m.particles_anim_h_frames = 4
	m.particles_anim_v_frames = 4
	m.vertex_color_use_as_albedo = true
	quad.material = m
	p.mesh = quad
	p.anim_speed_min = 1.0
	p.anim_speed_max = 1.0
	p.color = Color(0.78, 0.75, 0.7, 0.75)
	return p


static func find_anim(n: Node) -> AnimationPlayer:
	var found := n.find_children("*", "AnimationPlayer", true, false)
	return found[0] if found.size() > 0 else null


## Emissive parts made for Blender's renders are too hot under Godot's glow; cap them.
static func tame_emission(root: Node, energy: float) -> void:
	for mi in root.find_children("*", "MeshInstance3D", true, false):
		var m := mi as MeshInstance3D
		for i in m.get_surface_override_material_count():
			var mat := m.get_active_material(i)
			if mat is StandardMaterial3D and (mat as StandardMaterial3D).emission_enabled:
				var d: StandardMaterial3D = mat.duplicate()
				d.emission_energy_multiplier = minf(d.emission_energy_multiplier, energy)
				m.set_surface_override_material(i, d)
