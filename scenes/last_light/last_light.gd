extends Node3D
## Last Light Operations: independent mission, model-driven decisions, immutable submission.
const Model := preload("res://scripts/last_light_model.gd")
const ScienceView := preload("res://scenes/last_light/science_view.gd")
const Astronaut := preload("res://scenes/mission/astronaut.gd")
const DescentPhase := preload("res://scenes/mission/descent_phase.gd")
@export var log_path := "user://last_light_log.json"
const CREAM := Color("ffd23f")
const TEAL := Color("2ef2ff")
var model: RefCounted
var site := ""
var start := 0
var inspect_at := 0.0
var timeline_start := 0
var timeline_end := 0
var cards: Array[Dictionary] = []
var active := 0
var compare_mode := 0 # Sites: UTC fixed. Dates: site fixed.
var result: Dictionary = {}
var submitted: Dictionary = {}
var submitted_alternative: Dictionary = {}
var prediction := "Meets"
var recommendation := "Hold pending evidence"
var phase := "dispatch"
var reduced_motion := false
var log_entries: Array = []
var body: VBoxContainer
var page: Control
var overlay: Control
var readout: Label
var schedule_label: Label
var utc_input: LineEdit
var transition_menu: OptionButton
var card_buttons: Array[Button] = []
var views: Array[Control] = []
var world: SiteWorld
var inspector: CharacterBody3D
var camera: Camera3D
var replay_elapsed := 0.0
var replay_label: Label
var replay_bar: ProgressBar
var instrument: MeshInstance3D
var surface_generation := 0
var paused := false
var descent: Node

func utc(t: float) -> String:
	return Time.get_datetime_string_from_unix_time(int(t),true).replace("T"," ") + " UTC"

func _ready() -> void:
	model = Model.new()
	var featured: Dictionary = model.package.featured
	site = featured.site
	start = int(featured.initial_start)
	cards = [model.snapshot(site,start), model.snapshot(site,int(featured.alternative_start))]
	compare_mode = 1
	timeline_start = int(featured.alternative_start)-10800
	timeline_end = int(featured.initial_start)+10800
	inspect_at = featured.loss
	if FileAccess.file_exists(log_path):
		var saved: Variant = JSON.parse_string(FileAccess.get_file_as_string(log_path))
		if saved is Array: log_entries = saved
	var layer := CanvasLayer.new()
	add_child(layer)
	page = UIKit.full_rect(Control.new())
	layer.add_child(page)
	var bg := UIKit.full_rect(ColorRect.new())
	bg.color = Game.SPACE
	page.add_child(bg)
	var margin := UIKit.full_rect(UIKit.margin(20))
	page.add_child(margin)
	var scroll := ScrollContainer.new()
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	margin.add_child(scroll)
	body = UIKit.vbox(8)
	body.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	scroll.add_child(body)
	overlay = UIKit.full_rect(Control.new())
	overlay.mouse_filter = Control.MOUSE_FILTER_IGNORE
	layer.add_child(overlay)
	plan_screen()
	Game.orientation_changed.connect(func(_portrait: bool) -> void:
		if phase == "plan": plan_screen.call_deferred())
	Sfx.music("mission")

func button(text: String, action: Callable) -> Button:
	# Avoid motion-producing shared button effects in this mission.
	var b := Button.new()
	b.text = text
	b.focus_mode = Control.FOCUS_ALL
	b.add_theme_font_size_override("font_size",15)
	b.custom_minimum_size.y = 36
	var focus := StyleBoxFlat.new()
	focus.bg_color = Color(0,0,0,0)
	focus.border_color = CREAM
	focus.set_border_width_all(3)
	focus.set_corner_radius_all(5)
	b.add_theme_stylebox_override("focus",focus)
	b.pressed.connect(action)
	return b

func text(value: String, color: Color = Color("d7e2e6"), font_size: int = 15) -> Label:
	var label := UIKit.label(value,font_size,color,true)
	body.add_child(label)
	return label

