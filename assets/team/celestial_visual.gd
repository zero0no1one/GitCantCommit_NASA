extends Node3D
## Normalized illustrative body. Position, angular size, and spin come from outside.

@export var source_model: PackedScene
@export var self_lit := false
@export var display_diameter := 2.0


func _ready() -> void:
	if source_model == null:
		push_error("Celestial visual needs a source model")
		return
	var visual := source_model.instantiate() as Node3D
	visual.name = "Visual"
	add_child(visual)
	var meshes := visual.find_children("*", "MeshInstance3D", true, false)
	if visual is MeshInstance3D:
		meshes.append(visual)
	if meshes.is_empty():
		push_error("Celestial visual contains no mesh")
		return
	var bounds := AABB()
	var first := true
	for mesh: MeshInstance3D in meshes:
		var relative := global_transform.affine_inverse() * mesh.global_transform
		var mesh_bounds: AABB = relative * mesh.get_aabb()
		bounds = mesh_bounds if first else bounds.merge(mesh_bounds)
		first = false
		for surface in mesh.mesh.get_surface_count():
			var original := mesh.get_active_material(surface)
			var material := original.duplicate() as StandardMaterial3D if original is StandardMaterial3D else StandardMaterial3D.new()
			material.metallic = 0.0
			material.roughness = 1.0
			if self_lit:
				material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
				material.normal_enabled = false
			mesh.set_surface_override_material(surface, material)
	var extent := bounds.size[bounds.size.max_axis_index()]
	if extent <= 0.0:
		push_error("Celestial model has zero extent")
		return
	var factor := display_diameter / extent
	visual.transform = Transform3D(Basis.IDENTITY.scaled(Vector3.ONE * factor), -bounds.get_center() * factor) * visual.transform
