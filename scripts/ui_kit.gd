class_name UIKit
## Helpers for the code-built screens. Styling lives in ui/theme.tres (type variations PrimaryButton,
## DangerButton, DisplayLabel, CardPanel, HUDPanel); colours in the Game palette.
## The fonts (Chakra Petch, Russo One) have no ✓ ✗ ★ glyphs: stars and ticks are drawn as shapes here.


static func label(text: String, size := 20, color := Color("e9f1ff"), wrap := false) -> Label:
	var l := Label.new()
	l.text = text
	l.add_theme_font_size_override("font_size", size)
	l.add_theme_color_override("font_color", color)
	if wrap:
		l.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		l.custom_minimum_size.x = 120
	return l


## Big title text in the display font (Russo One) with a heavy outline.
static func display(text: String, size := 48, color := Color("ffd23f")) -> Label:
	var l := Label.new()
	l.theme_type_variation = &"DisplayLabel"
	l.text = text
	l.add_theme_font_size_override("font_size", size)
	l.add_theme_color_override("font_color", color)
	return l


static func rich(bbcode: String, size := 18) -> RichTextLabel:
	var r := RichTextLabel.new()
	r.bbcode_enabled = true
	r.fit_content = true
	r.scroll_active = false
	r.text = bbcode
	for k in ["normal_font_size", "bold_font_size", "italics_font_size"]:
		r.add_theme_font_size_override(k, size)
	r.meta_clicked.connect(func(meta: Variant) -> void: OS.shell_open(str(meta)))
	return r


## kind: "" (outline), "primary" (yellow), "danger" (coral).
static func button(text: String, on_press: Callable, size := 20, kind := "") -> Button:
	var b := Button.new()
	b.text = text
	b.add_theme_font_size_override("font_size", size)
	b.focus_mode = Control.FOCUS_NONE
	if kind == "primary":
		b.theme_type_variation = &"PrimaryButton"
	elif kind == "danger":
		b.theme_type_variation = &"DangerButton"
	b.pressed.connect(func() -> void:
		Sfx.play("click")
		press_bounce(b))
	b.pressed.connect(on_press)
	b.mouse_entered.connect(func() -> void: Sfx.play("hover"))
	return b


static func panel(kind := "") -> PanelContainer:
	var p := PanelContainer.new()
	if kind == "card":
		p.theme_type_variation = &"CardPanel"
	elif kind == "hud":
		p.theme_type_variation = &"HUDPanel"
	return p


static func vbox(sep := 10) -> VBoxContainer:
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", sep)
	return v


static func hbox(sep := 10) -> HBoxContainer:
	var h := HBoxContainer.new()
	h.add_theme_constant_override("separation", sep)
	return h


static func margin(m := 24) -> MarginContainer:
	var c := MarginContainer.new()
	for side in ["left", "right", "top", "bottom"]:
		c.add_theme_constant_override("margin_" + side, m)
	return c


static func spacer(vertical := true) -> Control:
	var s := Control.new()
	s.mouse_filter = Control.MOUSE_FILTER_IGNORE
	if vertical:
		s.size_flags_vertical = Control.SIZE_EXPAND_FILL
	else:
		s.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	return s


static func full_rect(c: Control) -> Control:
	c.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	return c


# ---------------------------------------------------------------- motion

## Pop in (scale up from 85% + fade) after `delay` seconds. Uses scale, which containers leave alone.
static func pop_in(c: Control, delay := 0.0) -> void:
	c.modulate.a = 0.0
	c.scale = Vector2(0.85, 0.85)
	var tw := c.create_tween().set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
	tw.tween_interval(delay)
	tw.tween_callback(func() -> void: c.pivot_offset = c.size * 0.5)
	tw.tween_property(c, "modulate:a", 1.0, 0.2)
	tw.parallel().tween_property(c, "scale", Vector2.ONE, 0.35)


static func press_bounce(c: Control) -> void:
	c.pivot_offset = c.size * 0.5
	var tw := c.create_tween().set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
	tw.tween_property(c, "scale", Vector2(0.93, 0.93), 0.05)
	tw.tween_property(c, "scale", Vector2.ONE, 0.18)


