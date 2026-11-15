extends RefCounted
## Navigator content inside the existing operations HUD, using its palette and controls.
var host: Node
var comparison_controls: Array[Dictionary] = []
const SITE_IDS := ["apollo-11", "apollo-17", "sl3", "site04", "site07", "site11"]
const WINDOW_LABELS := ["VIPER era", "Artemis IV era", "Artemis V era"]

func _init(scene: Node) -> void:
	host = scene
	Navigator.changed.connect(refresh_comparisons)
	host.tree_exiting.connect(func() -> void: Navigator.changed.disconnect(refresh_comparisons))

func refresh_comparisons() -> void:
	if host.phase != "compare":
		return
	for item: Dictionary in comparison_controls:
		if not is_instance_valid(item.evidence) or int(item.index) >= Navigator.cards.size():
			continue
		var card: Dictionary = Navigator.cards[item.index]
		item.evidence.text = card_text(card)
		item.utc.text = Time.get_datetime_string_from_unix_time(int(card.start))
		item.slider.set_value_no_signal(float(card.start))
	host.start = int(Navigator.cards[Navigator.active_index].start)
	host.at = float(host.start)
	host._refresh()

func sync_plan() -> void:
	var card: Dictionary = Navigator.cards[Navigator.active_index]
	Navigator.set_card(Navigator.active_index, card.key, int(host.start), int(card.duration))

func surface_available() -> bool:
	var card: Dictionary = Navigator.cards[Navigator.active_index]
	return bool(Navigator.records[card.key].verified) and Navigator.sample(card, "sun_el") != null

func training_available() -> bool:
	var card: Dictionary = Navigator.cards[Navigator.active_index]
	return surface_available() and Navigator.assess(card).covered and int(card.duration) == Operations.DURATION_S

func mission_assessment() -> Dictionary:
	var card: Dictionary = Navigator.cards[Navigator.active_index]
	if training_available():
		var assessment := Operations.assess(Mission.data, host.site, int(card.start), Game.mission_id, host.schedule)
		assessment["navigator_plan"] = card.duplicate(true)
		return assessment
	return {"state": "unknown", "scored": false, "site": Navigator.records[card.key].site.id,
		"start": card.start, "duration_s": card.duration, "schedule": host.schedule.duplicate(true),
		"navigator_plan": card.duplicate(true), "criteria": [Operations.criterion("Mission training assessment", "unknown",
		"Requires a covered six-hour plan from the original validated window. Exploration previews and other comparison durations cannot establish mission success.", Navigator.records[card.key].source)]}

func activate(index: int) -> void:
	Navigator.active_index = index
	var card: Dictionary = Navigator.cards[index]
	host.start = int(card.start)
	host.at = float(card.start)
	if Navigator.records[card.key].verified:
		host._change_site(str(Navigator.records[card.key].site.id))
	elif is_instance_valid(host.world):
		host.world.visible = false
	host._plan()

func prepare(phase: String, heading: String) -> void:
	host.previewing = false
	host.phase = phase
	if is_instance_valid(host.inspector):
		host.inspector.frozen = true
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	host._clear()
	host._text(heading, Game.SUN)

func compare() -> void:
	comparison_controls.clear()
	prepare("compare", "NAVIGATOR / COMPARE SITE AND DATE OPTIONS")
	host._text("Exploration-era planning scenario. Windows are hypothetical analysis choices, not NASA launch/landing dates or assigned sites.", Game.MUTED)
	var actions := HFlowContainer.new()
	host.body.add_child(actions)
	actions.add_child(host._button("RETURN TO PLAN", func() -> void: activate(Navigator.active_index)))
	actions.add_child(host._button("REVIEW", review))
	if Navigator.cards.size() < 4:
		actions.add_child(host._button("PIN OPTION", func() -> void:
			Navigator.cards.append(Navigator.cards[Navigator.active_index].duplicate(true))
			compare()))
	var same := CheckButton.new()
	same.text = "Same UTC start (location comparison)"
	same.button_pressed = Navigator.same_time
	same.toggled.connect(func(value: bool) -> void:
		Navigator.same_time = value
		if value:
			var active: Dictionary = Navigator.cards[Navigator.active_index]
			Navigator.set_card(Navigator.active_index, active.key, int(active.start), int(active.duration))
		compare())
	host.body.add_child(same)
	for index in Navigator.cards.size():
		build_card(index)

