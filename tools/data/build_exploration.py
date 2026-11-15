"""Build provisional exploration-era Navigator packs without changing data/mission.json."""
import json
from pathlib import Path
import numpy as np
from build_mission import build_site, cross_check, site_json
from sunline_data.constants import ROOT, REPO, SOURCE

SITES = ("apollo-11", "apollo-17", "sl3", "site04", "site07", "site11")
WINDOWS = (
    ("viper-era", "2027-11-15T00:00", "2027-12-15T00:00"),
    ("artemis-iv-era", "2028-02-18T00:00", "2028-03-19T00:00"),
    ("artemis-v-era", "2028-10-15T00:00", "2028-11-14T00:00"),
)
EXISTING = {"artemis-iv-era": {"apollo-11", "sl3"}}
OUT = REPO / "data" / "exploration"


def main():
    catalog = {s["id"]: s for s in json.loads((SOURCE / "sites_catalog.json").read_text())["sites"]}
    OUT.mkdir(parents=True, exist_ok=True)
    for scenario_id, start, end in WINDOWS:
        start_unix = int(np.datetime64(start, "s").astype(np.int64))
        end_unix = int(np.datetime64(end, "s").astype(np.int64))
        pack = {
            "schema": 1, "scenario_id": scenario_id,
            "start_utc": start + "Z", "end_utc": end + "Z",
            "label": "exploration-era planning scenario",
            "validated": False, "sites": [], "cross_checks": {},
        }
        for site_id in SITES:
            if site_id in EXISTING.get(scenario_id, set()):
                continue
            result = build_site(catalog[site_id], start_unix, end_unix)
            pack["sites"].append(site_json(result))
            pack["cross_checks"][site_id] = cross_check(result)
            print("Built", scenario_id, site_id, flush=True)
        output = OUT / (scenario_id + ".json")
        output.write_text(json.dumps(pack, separators=(",", ":")), encoding="utf-8")
        print("Wrote", output, flush=True)


if __name__ == "__main__":
    main()