## Gentle endless pulse (for "press start" style prompts).
static func pulse(c: CanvasItem, lo := 0.55, period := 1.2) -> void:
	var tw := c.create_tween().set_loops()
	tw.tween_property(c, "modulate:a", lo, period * 0.5).set_trans(Tween.TRANS_SINE)
	tw.tween_property(c, "modulate:a", 1.0, period * 0.5).set_trans(Tween.TRANS_SINE)


## Count a label up from 0 to `to`, formatting with `fmt` (one %d or %s).
static func count_up(l: Label, to: int, duration := 0.8, fmt := "%d", delay := 0.0) -> Tween:
	var tw := l.create_tween()
	tw.tween_interval(delay)
	tw.tween_method(func(v: float) -> void: l.text = fmt % int(round(v)), 0.0, float(to), duration) \
		.set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_OUT)
	return tw


# ---------------------------------------------------------------- icons

static func star_points(c: Vector2, r_out: float, r_in: float) -> PackedVector2Array:
	var pts := PackedVector2Array()
	for i in 10:
		var a := -PI / 2 + i * PI / 5
		pts.append(c + Vector2.from_angle(a) * (r_out if i % 2 == 0 else r_in))
	return pts


## A row of `total` stars, `filled` of them lit. Call set_meta("filled", n) + queue_redraw() to change.
static func stars(filled: int, total := 3, size := 28.0) -> Control:
	var c := Control.new()
	c.custom_minimum_size = Vector2(total * size * 1.15, size)
	c.mouse_filter = Control.MOUSE_FILTER_IGNORE
	c.set_meta("filled", filled)
	c.draw.connect(func() -> void:
		var n: int = c.get_meta("filled")
		for i in total:
			var ctr := Vector2(size * 0.5 + i * size * 1.15, size * 0.52)
			var pts := star_points(ctr, size * 0.5, size * 0.22)
			if i < n:
				c.draw_colored_polygon(pts, Color("ffd23f"))
			else:
				c.draw_colored_polygon(pts, Color(1, 1, 1, 0.08))
			pts.append(pts[0])
			c.draw_polyline(pts, Color("ffd23f") if i < n else Color(0.6, 0.6, 0.8, 0.6), 1.5, true))
	return c


static func tick(ok: bool, size := 22.0) -> Control:
	var c := Control.new()
	c.custom_minimum_size = Vector2(size, size)
	c.mouse_filter = Control.MOUSE_FILTER_IGNORE
	c.draw.connect(func() -> void:
		var col := Color("7dff6a") if ok else Color("ff5a36")
		c.draw_circle(Vector2(size, size) * 0.5, size * 0.5, col * Color(1, 1, 1, 0.2))
		if ok:
			c.draw_polyline(PackedVector2Array([Vector2(0.25, 0.52) * size, Vector2(0.43, 0.7) * size,
				Vector2(0.76, 0.3) * size]), col, 3.0, true)
		else:
			c.draw_line(Vector2(0.3, 0.3) * size, Vector2(0.7, 0.7) * size, col, 3.0, true)
			c.draw_line(Vector2(0.7, 0.3) * size, Vector2(0.3, 0.7) * size, col, 3.0, true))
	return c


# ---------------------------------------------------------------- overlays

## Modal card over a dimmed screen with a title, scrolling rich text and a Close button.
static func overlay(parent: Node, title: String, bbcode: String) -> Control:
	var dim := ColorRect.new()
	dim.color = Color(0.02, 0.01, 0.06, 0.75)
	full_rect(dim)
	parent.add_child(dim)
	var m := margin(20)
	full_rect(m)
	dim.add_child(m)
	var center := CenterContainer.new()
	m.add_child(center)
	var p := panel("card")
	var vp := parent.get_viewport().get_visible_rect().size
	p.custom_minimum_size = Vector2(min(660, vp.x - 40), 0)
	center.add_child(p)
	var v := vbox(14)
	p.add_child(v)
	v.add_child(display(title, 30, Color("ffd23f")))
	var scroll := ScrollContainer.new()
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	scroll.custom_minimum_size.y = min(440, vp.y - 240)
	v.add_child(scroll)
	var body := rich(bbcode, 18)
	body.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	scroll.add_child(body)
	var close := button("CLOSE", dim.queue_free, 20, "primary")
	close.size_flags_horizontal = Control.SIZE_SHRINK_END
	v.add_child(close)
	pop_in(p)
	return dim
