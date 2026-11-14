extends Control
## Twinkling star backdrop for the menus, drawn behind 3D (the menu Environments use BG_CANVAS).
## Menus only: on the sunlit surface, stars stay out of frame, as in real lunar photos.

@export var count := 220
var _stars: Array = []		# [pos (0..1), radius, phase, colour]
var _t := 0.0


func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	var rng := RandomNumberGenerator.new()
	rng.seed = 2026
	var tints := [Color(1, 1, 1), Color("bfe9ff"), Color("ffe9b0"), Color("ffc4f5")]
	for i in count:
		_stars.append([Vector2(rng.randf(), rng.randf()), rng.randf_range(0.6, 1.9), rng.randf() * TAU,
			tints[rng.randi() % tints.size()]])


func _process(delta: float) -> void:
	_t += delta
	queue_redraw()


func _draw() -> void:
	draw_rect(Rect2(Vector2.ZERO, size), Game.SPACE)
	# faint nebula wash
	draw_circle(size * Vector2(0.15, 0.2), size.x * 0.35, Color(0.45, 0.1, 0.6, 0.06))
	draw_circle(size * Vector2(0.85, 0.75), size.x * 0.3, Color(0.05, 0.4, 0.6, 0.05))
	for s: Array in _stars:
		var a := 0.45 + 0.55 * (0.5 + 0.5 * sin(_t * 1.7 + s[2]))
		var c: Color = s[3]
		c.a = a
		draw_circle(s[0] * size, s[1], c)
