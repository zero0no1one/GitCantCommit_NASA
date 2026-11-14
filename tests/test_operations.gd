extends SceneTree

const Ops := preload("res://scripts/operations.gd")
var failed := 0
var checks := 0

func _initialize() -> void:
	if "--verify-failure-exit" in OS.get_cmdline_user_args():
		check(false, "Intentional failure to verify runner exit status")
	if _run() != true:
		failed += 1
	print("test_operations: %d checks, %d failed" % [checks, failed])
	quit(1 if failed else 0)

func check(ok: bool, message: String) -> void:
	checks += 1
	if not ok:
		failed += 1
		printerr(message)

func _run() -> bool:
	var data: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://data/mission.json"))
	var schedule: Array = [{"activity": "Observation request", "duration_s": 7200},
		{"activity": "Telemetry request", "duration_s": 7200}, {"activity": "Standby request", "duration_s": 7200}]
	var end := int(data.sites[0].intervals.sun_full[0][1])
	var start := end - 10800
	var sunset := Ops.assess(data, "apollo-11", start, "sunset-operations", schedule)
	check(sunset.state == "unknown", "Sunset cannot establish endurance without flight evidence")
	check(sunset.criteria[2].state == "met", "Six-hour interval straddles full-sun boundary")
	check(not sunset.scored, "No science score for unvalidated model")
	check(Ops.assess(data, "apollo-11", start, "earth-link", schedule).state == "unknown", "Earth geometry cannot certify a link")
	check(Ops.assess(data, "apollo-11", end - 30000, "sunset-operations", schedule).state == "violated", "No interruption violates training objective")
	check(not Ops.covered(data, "apollo-11", int(data.window.start_unix) - 1), "Never clamp an out-of-range assessment")
	check(not Ops.covered(data, "apollo-11", int(data.window.end_unix) - 1, 21600), "End coverage includes entire plan")
	check(not Ops.covered(data, "missing", start), "Unknown site rejected")
	check(Ops.assess(data, "apollo-11", start, "sunset-operations", []).criteria[1].state == "violated", "Empty sequence rejected")
	check(Ops.illumination({"sun_full": [[10, 20]], "sun_any": [[5, 25]]}, 10) == "FULL", "Inclusive interval start")
	check(Ops.illumination({"sun_full": [[10, 20]], "sun_any": [[5, 25]]}, 21) == "PARTIAL", "Partial is separate from full")
	check(Ops.illumination({"sun_full": [], "sun_any": []}, 21) == "BLOCKED", "Blocked geometry")
	var saved := sunset.duplicate(true)
	for time in range(start, start + 21600, 60):
		Ops.illumination(data.sites[0].intervals, time)
	check(saved == Ops.assess(data, "apollo-11", start, "sunset-operations", schedule), "Preview traversal does not alter final assessment")
	schedule[0].activity = "Changed"
	check(sunset.schedule[0].activity == "Observation request", "Assessment freezes the plan")
	var campaign: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://data/campaign.json"))
	var catalog := Ops.catalog(campaign.missions[0], data.window)
	check(catalog.size() == 4 and catalog[0].title == "Science Outpost", "Intro and Phase 2 catalog")
	check(catalog[3].roadmap and catalog[3].id == "polar-ice-scout", "Polar Ice Scout remains roadmap")
	return true
