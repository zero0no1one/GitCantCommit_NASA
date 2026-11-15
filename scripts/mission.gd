extends Node
## Loads the bundled mission dataset (res://data/mission.json, built by tools/data/build_mission.py) once at
## start-up and answers simple lookups. Registered as the `Mission` autoload.
##
## Times are UTC unix seconds; angles are degrees (azimuth from lunar north, clockwise). See the
## "conventions" block of mission.json.

const PATH := "res://data/mission.json"

var data: Dictionary = {}
var sites: Dictionary = {}		# site id -> site dictionary
var site_ids: PackedStringArray = []
var error := ""


func _ready() -> void:
	_load()


func is_loaded() -> bool:
	return error.is_empty() and not data.is_empty()


func _load() -> void:
	var f := FileAccess.open(PATH, FileAccess.READ)
	if f == null:
		error = "cannot open %s (%s)" % [PATH, error_string(FileAccess.get_open_error())]
		push_error(error)
		return
	var parsed: Variant = JSON.parse_string(f.get_as_text())
	if typeof(parsed) != TYPE_DICTIONARY or not parsed.has("sites"):
		error = "%s is not a valid mission file" % PATH
		push_error(error)
		return
	data = parsed
	for s: Dictionary in data.sites:
		sites[s.id] = s
		site_ids.append(s.id)


## Linearly interpolated sample at `unix` for one series of a site: sun_az, sun_el, sun_radius, earth_az,
## earth_el or earth_radius. Azimuths interpolate along the short way round. Clamped to the dataset window.
func sample(site_id: String, key: String, unix: float) -> float:
	var s: Dictionary = sites[site_id].samples
	var x := (unix - float(s.start_unix)) / float(s.step_s)
	var i := clampi(floori(x), 0, int(s.count) - 2)
	var t := clampf(x - i, 0.0, 1.0)
	var a: float = s[key][i]
	var b: float = s[key][i + 1]
	if key.ends_with("_az"):
		return fposmod(rad_to_deg(lerp_angle(deg_to_rad(a), deg_to_rad(b), t)), 360.0)
	return lerpf(a, b, t)


## Terrain skyline elevation (deg) toward azimuth `az` (deg), linearly interpolated between the 0.1° rays.
func skyline(site_id: String, az: float) -> float:
	var sk: Dictionary = sites[site_id].skyline
	var el: Array = sk.elevation_deg
	var x := fposmod(az, 360.0) / float(sk.azimuth_step_deg)
	var i := floori(x)
	return lerpf(el[i % el.size()], el[(i + 1) % el.size()], x - i)


## "2028-02-18 00:00 UTC" style label for a unix time.
static func utc_label(unix: float) -> String:
	return Time.get_datetime_string_from_unix_time(int(unix), true).left(16) + " UTC"
