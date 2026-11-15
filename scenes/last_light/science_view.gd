extends Control
## All geometry comes from the mission model; this drawing never feeds assessment.
var host: Node
var kind := "horizon"
var dragging := false
const GOLD := Color("ffd23f")
const TEAL := Color("2ef2ff")
const RED := Color("ff5a36")

func _ready() -> void:
	clip_contents = true
	focus_mode = Control.FOCUS_ALL if kind == "timeline" else Control.FOCUS_NONE
	mouse_default_cursor_shape = Control.CURSOR_DRAG if kind == "timeline" else Control.CURSOR_ARROW
	resized.connect(queue_redraw)

func label_at(text: String, pos: Vector2, color: Color = Color("c8d7e2"), font_size: int = 13) -> void:
	draw_string(get_theme_default_font(), pos, text, HORIZONTAL_ALIGNMENT_LEFT, -1, font_size, color)

func _draw() -> void:
	draw_style_box(_background(), Rect2(Vector2.ZERO, size))
	if host == null: return
	if kind == "map": _map()
	elif kind == "timeline": _timeline()
	else: _horizon()
	if has_focus(): draw_rect(Rect2(Vector2(2,2),size-Vector2(4,4)), GOLD, false, 3)

func _background() -> StyleBoxFlat:
	var style := StyleBoxFlat.new()
	style.bg_color = Color("161040")
	style.border_color = Color("2ef2ff")
	style.set_border_width_all(2)
	style.set_corner_radius_all(4)
	return style

func _map() -> void:
	label_at("MOON MAP / equirectangular locator", Vector2(12,22), TEAL)
	var area := Rect2(12,36,size.x-24,size.y-62)
	draw_rect(area, Color("242050"))
	for i in range(1,6):
		draw_line(Vector2(area.position.x+i*area.size.x/6,area.position.y),Vector2(area.position.x+i*area.size.x/6,area.end.y),Color("4a5e65"))
	for i in range(1,4):
		draw_line(Vector2(area.position.x,area.position.y+i*area.size.y/4),Vector2(area.end.x,area.position.y+i*area.size.y/4),Color("4a5e65"))
	for sid: String in host.model.records:
		var site: Dictionary = host.model.records[sid].site
		var x := area.position.x + fposmod(float(site.lon)+180,360)/360*area.size.x
		var y := area.position.y + (90-float(site.lat))/180*area.size.y
		draw_circle(Vector2(x,y), 5, GOLD if sid == host.site else TEAL)
		label_at("A11" if sid == "apollo-11" else "RIDGE", Vector2(x+7, minf(y+4,area.end.y-3)), GOLD if sid == host.site else TEAL, 12)
	label_at("90 N  |  east-positive longitude  |  90 S", Vector2(12,size.y-9), Color("98adb8"), 11)

func _horizon() -> void:
	var p: Dictionary = host.model.geometry(host.site, host.inspect_at)
	label_at("HORIZON VIEW / fixed 1 m observer", Vector2(12,22), TEAL)
	if p.is_empty():
		label_at("UNKNOWN / source coverage unavailable", Vector2(14,75), RED)
		return
	var bearing := float(p.sun_az)
	var low := minf(-1, float(p.skyline)-2)
	var high := maxf(4, float(p.sun_el)+1)
	var area := Rect2(36,34,size.x-50,size.y-71)
	var project := func(az: float, el: float) -> Vector2:
		return Vector2(area.position.x+(az-bearing+8)/16*area.size.x, area.end.y-(el-low)/(high-low)*area.size.y)
	var points := PackedVector2Array([Vector2(area.position.x,area.end.y)])
	for i in 161:
		var az := bearing-8+i*.1
		points.append(project.call(az,host.model.skyline(host.site,az)))
	points.append(area.end)
	draw_colored_polygon(points,Color("403763"))
	draw_polyline(PackedVector2Array(points.slice(1,points.size()-1)),Color("9aabb1"),2,true)
	var level: Vector2 = project.call(bearing,0.)
	draw_line(Vector2(area.position.x,level.y),Vector2(area.end.x,level.y),Color("81919b"),1)
	label_at("0 deg level",Vector2(3,level.y-3),Color("a5b3ba"),10)
	# Actual apparent angular size; asymmetric axis scales documented by bearing/elevation labels.
	var center: Vector2 = project.call(bearing,float(p.sun_el))
	var radius := Vector2(float(p.sun_radius)/16*area.size.x,float(p.sun_radius)/(high-low)*area.size.y)
	var disk := PackedVector2Array()
	for i in 64: disk.append(center + Vector2(cos(i*TAU/64),sin(i*TAU/64))*radius)
	draw_colored_polygon(disk,GOLD)
	for offset in range(-6,7):
		var g: Dictionary = host.model.geometry(host.site,host.inspect_at+offset*600)
		if not g.is_empty(): draw_circle(project.call(bearing+wrapf(float(g.sun_az)-bearing,-180,180),g.sun_el),2,TEAL)
	label_at("%s | bearing %.1f deg" % [p.state,bearing],Vector2(12,size.y-37),GOLD,12)
	label_at("Sun %.2f deg | ridge %.2f deg" % [p.sun_el,p.skyline],Vector2(12,size.y-22),GOLD,12)
	label_at("Cyan: 10-min Sun track. Independent axis scales.",Vector2(12,size.y-7),Color("98adb8"),10)

