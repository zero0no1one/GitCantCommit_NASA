extends Control
## The Sunlight Clock: a ring that fills with the hours of unbroken full-disc sunlight ahead of the chosen
## touchdown, with the mission's requirement marked. Gold while short, lime once the requirement is met.

var need_s := 21600
var clear_s := 0			# unbroken sunlight from touchdown (0 if the Sun is not clear at touchdown)
var open_end := false		# sunlight runs past the end of the data
var wait_s := -1			# when dark: time until full sunlight returns (-1 if not in the data)
var _shown := 0.0
var _t := 0.0


func _ready() -> void:
	custom_minimum_size = Vector2(150, 150)
	mouse_filter = Control.MOUSE_FILTER_IGNORE


func _process(delta: float) -> void:
	_t += delta
	_shown = lerpf(_shown, float(clear_s), minf(1.0, delta * 10.0))
	queue_redraw()


func _draw() -> void:
	var c := size * 0.5
	var r := minf(size.x, size.y) * 0.5 - 10
	var font := get_theme_default_font()
	var full := float(need_s) * 1.5			# the ring shows up to 1.5x the requirement
	var ok := clear_s >= need_s
	draw_circle(c, r + 8, Color(0, 0, 0, 0.45))
	draw_arc(c, r, 0, TAU, 64, Game.PANEL, 12, true)
	var frac := clampf(_shown / full, 0.0, 1.0)
	var col := Game.LIME if ok else Game.SUN
	if frac > 0.0:
		draw_arc(c, r, -PI / 2, -PI / 2 + TAU * frac, 64, col, 12, true)
	# requirement mark
	var need_a := -PI / 2 + TAU * float(need_s) / full
	draw_line(c + Vector2.from_angle(need_a) * (r - 12), c + Vector2.from_angle(need_a) * (r + 12), Game.INK, 3.0, true)
	if ok:
		draw_arc(c, r + 10, 0, TAU, 64, Color(Game.LIME, 0.25 + 0.2 * sin(_t * 5.0)), 4, true)
	var big := ""
	var small := ""
	if clear_s <= 0:
		big = "DARK"
		small = ("SUN IN " + Scoring.duration_label(wait_s)) if wait_s >= 0 else "NO SUN AHEAD"
		col = Game.CORAL
	else:
		big = _short(clear_s) + ("+" if open_end else "")
		small = "OF LIGHT · NEED %dH" % int(need_s / 3600)
	draw_string(font, c + Vector2(-r, 6), big, HORIZONTAL_ALIGNMENT_CENTER, r * 2, 30, col)
	draw_string(font, c + Vector2(-r, 28), small, HORIZONTAL_ALIGNMENT_CENTER, r * 2, 11, Game.MUTED)


static func _short(s: int) -> String:
	var m := int(s / 60.0)
	if m >= 48 * 60:
		return "%dD" % (m / 1440)
	return "%dH%02d" % [m / 60, m % 60]
