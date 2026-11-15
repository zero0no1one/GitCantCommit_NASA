extends SceneTree
## Exercises Mission 1 without writing player progress.
var failed := 0
var checks := 0
var completions := 0
var captured: Dictionary = {}

func _initialize() -> void:
	call_deferred("run")

func check(ok: bool, message: String) -> void:
	checks += 1
	if not ok:
		failed += 1
		printerr("FAIL: " + message)

func run() -> void:
	if "--verify-failure-exit" in OS.get_cmdline_user_args():
		check(false, "Intentional runner failure")
	if await exercise() != true:
		failed += 1
	print("test_science_outpost: %d checks, %d failed" % [checks, failed])
	quit(1 if failed else 0)

func exercise() -> bool:
	await process_frame
	var game: Node = root.get_node("Game")
	var campaign: Node = root.get_node("Campaign")
	game.mission_id = "first-light"
	var mission: Node3D = load("res://scenes/mission/mission.tscn").instantiate()
	root.add_child(mission)
	await process_frame
	check(mission.mission.title == "Science Outpost", "Campaign loads Science Outpost with legacy identity")
	check(mission.mission.science_goals == {"delivered": 3, "scanned": 2}, "Science training goals")
	check(mission.mission.need_s == 7200, "Two-hour illumination requirement")
	for sid: String in mission.mission.sites:
		mission._on_site_switch(sid)
		await process_frame
		check(mission.world.site == sid, "Site selection loads " + sid)
		var passing := 0
		var bonus_passing := 0
		var robust_passing := 0
		var data: Node = root.get_node("Mission")
		for time in range(int(mission.mission.window.start), int(mission.mission.window.end) + 1, int(mission.mission.window.step)):
			var assessment: Dictionary = game.evaluate(sid, time, 7200)
			if assessment.pass:
				passing += 1
				mission.touchdown = time
				if mission._bonus_met(assessment):
					bonus_passing += 1
			for iv: Array in data.sites[sid].intervals.sun_full:
				if time >= int(iv[0]) + int(iv[2]) and time + 7200 <= int(iv[1]) + 1 - int(iv[3]):
					robust_passing += 1
		check(passing > 0 and robust_passing > 0, sid + " has passing plans beyond boundary uncertainty")
		check(bonus_passing > 0, sid + " bonus is achievable with a passing plan")
		check(mission.phase._dial.start == int(mission.mission.window.start) and mission.phase._dial.end == int(mission.mission.window.end), sid + " dial uses site window")
	mission._on_site_switch("apollo-11")
	await process_frame
	mission.touchdown = int(campaign.missions[0].stats["apollo-11"].example_pass)
	check(game.evaluate("apollo-11", mission.touchdown, 7200).pass, "Covered passing plan")
	check(not game.evaluate("apollo-11", int(mission.mission.window.start), 7200).pass, "Nighttime plan fails")
	mission._on_landed({"precision": 0, "soft": 0, "x": 0.0, "ground": mission.world.ground_y(Vector2.ZERO)})
	await process_frame
	var hold: Node = mission.phase
	hold.finished.disconnect(mission._on_hold_done)
	hold.finished.connect(func(stats: Dictionary) -> void:
		completions += 1
		captured = stats)
	mission.world.rover.position.x = 20.0
	hold._spawn_canister()
	hold._player.global_position = hold._canisters[0].global_position
	hold._pickups()
	check(hold._carried == 1, "Nearby sample collected")
	hold._player.global_position = hold.lander_pos
	hold._pickups()
	check(hold._delivered == 1 and mission.score.samples == 300, "Sample delivered and scored once")
	hold._pickups()
	check(mission.score.samples == 300, "Delivery cannot double count")
	hold._finish()
	hold._finish()
	check(completions == 1 and captured.delivered == 1, "Completion emits science totals exactly once")
	check(not hold._running and hold._scan_btn.disabled, "Completion stops sampling and scan control")
	var debrief: Control = load("res://scenes/mission/debrief.gd").new()
	debrief.mission = mission.mission
	debrief.site = "apollo-11"
	debrief.result = game.evaluate("apollo-11", mission.touchdown, 7200)
	debrief.science_stats = captured
	root.add_child(debrief)
	await process_frame
	check(debrief.find_children("*", "Label", true, false).any(func(label: Node) -> bool: return label.text == "OUTPOST GOALS INCOMPLETE"), "Debrief reports incomplete science goals")
	debrief.queue_free()
	mission.queue_free()
	await process_frame
	return true
