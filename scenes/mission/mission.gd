extends Node3D
## One mission: BRIEF → PLAN → DESCENT → HOLD THE LIGHT → DEBRIEF, on one loaded site.
## Pass/fail comes only from Scoring (the real data); skill adds points and stars:
##   star 1 = the plan holds the light, star 2 = the bonus goal, star 3 = total ≥ par (2 and 3 need star 1).

const PlanPhase := preload("res://scenes/mission/plan_phase.gd")
const DescentPhase := preload("res://scenes/mission/descent_phase.gd")
const HoldPhase := preload("res://scenes/mission/hold_phase.gd")
const Debrief := preload("res://scenes/mission/debrief.gd")

var mission: Dictionary
var site := ""
var world: SiteWorld
var phase: Node
var touchdown := 0
var score := {}
var landing := {}
var forecast_used := false
var paused: bool:
	get:
		return get_tree().paused

var _fx_layer: CanvasLayer
var _popups: VBoxContainer
var _banner: Label
var _pause_ui: Control


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS		# so the pause menu works; world and phases stay pausable
	var id := Game.mission_id if Campaign.by_id.has(Game.mission_id) else str(Campaign.missions[0].id)
	Game.mission_id = id
	mission = Campaign.by_id[id]
	site = mission.sites[0]
	touchdown = int(mission.window.start)
	_build_fx_layer()
	_make_world(site)
	_show_brief()
	Sfx.music("mission")


func _make_world(sid: String) -> void:
	if world:
		world.queue_free()
	site = sid
	world = SiteWorld.new(sid)
	world.process_mode = Node.PROCESS_MODE_PAUSABLE
	add_child(world)
	world.set_time(touchdown)


func _start_phase(p: Node) -> void:
	if is_instance_valid(phase):
		phase.queue_free()
	phase = p
	p.process_mode = Node.PROCESS_MODE_PAUSABLE
	add_child(p)


# ---------------------------------------------------------------- flow

func _show_brief() -> void:
	# a plan camera behind the card, so the site is visible while reading
	_go_plan(false)
	var dim := ColorRect.new()
	dim.color = Color(0.02, 0.01, 0.06, 0.55)
	_fx_layer.add_child(UIKit.full_rect(dim))
	var center := CenterContainer.new()
	dim.add_child(UIKit.full_rect(center))
	var card := UIKit.panel("card")
	card.custom_minimum_size.x = minf(600, get_viewport().get_visible_rect().size.x - 36)
	center.add_child(card)
	var v := UIKit.vbox(10)
	card.add_child(v)
	v.add_child(UIKit.label("MISSION %d" % mission.number, 16, Game.MAGENTA))
	v.add_child(UIKit.display(str(mission.title).to_upper(), 38, Game.SUN))
	v.add_child(UIKit.label(str(mission.brief), 18, Game.INK, true))
	var goals := UIKit.vbox(4)
	v.add_child(goals)
	for g in ["Hold %d h of unbroken sunlight" % int(mission.need_s / 3600), "Bonus: " + str(mission.bonus.text),
			"Par: %d points" % int(mission.par)]:
		goals.add_child(UIKit.label("▶  " + g, 16, Game.CYAN, true))
	var go := UIKit.button("START PLANNING  ▶", func() -> void:
		Sfx.play("confirm")
		dim.queue_free(), 24, "primary")
	v.add_child(go)
	UIKit.pop_in(card)


func _go_plan(_from_brief := true) -> void:
	var p := PlanPhase.new()
	p.setup(self, mission, world, touchdown)
	p.committed.connect(_on_commit)
	p.site_switch.connect(_on_site_switch)
	_start_phase(p)


func _on_site_switch(sid: String) -> void:
	if sid == site:
		return
	Sfx.play("confirm")
	_make_world(sid)
	_go_plan()


func _on_commit(t: int, forecast: bool) -> void:
	touchdown = t
	forecast_used = forecast
	world.set_time(t)
	banner("DESCENT", Game.CYAN)
	var d := DescentPhase.new()
	d.setup(self, world)
	d.landed.connect(_on_landed)
	_start_phase(d)


func _on_landed(info: Dictionary) -> void:
	landing = info
	score = {"precision": int(info.precision), "soft": int(info.soft), "samples": 0, "scans": 0}
	if forecast_used:
		score.forecast = -PlanPhase.FORECAST_COST
	var h := HoldPhase.new()
	h.setup(self, world, mission, touchdown, Vector3(info.x, info.ground, 0))
	h.finished.connect(_on_hold_done)
	_start_phase(h)


func _on_hold_done(_stats: Dictionary) -> void:
	var r := Game.evaluate(site, touchdown, int(mission.need_s))
	if r.pass:
		score.sunlight = 1000
		score.margin = int(minf(float(r.margin_s) / 3600.0, 24.0) * 25.0)
	else:
		score.sunlight = int(400.0 * float(r.sampled_s) / float(mission.need_s))
	var total := 0
	for k in score:
		total += int(score[k])
	var bonus := _bonus_met(r)
	var stars := 0
	if r.pass:
		stars = 1 + (1 if bonus else 0) + (1 if total >= int(mission.par) else 0)
	var best := Campaign.record(mission.id, stars, maxi(total, 0))
	var d := Debrief.new()
	d.mission = mission
	d.site = site
	d.result = r
	d.score = score
	d.stars = stars
	d.bonus_met = bonus
	d.new_best = best and total > 0
	d.what_if = _what_if(r)
	d.retry.connect(func() -> void: Game.play_mission(mission.id))
	d.next_mission.connect(func() -> void: Game.play_mission(Campaign.next_after(mission.id)))
	d.to_campaign.connect(func() -> void: Game.goto("campaign"))
	_fx_layer.add_child(d)


