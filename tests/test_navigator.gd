extends SceneTree
var failures := 0
func _initialize() -> void:
	call_deferred("run")
func check(ok: bool, message: String) -> void:
	if not ok:
		failures += 1
		printerr(message)
func run() -> void:
	var state: Node = root.get_node("Navigator")
	check(state.records.size() == 18, "six sites x three windows")
	check(state.cards.size() == 2, "two default comparison cards")
	var preview := 0
	for key: String in state.records:
		var record: Dictionary = state.records[key]
		var s: Dictionary = record.site.samples
		check(int(s.count) == 4321 and int(s.step_s) == 600, "sample completeness: " + key)
		for field: String in ["sun_az", "sun_el", "sun_radius", "earth_az", "earth_el", "earth_radius"]:
			check(s[field].size() == int(s.count), "series length: " + key + field)
		var card := {"key": key, "start": int(s.start_unix), "duration": 600}
		var assessment: Dictionary = state.assess(card)
		if not record.verified:
			preview += 1
			check(assessment.sun == "unknown" and assessment.earth == "unknown", "preview gate")
		check(assessment.power == "unknown" and assessment.radio == "unknown", "operational gates")
		card.start = int(s.start_unix) + 30*86400
		check(not state.assess(card).covered, "dataset endpoint cannot pass")
		card.start += 1
		check(state.sample(card, "sun_el") == null, "no extrapolation")
	check(preview == 16, "sixteen preview records")
	var saved: Dictionary = state.save_brief()
	state.set_card(0, state.cards[0].key, int(state.cards[0].start)+600, 600)
	check(saved.cards[0].start != state.cards[0].start, "immutable brief")
	check(state.cards[0].start == state.cards[1].start, "same time")
	state.same_time = false
	state.set_card(1, state.cards[0].key, int(state.cards[0].start)+600, 600)
	check(state.cards[1].start != state.cards[0].start, "same site independent date")
	print("Navigator checks failed: ", failures)
	quit(1 if failures else 0)
