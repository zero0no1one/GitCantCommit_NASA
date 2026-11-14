extends Node3D
## The sun-path ribbon: where the Sun's centre travels from touchdown over the sampling block, drawn in the sky
## in front of the skyline. Gold where the whole disc clears the skyline, coral where it does not (the data's
## full-sunlight intervals decide), with hour labels and an X at the first blocked point. Always drawn on top.

const R := 1300.0		# metres: inside the 1500 m skyline ring, so it reads as "in the sky"

var _mesh := ImmediateMesh.new()
var _mi := MeshInstance3D.new()
var _labels: Array[Node3D] = []
var _x: Label3D


func _ready() -> void:
	_mi.mesh = _mesh
	var mat := StandardMaterial3D.new()
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	mat.vertex_color_use_as_albedo = true
	mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	mat.no_depth_test = true
	mat.cull_mode = BaseMaterial3D.CULL_DISABLED
	mat.render_priority = 10
	_mi.material_override = mat
	_mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(_mi)
	_x = _label("X", Game.CORAL, 64)


func _label(text: String, c: Color, size := 40) -> Label3D:
	var l := Label3D.new()
	l.text = text
	l.modulate = c
	l.font_size = size
	l.pixel_size = 0.25
	l.outline_size = 10
	l.outline_modulate = Color(0, 0, 0, 0.8)
	l.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	l.no_depth_test = true
	l.render_priority = 11
	l.fixed_size = true
	l.pixel_size = 0.00045
	add_child(l)
	return l


## Rebuild for one site and touchdown. `world` gives sun directions; `need_s` is the block length.
func build(world: SiteWorld, touchdown: int, need_s: int) -> void:
	var iv: Array = Mission.sites[world.site].intervals.sun_full
	_mesh.clear_surfaces()
	var step := 300
	var pts: Array[Vector3] = []
	var ok: Array[bool] = []
	var t := touchdown
	while t <= touchdown + need_s:
		pts.append(world.sun_dir(t) * R)
		ok.append(Scoring.find(iv, t) >= 0)
		t += step
	var width := R * tan(deg_to_rad(0.27)) * 0.9		# about the Sun's diameter
	_mesh.surface_begin(Mesh.PRIMITIVE_TRIANGLES)
	var first_bad := -1
	for i in pts.size() - 1:
		var a := pts[i]
		var b := pts[i + 1]
		var along := (b - a).normalized()
		var side := along.cross(a.normalized()).normalized() * width * 0.5
		var c := Game.SUN if ok[i] else Game.CORAL
		if not ok[i] and first_bad < 0:
			first_bad = i
		var ca := Color(c, 0.85)
		for v in [a - side, a + side, b + side, a - side, b + side, b - side]:
			_mesh.surface_set_color(ca)
			_mesh.surface_add_vertex(v)
	_mesh.surface_end()
	# hour labels
	for l in _labels:
		l.queue_free()
	_labels.clear()
	# one marker at the end of the block ("+6H"), lit or not by whether the Sun is still clear there
	var last := pts.size() - 1
	var l := _label("+%dH" % int(need_s / 3600), Game.LIME if ok[last] else Game.CORAL, 14)
	l.position = pts[last] + Vector3.UP * width * 2.5
	_labels.append(l)
	var tick := MeshInstance3D.new()		# small end cap
	var sph := SphereMesh.new()
	sph.radius = width * 0.9
	sph.height = width * 1.8
	tick.mesh = sph
	tick.material_override = _mi.material_override
	tick.position = pts[last]
	add_child(tick)
	_labels.append(tick)
	_x.visible = first_bad >= 0
	if first_bad >= 0:
		_x.position = pts[first_bad]
