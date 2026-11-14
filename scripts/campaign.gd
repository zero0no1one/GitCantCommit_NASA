extends Node
## The mission campaign (res://data/campaign.json, built and checked by tools/data/build_campaign.py) and the
## player's progress (stars and best score per mission, saved to user://progress.cfg; IndexedDB on the web).
## Registered as the `Campaign` autoload.

const PATH := "res://data/campaign.json"
const SAVE := "user://progress.cfg"

var missions: Array = []
var by_id := {}
var error := ""

var _cfg := ConfigFile.new()


func _ready() -> void:
	var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(PATH))
	if typeof(parsed) != TYPE_DICTIONARY:
		error = "cannot read " + PATH
		push_error(error)
		return
	missions = parsed.missions
	for m: Dictionary in missions:
		by_id[m.id] = m
	_cfg.load(SAVE)		# a missing file just means no progress yet


func index_of(id: String) -> int:
	for i in missions.size():
		if missions[i].id == id:
			return i
	return -1


func stars(id: String) -> int:
	return int(_cfg.get_value(id, "stars", 0))


func best(id: String) -> int:
	return int(_cfg.get_value(id, "best", 0))


func total_stars() -> int:
	var n := 0
	for m: Dictionary in missions:
		n += stars(m.id)
	return n


## Mission 1 is always open; each later one opens when the one before has at least one star.
func unlocked(id: String) -> bool:
	var i := index_of(id)
	return i == 0 or (i > 0 and stars(missions[i - 1].id) > 0)


## First unlocked mission without stars, else the last one played.
func next_up() -> String:
	for m: Dictionary in missions:
		if unlocked(m.id) and stars(m.id) == 0:
			return m.id
	return missions[missions.size() - 1].id


func next_after(id: String) -> String:
	var i := index_of(id)
	return missions[i + 1].id if i >= 0 and i + 1 < missions.size() else ""


func has_progress() -> bool:
	return total_stars() > 0


## Keeps the best of each; returns true when it is a new best score.
func record(id: String, new_stars: int, score: int) -> bool:
	var better := score > best(id)
	_cfg.set_value(id, "stars", maxi(stars(id), new_stars))
	_cfg.set_value(id, "best", maxi(best(id), score))
	_cfg.save(SAVE)
	return better


func reset() -> void:
	_cfg = ConfigFile.new()
	_cfg.save(SAVE)
