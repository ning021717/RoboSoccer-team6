"""Run one labelled, fixed-condition 4v4 match window in real Webots."""

import json
import os
import subprocess
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
WEBOTS = Path(os.environ.get("WEBOTS_EXECUTABLE", r"C:\Program Files\Webots\msys64\mingw64\bin\webots.exe"))
SECONDS = float(os.environ.get("ROBOCUP_FIXED_WINDOW_SECONDS", "300"))
SOURCE = os.environ.get("ROBOCUP_FIXED_BALL_SOURCE", "camera")
LABEL = os.environ.get("ROBOCUP_FIXED_LABEL", "baseline")
RUN = PROJECT / "evidence" / f"p0_fixed_4v4_{SOURCE}_{int(SECONDS)}s_{LABEL}"


def main():
    if SOURCE not in {"camera", "fused", "supervisor"}:
        raise ValueError("ROBOCUP_FIXED_BALL_SOURCE must be camera, fused, or supervisor")
    if not (1 <= SECONDS <= 900):
        raise ValueError("fixed window must be between 1 and 900 simulated seconds")
    if RUN.exists():
        raise FileExistsError(f"Refusing to overwrite evidence: {RUN}")
    RUN.mkdir(parents=True)
    (RUN / "run_manifest.json").write_text(json.dumps({
        "scenario": "kickoff", "simulated_seconds_requested": SECONDS,
        "ball_source_for_controllers": SOURCE, "players": "4v4",
        "purpose": "fixed-condition baseline; not a multi-seed statistical result",
        "ball_velocity_injected": False,
    }, indent=2), encoding="utf-8")
    env = os.environ.copy()
    env.update({"ROBOCUP_SCENARIO": "kickoff", "ROBOCUP_MATCH_SECONDS": str(SECONDS),
                "ROBOCUP_EVIDENCE_DIR": str(RUN), "ROBOCUP_BALL_SOURCE": SOURCE,
                "ROBOCUP_USE_RETARGETED_MOTIONS": "1"})
    result = subprocess.run([str(WEBOTS), "--mode=fast", "--stdout", "--stderr", "worlds/nao_soccer.wbt"],
                            cwd=PROJECT, env=env, capture_output=True, text=True,
                            encoding="utf-8", errors="replace", timeout=max(300, int(SECONDS * 3)))
    (RUN / "webots.log").write_text(result.stdout + "\n--- STDERR ---\n" + result.stderr, encoding="utf-8")
    if result.returncode:
        raise RuntimeError(f"Webots exited {result.returncode}; inspect {RUN / 'webots.log'}")
    print(f"completed_fixed_window={SECONDS}s evidence={RUN}")


if __name__ == "__main__":
    main()