func _bonus_met(r: Dictionary) -> bool:
	if not r.pass:
		return false
	var b: Dictionary = mission.bonus
	match str(b.type):
		"margin":
			return int(r.margin_s) >= int(b.hours) * 3600
		"touchdown_before":
			return touchdown <= int(b.unix)
		"earth_up":
			return Scoring.find(Mission.sites[site].intervals.earth_up, touchdown) >= 0
		"landing":
			return not landing.get("auto", true) and float(landing.get("offset_m", 99.0)) <= float(b.offset_m)
	return false


## "Touchdown 2 h 20 m earlier would have failed" (nearest opposite outcome within 3 days, same site), or for a
## fixed launch time, what the other site would have done.
func _what_if(r: Dictionary) -> String:
	var need := int(mission.need_s)
	if mission.fixed_touchdown:
		for other: String in mission.sites:
			if other != site:
				var o := Game.evaluate(other, touchdown, need)
				return "At the same moment, %s would have %s." % [Texts.site_info(other).title, "passed" if o.pass else "failed"]
		return ""
	var w: Dictionary = Mission.data.window
	for k in range(1, 3 * 144 + 1):
		for sgn in [1, -1]:
			var tt: int = touchdown + sgn * k * 600
			if tt < int(w.touchdown_min_unix) or tt + need > int(w.end_unix):
				continue
			if Game.evaluate(site, tt, need).pass != bool(r.pass):
				return "Small changes matter: touchdown %s %s would have %s." % [Scoring.duration_label(k * 600),
					"later" if sgn > 0 else "earlier", "failed" if r.pass else "passed"]
	return ""


# ---------------------------------------------------------------- feedback: popups, banners, score

func _build_fx_layer() -> void:
	_fx_layer = CanvasLayer.new()
	_fx_layer.layer = 10
	add_child(_fx_layer)
	var holder := UIKit.full_rect(Control.new())
	holder.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_fx_layer.add_child(holder)
	_banner = UIKit.display("", 52, Game.SUN)
	_banner.set_anchors_and_offsets_preset(Control.PRESET_CENTER_TOP)
	_banner.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_banner.position.y = 120
	_banner.modulate.a = 0.0
	holder.add_child(_banner)
	_popups = UIKit.vbox(4)
	_popups.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_popups.set_anchors_and_offsets_preset(Control.PRESET_CENTER)
	_popups.alignment = BoxContainer.ALIGNMENT_CENTER
	holder.add_child(_popups)


func add_score(key: String, pts: int) -> void:
	score[key] = int(score.get(key, 0)) + pts


func popup(text: String, c: Color) -> void:
	var l := UIKit.display(text, 26, c)
	l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_popups.add_child(l)
	UIKit.pop_in(l)
	var tw := l.create_tween()
	tw.tween_interval(1.1)
	tw.tween_property(l, "modulate:a", 0.0, 0.4)
	tw.tween_callback(l.queue_free)


func banner(text: String, c: Color) -> void:
	_banner.text = text
	_banner.add_theme_color_override("font_color", c)
	_banner.size = Vector2.ZERO
	_banner.reset_size()
	_banner.position.x = (get_viewport().get_visible_rect().size.x - _banner.size.x) * 0.5
	var tw := _banner.create_tween()
	_banner.modulate.a = 0.0
	_banner.scale = Vector2(1.3, 1.3)
	_banner.pivot_offset = _banner.size * 0.5
	tw.tween_property(_banner, "modulate:a", 1.0, 0.15)
	tw.parallel().tween_property(_banner, "scale", Vector2.ONE, 0.3).set_trans(Tween.TRANS_BACK)
	tw.tween_interval(1.4)
	tw.tween_property(_banner, "modulate:a", 0.0, 0.4)


# ---------------------------------------------------------------- pause

func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("pause"):
		toggle_pause()


func toggle_pause() -> void:
	if paused:
		get_tree().paused = false
		if _pause_ui:
			_pause_ui.queue_free()
		return
	get_tree().paused = true
	Sfx.loop("thrust", false)
	_pause_ui = ColorRect.new()
	(_pause_ui as ColorRect).color = Color(0.02, 0.01, 0.06, 0.75)
	_fx_layer.add_child(UIKit.full_rect(_pause_ui))
	var center := CenterContainer.new()
	_pause_ui.add_child(UIKit.full_rect(center))
	var card := UIKit.panel("card")
	center.add_child(card)
	var v := UIKit.vbox(10)
	card.add_child(v)
	v.add_child(UIKit.display("PAUSED", 40, Game.SUN))
	var items := [
		["RESUME", toggle_pause, "primary"],
		["RESTART MISSION", func() -> void:
			get_tree().paused = false
			Game.play_mission(mission.id), ""],
		["HOW TO PLAY", func() -> void: UIKit.overlay(_fx_layer, "HOW TO PLAY", Texts.help()), ""],
		["SCIENCE LOG", func() -> void: UIKit.overlay(_fx_layer, "SCIENCE LOG", Texts.science_log()), ""],
		["SOUND ON / OFF", func() -> void: Sfx.set_muted(not Sfx.muted), ""],
		["QUIT TO MISSIONS", func() -> void:
			get_tree().paused = false
			Game.goto("campaign"), "danger"],
	]
	for it in items:
		var b := UIKit.button(it[0], it[1], 20, it[2])
		b.custom_minimum_size.x = 300
		v.add_child(b)
	UIKit.pop_in(card)
