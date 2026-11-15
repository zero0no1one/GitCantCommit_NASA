extends Node
## Session-only decisions. Never adds provisional records to Mission's scoring catalog.
signal changed
const WINDOWS := ["viper-era", "artemis-iv-era", "artemis-v-era"]
var records: Dictionary = {}
var cards: Array[Dictionary] = []
var briefs: Array[Dictionary] = []
var same_time := true
var active_index := 0
var mission_plan_initialized := false

func _ready() -> void:
	for window: String in WINDOWS:
		var path := "res://data/exploration/%s.json" % window
		var pack: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(path))
		for site: Dictionary in pack.sites:
			records[window + "/" + str(site.id)] = {"site": site, "verified": false, "source": path, "version": FileAccess.get_sha256(path)}
	var path := "res://data/mission.json"
	var original: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(path))
	for site: Dictionary in original.sites:
		records["artemis-iv-era/" + str(site.id)] = {"site": site, "verified": true, "source": path, "version": FileAccess.get_sha256(path)}
	for id: String in ["apollo-11", "sl3"]:
		var key := "artemis-iv-era/" + id
		cards.append({"key": key, "start": int(records[key].site.samples.start_unix), "duration": 21600})

func set_card(index: int, key: String, start: int, duration: int) -> void:
	if not records.has(key) or index < 0 or index >= cards.size():
		return
	cards[index].merge({"key": key, "start": start, "duration": duration}, true)
	if same_time:
		for card: Dictionary in cards:
			card.start = start
	changed.emit()

func sample(card: Dictionary, field: String) -> Variant:
	var s: Dictionary = records[card.key].site.samples
	var x := (float(card.start) - float(s.start_unix)) / float(s.step_s)
	if x < 0 or x > int(s.count) - 1:
		return null
	var i := mini(floori(x), int(s.count) - 2)
	var a := float(s[field][i])
	var b := float(s[field][i + 1])
	return fposmod(rad_to_deg(lerp_angle(deg_to_rad(a), deg_to_rad(b), x-i)), 360.0) if field.ends_with("_az") else lerpf(a, b, x-i)

func assess(card: Dictionary) -> Dictionary:
	var record: Dictionary = records[card.key]
	var site: Dictionary = record.site
	var s: Dictionary = site.samples
	var end := int(s.start_unix) + (int(s.count)-1)*int(s.step_s)
	var covered := int(card.start) >= int(s.start_unix) and int(card.start)+int(card.duration) <= end and int(card.duration) >= 600 and int(card.duration) <= 86400 and int(card.duration)%600 == 0
	var r := {"covered": covered, "status": "validated original model" if record.verified else "UNVERIFIED PREVIEW", "sun": "unknown", "earth": "unknown", "hazards": "unknown", "power": "unknown", "thermal": "unknown", "radio": "unknown", "feasibility": "unknown", "events": [], "source": record.source, "version": record.version, "uncertainty": "±0.1° skyline sensitivity only; incomplete uncertainty budget; observer height 1 m assumed"}
	if not covered or not record.verified:
		return r
	r.sun = "supported" if Scoring.evaluate(site.intervals.sun_full, int(card.start), end, int(card.duration))["pass"] else "concern"
	r.earth = "concern"
	for iv: Array in site.intervals.earth_up:
		if int(iv[0]) <= int(card.start) and int(iv[1])+1 >= int(card.start)+int(card.duration):
			r.earth = "supported"
	var full_s := 0
	for iv: Array in site.intervals.sun_full:
		full_s += maxi(0, mini(int(iv[1])+1, int(card.start)+int(card.duration))-maxi(int(iv[0]), int(card.start)))
	r["full_s"] = full_s
	for field: String in ["sun_full", "sun_any", "earth_up"]:
		var event := Scoring.next_change(site.intervals[field], int(card.start))
		var t := int(event.change)
		if t > int(card.start) and t < end:
			var label := "Full-disc sunlight ends" if field == "sun_full" and event.inside else "Full-disc sunlight begins"
			if field == "sun_any": label = "Sun fully hidden" if event.inside else "First sunlight"
			if field == "earth_up": label = "Earth-center set" if event.inside else "Earth-center rise"
			var band := "sensitivity unavailable" if int(event.uncertainty_s) == 0 else "±%d s skyline sensitivity" % event.uncertainty_s
			r.events.append("%s: %s; %s (10-minute samples, interpolated; terrain model)" % [label, Mission.utc_label(t), band])
	return r

func save_brief(summaries: Array = []) -> Dictionary:
	var brief := {"cards": cards.duplicate(true), "results": [], "summaries": summaries.duplicate(true)}
	for card: Dictionary in cards:
		brief.results.append(assess(card).duplicate(true))
	briefs.append(brief.duplicate(true))
	return brief.duplicate(true)
