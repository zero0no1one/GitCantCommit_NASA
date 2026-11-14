extends Node
## Arcade sound effects and a menu/mission ambience, synthesised at start-up (no audio files to download or
## license). Registered as the `Sfx` autoload.  Sfx.play("click"), Sfx.loop("thrust", on), Sfx.music("menu").
## Browsers only start audio after the first click or key; Godot resumes the audio context by itself then.

const RATE := 22050

var muted := false
var _streams := {}
var _players: Array[AudioStreamPlayer] = []
var _loops := {}
var _music: AudioStreamPlayer
var _music_name := ""


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	_streams = {
		"hover": _tone([2600.0], 0.025, 0.12, "square"),
		"click": _tone([1400.0, 1900.0], 0.05, 0.3, "square"),
		"confirm": _tone([660.0, 880.0, 1320.0], 0.16, 0.35, "square"),
		"back": _tone([900.0, 600.0], 0.08, 0.28, "square"),
		"tick": _tone([1800.0], 0.02, 0.15, "sine"),
		"star": _tone([1046.0, 1318.0, 1568.0, 2093.0], 0.32, 0.4, "sine"),
		"pickup": _tone([700.0, 1050.0, 1400.0], 0.12, 0.35, "square"),
		"deliver": _tone([523.0, 659.0, 784.0, 1046.0], 0.28, 0.4, "square"),
		"scan": _sweep(500.0, 1700.0, 0.35, 0.3),
		"fail": _tone([440.0, 330.0, 220.0], 0.45, 0.4, "saw"),
		"win": _tone([523.0, 659.0, 784.0, 1046.0, 1318.0], 0.6, 0.4, "square"),
		"alarm": _alarm(),
		"touchdown": _thump(),
		"crash": _noise_burst(0.7, 0.6),
		"thrust": _noise_loop(0.6, 0.35),
	}
	for i in 8:
		var p := AudioStreamPlayer.new()
		add_child(p)
		_players.append(p)
	_music = AudioStreamPlayer.new()
	_music.volume_db = -14.0
	add_child(_music)


func play(name: String, pitch := 1.0, volume_db := 0.0) -> void:
	if muted or not _streams.has(name):
		return
	for p in _players:
		if not p.playing:
			p.stream = _streams[name]
			p.pitch_scale = pitch
			p.volume_db = volume_db
			p.play()
			return


## Start or stop a looping effect ("thrust").
func loop(name: String, on: bool, volume_db := -4.0) -> void:
	if not _loops.has(name):
		var p := AudioStreamPlayer.new()
		p.stream = _streams[name]
		add_child(p)
		_loops[name] = p
	var lp: AudioStreamPlayer = _loops[name]
	lp.volume_db = volume_db
	if on and not muted and not lp.playing:
		lp.play()
	elif not on and lp.playing:
		lp.stop()


func music(name: String) -> void:
	if name == _music_name:
		return
	_music_name = name
	_music.stop()
	if name != "" and not muted:
		var key := "music_" + name
		if not _streams.has(key):		# built on first use: a few hundred ms of GDScript
			_streams[key] = _pad([110.0, 164.8, 220.0, 277.2] if name == "menu" else [98.0, 146.8, 196.0, 233.1], 6.0)
		_music.stream = _streams[key]
		_music.play()


func set_muted(m: bool) -> void:
	muted = m
	if m:
		_music.stop()
		for k in _loops:
			_loops[k].stop()
	else:
		var n := _music_name
		_music_name = ""
		music(n)


# ---------------------------------------------------------------- synthesis

func _wav(samples: PackedFloat32Array, looped := false) -> AudioStreamWAV:
	var bytes := PackedByteArray()
	bytes.resize(samples.size() * 2)
	for i in samples.size():
		bytes.encode_s16(i * 2, int(clampf(samples[i], -1.0, 1.0) * 32000.0))
	var w := AudioStreamWAV.new()
	w.format = AudioStreamWAV.FORMAT_16_BITS
	w.mix_rate = RATE
	w.data = bytes
	if looped:
		w.loop_mode = AudioStreamWAV.LOOP_FORWARD
		w.loop_end = samples.size()
	return w