func clear_body() -> void:
	views.clear()
	card_buttons.clear()
	for child in body.get_children():
		body.remove_child(child)
		child.queue_free()
	page.show()
	for child in overlay.get_children(): child.queue_free()

func actions() -> HFlowContainer:
	var row := HFlowContainer.new()
	row.add_theme_constant_override("h_separation",8)
	row.add_theme_constant_override("v_separation",6)
	body.add_child(row)
	return row

func plan_screen() -> void:
	phase = "plan"
	clear_body()
	if is_instance_valid(inspector): inspector.frozen = true
	var top := actions()
	top.add_child(button("MISSIONS",func() -> void: Game.goto("campaign")))
	top.add_child(UIKit.display("MISSION 2 / LAST LIGHT OPERATIONS",24,CREAM))
	top.add_child(button("MISSION LOG (%d)" % log_entries.size(),show_log))
	text("Complete setup and observation in continuous full sunlight. Leave as much verified time before the first interruption as you can.",TEAL,17)
	text("DISPATCH / %s. A ridge has interrupted full sunlight. Inspect the red transition, then revise the schedule or compare an alternative. Coverage: %s through %s." % [site_name(site),utc(model.records[site].coverage[0]),utc(model.records[site].coverage[1])],Color("aabcc7"),13)
	var main_body := body
	var columns := BoxContainer.new()
	columns.vertical = Game.portrait
	columns.add_theme_constant_override("separation",14)
	body.add_child(columns)
	var left := UIKit.vbox(8)
	var right := UIKit.vbox(8)
	for column in [left,right]:
		column.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		columns.add_child(column)
	left.size_flags_stretch_ratio = 1.15
	body = left
	var visual_row := HBoxContainer.new()
	visual_row.add_theme_constant_override("separation",10)
	body.add_child(visual_row)
	for kind: String in ["map","horizon"]:
		var view := ScienceView.new()
		view.host = self
		view.kind = kind
		view.custom_minimum_size = Vector2(150 if kind == "map" else 300,150)
		view.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		visual_row.add_child(view)
		views.append(view)
	body = right
	var compare := actions()
	compare.add_child(button("COMPARE SITES / UTC fixed",func() -> void: set_compare_mode(0)))
	compare.add_child(button("COMPARE DATES / site fixed",func() -> void: set_compare_mode(1)))
	compare.add_child(button("OTHER SITE",switch_site))
	compare.add_child(button("DATE -1 DAY",func() -> void: set_start(start-86400,true)))
	compare.add_child(button("DATE +1 DAY",func() -> void: set_start(start+86400,true)))
	var card_row := VBoxContainer.new()
	body.add_child(card_row)
	for i in 2:
		var card := button("",func() -> void: restore_card(i))
		card.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		card.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		card.custom_minimum_size.y = 78
		card_row.add_child(card)
		card_buttons.append(card)
	body = left
	var timeline := ScienceView.new()
	timeline.kind = "timeline"
	timeline.host = self
	timeline.custom_minimum_size.y = 145
	body.add_child(timeline)
	views.append(timeline)
	var edit := actions()
	edit.add_child(UIKit.label("Setup start UTC",15,TEAL))
	utc_input = LineEdit.new()
	utc_input.custom_minimum_size.x = 230
	utc_input.placeholder_text = "YYYY-MM-DD HH:MM:SS"
	utc_input.tooltip_text = "UTC. Enter applies the start; setup and observation stay consecutive."
	utc_input.text_submitted.connect(apply_utc)
	edit.add_child(utc_input)
	edit.add_child(button("APPLY UTC",func() -> void: apply_utc(utc_input.text)))
	edit.add_child(button("-15 MIN",func() -> void: set_start(start-900)))
	edit.add_child(button("+15 MIN",func() -> void: set_start(start+900)))
	edit.add_child(button("INSPECT LIMIT",inspect_limit))
	edit.add_child(button("SURFACE VIEW",func() -> void: open_surface(false)))
	edit.add_child(button("PRACTICE LANDING",practice_descent))
	var transitions := OptionButton.new()
	transition_menu = transitions
	transitions.item_selected.connect(func(index: int) -> void:
		if index > 0:
			var events: Array = model.records[site].events
			inspect_at = float(events[index-1].unix)
			for view in views: view.queue_redraw())
	transitions.clip_text = true
	transitions.custom_minimum_size.x = 200
	body.add_child(transitions)
	schedule_label = text("",CREAM,14)
	body = right
	readout = text("",Color("d7e2e6"),14)
	var bottom := actions()
	var predict := OptionButton.new()
	for choice: String in ["Meets","Misses","Unknown"]: predict.add_item("I predict: "+choice)
	predict.select(["Meets","Misses","Unknown"].find(prediction))
	predict.item_selected.connect(func(i: int) -> void: prediction = ["Meets","Misses","Unknown"][i])
	bottom.add_child(predict)
	var reduced := CheckButton.new()
	reduced.text = "Reduced motion"
	reduced.button_pressed = reduced_motion
	reduced.toggled.connect(func(value: bool) -> void: reduced_motion = value)
	bottom.add_child(reduced)
	var submit := button("SUBMIT OPERATIONS PLAN",commit)
	submit.theme_type_variation = &"PrimaryButton"
	bottom.add_child(submit)
	bottom.add_child(button("HINT",func() -> void:
		readout.text += "\nHINT: Fit the whole bracket inside one teal interval, before the red loss line. Leave time for uncertainty. A hold with evidence is valid."))
	body = main_body
	refresh()
	submit.grab_focus()

