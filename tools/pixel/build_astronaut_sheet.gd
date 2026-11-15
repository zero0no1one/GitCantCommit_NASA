extends SceneTree
## Builds the pixel astronaut's sprite sheet from the PixelLab rotations in assets/pixel/astronaut/source/.
## The idle and walk frames are drawn here by moving the source's own pixels (no AI, no new colours).
##
## Run:  godot --headless --path . --script res://tools/pixel/build_astronaut_sheet.gd
## Sheet: one 64x64 cell per frame. Rows: south, east, north, west. Columns: see COLS.

const SRC := "res://assets/pixel/astronaut/source/%s.png"
const OUT := "res://assets/pixel/astronaut/astronaut_sheet.png"
const PREVIEW_ARG := "--preview"		# also write an enlarged preview to the path after this flag
const CELL := 64
const COLS := ["idle0", "idle1", "walk0", "walk1", "walk2", "walk3"]
const ROWS := ["south", "east", "north", "west"]

## Front and back views: the legs are separate below `top`; `split` is the first column of the right leg.
const FRONT := {"south": {"top": 51, "split": 31}, "north": {"top": 52, "split": 32}}
## Side view: legs below `top`. For each leg row, the first column that belongs to the far leg.
const SIDE_TOP := 52
const SIDE_SPLIT := {52: 35, 53: 36, 54: 32, 55: 33, 56: 36, 57: 37, 58: 37, 59: 99, 60: 99}
const STRIDE := 3			# side view: how far the feet reach forward/back, in pixels
const LIFT := 2				# front/back views: how high the stepping foot lifts


func _init() -> void:
	var sheet := Image.create(CELL * COLS.size(), CELL * ROWS.size(), false, Image.FORMAT_RGBA8)
	for r in ROWS.size():
		var frames: Array[Image] = _frames(ROWS[r])
		for c in frames.size():
			sheet.blit_rect(frames[c], Rect2i(0, 0, CELL, CELL), Vector2i(c * CELL, r * CELL))
	var err := sheet.save_png(ProjectSettings.globalize_path(OUT))
	print("wrote %s (%dx%d): %s" % [OUT, sheet.get_width(), sheet.get_height(), error_string(err)])
	var args := OS.get_cmdline_user_args()
	var at := args.find(PREVIEW_ARG)
	if at >= 0 and at + 1 < args.size():
		_preview(sheet, args[at + 1])
	quit()


func _frames(dir: String) -> Array[Image]:
	if dir == "west":		# west is the east walk mirrored, so both sides move identically
		var out: Array[Image] = []
		for f: Image in _frames("east"):
			f.flip_x()
			out.append(f)
		return out
	var src := Image.load_from_file(ProjectSettings.globalize_path(SRC % dir))
	src.convert(Image.FORMAT_RGBA8)
	if FRONT.has(dir):
		return _front_frames(src, FRONT[dir].top, FRONT[dir].split)
	return _side_frames(src)


# ---------------------------------------------------------------- front / back

## Idle breathes (body sinks 1 px). The walk alternates lifting each foot; the body sinks on the passing frames.
func _front_frames(src: Image, top: int, split: int) -> Array[Image]:
	var body := _mask(src, func(x: int, y: int) -> bool: return y < top)
	var left := _mask(src, func(x: int, y: int) -> bool: return y >= top and x < split)
	var right := _mask(src, func(x: int, y: int) -> bool: return y >= top and x >= split)
	var out: Array[Image] = []
	# [body dy, left leg dy, right leg dy]
	for p: Array in [[0, 0, 0], [1, 0, 0], [0, -LIFT, 0], [1, 0, 0], [0, 0, -LIFT], [1, 0, 0]]:
		var img := _blank()
		_stamp(img, left, Vector2i(0, p[1]))
		_stamp(img, right, Vector2i(0, p[2]))
		_stamp(img, body, Vector2i(0, p[0]))		# body last: a lifted leg tucks under the hips
		out.append(img)
	return out


# ---------------------------------------------------------------- side

## The near boot is cut from the source. The far boot is the same shape one shade darker, so no hidden pixels
## are needed when the legs open. Boots move rigidly and tuck under the hips; the body sinks 1 px at each
## contact (legs apart) and the swinging boot lifts as it passes.
func _side_frames(src: Image) -> Array[Image]:
	var body := _mask(src, func(x: int, y: int) -> bool: return y < SIDE_TOP)
	var near := _mask(src, func(x: int, y: int) -> bool: return y >= SIDE_TOP and x < int(SIDE_SPLIT.get(y, 99)))
	var far := _shade(near, src)
	var out: Array[Image] = [src.duplicate(), _blank()]
	_stamp(out[1], _mask(src, func(x: int, y: int) -> bool: return y >= SIDE_TOP), Vector2i.ZERO)
	_stamp(out[1], body, Vector2i(0, 1))
	# [body dy, near boot dx, near dy, far boot dx, far dy]
	for p: Array in [[1, STRIDE, 0, -STRIDE, 0], [0, 0, 0, 0, -LIFT], [1, -STRIDE, 0, STRIDE, 0], [0, 0, -LIFT, 0, 0]]:
		var img := _blank()
		_stamp(img, far, Vector2i(p[3], p[4]))
		_stamp(img, near, Vector2i(p[1], p[2]))
		_stamp(img, body, Vector2i(0, p[0]))
		out.append(img)
	return out


# ---------------------------------------------------------------- pixel helpers

func _blank() -> Image:
	return Image.create(CELL, CELL, false, Image.FORMAT_RGBA8)


## The opaque pixels of `src` for which keep(x, y) is true, as {Vector2i: Color}.
func _mask(src: Image, keep: Callable) -> Dictionary:
	var part := {}
	for y in CELL:
		for x in CELL:
			var c := src.get_pixel(x, y)
			if c.a > 0.5 and keep.call(x, y):
				part[Vector2i(x, y)] = c
	return part


func _stamp(img: Image, part: Dictionary, offset: Vector2i) -> void:
	for at: Vector2i in part:
		_put(img, at + offset, part[at])


func _put(img: Image, at: Vector2i, c: Color) -> void:
	if at.x >= 0 and at.y >= 0 and at.x < CELL and at.y < CELL:
		img.set_pixel(at.x, at.y, c)


## A darker copy of `part`, snapped to colours already in `src` so the palette stays the same.
func _shade(part: Dictionary, src: Image) -> Dictionary:
	var palette: Array[Color] = []
	for y in CELL:
		for x in CELL:
			var c := src.get_pixel(x, y)
			if c.a > 0.5 and not palette.has(c):
				palette.append(c)
	var out := {}
	for at: Vector2i in part:
		var want: Color = part[at].darkened(0.3)
		var best: Color = want
		var best_d := INF
		for c: Color in palette:
			var d := Vector3(c.r - want.r, c.g - want.g, c.b - want.b).length_squared()
			if d < best_d:
				best_d = d
				best = c
		out[at] = best
	return out


## A 6x enlargement on a grey backdrop, for reviewing the frames by eye.
func _preview(sheet: Image, path: String) -> void:
	var big := sheet.duplicate() as Image
	big.resize(sheet.get_width() * 6, sheet.get_height() * 6, Image.INTERPOLATE_NEAREST)
	var bg := Image.create(big.get_width(), big.get_height(), false, Image.FORMAT_RGBA8)
	bg.fill(Color("3a3f52"))
	bg.blend_rect(big, Rect2i(Vector2i.ZERO, big.get_size()), Vector2i.ZERO)
	print("preview: ", error_string(bg.save_png(path)))
