"""Evidence-gated action-to-ball-motion summary for a Webots match run."""

import argparse
import csv
import json
import math
from collections import Counter
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence_dir", type=Path)
    args = parser.parse_args()
    truth_path = args.evidence_dir / "supervisor_match_truth.jsonl"
    action_paths = sorted((args.evidence_dir / "actions").glob("*_actions.jsonl"))
    if not truth_path.exists() or not action_paths:
        raise SystemExit("Missing retained truth or action JSONL; refusing to infer a match result.")

    truth = [json.loads(line) for line in truth_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(truth) < 2:
        raise SystemExit("Fewer than two truth samples; ball displacement is not measurable.")
    initial = truth[0]["ball_gt"]
    max_displacement = max(math.hypot(row["ball_gt"][0] - initial[0], row["ball_gt"][1] - initial[1]) for row in truth)

    records = []
    counts = Counter()
    for action_path in action_paths:
        for line in action_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            event = json.loads(line)
            tactical = event["tactical_action"]
            counts[tactical] += 1
            records.append({"robot": action_path.stem.replace("_actions", ""), **event})

    output = args.evidence_dir / "analysis"
    output.mkdir(exist_ok=True)
    with (output / "action_events.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["robot", "time_s", "motion", "tactical_action", "ball_source"])
        writer.writeheader()
        writer.writerows(records)
    summary = {
        "truth_samples": len(truth),
        "initial_ball_gt": initial,
        "max_ball_displacement_m": max_displacement,
        "score_final": truth[-1]["score"],
        "tactical_action_requests": dict(counts),
        "acceptance": {
            "shoot_requested": counts["shoot"] > 0,
            "pass_requested": any(action.startswith("pass_to_") for action in counts),
            "ball_moved": max_displacement > 0.10,
            "goal_recorded": truth[-1]["score"]["red"] + truth[-1]["score"]["blue"] > 0,
        },
        "warning": "A requested motion is not counted as a completed kick unless Supervisor truth records ball displacement.",
    }
    (output / "action_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
