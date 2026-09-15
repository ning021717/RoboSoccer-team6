"""Create an auditable CSV/JSON summary from one completed fixed match window."""

import argparse
import collections
import csv
import json
from pathlib import Path


def jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()] if path.exists() else []


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir", type=Path)
    args = parser.parse_args()
    root = args.run_dir
    manifest = json.loads((root / "run_manifest.json").read_text(encoding="utf-8"))
    truth = [row for row in jsonl(root / "supervisor_match_truth.jsonl") if row.get("kind") == "truth_sample"]
    if not truth:
        raise RuntimeError("no supervisor truth samples; refusing summary")
    robots = sorted(truth[0]["robots_gt"])
    metrics = []
    for robot in robots:
        poses = [row["robots_gt"][robot] for row in truth]
        metrics.append({"robot": robot, "max_abs_x_m": max(abs(pose[0]) for pose in poses),
                        "max_abs_y_m": max(abs(pose[1]) for pose in poses),
                        "boundary_samples": sum(abs(pose[0]) >= 4.15 or abs(pose[1]) >= 2.75 for pose in poses)})
    detections = 0
    perception_samples = 0
    action_counts = collections.Counter()
    for path in (root / "perception").glob("*.jsonl"):
        records = jsonl(path)
        perception_samples += len(records)
        detections += sum(record.get("detected", False) for record in records)
    for path in (root / "actions").glob("*.jsonl"):
        action_counts.update(record.get("tactical_action", "unknown") for record in jsonl(path))
    events = [row for row in jsonl(root / "supervisor_match_truth.jsonl") if row.get("kind") == "match_event"]
    summary = {**manifest, "truth_samples": len(truth), "perception_samples": perception_samples,
               "detections": detections, "detection_rate": detections / perception_samples if perception_samples else None,
               "score_final": truth[-1]["score"], "match_events": len(events), "tactical_action_requests": dict(action_counts),
               "boundary_sample_total": sum(row["boundary_samples"] for row in metrics),
               # Goalkeepers intentionally stand close to x=±4.17, so their
               # samples are retained per robot but excluded from mobile-role
               # boundary regression metrics.
               "mobile_boundary_sample_total": sum(row["boundary_samples"] for row in metrics if not row["robot"].endswith("GK")),
               "evidence_status": "baseline_only_not_statistical"}
    (root / "fixed_window_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    with (root / "robot_metrics.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=metrics[0].keys())
        writer.writeheader(); writer.writerows(metrics)
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