func site_name(sid: String) -> String:
	return "Tranquility Base" if sid == "apollo-11" else "Connecting Ridge"

func set_compare_mode(mode: int) -> void:
	compare_mode = mode
	var other := 1-active
	if mode == 0:
		cards[other] = model.snapshot("sl3" if site == "apollo-11" else "apollo-11",start)
	else:
		cards[other] = model.snapshot(site,start+86400)
	refresh()

func switch_site() -> void:
	site = "sl3" if site == "apollo-11" else "apollo-11"
	cards[active] = model.snapshot(site,start)
	if compare_mode == 1: cards[1-active] = model.snapshot(site,int(cards[1-active].start))
	else: cards[1-active] = model.snapshot("sl3" if site == "apollo-11" else "apollo-11",start)
	refresh()

func practice_descent() -> void:
	if model.geometry(site,start).is_empty():
		readout.text = "Landing practice needs a date within the bundled site coverage. The uncovered plan remains available for assessment."
		return
	phase = "descent"
	paused = false
	page.hide()
	if is_instance_valid(world):
		remove_child(world)
		world.queue_free()
	world = SiteWorld.new(site)
	add_child(world)
	world.set_time(start)
	descent = DescentPhase.new()
	descent.setup(self,world)
	descent.landed.connect(_descent_finished)
	add_child(descent)

func _descent_finished(_landing: Dictionary) -> void:
	# The landing is an arcade visualization; the scientific observer stays fixed.
	if is_instance_valid(descent): descent.queue_free()
	if is_instance_valid(world): world.queue_free()
	paused = false
	plan_screen()

func toggle_pause() -> void:
	paused = not paused

func popup(_message: String, _color: Color) -> void:
	pass

func restore_card(index: int) -> void:
	active = index
	site = cards[index].site
	start = int(cards[index].start)
	inspect_at = start
	frame_timeline()
	refresh()

func frame_timeline() -> void:
	timeline_start = mini(start,int(cards[1-active].start))-7200 if compare_mode == 1 else start-10800
	timeline_end = maxi(start,int(cards[1-active].start))+10800 if compare_mode == 1 else start+14400

func set_start(value: int, reframe: bool = false) -> void:
	start = value # Preserve unsupported previews; never clamp to a covered winning period.
	inspect_at = start
	cards[active] = model.snapshot(site,start)
	if compare_mode == 0:
		cards[1-active] = model.snapshot(cards[1-active].site,start)
	if reframe: frame_timeline()
	refresh()

