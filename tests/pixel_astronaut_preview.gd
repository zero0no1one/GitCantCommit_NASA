extends SceneTree
## Visual check of the HD-2D astronaut on a real site: four sprites facing away / right / toward / left of the
## camera, then the same four walking. Needs a display (not --headless).
##
## Run:  godot --path . --script res://tests/pixel_astronaut_preview.gd -- <output_dir>
## Writes pixel_astronaut_idle.png and pixel_astronaut_walk_<n>.png into <output_dir>.

func _initialize() -> void:
	_run.call_deferred()


func _run() -> void:
	await process_frame
	var out_dir: String = OS.get_cmdline_user_args()[0] if OS.get_cmdline_user_args().size() > 0 else OS.get_user_data_dir()
	var site := "apollo-11"
	# loaded at run time: scripts that use autoloads can't be compiled before the autoloads exist
	var world: Node3D = load("res://scenes/mission/site_world.gd").new(site)
	root.add_child(world)
	# first time in the window with the Sun well up
	var mission: Node = root.get_node("Mission")		# autoloads aren't global identifiers in a --script run
	var t: int = int(mission.data.window.start_unix)
	while t < int(mission.data.window.end_unix) and float(mission.sample(site, "sun_el", t)) < 25.0:
		t += 3600
	world.set_time(t)
	await physics_frame
	var ground: float = world.ground_y(Vector2.ZERO)

	var cam := Camera3D.new()
	cam.fov = 40
	world.add_child(cam)
	cam.position = Vector3(0, ground + 2.2, 9)
	cam.look_at(Vector3(0, ground + 0.9, 0))
	cam.current = true

	var bots: Array[PixelAstronaut] = []
	var facings := [Vector3.FORWARD, Vector3.RIGHT, Vector3.BACK, Vector3.LEFT]
	for i in 4:
		var a := PixelAstronaut.new()
		world.add_child(a)
		a.position = Vector3(-3.3 + i * 2.2, world.ground_y(Vector2(-3.3 + i * 2.2, 0)), 0)
		a.facing = facings[i]
		bots.append(a)
	for i in 30:
		await process_frame
	_shot(out_dir.path_join("pixel_astronaut_idle.png"))
	for a in bots:
		a.play("walk")
	for n in 4:
		for i in 7:
			await process_frame
		_shot(out_dir.path_join("pixel_astronaut_walk_%d.png" % n))
	print("views: ", bots.map(func(a: PixelAstronaut) -> String: return a.view))

	# the player, seen through its own third-person camera, walking forward then to the right
	for a in bots:
		a.queue_free()
	var player: CharacterBody3D = load("res://scenes/mission/astronaut.gd").new()
	world.add_child(player)
	player.position = Vector3(0, ground + 1, 0)
	player.camera.make_current()
	Input.action_press("move_forward")
	for i in 60:
		await physics_frame
	_shot(out_dir.path_join("pixel_astronaut_player_forward.png"))
	Input.action_release("move_forward")
	Input.action_press("move_right")
	for i in 60:
		await physics_frame
	_shot(out_dir.path_join("pixel_astronaut_player_right.png"))
	Input.action_release("move_right")
	print("player view while moving right: ", player.model.view)
	quit()


func _shot(path: String) -> void:
	var img := root.get_viewport().get_texture().get_image()
	print("saved ", path, " ", error_string(img.save_png(path)))
