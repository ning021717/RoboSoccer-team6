# Versioned evidence summaries

These CSVs were exported by `tools/export_versioned_evidence.py` from actual local Webots runs. They contain summary values only; the source file SHA-256 is recorded in every row. Raw JSONL, video and full telemetry are retained locally under `evidence/` and are intentionally git-ignored because of size.

The P3 file records three deterministic repeats at a single calibrated fixed pose. It is physical-contact evidence, not a match-level success-rate estimate. The P0 file is two unequal-duration regression windows, not a parameter-comparison experiment.
