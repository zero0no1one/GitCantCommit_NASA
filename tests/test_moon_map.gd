extends SceneTree
## The opening Moon map: Change of Plans is seeded from the data, and both ways in reach the Compare view.
## Run:  godot --headless --path . --script res://tests/test_moon_map.gd
## With a display, `-- <dir>` also saves map_landscape.png, map_portrait.png and map_compare.png there.

var failed := 0
var checks := 0
var shots := ""


func _initialize() -> void:
	run.call_deferred()


func check(ok: bool, message: String) -> void:
	checks += 1
	if not ok:
		failed += 1
		printerr("FAIL: " + message)


func run() -> void:
	await process_frame
	if OS.get_cmdline_user_args().size() > 0:
		shots = OS.get_cmdline_user_args()[0]
	var map_script: GDScript = load("res://scenes/map/map.gd")
	var game: Node = root.get_node("Game")
	var nav: Node = root.get_node("Navigator")

	# the scenario teaches what it claims: keep the site misses, move the site meets, the old slot met
	var cop: Dictionary = map_script.change_of_plans()
	check(cop.planned_keep == "meets", "planned slot at Tranquility meets 6 h of full Sun (got %s)" % cop.planned_keep)
	check(cop.locked_keep == "misses", "locked slot at Tranquility misses (got %s)" % cop.locked_keep)
	check(cop.locked_move == "meets", "locked slot at the polar ridge meets (got %s)" % cop.locked_move)
	check(map_script.verdict("apollo-11", int(cop.locked), 21600) == "misses", "verdict is deterministic")
	var window_end: int = int(root.get_node("Mission").data.window.end_unix)
	check(map_script.verdict("sl3", window_end - 3600, 21600) == "unknown", "the data ending first gives unknown")

	# the map loads as the main scene, with a pin per site
	check(ProjectSettings.get_setting("application/run/main_scene") == "res://scenes/map/map.tscn", "map is the main scene")
	var map: Node = load("res://scenes/map/map.tscn").instantiate()
	root.add_child(map)
	current_scene = map
	await process_frame
	await process_frame
	check(map._pins.size() == 2, "a pin for each study site")
	await _shot("map_landscape.png")
	# tapping a pin selects its site (pick by the pin's on-screen position)
	if shots != "":
		var cam: Camera3D = map._camera
		var at := cam.unproject_position(map._pins["apollo-11"].node.global_position)
		map._pick(at + Vector2(0, -6))
		check(map._selected == "apollo-11", "tapping the Tranquility pin selects it")
		map._select_site("sl3")
		for i in 50:
			await process_frame
		await _shot("map_site.png")
	if shots != "":
		get_root().size = Vector2i(560, 996)		# portrait layout
		await process_frame
		await process_frame
		map._show_change_of_plans()
		for i in 50:
			await process_frame
		await _shot("map_portrait.png")
		get_root().size = Vector2i(1280, 720)
		await process_frame

	# Change of Plans opens Compare with both sites at the locked start
	map._open_compare(int(cop.locked), ["apollo-11", "sl3"])
	await create_timer(1.5).timeout		# Game.goto fades out, swaps the scene, fades in
	var ops: Node = current_scene
	check(ops != null and ops.scene_file_path == "res://scenes/operations/operations.tscn", "operations screen opened")
	if ops and ops.scene_file_path.ends_with("operations.tscn"):
		check(ops.phase == "compare", "it opened straight into Compare (phase %s)" % ops.phase)
		check(not game.open_compare, "the open-compare request was consumed")
		check(nav.cards[0].key == "artemis-iv-era/apollo-11" and nav.cards[1].key == "artemis-iv-era/sl3", "cards hold both sites")
		check(int(nav.cards[0].start) == int(cop.locked) and int(nav.cards[1].start) == int(cop.locked), "cards share the locked start")
		check(game.return_to == "map", "back button returns to the map")
		await _shot("map_compare.png")
	print("test_moon_map: %d checks, %d failed" % [checks, failed])
	quit(1 if failed else 0)


func _shot(name: String) -> void:
	if shots == "":
		return
	await process_frame
	var img := root.get_viewport().get_texture().get_image()
	img.save_png(shots.path_join(name))
