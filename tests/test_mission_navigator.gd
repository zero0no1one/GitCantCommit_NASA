extends SceneTree
var failed := 0
var checks := 0
func _initialize() -> void:
	call_deferred("run")
func check(ok: bool, message: String) -> void:
	checks += 1
	if not ok:
		failed += 1
		printerr("FAIL: " + message)
func run() -> void:
	await process_frame
	var game: Node = root.get_node("Game")
	var state: Node = root.get_node("Navigator")
	game.mission_id = "sunset-operations"
	var scene: Node = load("res://scenes/operations/operations.tscn").instantiate()
	root.add_child(scene)
	await physics_frame
	await process_frame
	check(scene.phase == "plan", "Mission 2 keeps existing plan screen")
	scene.navigator_ui.compare()
	check(scene.phase == "compare", "Compare lives in mission HUD")
	check(scene.body.find_children("", "OptionButton", true, false).size() == 2, "Two comparison card selectors")
	var picker: OptionButton = scene.body.find_children("", "OptionButton", true, false)[0]
	check(picker.item_count == 18, "Six sites and three windows")
	var duration: SpinBox = scene.body.find_children("", "SpinBox", true, false)[0]
	duration.value = 120
	check(state.cards[0].duration == 7200, "Duration control updates decision state")
	duration.value = 360
	if DisplayServer.get_name() != "headless":
		for dimensions: Vector2i in [Vector2i(1280,720),Vector2i(560,996)]:
			root.size = dimensions
			await process_frame
			await process_frame
			check(scene.body.get_combined_minimum_size().x <= root.get_visible_rect().size.x-60, "Compare fits " + str(dimensions))
			await RenderingServer.frame_post_draw
			root.get_texture().get_image().save_png("res://build/mission-navigator-%dx%d.png" % [dimensions.x,dimensions.y])
	scene.navigator_ui.review()
	check(scene.phase == "review", "Review needs no replay")
	var summaries: Array = []
	for card: Dictionary in state.cards:
		summaries.append(scene.navigator_ui.card_text(card))
	var brief: Dictionary = state.save_brief(summaries)
	var original_start := int(state.cards[0].start)
	state.set_card(0, "artemis-iv-era/sl3", original_start+600, 21600)
	scene.navigator_ui.activate(0)
	await physics_frame
	await process_frame
	check(scene.site == "sl3" and scene.start == original_start+600, "Chosen plan drives surface")
	check(brief.cards[0].start == original_start, "Saved inputs immutable")
	scene.navigator_ui.review(brief)
	check(state.cards[0].start == original_start+600, "Saved review does not restore inputs")
	scene.navigator_ui.activate(0)
	scene._preview()
	var skipped: Dictionary = scene.result.duplicate(true)
	scene._debrief()
	scene._plan()
	scene._preview()
	scene._process(30)
	check(scene.result == skipped, "Watch/skip use same saved plan")
	state.set_card(0, "viper-era/apollo-17", 1826236800, 21600)
	scene.navigator_ui.activate(0)
	check(not scene.world.visible, "Preview cannot borrow old surface")
	scene._assess()
	check(scene.result.state == "unknown", "Preview assessment unknown")
	state.set_card(0,"artemis-iv-era/apollo-11",int(root.get_node("Mission").data.window.end_unix),21600)
	scene.navigator_ui.activate(0)
	scene._assess()
	check(scene.result.state == "unknown", "Out-of-coverage cannot pass")
	var selected: Dictionary = state.cards[0].duplicate(true)
	scene.queue_free()
	await process_frame
	game.mission_id = "earth-link"
	scene = load("res://scenes/operations/operations.tscn").instantiate()
	root.add_child(scene)
	await physics_frame
	await process_frame
	check(scene.start == selected.start, "Mission 3 preserves shared plan")
	scene.navigator_ui.compare()
	check(scene.phase == "compare", "Mission 3 has same comparison")
	scene.queue_free()
	await process_frame
	print("test_mission_navigator: %d checks, %d failed" % [checks,failed])
	quit(1 if failed else 0)
