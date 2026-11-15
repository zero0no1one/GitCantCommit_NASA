extends RefCounted
## Single assessment service for all Last Light presentation and saved briefs.
const DATA := "res://data/last_light.json"
var package: Dictionary
var records: Dictionary = {}
var requirements: Dictionary

func _init() -> void:
	package = JSON.parse_string(FileAccess.get_file_as_string(DATA))
	requirements = package.requirements.duplicate(true)
	for record: Dictionary in package.records:
		records[record.id] = record

func duration() -> int:
	return int(requirements.setup_s) + int(requirements.observation_s)

func snapshot(site: String, start: int) -> Dictionary:
	var record: Dictionary = records[site]
	return {"site": site, "start": start, "coordinates": {"lat": record.site.lat, "lon": record.site.lon},
		"observer": record.observer.duplicate(true), "source_status": record.status,
		"source_sha256": package.source.sha256, "requirements": requirements.duplicate(true)}

func geometry(site: String, at: float) -> Dictionary:
	if not records.has(site): return {}
	var record: Dictionary = records[site]
	if at < record.coverage[0] or at > record.coverage[1]: return {}
	var s: Dictionary = record.site.samples
	var x := (at - float(s.start_unix)) / float(s.step_s)
	var i := mini(floori(x), int(s.count)-2)
	var p: Dictionary = {}
	for key: String in ["sun_az", "sun_el", "sun_radius"]:
		var a := float(s[key][i])
		var b := float(s[key][i+1])
		p[key] = fposmod(rad_to_deg(lerp_angle(deg_to_rad(a), deg_to_rad(b), x-i)), 360.0) if key.ends_with("_az") else lerpf(a, b, x-i)
	p.skyline = skyline(site, p.sun_az)
	p.state = "FULL" if float(p.sun_el)-float(p.sun_radius) >= float(p.skyline) else ("BLOCKED" if float(p.sun_el)+float(p.sun_radius) < float(p.skyline) else "PARTIAL")
	return p

func skyline(site: String, bearing: float) -> float:
	var sk: Dictionary = records[site].site.skyline
	var el: Array = sk.elevation_deg
	var x := fposmod(bearing, 360.0) / float(sk.azimuth_step_deg)
	var i := floori(x)
	return lerpf(float(el[i % el.size()]), float(el[(i+1) % el.size()]), x-i)

func containing(intervals: Array, start: int) -> Array:
	for iv: Array in intervals:
		if int(iv[0]) <= start and start <= int(iv[1]): return iv
	return []

func interval_result(record: Dictionary, start: int, seconds: int) -> String:
	var count := 0
	for variant: Dictionary in record.variants:
		var iv := containing(variant.full, start)
		if not iv.is_empty() and start+seconds <= int(iv[1])+1: count += 1
	return "Meets" if count == record.variants.size() else ("Misses" if count == 0 else "Unknown")

func assess(plan: Dictionary) -> Dictionary:
	var start := int(plan.start)
	var setup_s := int(plan.get("requirements", requirements).setup_s)
	var observation_s := int(plan.get("requirements", requirements).observation_s)
	var finish := start+setup_s+observation_s
	var r := {"site": plan.site, "start": start, "setup_end": start+setup_s, "end": finish,
		"illumination": "Unknown", "setup": "Unknown", "observation": "Unknown", "bonus": false,
		"electrical": "Unknown", "thermal": "Unknown", "limit": null, "margin_lower_s": null, "margin_upper_s": null,
		"margin_is_lower_bound": false, "continuous": [], "reason": "Source, terrain or observer definition unavailable.",
		"uncertainty": "Evaluated variants only; absolute terrain registration and complete physical uncertainty remain unverified."}
	if not records.has(str(plan.site)): return r
	var record: Dictionary = records[plan.site]
	if plan.get("observer", {}) != record.observer or plan.get("source_sha256", "") != package.source.sha256:
		r.reason = "Observer definition or source version differs from the evaluated package."
		return r
	if start < int(record.coverage[0]) or finish > int(record.coverage[1]) or setup_s <= 0 or observation_s <= 0:
		r.reason = "Required interval is outside bundled source coverage or activity durations are invalid. No extrapolation."
		return r
	r.illumination = interval_result(record, start, finish-start)
	r.setup = interval_result(record, start, setup_s)
	r.observation = interval_result(record, start+setup_s, observation_s)
	var nominal := containing(record.variants[0].full, start)
	if nominal.is_empty():
		r.limit = start
		r.reason = "Full sunlight is already absent at setup start (partial or blocked)."
	else:
		var coverage_end := int(record.coverage[1])
		r.continuous = [nominal[0], mini(int(nominal[1])+1, coverage_end)]
		r.limit = int(nominal[1])+1 if int(nominal[1]) < coverage_end else null
		r.reason = "First loss of full sunlight: terrain covers the lower solar limb." if r.limit != null else "No loss of full sunlight is modeled before source coverage ends."
		var lows: Array[int] = []
		var highs: Array[int] = []
		var all_lit := true
		var any_open := false
		for variant: Dictionary in record.variants:
			var iv := containing(variant.full, start)
			if iv.is_empty():
				all_lit = false
				continue
			var open := int(iv[1]) >= coverage_end
			any_open = any_open or open
			lows.append((coverage_end if open else int(iv[1])+1)-finish)
			highs.append((coverage_end if open else int(iv[1])+1)-finish)
		if all_lit:
			r.margin_lower_s = lows.min()
			r.margin_upper_s = null if any_open else highs.max()
			r.margin_is_lower_bound = any_open
			r.bonus = r.illumination == "Meets" and int(r.margin_lower_s) >= int(plan.get("requirements", requirements).bonus_margin_s)
	if r.illumination == "Unknown": r.reason += " Evaluated event times disagree on whether the complete schedule fits."
	return r

func brief(plan: Dictionary, alternative: Dictionary, result: Dictionary, prediction: String, recommendation: String) -> Dictionary:
	return {"mission": "Last Light Operations", "plan": plan.duplicate(true), "alternative": alternative.duplicate(true),
		"assessment": result.duplicate(true), "prediction": prediction, "recommendation": recommendation,
		"filed_utc": Time.get_datetime_string_from_system(true),
		"sources": package.source.duplicate(true), "package_sha256": FileAccess.get_sha256(DATA),
		"missing_electrical": "Validated array output and pointing, activity loads, storage, initial state and operating limits.",
		"missing_thermal": "Validated material properties, thermal coupling, initial temperatures, environment and operating limits."}
