class_name Operations
extends RefCounted
## Phase 2 assessments are independent of arcade scoring. No unverified flight constants.

const DURATION_S := 21600
const CONTACT_S := 1800 # Training objective, not a historical specification.
const SOURCES := [
	["Surveyor batteries: configuration verification pending", "https://ntrs.nasa.gov/citations/19700010014"],
	["DSN 810-005: Coverage and Geometry (301M)", "https://deepspace.jpl.nasa.gov/dsndocs/810-005/301/301M.pdf"],
	["Blue Ghost educational context (not Surveyor performance)", "https://www.nasa.gov/news-release/nasa-firefly-invite-media-to-discuss-end-of-blue-ghost-moon-mission/"],
	["QuickMap: exploration, not a numerical data source", "https://quickmap.lroc.asu.edu/"],
	["Moon Trek: educational comparison", "https://trek.nasa.gov/moon/"],
	["CSA: Moon exploration context", "https://www.asc-csa.gc.ca/eng/astronomy/moon-exploration/"],
]

static func catalog(intro: Dictionary, window: Dictionary) -> Array:
	var first := intro.duplicate(true)
	first.title = "Science Outpost"
	first.tagline = "Introduction: choose a site and a window of sunlight."
	first.brief = "Plan an introductory sunlight window. This arcade exercise assesses illumination only; it does not model electrical or thermal survival. The astronaut is a virtual inspection aid."
	first.sites = ["apollo-11", "sl3"]
	var result: Array = [first]
	for spec in [["sunset-operations", "Sunset Operations", "Can assigned work continue when sunlight is interrupted?"],
		["earth-link", "Earth Link", "When can a supported signal reach Goldstone DSS-14?"],
		["polar-ice-scout", "Polar Ice Scout", "Future roadmap: investigate polar resources."]]:
		result.append({"id": spec[0], "title": spec[1], "tagline": spec[2], "number": result.size() + 1,
			"sites": ["apollo-11", "sl3"], "operations": true, "roadmap": spec[0] == "polar-ice-scout",
			"window": {"start": window.start_unix, "end": int(window.end_unix) - DURATION_S, "step": 600},
			"need_s": DURATION_S})
	return result

static func covered(data: Dictionary, site: String, start: int, duration: int = 0) -> bool:
	if not data.has("window") or duration < 0:
		return false
	if start < int(data.window.start_unix) or start + duration > int(data.window.end_unix):
		return false
	for s: Dictionary in data.get("sites", []):
		if s.id == site:
			return true
	return false

static func contains(intervals: Array, at: int) -> bool:
	for iv: Array in intervals:
		if at >= int(iv[0]) and at <= int(iv[1]):
			return true
	return false

static func illumination(intervals: Dictionary, at: int) -> String:
	if contains(intervals.get("sun_full", []), at):
		return "FULL"
	if contains(intervals.get("sun_any", []), at):
		return "PARTIAL"
	return "BLOCKED"

static func criterion(name: String, state: String, cause: String, evidence: String) -> Dictionary:
	return {"name": name, "state": state, "cause": cause, "evidence": evidence}

static func assess(data: Dictionary, site: String, start: int, mission_id: String, schedule: Array) -> Dictionary:
	var criteria: Array = []
	var coverage := covered(data, site, start, DURATION_S)
	criteria.append(criterion("Six-hour interval inside data coverage", "met" if coverage else "unknown",
		"Training interval: six hours; dates are hypothetical, not a Surveyor reconstruction.", "data/mission.json: window"))
	var planned_s := 0
	for block: Dictionary in schedule:
		planned_s += int(block.get("duration_s", 0))
	criteria.append(criterion("Schedule fills six hours", "met" if planned_s == DURATION_S else "violated",
		"Requested activities are intentions until matched to a verified flight mode.", "Training rule: sum of scheduled durations"))
	if mission_id == "sunset-operations":
		var interruption := false
		if coverage:
			for s: Dictionary in data.sites:
				if s.id == site:
					# Full-disc interval boundaries, not a frame-rate dependent sample loop.
					var continuous := false
					for iv: Array in s.intervals.sun_full:
						if start >= int(iv[0]) and start + DURATION_S <= int(iv[1]):
							continuous = true
					interruption = not continuous
		criteria.append(criterion("Modeled full-sunlight interruption", ("met" if interruption else "violated") if coverage else "unknown",
			"Partial or blocked sunlight interrupts full-disc illumination; boundary uncertainty remains applicable.", "data/mission.json: sun_full intervals and boundary uncertainty"))
		criteria.append(criterion("Electrical endurance", "unknown",
			"Surveyor 1 flight battery configuration, initial charge, temperature, array pointing/output, activity loads and operating limits are not verified. No energy estimate or charging behavior is assumed.", "Surveyor power-system and battery reports: flight-specific extraction pending"))
	else:
		criteria.append(criterion("Earth visibility", "unknown",
			"Preview shows the Earth centre relative to terrain at the fixed observer. Continuous visibility over a selected contact must be checked separately; this is not a station-access test.", "data/mission.json: earth_up convention and intervals"))
		criteria.append(criterion("DSS-14 station geometry", "unknown",
			"Earth-centre visibility does not locate DSS-14. Station vectors, horizon mask and pointing constraints are not bundled.", "DSN 810-005, module 301; station ephemeris pending"))
		criteria.append(criterion("Signal reception and continuous 30-minute downlink", "unknown",
			"30 minutes is a training objective. Surveyor 1 telemetry configuration, antenna gain/pointing, range, receiver noise and signal-specific reception criteria need verification.", "Surveyor telecommunications report and applicable DSN signal modules: verification pending"))
	var state := "met"
	for c: Dictionary in criteria:
		if c.state == "unknown" and state == "met":
			state = "unknown"
		if c.state == "violated":
			state = "violated"
	return {"state": state, "criteria": criteria, "site": site, "start": start,
		"duration_s": DURATION_S, "schedule": schedule.duplicate(true), "scored": false}
