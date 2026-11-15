extends SceneTree
## Integration check, including preview/skip parity and fixed observer under avatar motion.

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
	if await exercise() != true:
		failed += 1
	print("test_operations_flow: %d checks, %d failed" % [checks, failed])
	quit(1 if failed else 0)

func exercise() -> bool:
	await process_frame
	var game: Node = root.get_node("Game")
	game.mission_id = "sunset-operations"
	var scene: Node3D = load("res://scenes/operations/operations.tscn").instantiate()
	root.add_child(scene)
	await physics_frame
	await process_frame
	await process_frame
	check(scene.phase == "plan", "Starts in planning")
	check(root.gui_get_focus_owner() != null, "Planning has keyboard focus")
	scene._inspect()
	scene._cycle_view()
	check(scene.view_index == 1, "Third-person inspection")
	scene._cycle_view()
	check(scene.view_index == 2, "First-person inspection")
	var start: int = scene.start
	scene.inspector.position.x += 30
	check(scene.start == start and scene.site == "apollo-11", "Walking preserves assessment origin and time")
	scene._plan()
	check(scene.inspector.frozen, "Planning freezes inspector")
	scene._preview()
	var saved: Dictionary = scene.result.duplicate(true)
	scene._debrief()
	check(scene.result == saved and not scene.previewing, "Skip keeps saved assessment")
	scene._plan()
	scene._preview()
	scene._process(30)
	check(scene.phase == "debrief" and scene.result == saved, "Complete preview equals skipped preview")
	scene._evidence()
	check(scene.phase == "evidence", "Evidence panel opens")
	scene._plan()
	scene._change_site("sl3")
	await physics_frame
	await process_frame
	check(scene.world.site == "sl3", "Second measured site loads")
	game.mission_id = "earth-link"
	scene._assess()
	check(scene.result.state == "unknown", "Earth Link remains evidence gated")
	# Capture a rendered review artifact only when a graphics display is available.
	if DisplayServer.get_name() != "headless":
		scene._plan()
		for dimensions in [Vector2i(1280, 720), Vector2i(560, 996), Vector2i(2560, 1080)]:
			root.size = dimensions
			await process_frame
			await process_frame
			check(scene.body.get_combined_minimum_size().x <= root.get_visible_rect().size.x - 60, "Planning width fits %s" % dimensions)
			await RenderingServer.frame_post_draw
			root.get_texture().get_image().save_png("user://phase2-planning-%dx%d.png" % [dimensions.x, dimensions.y])
	scene.queue_free()
	await process_frame
	await process_frame
	return true