func build_card(index: int) -> void:
	var card: Dictionary = Navigator.cards[index]
	var panel := UIKit.panel("card")
	host.body.add_child(panel)
	var col := UIKit.vbox(8)
	var evidence := UIKit.label("",17,Game.INK,true)
	panel.add_child(col)
	col.add_child(UIKit.label("OPTION %d%s" % [index+1, " / ACTIVE MISSION PLAN" if index == Navigator.active_index else ""], 19, Game.SUN, true))
	var picker := OptionButton.new()
	picker.clip_text = true
	picker.custom_minimum_size.y = 44
	var keys: Array = []
	for w in Navigator.WINDOWS.size():
		for id: String in SITE_IDS:
			var key: String = Navigator.WINDOWS[w] + "/" + id
			keys.append(key)
			picker.add_item("%s / %s" % [WINDOW_LABELS[w], Navigator.records[key].site.name])
	picker.select(keys.find(card.key))
	picker.item_selected.connect(func(selected: int) -> void:
		# Preserve UTC so gaps and comparisons across dates remain explicit.
		Navigator.set_card(index, keys[selected], int(card.start), int(card.duration))
		if index == Navigator.active_index:
			activate(index)
		compare())
	col.add_child(picker)
	col.add_child(UIKit.label("UTC start (YYYY-MM-DDTHH:MM:SS); press Enter to apply",16,Game.MUTED,true))
	var utc := LineEdit.new()
	utc.text = Time.get_datetime_string_from_unix_time(int(card.start))
	utc.text_submitted.connect(func(value: String) -> void:
		var parsed := Time.get_unix_time_from_datetime_string(value.trim_suffix("Z"))
		if value.length() < 16 or not value.contains("T") or Time.get_datetime_string_from_unix_time(parsed).left(16) != value.left(16):
			utc.tooltip_text = "Invalid UTC. Use YYYY-MM-DDTHH:MM:SS."
			utc.text = Time.get_datetime_string_from_unix_time(int(card.start))
			return
		Navigator.set_card(index,card.key,parsed,int(card.duration))
		compare())
	col.add_child(utc)
	var duration := SpinBox.new()
	duration.min_value = 10
	duration.max_value = 1440
	duration.step = 10
	duration.value = float(card.duration)/60.0
	duration.suffix = "min comparison interval"
	duration.value_changed.connect(func(value: float) -> void:
		Navigator.set_card(index,card.key,int(card.start),int(value)*60)
		# Keep this control's focus; refresh its evidence only.
		evidence.text = card_text(card))
	col.add_child(duration)
	var samples: Dictionary = Navigator.records[card.key].site.samples
	var slider := HSlider.new()
	slider.min_value = float(samples.start_unix)
	slider.max_value = float(samples.start_unix)+(int(samples.count)-1)*int(samples.step_s)
	slider.step = 600
	slider.value = float(card.start)
	slider.value_changed.connect(func(value: float) -> void:
		Navigator.set_card(index,card.key,int(value),int(card.duration))
		utc.text = Time.get_datetime_string_from_unix_time(int(value))
		evidence.text = card_text(card))
	col.add_child(slider)
	var actions := HFlowContainer.new()
	col.add_child(actions)
	actions.add_child(host._button("JUMP TO WINDOW", func() -> void:
		Navigator.set_card(index,card.key,int(samples.start_unix),int(card.duration))
		compare()))
	actions.add_child(host._button("USE PLAN / EXPLORE", func() -> void: activate(index)))
	if Navigator.cards.size() > 2:
		actions.add_child(host._button("UNPIN", func() -> void:
			Navigator.cards.remove_at(index)
			Navigator.active_index = mini(Navigator.active_index,Navigator.cards.size()-1)
			compare()))
	evidence.text = card_text(card)
	evidence.name = "Evidence"
	col.add_child(evidence)
	comparison_controls.append({"index": index, "evidence": evidence, "utc": utc, "slider": slider})
	# Bind after children exist; closures above access this column's evidence.