func apply_utc(value: String) -> void:
	var clean := value.strip_edges().replace(" UTC","").replace(" ","T")
	if clean.length() == 16: clean += ":00"
	var regex := RegEx.new()
	regex.compile("^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}$")
	if regex.search(clean) == null:
		readout.text = "Enter UTC as YYYY-MM-DD HH:MM:SS."
		return
	var t := Time.get_unix_time_from_datetime_string(clean)
	if Time.get_datetime_string_from_unix_time(t) != clean:
		readout.text = "That UTC date or time is invalid."
		return
	set_start(t,true)

func inspect_limit() -> void:
	var limit: Variant = result.limit
	# When starting in shadow, reveal the preceding transition that caused it.
	if limit == null or int(limit) == start:
		var nearest := 1.0e30
		for event: Dictionary in model.records[site].events:
			if event.kind == "Full to partial" and absf(float(event.unix)-start) < nearest:
				nearest = absf(float(event.unix)-start)
				limit = event.unix
	if limit != null: inspect_at = float(limit)
	for view in views: view.queue_redraw()
	schedule_label.text += "\nHorizon inspection: " + utc(inspect_at)

func refresh() -> void:
	result = model.assess(cards[active])
	if not is_instance_valid(readout): return
	utc_input.text = utc(start).replace(" UTC","")
	transition_menu.clear()
	transition_menu.add_item("Select a modeled transition to inspect")
	for event: Dictionary in model.records[site].events:
		transition_menu.add_item(str(event.kind)+" / "+utc(event.unix))
	var r: Dictionary = model.requirements
	schedule_label.text = "GAME TRAINING REQUIREMENTS / Setup %d min: %s -> %s | Observation %d min -> %s\nRequired: %d continuous minutes. Optional bonus: %d min supported margin. Observer: 1 m, Moon ME frame; movement does not change it." % [int(r.setup_s)/60,utc(start),utc(result.setup_end),int(r.observation_s)/60,utc(result.end),model.duration()/60,int(r.bonus_margin_s)/60]
	readout.text = summary(result)
	for i in card_buttons.size():
		var card: Dictionary = cards[i]
		var coords: Dictionary = card.coordinates
		card_buttons[i].text = "%s %s | %s\n%.4f N, %.4f E | %s\n1 m ME observer | evaluated model variants" % ["EDITING" if i == active else "RESTORE", "A" if i == 0 else "B",site_name(card.site),coords.lat,coords.lon,utc(card.start)]
	for view in views: view.queue_redraw()

func summary(r: Dictionary) -> String:
	var margin := "Unresolved"
	if r.margin_lower_s != null:
		margin = ("at least " if r.margin_is_lower_bound else "supported minimum ") + "%+.1f min" % (float(r.margin_lower_s)/60)
		if r.margin_upper_s != null: margin += " (evaluated upper %+.1f min)" % (float(r.margin_upper_s)/60)
	return "ILLUMINATION: %s | Setup: %s | Observation: %s | Bonus: %s\n%s\nFirst limiting event: %s | Margin: %s\nELECTRICAL: Unknown | THERMAL: Unknown. Equipment inputs and validated models required.\n%s" % [r.illumination,r.setup,r.observation,"earned" if r.bonus else "not established",r.reason,utc(r.limit) if r.limit != null else "unresolved / beyond coverage",margin,r.uncertainty]

func commit() -> void:
	submitted = cards[active].duplicate(true)
	submitted_alternative = cards[1-active].duplicate(true)
	result = model.assess(submitted).duplicate(true)
	replay_elapsed = 0
	if reduced_motion: debrief()
	else: open_surface(true)

