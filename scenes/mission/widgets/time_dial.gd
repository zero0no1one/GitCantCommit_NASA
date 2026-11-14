extends Control
## Touchdown time dial: a glowing track across the mission's decision window with a sun-shaped knob.
## Drag anywhere on the track (10-minute steps). With "forecast" on, passing touchdowns are lit on the track.

signal changed(t: int)

var start := 0
var end := 0
var step := 600
var value := 0
var locked := false
var forecast: Array = []		# [[a, b], ...] passing touchdown spans, shown only when the forecast is bought

var _drag := false
var _t := 0.0


func _ready() -> void:
	custom_minimum_size = Vector2(240, 64)
	mouse_filter = Control.MOUSE_FILTER_STOP


func _process(delta: float) -> void:
	_t += delta
	queue_redraw()


func set_value(v: int, emit := false) -> void:
	v = clampi(start + int(round(float(v - start) / step)) * step, start, end)
	if v == value:
		return
	value = v
	if emit:
		changed.emit(v)


func _track() -> Rect2:
	return Rect2(22, size.y * 0.5 - 5, size.x - 44, 10)


func _x(t: float) -> float:
	var r := _track()
	return r.position.x + (t - start) / maxf(1.0, float(end - start)) * r.size.x


func _gui_input(event: InputEvent) -> void:
	if locked:
		return
	var pos := Vector2.INF
	if event is InputEventMouseButton and event.button_index == MOUSE_BUTTON_LEFT:
		_drag = event.pressed
		if event.pressed:
			pos = event.position
	elif event is InputEventScreenTouch:
		_drag = event.pressed
		if event.pressed:
			pos = event.position
	elif (event is InputEventMouseMotion or event is InputEventScreenDrag) and _drag:
		pos = event.position
	if pos != Vector2.INF:
		var r := _track()
		var f := clampf((pos.x - r.position.x) / r.size.x, 0.0, 1.0)
		var before := value
		set_value(start + int(f * (end - start)), true)
		if value != before:
			Sfx.play("tick", 1.0 + f * 0.5, -8.0)
		accept_event()


func _draw() -> void:
	var r := _track()
	var font := get_theme_default_font()
	draw_rect(r.grow(3), Color(0, 0, 0, 0.5))
	draw_rect(r, Game.PANEL)
	for f: Array in forecast:		# bought forecast: passing spans
		var a := _x(f[0])
		var b := _x(f[1]) + 2.0
		draw_rect(Rect2(a, r.position.y, maxf(2.0, b - a), r.size.y), Color(Game.LIME, 0.75))
	# hour ticks, day labels
	var span := end - start
	var tick := 3600 if span <= 3 * 86400 else 6 * 3600
	var tt := int(ceil(float(start) / tick)) * tick
	while tt <= end:
		var x := _x(tt)
		var d := Time.get_datetime_dict_from_unix_time(tt)
		var major: bool = int(d.hour) % 6 == 0
		draw_line(Vector2(x, r.end.y + 2), Vector2(x, r.end.y + (9 if major else 4)), Color(Game.CYAN, 0.6 if major else 0.3), 1.0)
		if d.hour == 0:
			draw_string(font, Vector2(x - 30, r.end.y + 24), "%s %d" % [["", "JAN", "FEB", "MAR", "APR"][mini(d.month, 4)], d.day],
				HORIZONTAL_ALIGNMENT_CENTER, 60, 13, Game.MUTED)
		tt += tick
	if locked:
		draw_string(font, Vector2(r.position.x, r.position.y - 8), "LAUNCH TIME LOCKED", HORIZONTAL_ALIGNMENT_LEFT, -1, 13,
			Game.CORAL)
	# knob: a little sun
	var k := Vector2(_x(value), r.get_center().y)
	var pulse := 1.0 + 0.08 * sin(_t * 5.0)
	draw_circle(k, 20 * pulse, Color(Game.SUN, 0.18))
	for i in 8:
		var a := i * TAU / 8 + _t * 0.6
		draw_line(k + Vector2.from_angle(a) * 12, k + Vector2.from_angle(a) * 17, Game.SUN, 2.5, true)
	draw_circle(k, 10, Game.SUN)
	draw_circle(k, 10, Game.SPACE, false, 2.0, true)
