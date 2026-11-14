extends Control
## DEBRIEF: what happened (from the data), the score counting up, the stars, and what to do next.

signal retry
signal next_mission
signal to_campaign

var mission: Dictionary
var site := ""
var result := {}				# Scoring.evaluate()
var score := {}				# category -> points (from the mission host)
var stars := 0
var bonus_met := false
var new_best := false
var what_if := ""


func _ready() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	var dim := ColorRect.new()
	dim.color = Color(0.02, 0.01, 0.06, 0.7)
	add_child(UIKit.full_rect(dim))
	var scroll := ScrollContainer.new()
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	add_child(UIKit.full_rect(scroll))
	var m := UIKit.margin(18)
	m.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	m.size_flags_vertical = Control.SIZE_EXPAND_FILL
	scroll.add_child(m)
	var center := CenterContainer.new()
	m.add_child(center)
	var card := UIKit.panel("card")
	card.custom_minimum_size.x = minf(640, get_viewport().get_visible_rect().size.x - 36)
	center.add_child(card)
	var v := UIKit.vbox(10)
	card.add_child(v)

	v.add_child(UIKit.label("MISSION %d · %s" % [mission.number, str(mission.title).to_upper()], 15, Game.MAGENTA))
	var head := UIKit.display("SAMPLE SECURED" if result.pass else "SUNLIGHT LOST", 40,
		Game.LIME if result.pass else Game.CORAL)
	v.add_child(head)
	var star_row := UIKit.stars(0, 3, 46)
	v.add_child(star_row)
	var story := UIKit.rich(_story(), 17)
	v.add_child(story)

	var rows := UIKit.vbox(4)
	v.add_child(rows)
	var labels := {"sunlight": "Sunlight held", "margin": "Spare sunlight bonus", "samples": "Samples delivered",
		"scans": "Rocks scanned", "precision": "Landing precision", "soft": "Soft touchdown", "forecast": "Forecast used"}
	var total := 0
	var delay := 0.4
	for k in ["sunlight", "margin", "samples", "scans", "precision", "soft", "forecast"]:
		var val: int = score.get(k, 0)
		if val == 0 and k in ["forecast", "margin"]:
			continue
		total += val
		var r := UIKit.hbox(8)
		rows.add_child(r)
		var name_l := UIKit.label(labels[k], 17, Game.INK)
		name_l.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		r.add_child(name_l)
		var vl := UIKit.label("0", 18, Game.CORAL if val < 0 else Game.SUN)
		r.add_child(vl)
		UIKit.pop_in(r, delay)
		UIKit.count_up(vl, val, 0.5, "%+d" if val < 0 else "%d", delay)
		delay += 0.25
	var tr := UIKit.hbox(8)
	v.add_child(tr)
	var tl := UIKit.display("TOTAL", 26, Game.INK)
	tl.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	tr.add_child(tl)
	var tv := UIKit.display("0", 30, Game.SUN)
	tr.add_child(tv)
	UIKit.count_up(tv, total, 1.0, "%d", delay)
	v.add_child(UIKit.label("PAR %d   ·   BONUS: %s %s" % [int(mission.par), str(mission.bonus.text),
		"(MET)" if bonus_met else "(MISSED)"], 14, Game.MUTED, true))
	if new_best:
		var nb := UIKit.label("NEW BEST!", 20, Game.MAGENTA)
		v.add_child(nb)
		UIKit.pop_in(nb, delay + 1.0)
		UIKit.pulse(nb, 0.4, 0.8)

	var btns := HFlowContainer.new()
	btns.add_theme_constant_override("h_separation", 10)
	btns.add_theme_constant_override("v_separation", 10)
	v.add_child(btns)
	var has_next := Campaign.next_after(mission.id) != "" and Campaign.unlocked(Campaign.next_after(mission.id))
	if has_next and stars > 0:
		btns.add_child(UIKit.button("NEXT MISSION  ▶", next_mission.emit, 20, "primary"))
	btns.add_child(UIKit.button("RETRY", retry.emit, 20, "" if (has_next and stars > 0) else "primary"))
	btns.add_child(UIKit.button("MISSIONS", to_campaign.emit, 18))
	UIKit.pop_in(card)

	# stars, one by one
	var tw := create_tween()
	tw.tween_interval(delay + 1.2)
	for i in stars:
		tw.tween_callback(func() -> void:
			star_row.set_meta("filled", i + 1)
			star_row.queue_redraw()
			Sfx.play("star", 1.0 + i * 0.15))
		tw.tween_interval(0.35)


func _story() -> String:
	var lines := PackedStringArray()
	var info := Texts.site_info(site)
	lines.append("[color=#9a9cc9]%s · touchdown %s[/color]" % [info.title, Mission.utc_label(result.touchdown)])
	if result.pass:
		lines.append("The whole Sun stayed above the skyline for all %d hours. Full sunlight lasted %s%s longer." % [
			int(mission.need_s / 3600), Scoring.duration_label(result.margin_s), " or more" if result.margin_open else ""])
	else:
		var ti: int = result.interruption
		var az := Mission.sample(site, "sun_az", ti)
		var el := Mission.sample(site, "sun_el", ti)
		var rad := Mission.sample(site, "sun_radius", ti)
		var sky := Mission.skyline(site, az)
		if result.sampled_s == 0 and el + rad < sky - 3.0:
			lines.append("It was night at touchdown: the Sun was %.0f° below the horizon." % absf(el))
		elif result.sampled_s == 0:
			lines.append("At touchdown the Sun was not clear of the ridge toward %03.0f° (terrain there stands at %.1f°)." % [
				az, sky])
		else:
			lines.append("After %s the Sun's lower edge slipped behind the terrain toward %03.0f°, where the skyline stands at %.1f°." % [
				Scoring.duration_label(result.sampled_s), az, sky])
	if what_if != "":
		lines.append("[color=#2ef2ff]" + what_if + "[/color]")
	return "\n".join(lines)