func angle(card: Dictionary, field: String) -> String:
	var value: Variant = Navigator.sample(card,field)
	return "unavailable" if value == null else "%.1f deg" % float(value)

func card_text(card: Dictionary) -> String:
	var record: Dictionary = Navigator.records[card.key]
	var site: Dictionary = record.site
	var result: Dictionary = Navigator.assess(card)
	var samples: Dictionary = site.samples
	var text := "%s / %s\n%.4f deg latitude / %.4f deg east longitude\n%s\n%s to %s\nCoverage: %s to %s\n" % [site.name, "historical landing" if str(site.id).begins_with("apollo") else "study point (not approved landing site)",site.lat,site.lon,result.status,Mission.utc_label(card.start),Mission.utc_label(int(card.start)+int(card.duration)),Mission.utc_label(samples.start_unix),Mission.utc_label(int(samples.start_unix)+(int(samples.count)-1)*int(samples.step_s))]
	text += "Sun az/el: %s / %s; Earth az/el: %s / %s\nFull-disc sunlight: %s; Earth-center geometry: %s\n" % [angle(card,"sun_az"),angle(card,"sun_el"),angle(card,"earth_az"),angle(card,"earth_el"),result.sun,result.earth]
	text += "Full-disc sunlight in interval: %s\n" % (Scoring.duration_label(result.full_s) if result.has("full_s") else "unknown")
	text += "UNAVAILABLE: incomplete coverage or invalid interval.\n" if not result.covered else ""
	text += "Landing hazards / electrical endurance / thermal survival / station radio / mission feasibility: UNKNOWN\n"
	text += str(result.uncertainty)+"\n"
	text += "Future terrain-horizon events: unknown / outside validated coverage\n" if result.events.is_empty() else "\n".join(result.events)+"\n"
	text += "Coordinate source: %s\nTerrain: %s\nDataset: %s\nSHA-256: %s" % [site.coordinate_source,site.terrain_source,result.source,result.version]
	return text

func review(saved: Dictionary = {}) -> void:
	prepare("review", "NAVIGATOR / CURRENT COMPARISON" if saved.is_empty() else "NAVIGATOR / SAVED ATTEMPT (CURRENT PLAN UNCHANGED)")
	var actions := HFlowContainer.new()
	host.body.add_child(actions)
	actions.add_child(host._button("RETURN TO PLAN", func() -> void: activate(Navigator.active_index)))
	actions.add_child(host._button("COMPARE", compare))
	if saved.is_empty():
		actions.add_child(host._button("SAVE SESSION BRIEF", func() -> void:
			var summaries: Array = []
			for card: Dictionary in Navigator.cards:
				summaries.append(card_text(card))
			Navigator.save_brief(summaries)
			review()))
	var cards: Array = Navigator.cards if saved.is_empty() else saved.cards
	for i in cards.size():
		var text := card_text(cards[i]) if saved.is_empty() else (str(saved.summaries[i]) if i < saved.summaries.size() else JSON.stringify({"input": saved.cards[i], "evidence": saved.results[i]}, "  "))
		host._text(text)
		host.body.add_child(UIKit.rich("[url=%s]SITE COORDINATE SOURCE[/url]" % Navigator.records[cards[i].key].site.coordinate_source,16))
	host._text("SESSION ATTEMPTS / cleared when the application closes",Game.CYAN)
	for i in Navigator.briefs.size():
		host.body.add_child(host._button("OPEN ATTEMPT %d" % (i+1), func() -> void: review(Navigator.briefs[i])))
