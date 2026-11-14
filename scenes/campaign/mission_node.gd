extends Control
## One mission on the campaign strip: a hexagon with the mission number, stars underneath, a lock when closed.

signal picked(id: String)

var id := ""
var number := 1
var stars := 0
var locked := false
var selected := false
var _hover := false
var _t := 0.0


func _ready() -> void:
	custom_minimum_size = Vector2(60, 84)
	mouse_filter = Control.MOUSE_FILTER_STOP
	mouse_entered.connect(func() -> void:
		_hover = true
		if not locked:
			Sfx.play("hover"))
	mouse_exited.connect(func() -> void: _hover = false)


func _process(delta: float) -> void:
	_t += delta
	if selected:
		queue_redraw()


func _gui_input(event: InputEvent) -> void:
	var pressed: bool = (event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_LEFT) \
		or (event is InputEventScreenTouch and event.pressed)
	if pressed:
		accept_event()
		if locked:
			Sfx.play("back", 0.8)
		else:
			Sfx.play("click")
			picked.emit(id)


func _hex(c: Vector2, r: float) -> PackedVector2Array:
	var pts := PackedVector2Array()
	for i in 6:
		pts.append(c + Vector2.from_angle(PI / 6 + i * PI / 3) * r)
	return pts


func _draw() -> void:
	var c := Vector2(size.x * 0.5, 30)
	var r := 26.0 + (2.0 if _hover and not locked else 0.0)
	var font := get_theme_default_font()
	if selected:
		var glow := 0.35 + 0.25 * sin(_t * 4.0)
		draw_colored_polygon(_hex(c, r + 8), Color(Game.SUN, glow * 0.5))
	var fill := Game.PANEL if not locked else Color(0.06, 0.05, 0.12)
	if selected:
		fill = Game.SUN
	elif stars > 0:
		fill = Color("1d3a5c")
	draw_colored_polygon(_hex(c, r), fill)
	var outline := _hex(c, r)
	outline.append(outline[0])
	draw_polyline(outline, Game.MUTED if locked else (Game.SUN if selected else Game.CYAN), 2.5, true)
	if locked:		# padlock
		draw_rect(Rect2(c + Vector2(-8, -2), Vector2(16, 12)), Game.MUTED)
		draw_arc(c + Vector2(0, -3), 6, PI, TAU, 12, Game.MUTED, 2.5)
	else:
		var txt := str(number)
		var col := Game.SPACE if selected else Game.INK
		draw_string(font, c + Vector2(-20, 9), txt, HORIZONTAL_ALIGNMENT_CENTER, 40, 24, col)
	for i in 3:		# stars
		var p := Vector2(c.x - 16 + i * 16, 72)
		var pts := UIKit.star_points(p, 7, 3)
		draw_colored_polygon(pts, Game.SUN if i < stars else Color(1, 1, 1, 0.12))
