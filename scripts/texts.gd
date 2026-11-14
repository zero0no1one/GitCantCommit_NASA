class_name Texts
## Longer player-facing texts: site descriptions, how to play, the Science log, credits. Numbers come from the data.


## Short site title, location line and a description built from that site's data.
static func site_info(id: String) -> Dictionary:
	var s: Dictionary = Mission.sites[id]
	var el: Array = s.samples.sun_el
	var lo: float = el.min()
	var hi: float = el.max()
	var sk: Dictionary = s.skyline
	var where := "%.2f° %s, %.2f° %s" % [abs(s.lat), "N" if s.lat >= 0 else "S", abs(s.lon), "E" if s.lon >= 0 else "W"]
	if id == "apollo-11":
		return {"title": "Tranquility Base", "short": "Tranquility", "where": "Apollo 11 site · " + where,
			"text": "Smooth plains near the equator. The Sun rises once a month, climbs high (up to %.0f° here) " % hi
			+ "and stays up for about two weeks. The skyline only reaches %.1f°." % sk.max_deg}
	return {"title": "Connecting Ridge", "short": "Ridge", "where": "South pole · " + where,
		"text": "A ridge near the south pole. The Sun skims the horizon (between %.1f° and %.1f° here) " % [lo, hi]
		+ "and circles the sky once a month. The ridge looks down on its surroundings, so the skyline dips to %.1f°; " % sk.min_deg
		+ "distant peaks up to %.1f° can still hide the Sun." % sk.max_deg}


static func help() -> String:
	return ("[b][color=#ffd23f]THE JOB[/color][/b]\nYour rover needs a stretch of unbroken sunlight right after it "
		+ "lands, usually 6 hours. The [i]whole[/i] disc of the Sun has to stay above the skyline, seen from the "
		+ "solar panel 1 m above the ground. If any part of it slips behind the terrain, the rover stops.\n\n"
		+ "[b][color=#2ef2ff]1. PLAN[/color][/b]  Drag the time dial (or the Sun itself) to pick a touchdown time. "
		+ "The sun-path ribbon shows the next hours: [color=#ffd23f]gold[/color] is clear, "
		+ "[color=#ff5a36]red[/color] is blocked. The Sunlight Clock shows how long the light will last.\n"
		+ "[b][color=#2ef2ff]2. LAND[/color][/b]  Fly the lander into the ring. Thrust: Space / W / ↑ or hold the "
		+ "right side of the screen. Steer: A/D or ←/→, or the left side. Touch down slowly.\n"
		+ "[b][color=#2ef2ff]3. HOLD THE LIGHT[/color][/b]  While the rover drills, carry sample canisters to the "
		+ "lander (walk into them, then into the lander) and scan glowing rocks (aim and press E / tap SCAN). "
		+ "Move: WASD/arrows or the left stick (hold Shift, or push the stick all the way, to lunar-lope). Look: drag. "
		+ "Hop: Space. View: V.\n"
		+ "[b][color=#2ef2ff]4. DEBRIEF[/color][/b]  One star for a plan that holds the light, one for the bonus "
		+ "goal, one for beating par.\n\n"
		+ "[color=#9a9cc9]The sunlight hours are made-up mission requirements. The Sun, Earth and terrain are real "
		+ "data: open the Science log to see where they come from.[/color]")


static func science_log() -> String:
	var c: Dictionary = Mission.data.conventions
	var t := ("[b][color=#ffd23f]REAL DATA, GAME RULES[/color][/b]\n"
		+ "• Sun and Earth positions: NASA JPL Horizons, seen from each site, every 10 minutes (interpolated between).\n"
		+ "• Skylines: traced from LRO LOLA laser-altimeter terrain at 0.1° steps, out to 400 km, with the Moon's "
		+ "curvature and no atmosphere. The distant mountains you see on the horizon are built from the same numbers.\n"
		+ "• Skyline uncertainty is about ±%.1f°, which moves sunrise and sunset by minutes to hours at the pole. " % c.skyline_error_deg
		+ "Every mission has passing times that still pass with that error.\n"
		+ "• The pass/fail result always comes from the data. Your skill (landing, samples, scans) changes the score "
		+ "and stars, never whether the Sun was up.\n"
		+ "• The landing ring is a few tens of metres wide: too small to change the skyline, so the plan's result holds "
		+ "wherever you set down inside it. Time is frozen while you fly.\n"
		+ "• Earth \"in view\" means the centre of its disc is above the skyline. Geometry only; no claim about radio.\n"
		+ "• Ground detail closer than ~600 m (small craters, rocks) is illustrative and kept below the skyline.\n"
		+ "• The sampling hours (2, 6 or 8) are fictional mission requirements.\n\n"
		+ "[b][color=#ffd23f]THE TWO SITES[/color][/b]\n")
	for id in Mission.site_ids:
		var info := site_info(id)
		t += "[b]%s[/b] (%s)\n%s\n\n" % [info.title, info.where, info.text]
	return t


static func credits() -> String:
	var t := ("[b]SUNLINE[/b], a NASA Space Apps Challenge 2026 entry (Lunar Landing Site Navigator) by team "
		+ "GitCantCommit.\n\n[b][color=#ffd23f]DATA[/color][/b]\n")
	for s: Dictionary in Mission.data.sources:
		t += "• [url=%s]%s[/url]%s\n" % [s.url, s.name, (" · doi:" + s.doi) if s.has("doi") else ""]
	t += ("\n[b][color=#ffd23f]MADE WITH[/color][/b]\n• Godot Engine 4.7 (MIT) · Blender 5.2.\n"
		+ "• Astronaut, rover, survey beacon, Sun and Earth models: made by our team with MINT. The astronaut is "
		+ "rigged and animated on our own Blender skeleton.\n"
		+ "• Lander, rocks, terrain and Moon globe: built procedurally in Blender from the mission data.\n"
		+ "• Fonts: Russo One and Chakra Petch (SIL Open Font License).\n"
		+ "• Sound: synthesised in the game.\n"
		+ "• Moon textures from LOLA LDEM_4.\n\n"
		+ "[b][color=#ffd23f]AI USE[/color][/b]\nCode and several 3D models were made with help from AI tools "
		+ "(including MINT for the team models). Sun and Earth models are illustrative: their positions and sizes "
		+ "come from the Horizons data, never from the meshes.\n\n"
		+ "Full credits and licences: [url=https://github.com/zero0no1one/GitCantCommit_NASA/blob/main/CREDITS.md]CREDITS.md[/url]")
	return t
