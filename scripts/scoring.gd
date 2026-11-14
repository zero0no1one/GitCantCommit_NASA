class_name Scoring
## The mission rule, ported from tools/data/sunline_data/scoring.py (the Python file is the reference;
## tests/test_scoring.gd checks this port against tools/data/golden_results.json).
##
## Intervals are [start_unix, end_unix, ...] where the end is the LAST second inside, i.e. the span [a, b+1).
## The sampling block is [touchdown, touchdown + 6 h). The 6 h requirement is fictional (see mission.json).
## The timeline, sky markers, lighting, replay and result screens all read from these functions.

const SAMPLING_S := 21600


## Mission result for a touchdown time, from the precomputed full-disc sunlight intervals.
## Returns {pass, touchdown, sampling_end, interruption, sampled_s, remaining_s, margin_s, margin_open}, with
## interruption and margin_s null when they do not apply (same keys and values as the Python evaluate()).
static func evaluate(sun_full: Array, touchdown: int, data_end: int, need_s := SAMPLING_S) -> Dictionary:
	var finish := touchdown + need_s
	assert(finish <= data_end, "touchdown too late: the dataset ends before the sampling block does")
	for iv: Array in sun_full:
		var a := int(iv[0])
		var b := int(iv[1])
		if a <= touchdown and touchdown <= b:
			if b + 1 >= finish:
				var open_end := b >= data_end
				return {"pass": true, "touchdown": touchdown, "sampling_end": finish, "interruption": null,
					"sampled_s": need_s, "remaining_s": 0, "margin_s": (data_end if open_end else b + 1) - finish,
					"margin_open": open_end}
			var done := b + 1 - touchdown
			return {"pass": false, "touchdown": touchdown, "sampling_end": finish, "interruption": b + 1,
				"sampled_s": done, "remaining_s": need_s - done, "margin_s": null, "margin_open": false}
	return {"pass": false, "touchdown": touchdown, "sampling_end": finish, "interruption": touchdown,
		"sampled_s": 0, "remaining_s": need_s, "margin_s": null, "margin_open": false}


## Index of the interval containing second t, or -1.
static func find(intervals: Array, t: int) -> int:
	for i in intervals.size():
		if int(intervals[i][0]) <= t and t <= int(intervals[i][1]):
			return i
	return -1


## Where t sits relative to a set of intervals:
## {inside: bool, change: unix second of the next change (end+1 when inside, next start when outside) or -1 if none
##  inside the data, uncertainty_s: the listed uncertainty of that change (0 when not listed)}.
static func next_change(intervals: Array, t: int) -> Dictionary:
	var i := find(intervals, t)
	if i >= 0:
		var iv: Array = intervals[i]
		return {"inside": true, "change": int(iv[1]) + 1, "uncertainty_s": int(iv[3]) if iv.size() > 3 else 0}
	for iv: Array in intervals:
		if int(iv[0]) > t:
			return {"inside": false, "change": int(iv[0]), "uncertainty_s": int(iv[2]) if iv.size() > 2 else 0}
	return {"inside": false, "change": -1, "uncertainty_s": 0}


## "3 h 05 m" / "45 m" / "2 d 4 h" style duration.
static func duration_label(seconds: int) -> String:
	var m := int(round(abs(seconds) / 60.0))
	if m >= 48 * 60:
		return "%d d %d h" % [m / 1440, (m % 1440) / 60]
	if m >= 60:
		return "%d h %02d m" % [m / 60, m % 60]
	return "%d m" % m
