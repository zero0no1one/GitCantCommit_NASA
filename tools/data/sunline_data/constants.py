"""Fixed numbers and conventions shared by every step of the pipeline."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]          # tools/data
SOURCE = ROOT/'source'                               # input terrain and ephemeris files
RAW = ROOT/'raw'                                     # cached JPL Horizons responses
REPO = ROOT.parents[1]                               # the Godot project
MISSION_JSON = REPO/'data'/'mission.json'
GOLDEN_JSON = ROOT/'golden_results.json'

MOON_RADIUS_M = 1_737_400.0      # reference sphere for LOLA heights and Horizons' MEAN_ME site coordinates
PANEL_HEIGHT_M = 1.0             # modelled height of the rover's solar panel above the ground (our assumption)
SAMPLING_HOURS = 6.0             # FICTIONAL instrument requirement: continuous full-disc sunlight needed
STEP_MIN = 10                    # Horizons sample spacing and touchdown step
SUBSTEP_S = 60                   # crossing search spacing between samples, refined by bisection
SKYLINE_STEP_DEG = 0.1           # skyline azimuth resolution
WINDOW_DAYS = 30                 # length of the playable window
EARTH_RADIUS_KM = 6378.137       # Horizons' equatorial radius, used only for the occultation check