func open_surface(replay: bool) -> void:
	var at := float(start) if replay else inspect_at
	if model.geometry(site,at).is_empty():
		if replay: debrief()
		else: readout.text = "Surface unavailable for this uncovered preview. Its assessment remains Unknown."
		return
	phase = "replay" if replay else "inspect"
	page.hide()
	for child in overlay.get_children(): child.queue_free()
	if is_instance_valid(world):
		remove_child(world)
		world.queue_free()
	world = SiteWorld.new(site)
	add_child(world)
	world.set_time(at)
	var ground := world.ground_y(Vector2.ZERO)
	inspector = Astronaut.new()
	world.add_child(inspector)
	inspector.position = Vector3(0,ground+1,5)
	var sun := world.sun_dir(at)
	inspector.face(atan2(-sun.x,-sun.z))
	inspector.frozen = replay
	camera = Camera3D.new()
	camera.far = 6500
	world.add_child(camera)
	camera.position = Vector3(10,ground+7,16)
	camera.look_at(Vector3(0,ground+1,0))
	camera.make_current()
	var marker := Label3D.new()
	marker.text = "FIXED SCIENCE OBSERVER / 1 m\nDecorative surface; use Horizon View for measured ridge"
	marker.position = Vector3(0,ground+2,0)
	marker.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	marker.font_size = 30
	marker.pixel_size = .012
	world.add_child(marker)
	instrument = MeshInstance3D.new()
	var mesh := CylinderMesh.new()
	mesh.top_radius = .5
	mesh.bottom_radius = .7
	mesh.height = 1.0
	instrument.mesh = mesh
	instrument.position = Vector3(2,ground+.5,0)
	var mat := StandardMaterial3D.new()
	mat.albedo_color = TEAL
	instrument.material_override = mat
	world.add_child(instrument)
	var panel := UIKit.panel("hud")
	panel.set_anchors_and_offsets_preset(Control.PRESET_TOP_WIDE)
	panel.offset_left = 20
	panel.offset_top = 20
	panel.offset_right = -20
	overlay.add_child(panel)
	var col := UIKit.vbox(8)
	panel.add_child(col)
	replay_label = UIKit.label("",16,CREAM,true)
	col.add_child(replay_label)
	replay_bar = ProgressBar.new()
	replay_bar.max_value = 12
	col.add_child(replay_bar)
	var row := HBoxContainer.new()
	col.add_child(row)
	var back := button("SKIP REPLAY / DEBRIEF" if replay else "BACK TO PLANNER",debrief if replay else plan_screen)
	row.add_child(back)
	row.add_child(button("THIRD PERSON",func() -> void: inspector.set_view(false); inspector.camera.make_current()))
	row.add_child(button("FIRST PERSON",func() -> void: inspector.set_view(true); inspector.camera.make_current()))
	row.add_child(button("SURVEY",func() -> void: camera.make_current()))
	back.grab_focus()
	if not replay:
		inspector.frozen = false
		replay_label.text = "SURFACE INSPECTION / WASD move, drag to look. Assessment stays at the marked 1 m observer. The terrain presentation is illustrative."

func _process(delta: float) -> void:
	if phase != "replay": return
	replay_elapsed = minf(12,replay_elapsed+delta)
	var at: float = int(submitted.start)+replay_elapsed/12*model.duration()
	world.set_time(at)
	var setting_up: bool = at < int(result.setup_end)
	inspector.scanning = setting_up
	instrument.scale.y = .35+minf(1,replay_elapsed/3)*.65 if setting_up else 1
	var p: Dictionary = model.geometry(submitted.site,at)
	replay_label.text = "%s / %s / %s\nIllustrative astronaut activity. The submitted assessment is fixed; skip gives the identical result." % ["SETUP" if setting_up else "OBSERVATION",utc(at),p.get("state","UNKNOWN")]
	replay_bar.value = replay_elapsed
	if replay_elapsed >= 12: debrief()

