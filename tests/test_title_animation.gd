extends SceneTree
## Rig, material and title-animation integration checks.

func _initialize() -> void:
	call_deferred("_run")


func _run() -> void:
	var title: Node3D = (load("res://scenes/title/title.tscn") as PackedScene).instantiate()
	root.add_child(title)
	await process_frame
	var astronaut: AnimationPlayer = title.get("_astronaut_anim")
	var rover: AnimationPlayer = title.get("_rover_anim")
	assert(astronaut != null and rover != null, "Both display models must be rigged")
	assert(astronaut.current_animation == "idle")
	assert(rover.current_animation == "mast_look")
	rover.advance(0.5)
	assert(rover.current_animation_position > 0.0, "Rover animation must advance")
	title.call("_process", 9.0)
	assert(astronaut.current_animation == "scan_sweep", "Survey gesture must start")
	title.call("_process", 6.0)
	assert(astronaut.current_animation == "idle", "Survey must return to idle")
	var white_found: bool = false
	var gold_found: bool = false
	var model: Node3D = title.get("_astronaut")
	for child: Node in model.find_children("*", "MeshInstance3D", true, false):
		var mesh: MeshInstance3D = child as MeshInstance3D
		for surface: int in mesh.mesh.get_surface_count():
			var material: StandardMaterial3D = mesh.get_active_material(surface) as StandardMaterial3D
			if material.resource_name == "suit_orange":
				white_found = material.albedo_color.is_equal_approx(Color("eeeae0"))
			if material.resource_name == "visor_black":
				gold_found = material.albedo_color.is_equal_approx(Color("ba8534"))
	assert(white_found and gold_found, "White EVA fabric and gold visor must be applied")
	title.queue_free()
	await process_frame
	print("test_title_animation: rig playback, survey transitions and EVA materials passed")
	quit(0)
