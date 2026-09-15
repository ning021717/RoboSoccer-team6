"""Turn real Webots kick-fixture telemetry into a guarded calibration table.

This tool never invents contact.  A row is marked ``insufficient_evidence``
when no supervisor samples, no kick request, or no resolved foot geometry is
available.  Physical success requires measured ball displacement and velocity.
"""

import argparse
import csv
import json
import math
from pathlib import Path


def distance(a, b):
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a[:2], b[:2])))


def load_jsonl(path):
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def numeric_peak(value):
    if isinstance(value, list):
        return max((abs(float(item)) for item in value), default=0.0)
    return abs(float(value)) if value is not None else 0.0


def analyse(run_dir):
    root = Path(run_dir)
    manifest_path = root / "run_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    truth = [row for row in load_jsonl(root / "supervisor_match_truth.jsonl") if row.get("kind") == "truth_sample"]
    actions = load_jsonl(root / "actions" / "RED_FW_actions.jsonl")
    contacts = load_jsonl(root / "contacts" / "RED_FW_foot_contacts.jsonl")
    kick_actions = [row for row in actions if row.get("tactical_action") in {"shoot", "long_clearance"} or str(row.get("tactical_action", "")).startswith("pass_to_")]
    if not truth:
        return {**manifest, "evidence_status": "insufficient_evidence", "reason": "missing_supervisor_truth"}

    first_ball = truth[0]["ball_gt"]
    peak_speed = max(math.sqrt(sum(v * v for v in row.get("ball_velocity_gt_mps", [0, 0, 0]))) for row in truth)
    displacement = max(distance(first_ball, row["ball_gt"]) for row in truth)
    min_foot_distance = None
    for row in truth:
        feet = row.get("feet_gt", {}).get("RED_FW", {})
        for foot in (feet.get("left"), feet.get("right")):
            if foot is not None:
                candidate = distance(foot, row["ball_gt"])
                min_foot_distance = candidate if min_foot_distance is None else min(min_foot_distance, candidate)

    kick_motion_names = {"shoot", "rightShoot", "longPass", "longShoot", "leftSidePass", "rightSidePass"}
    kick_contact_rows = [row for row in contacts if row.get("active_motion") in kick_motion_names]
    toe_bumper_peak = max(
        (numeric_peak(value) for row in kick_contact_rows for value in row.get("toe_bumpers", {}).values()),
        default=0.0,
    )

    if not kick_actions:
        status, reason = "insufficient_evidence", "no_kick_motion_requested"
    elif not contacts:
        status, reason = "insufficient_evidence", "foot_node_not_resolved"
    elif toe_bumper_peak <= 0.0:
        status, reason = "insufficient_evidence", "no_toe_contact_during_kick_motion"
    elif displacement >= 0.10 and peak_speed >= 0.10:
        status, reason = "physical_kick_success", "measured_ball_motion"
    else:
        status, reason = "physical_kick_failure", "kick_requested_but_ball_motion_below_threshold"
    return {
        **manifest,
        "samples": len(truth),
        "kick_requests": len(kick_actions),
        "min_foot_ball_distance_m": None if min_foot_distance is None else round(min_foot_distance, 5),
        "toe_bumper_peak": round(toe_bumper_peak, 5),
        "peak_ball_speed_mps": round(peak_speed, 5),
        "max_ball_displacement_m": round(displacement, 5),
        "evidence_status": status,
        "reason": reason,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dirs", nargs="+", type=Path)
    parser.add_argument("--csv", type=Path, required=True)
    args = parser.parse_args()
    rows = [analyse(path) for path in args.run_dirs]
    args.csv.parent.mkdir(parents=True, exist_ok=True)
    fields = sorted({key for row in rows for key in row})
    with args.csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps({"rows": len(rows), "csv": str(args.csv), "statuses": [row["evidence_status"] for row in rows]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