func debrief() -> void:
	phase = "debrief"
	if is_instance_valid(inspector): inspector.frozen = true
	clear_body()
	text("OPERATIONS DEBRIEF / " + str(result.illumination).to_upper(),CREAM,28)
	text(summary(result))
	text("Sources: JPL Horizons DE441; " + str(model.records[result.site].site.terrain_source) + ". " + str(model.records[result.site].status),Color("aabcc7"),13)
	text("Prediction: %s. %s Predictions and replay do not affect the calculation." % [prediction,"Your prediction matched the assessment." if prediction == result.illumination else "Compare your prediction with the first limiting event."],TEAL)
	var interval: Array = result.continuous
	text("Assessed nominal continuous interval: " + (utc(interval[0])+" through "+utc(interval[1]) if interval.size() == 2 else "none at setup start / unresolved") + ". Full disk clearance is required throughout both activities.")
	text("Electrical evidence needed: validated array output/pointing, activity loads, storage, initial state and operating limits. Thermal evidence needed: material properties, coupling, initial temperatures, environment and operating limits.",Color("aabcc7"))
	text("File a supported window, alternate-site recommendation, or hold. Every outcome can reach the Mission Log without retrying.",TEAL)
	var choice := OptionButton.new()
	for item: String in ["Recommend this window","Recommend compared alternative","Hold pending evidence"]: choice.add_item(item)
	choice.select(0 if result.illumination == "Meets" else 2)
	recommendation = choice.get_item_text(choice.selected)
	choice.item_selected.connect(func(i: int) -> void: recommendation = choice.get_item_text(i))
	body.add_child(choice)
	var note := TextEdit.new()
	note.custom_minimum_size.y = 100
	note.placeholder_text = "Explain the evidence behind your recommendation (optional)."
	body.add_child(note)
	var row := actions()
	var file := button("FILE MISSION LOG BRIEF",func() -> void: file_brief(note.text))
	row.add_child(file)
	row.add_child(button("REVISE CURRENT PLAN",plan_screen))
	file.grab_focus()

func file_brief(note: String = "") -> void:
	var entry: Dictionary = model.brief(submitted,submitted_alternative,result,prediction,recommendation)
	entry.player_note = note
	entry.alternative_assessment = model.assess(submitted_alternative)
	log_entries.append(entry.duplicate(true))
	var file := FileAccess.open(log_path,FileAccess.WRITE)
	if file != null:
		file.store_string(JSON.stringify(log_entries,"\t"))
		file.close()
	show_log()

func show_log() -> void:
	phase = "log"
	clear_body()
	text("MISSION LOG / LAST LIGHT OPERATIONS",CREAM,26)
	text("Briefs retain submitted coordinates, observer settings, UTC times, source hash, requirements, comparison and evidence. Saved on this device.",TEAL)
	for entry: Dictionary in log_entries:
		var plan: Dictionary = entry.plan
		var r: Dictionary = entry.assessment
		text("%s / %.4f N, %.4f E / %s\nSetup end: %s | Observation end: %s\nRequired full sunlight: %d min. Observer: %.1f m; %s\nCompared: %s / %s\nRecommendation: %s\n%s" % [site_name(plan.site),plan.coordinates.lat,plan.coordinates.lon,utc(plan.start),utc(r.setup_end),utc(r.end),(int(plan.requirements.setup_s)+int(plan.requirements.observation_s))/60,plan.observer.height_m,plan.observer.frame,site_name(entry.alternative.site),utc(entry.alternative.start),entry.recommendation,entry.get("player_note","")],TEAL)
		text(summary(r))
		var continuous: Array = r.continuous
		text("Assessed nominal full-sun interval: " + (utc(continuous[0])+" through "+utc(continuous[1]) if continuous.size() == 2 else "none at setup start / unresolved") + "\nCompared alternative illumination: " + str(entry.alternative_assessment.illumination),Color("aabcc7"),13)
		text("Source: data/last_light.json -> data/mission.json / SHA256 " + str(plan.source_sha256) + "\n" + str(entry.missing_electrical) + "\n" + str(entry.missing_thermal),Color("aabcc7"),12)
	var row := actions()
	var revise := button("RETURN TO PLANNER",plan_screen)
	row.add_child(revise)
	row.add_child(button("MISSIONS",func() -> void: Game.goto("campaign")))
	revise.grab_focus()