func _osc(kind: String, phase: float) -> float:
	match kind:
		"square":
			return 1.0 if fmod(phase, 1.0) < 0.5 else -1.0
		"saw":
			return fmod(phase, 1.0) * 2.0 - 1.0
	return sin(phase * TAU)


## Notes played one after another over `dur` seconds, each with a quick decay.
func _tone(freqs: Array, dur: float, amp: float, kind: String) -> AudioStreamWAV:
	var n := int(dur * RATE)
	var s := PackedFloat32Array()
	s.resize(n)
	var per := n / freqs.size()
	var phase := 0.0
	for i in n:
		var k := mini(i / per, freqs.size() - 1)
		var local := float(i - k * per) / per
		phase += freqs[k] / RATE
		var env := (1.0 - local) * minf(1.0, float(i) / 40.0)
		s[i] = _osc(kind, phase) * amp * env * (0.6 if kind == "square" else 1.0)
	return _wav(s)


func _sweep(f0: float, f1: float, dur: float, amp: float) -> AudioStreamWAV:
	var n := int(dur * RATE)
	var s := PackedFloat32Array()
	s.resize(n)
	var phase := 0.0
	for i in n:
		var x := float(i) / n
		phase += lerpf(f0, f1, x) / RATE
		s[i] = sin(phase * TAU) * amp * sin(x * PI)
	return _wav(s)


func _alarm() -> AudioStreamWAV:
	var n := int(0.8 * RATE)
	var s := PackedFloat32Array()
	s.resize(n)
	var phase := 0.0
	for i in n:
		var f := 740.0 if (i / (RATE / 5)) % 2 == 0 else 520.0
		phase += f / RATE
		s[i] = _osc("square", phase) * 0.22
	return _wav(s)


func _thump() -> AudioStreamWAV:
	var n := int(0.5 * RATE)
	var s := PackedFloat32Array()
	s.resize(n)
	var phase := 0.0
	var rng := RandomNumberGenerator.new()
	rng.seed = 7
	for i in n:
		var x := float(i) / n
		phase += lerpf(120.0, 40.0, x) / RATE
		s[i] = (sin(phase * TAU) * 0.7 + rng.randf_range(-1, 1) * 0.25 * (1.0 - x)) * pow(1.0 - x, 2.0)
	return _wav(s)


func _noise_burst(dur: float, amp: float) -> AudioStreamWAV:
	var n := int(dur * RATE)
	var s := PackedFloat32Array()
	s.resize(n)
	var rng := RandomNumberGenerator.new()
	rng.seed = 11
	var lp := 0.0
	for i in n:
		var x := float(i) / n
		lp = lerpf(lp, rng.randf_range(-1, 1), 0.25)
		s[i] = lp * amp * pow(1.0 - x, 1.5)
	return _wav(s)


## Low rumble that loops seamlessly (crossfaded ends).
func _noise_loop(dur: float, amp: float) -> AudioStreamWAV:
	var n := int(dur * RATE)
	var s := PackedFloat32Array()
	s.resize(n)
	var rng := RandomNumberGenerator.new()
	rng.seed = 3
	var lp := 0.0
	for i in n:
		lp = lerpf(lp, rng.randf_range(-1, 1), 0.08)
		s[i] = lp * amp * 2.5
	var fade := RATE / 20
	for i in fade:
		var a := float(i) / fade
		s[i] = s[i] * a + s[n - fade + i] * (1.0 - a)
	return _wav(s.slice(0, n - fade), true)


## Slow ambient chord with a gentle swell; loops.
func _pad(freqs: Array, dur: float) -> AudioStreamWAV:
	var n := int(dur * RATE)
	var s := PackedFloat32Array()
	s.resize(n)
	for i in n:
		var t := float(i) / RATE
		var v := 0.0
		for j in freqs.size():
			var f: float = freqs[j]
			# whole cycles per loop keep it seamless
			f = round(f * dur) / dur
			v += sin(TAU * f * t) * (0.6 + 0.4 * sin(TAU * t / dur * (j + 1)))
		s[i] = v / freqs.size() * 0.35
	return _wav(s, true)
