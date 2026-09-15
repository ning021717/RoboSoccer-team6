"""Export small, reviewable summaries from immutable local Webots evidence.

The full JSONL, movies and intermediate logs remain ignored under ``evidence/``.
This exporter intentionally copies only measured summary values and writes the
SHA-256 of every source artifact, allowing the versioned report to remain
auditable without pretending that a summary is the raw experiment.
"""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence"
REPORTS = ROOT / "reports"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    repeatability = EVIDENCE / "p3_kick_repeatability_f014_lm004_t25" / "repeatability.csv"
    fixed_300 = EVIDENCE / "p0_fixed_4v4_camera_300s" / "fixed_window_summary.json"
    fixed_60 = EVIDENCE / "p0_fixed_4v4_camera_60s_boundary_search_r1" / "fixed_window_summary.json"
    required = (repeatability, fixed_300, fixed_60)
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise SystemExit("Missing real evidence; refusing export:\n" + "\n".join(missing))

    REPORTS.mkdir(exist_ok=True)
    with repeatability.open(newline="", encoding="utf-8") as handle:
        kick_rows = list(csv.DictReader(handle))
    fields = [
        "repeat_index", "scenario", "forward_offset_m", "lateral_offset_m",
        "kick_alignment_tolerance_deg", "kick_requests", "toe_bumper_peak",
        "max_ball_displacement_m", "peak_ball_speed_mps", "ball_velocity_injected",
        "evidence_status", "reason", "source_sha256",
    ]
    source_hash = digest(repeatability)
    exported_kick_rows = [
        {field: (source_hash if field == "source_sha256" else row.get(field, "")) for field in fields}
        for row in kick_rows
    ]
    write_csv(REPORTS / "p3_kick_repeatability_summary.csv", fields, exported_kick_rows)

    fixed_rows: list[dict[str, object]] = []
    for label, path in (("before_boundary_search", fixed_300), ("after_boundary_search", fixed_60)):
        payload = json.loads(path.read_text(encoding="utf-8"))
        actions = payload["tactical_action_requests"]
        fixed_rows.append({
            "run_label": label,
            "simulated_seconds_requested": payload["simulated_seconds_requested"],
            "ball_source_for_controllers": payload["ball_source_for_controllers"],
            "perception_samples": payload["perception_samples"],
            "detections": payload["detections"],
            "detection_rate": payload["detection_rate"],
            "blue_score": payload["score_final"]["blue"],
            "red_score": payload["score_final"]["red"],
            "match_events": payload["match_events"],
            "search_ball_requests": actions.get("search_ball", 0),
            "mobile_boundary_sample_total": payload["mobile_boundary_sample_total"],
            "ball_velocity_injected": payload["ball_velocity_injected"],
            "evidence_status": payload["evidence_status"],
            "source_sha256": digest(path),
        })
    write_csv(
        REPORTS / "p0_camera_boundary_regression_summary.csv",
        list(fixed_rows[0]),
        fixed_rows,
    )

    (REPORTS / "DATA_PROVENANCE.md").write_text(
        "# Versioned evidence summaries\n\n"
        "These CSVs were exported by `tools/export_versioned_evidence.py` from actual local "
        "Webots runs. They contain summary values only; the source file SHA-256 is recorded "
        "in every row. Raw JSONL, video and full telemetry are retained locally under `evidence/` "
        "and are intentionally git-ignored because of size.\n\n"
        "The P3 file records three deterministic repeats at a single calibrated fixed pose. "
        "It is physical-contact evidence, not a match-level success-rate estimate. The P0 file "
        "is two unequal-duration regression windows, not a parameter-comparison experiment.\n",
        encoding="utf-8",
    )
    print("Exported versioned evidence summaries to", REPORTS)


if __name__ == "__main__":
    main()
