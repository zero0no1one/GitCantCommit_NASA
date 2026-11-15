extends SceneTree
## Campaign parity: every mission's example touchdowns (chosen and checked in Python by
## tools/data/build_campaign.py) give the same pass/fail in the GDScript port, at the mission's required hours.
## Run:  godot --headless --path . --script res://tests/test_campaign.gd

const Score := preload("res://scripts/scoring.gd")

var _fails := 0
var _checks := 0


func _init() -> void:
	var mission: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://data/mission.json"))
	var campaign: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://data/campaign.json"))
	var sites := {}
	for s: Dictionary in mission.sites:
		sites[s.id] = s
	var end := int(mission.window.end_unix)
	_check(campaign.missions.size() == 8, "8 missions")
	for m: Dictionary in campaign.missions:
		var any_pass := false
		for sid: String in m.sites:
			var st: Dictionary = m.stats[sid]
			var iv: Array = sites[sid].intervals.sun_full
			if st.example_pass != null:
				any_pass = true
				_check(Score.evaluate(iv, int(st.example_pass), end, int(m.need_s)).pass, "%s/%s example pass" % [m.id, sid])
			if st.example_fail != null:
				_check(not Score.evaluate(iv, int(st.example_fail), end, int(m.need_s)).pass, "%s/%s example fail" % [m.id, sid])
			# pass counts across the whole decision window match the Python stats
			var n := 0
			var t := int(m.window.start)
			while t <= int(m.window.end):
				if Score.evaluate(iv, t, end, int(m.need_s)).pass:
					n += 1
				t += int(m.window.step)
			_check(n == int(st.passes), "%s/%s pass count %d == %d" % [m.id, sid, n, int(st.passes)])
		_check(any_pass, "%s has a passing touchdown" % m.id)
	print("test_campaign: %d checks, %d failed" % [_checks, _fails])
	quit(1 if _fails > 0 else 0)


func _check(ok: bool, what: String) -> void:
	_checks += 1
	if not ok:
		_fails += 1
		printerr("FAIL: " + what)
