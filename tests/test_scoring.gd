extends SceneTree
## Parity tests for scripts/scoring.gd against the Python reference (tools/data/golden_results.json).
## Run:  godot --headless --path . --script res://tests/test_scoring.gd
## Exit code 0 when every check passes.

const Score := preload("res://scripts/scoring.gd")
const H := 3600

var _fails := 0
var _checks := 0


func _init() -> void:
	_unit_cases()
	_golden_parity()
	print("test_scoring: %d checks, %d failed" % [_checks, _fails])
	quit(1 if _fails > 0 else 0)


func _check(ok: bool, what: String) -> void:
	_checks += 1
	if not ok:
		_fails += 1
		printerr("FAIL: " + what)


## The boundary cases from tools/data/tests/test_scoring.py.
func _unit_cases() -> void:
	var need := Score.SAMPLING_S
	var r := Score.evaluate([[0, need - 1]], 0, 10 * H)
	_check(r.pass and r.margin_s == 0, "exactly 6 h of sun passes with zero margin")
	r = Score.evaluate([[0, need - 2]], 0, 10 * H)
	_check(not r.pass and r.interruption == need - 1 and r.remaining_s == 1, "one second short fails")
	r = Score.evaluate([[0, need + 599]], 0, 10 * H)
	_check(r.pass and r.margin_s == 600, "margin counts the seconds after sampling")
	r = Score.evaluate([[5 * H, 20 * H]], H, 30 * H)
	_check(not r.pass and r.interruption == H and r.sampled_s == 0, "touchdown in darkness fails at once")
	r = Score.evaluate([[0, 10 * H]], 4 * H, 10 * H)
	_check(r.pass and r.margin_open, "sunlight to the end of the data is an open margin")
	var nc := Score.next_change([[10, 20, 0, 5], [40, 50, 3, 4]], 15)
	_check(nc.inside and nc.change == 21 and nc.uncertainty_s == 5, "next_change inside")
	nc = Score.next_change([[10, 20, 0, 5], [40, 50, 3, 4]], 25)
	_check(not nc.inside and nc.change == 40 and nc.uncertainty_s == 3, "next_change outside")
	nc = Score.next_change([[10, 20]], 30)
	_check(nc.change == -1, "next_change past the last interval")
	_check(Score.duration_label(3 * H + 300) == "3 h 05 m", "duration label")


## Every touchdown in the window, for both sites, must match the Python results exactly.
func _golden_parity() -> void:
	var mission: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://data/mission.json"))
	var golden: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://tools/data/golden_results.json"))
	_check(mission != null and golden != null, "data files load")
	var end := int(mission.window.end_unix)
	for s: Dictionary in mission.sites:
		var iv: Array = s.intervals.sun_full
		var want_all: Array = golden.results[s.id]
		var bad := 0
		for k in golden.touchdowns.size():
			var got := Score.evaluate(iv, int(golden.touchdowns[k]), end)
			if not _same(got, want_all[k]):
				bad += 1
				if bad <= 3:
					printerr("  %s @ %d: got %s want %s" % [s.id, int(golden.touchdowns[k]), got, want_all[k]])
		_check(bad == 0, "%s: %d touchdowns match the Python results (%d mismatches)" % [
			s.id, golden.touchdowns.size(), bad])
	var ex: Dictionary = mission.examples
	var sites := {}
	for s: Dictionary in mission.sites:
		sites[s.id] = s.intervals.sun_full
	_check(Score.evaluate(sites[ex.same_site.site], int(ex.same_site.pass_touchdown), end).pass, "same-site pass example")
	_check(not Score.evaluate(sites[ex.same_site.site], int(ex.same_site.fail_touchdown), end).pass, "same-site fail example")
	for key in ["same_time", "same_time_reverse"]:
		if ex.has(key):
			var b: Dictionary = ex[key]
			_check(Score.evaluate(sites[b.winner], int(b.touchdown), end).pass, key + " winner passes")
			_check(not Score.evaluate(sites[b.loser], int(b.touchdown), end).pass, key + " loser fails")


## JSON numbers arrive as floats; compare values, treating null alike.
func _same(got: Dictionary, want: Dictionary) -> bool:
	for k in want:
		var a: Variant = got.get(k)
		var b: Variant = want[k]
		if a == null or b == null:
			if a != b:
				return false
		elif typeof(b) == TYPE_BOOL:
			if bool(a) != b:
				return false
		elif int(a) != int(b):
			return false
	return true
