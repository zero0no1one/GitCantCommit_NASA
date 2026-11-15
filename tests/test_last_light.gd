extends SceneTree
const Model := preload("res://scripts/last_light_model.gd")
var checks := 0
var failed := 0

func _initialize() -> void:
	call_deferred("run")

func check(ok: bool, message: String) -> void:
	checks += 1
	if not ok:
		failed += 1
		printerr("FAIL: " + message)

func run() -> void:
	if "--verify-failure-exit" in OS.get_cmdline_user_args(): check(false,"Intentional runner failure")
	if model_checks() != true: failed += 1
	if await flow_checks() != true: failed += 1
	print("test_last_light: %d checks, %d failed" % [checks,failed])
	quit(1 if failed else 0)

func model_checks() -> bool:
	var model := Model.new()
	var featured: Dictionary = model.package.featured
	var bad := model.snapshot(featured.site,int(featured.initial_start))
	var good := model.snapshot(featured.site,int(featured.alternative_start))
	var miss := model.assess(bad)
	var met := model.assess(good)
	check(miss.illumination == "Misses","Generated initial plan misses")
	check(met.illumination == "Meets" and met.bonus,"Generated revision meets with stable bonus")
	check(int(met.margin_lower_s) == int(featured.alternative_margin_lower_s),"Python/GDScript margin parity")
	check(met.setup_end == int(good.start)+900 and met.end == int(good.start)+3600,"Consecutive activities")
	check(met.electrical == "Unknown" and met.thermal == "Unknown","No equipment verdict from illumination")
	check(float(featured.event.sun_el_deg) > float(featured.event.sun_radius_deg),"Terrain interrupts above level horizon")
	var record: Dictionary = model.records[featured.site]
	for event: Dictionary in record.events:
		if event.kind != "Full to partial": continue
		var crossing := model.snapshot(featured.site,int(event.unix)-1800)
		check(model.assess(crossing).illumination != "Meets","Crossing full-to-partial never meets")
	var outside := model.snapshot(featured.site,int(record.coverage[1])-100)
	check(model.assess(outside).illumination == "Unknown","No extrapolated uncovered assessment")
	var observer := good.duplicate(true)
	observer.observer.height_m = 1.62
	check(model.assess(observer).illumination == "Unknown","Unevaluated observer rejected")
	var changed := good.duplicate(true)
	changed.requirements.observation_s = 7200
	check(model.assess(changed).end == int(changed.start)+8100,"Data-driven duration independent of science functions")
	# Exact synthetic interval logic: no summed disjoint sunlight, ambiguous boundaries, open end.
	var synthetic: Dictionary = record.duplicate(true)
	synthetic.coverage = [0,10000]
	synthetic.variants = [{"full": [[0,5000]]},{"full": [[0,4000]]}]
	model.records[featured.site] = synthetic
	var ambiguous := model.snapshot(featured.site,1000)
	check(model.assess(ambiguous).illumination == "Unknown","Fits only favorable event time is Unknown")
	synthetic.variants = [{"full": [[0,2000],[2100,10000]]}]
	check(model.assess(ambiguous).illumination == "Misses","Disjoint sunlight cannot be summed")
	synthetic.variants = [{"full": [[0,10000]]}]
	var open: Dictionary = model.assess(ambiguous)
	check(open.illumination == "Meets" and open.limit == null and open.margin_is_lower_bound,"Coverage edge is lower bound, never exact loss")
	check(open.margin_lower_s == 5400 and open.margin_upper_s == null,"Open margin bound correct")
	var brief := model.brief(good,bad,met,"Misses","Recommend this window")
	good.start += 3600
	check(brief.plan.start != good.start and brief.assessment == met,"Brief is immutable independent of later edits and prediction")
	return true

func flow_checks() -> bool:
	await process_frame
	var scene: Node3D = load("res://scenes/last_light/last_light.tscn").instantiate()
	scene.log_path = "user://last_light_test_log.json"
	root.add_child(scene)
	await process_frame
	check(scene.phase == "plan" and scene.result.illumination == "Misses","Dispatch opens initial plan on decision screen")
	check(root.gui_get_focus_owner() != null,"Keyboard focus visible on entry")
	scene.set_compare_mode(0)
	scene.set_start(scene.start+60)
	check(scene.cards[0].start == scene.cards[1].start and scene.cards[0].site != scene.cards[1].site,"Site comparison holds UTC")
	scene.switch_site()
	check(scene.cards[0].site != scene.cards[1].site and scene.cards[0].start == scene.cards[1].start,"Switching the active site keeps a distinct comparison at fixed UTC")
	var before_landing: Dictionary = scene.result.duplicate(true)
	scene.practice_descent()
	await process_frame
	check(scene.phase == "descent" and is_instance_valid(scene.descent),"Landing practice starts")
	scene.descent._auto_land()
	await process_frame
	check(scene.phase == "plan" and scene.result == before_landing,"Landing returns to the unchanged scientific plan")
	scene.set_compare_mode(1)
	scene.switch_site()
	check(scene.cards[0].site == scene.cards[1].site,"Date comparison holds site")
	scene.restore_card(1)
	check(scene.start == int(scene.cards[1].start),"One click restores comparison")
	scene.set_start(int(scene.model.records[scene.site].coverage[1])+86400,true)
	check(scene.result.illumination == "Unknown","Uncovered candidate stays comparable")
	scene.reduced_motion = true
	scene.commit()
	check(scene.phase == "debrief" and scene.result.illumination == "Unknown","Reduced motion reaches debrief without retry")
	scene.recommendation = "Hold pending evidence"
	scene.file_brief("Source coverage absent")
	check(scene.phase == "log" and scene.log_entries.back().recommendation == "Hold pending evidence","Unresolved plan reaches Mission Log")
	check(FileAccess.file_exists(scene.log_path),"Mission Log persists on device")
	scene.plan_screen()
	scene.site = scene.model.package.featured.site
	scene.set_start(int(scene.model.package.featured.alternative_start),true)
	scene.reduced_motion = false
	scene.commit()
	var saved: Dictionary = scene.result.duplicate(true)
	scene.debrief()
	check(scene.result == saved,"Skip preserves submitted assessment")
	scene.plan_screen()
	scene.commit()
	scene._process(12.)
	check(scene.phase == "debrief" and scene.result == saved,"Replay completion equals skip")
	# Render/layout artifacts when a display is available.
	if DisplayServer.get_name() != "headless":
		scene.plan_screen()
		for dimensions in [Vector2i(1280,720),Vector2i(560,996),Vector2i(2560,1080)]:
			root.size = dimensions
			await process_frame
			await process_frame
			check(scene.body.get_combined_minimum_size().x <= root.get_visible_rect().size.x-40,"Planner fits " + str(dimensions))
			await RenderingServer.frame_post_draw
			root.get_texture().get_image().save_png("user://last-light-%dx%d.png" % [dimensions.x,dimensions.y])
	var log_path: String = scene.log_path
	scene.queue_free()
	await process_frame
	await process_frame
	DirAccess.remove_absolute(log_path)
	return true