func _timeline() -> void:
	label_at("UTC TIMELINE / drag bracket or use Left/Right (1 minute)",Vector2(12,21),TEAL)
	var area := Rect2(16,35,size.x-32,24)
	var span := float(host.timeline_end-host.timeline_start)
	var x := func(t: float) -> float: return area.position.x+(t-host.timeline_start)/span*area.size.x
	draw_rect(area,Color("653344"))
	var record: Dictionary = host.model.records[host.site]
	for iv: Array in record.sun_any:
		var a := maxf(iv[0],host.timeline_start)
		var b := minf(float(iv[1])+1,host.timeline_end)
		if b > a: draw_rect(Rect2(x.call(a),area.position.y,x.call(b)-x.call(a),24),Color("a5743e"))
	for iv: Array in record.variants[0].full:
		var a := maxf(iv[0],host.timeline_start)
		var b := minf(float(iv[1])+1,host.timeline_end)
		if b > a: draw_rect(Rect2(x.call(a),area.position.y,x.call(b)-x.call(a),24),Color("257b83"))
	for event: Dictionary in record.events:
		if event.unix < host.timeline_start or event.unix > host.timeline_end: continue
		var xx: float = x.call(event.unix)
		draw_line(Vector2(xx,31),Vector2(xx,105),RED if event.kind == "Full to partial" else GOLD,2)
	var xx: float = x.call(host.start)
	var setup_end: float = x.call(host.start+int(host.model.requirements.setup_s))
	var finish: float = x.call(host.start+host.model.duration())
	draw_rect(Rect2(xx,68,maxf(1,setup_end-xx),25),TEAL)
	draw_rect(Rect2(setup_end,68,maxf(1,finish-setup_end),25),GOLD)
	draw_rect(Rect2(xx,65,maxf(1,finish-xx),31),Color.WHITE,false,2)
	label_at("SETUP  /  OBSERVATION",Vector2(xx,110),GOLD,11)
	label_at(host.utc(host.timeline_start),Vector2(12,size.y-24),Color("c8d7e2"),12)
	var end_text: String = host.utc(host.timeline_end)
	label_at(end_text,Vector2(maxf(12,size.x-200),size.y-24),Color("c8d7e2"),12)
	label_at("FULL: teal   PARTIAL: amber   BLOCKED: rose   |   Red line: first full-sun loss",Vector2(12,size.y-8),Color("98adb8"),11)

func _gui_input(event: InputEvent) -> void:
	if kind != "timeline": return
	if event is InputEventKey and event.pressed:
		if event.keycode in [KEY_LEFT,KEY_RIGHT]:
			host.set_start(host.start+(-60 if event.keycode == KEY_LEFT else 60))
			accept_event()
	if event is InputEventMouseButton and event.button_index == MOUSE_BUTTON_LEFT:
		dragging = event.pressed
		grab_focus()
		if dragging: _seek(event.position.x)
	if event is InputEventMouseMotion and dragging: _seek(event.position.x)
	if event is InputEventScreenTouch:
		dragging = event.pressed
		if dragging: _seek(event.position.x)
	if event is InputEventScreenDrag and dragging: _seek(event.position.x)

func _seek(x: float) -> void:
	var f := clampf((x-16)/maxf(1,size.x-32),0,1)
	host.set_start(roundi((host.timeline_start+f*(host.timeline_end-host.timeline_start))/60)*60)
