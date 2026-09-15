"""Run a small, real 3x3 Webots kick-placement pilot.

It intentionally starts a fresh Webots process per cell, writes every raw log
to an immutable evidence folder, and then delegates conclusions to the guarded
analyser.  It does not modify ball velocity, score, or physical outcomes.
"""

import json
import os
import subprocess
import sys
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]
WEBOTS = Path(os.environ.get("WEBOTS_EXECUTABLE", r"C:\Program Files\Webots\msys64\mingw64\bin\webots.exe"))
# This second physical scan narrows around the right-foot strike corridor
# discovered in the first pilot.  It deliberately changes only alignment and
# ball placement; it never applies velocity/force to the ball.
FORWARD_M = (0.14, 0.18, 0.22)
LATERAL_M = (-0.06, -0.04, -0.02)
SECONDS = float(os.environ.get("ROBOCUP_CALIBRATION_SECONDS", "10"))


def main():
    if not WEBOTS.exists():
        raise FileNotFoundError(f"Webots executable not found: {WEBOTS}")
    batch = PROJECT / "evidence" / "p3_kick_calibration_strike_corridor_3x3_t25"
    if batch.exists():
        raise FileExistsError(f"Refusing to overwrite existing evidence: {batch}")
    batch.mkdir(parents=True)
    run_dirs = []
    for forward in FORWARD_M:
        for lateral in LATERAL_M:
            label = f"f{forward:.2f}_l{lateral:+.2f}".replace("+", "p").replace("-", "m")
            run_dir = batch / label
            run_dir.mkdir()
            (run_dir / "run_manifest.json").write_text(json.dumps({
                "scenario": "kick_calibration", "forward_offset_m": forward,
                "lateral_offset_m": lateral, "simulated_seconds_requested": SECONDS,
                "kick_alignment_tolerance_deg": 25.0,
                "ball_velocity_injected": False,
            }, indent=2), encoding="utf-8")
            env = os.environ.copy()
            env.update({
                "ROBOCUP_SCENARIO": "kick_calibration",
                "ROBOCUP_CALIBRATION_FORWARD_M": str(forward),
                "ROBOCUP_CALIBRATION_LATERAL_M": str(lateral),
                "ROBOCUP_MATCH_SECONDS": str(SECONDS),
                "ROBOCUP_EVIDENCE_DIR": str(run_dir),
                "ROBOCUP_BALL_SOURCE": "supervisor",
                "ROBOCUP_USE_RETARGETED_MOTIONS": "1",
                "ROBOCUP_KICK_ALIGNMENT_DEG": "25",
            })
            command = [str(WEBOTS), "--mode=fast", "--stdout", "--stderr", "worlds/nao_soccer.wbt"]
            completed = subprocess.run(
                command, cwd=PROJECT, env=env, capture_output=True,
                text=True, encoding="utf-8", errors="replace", timeout=180,
            )
            (run_dir / "webots.log").write_text(completed.stdout + "\n--- STDERR ---\n" + completed.stderr, encoding="utf-8")
            if completed.returncode != 0:
                raise RuntimeError(f"{label} exited {completed.returncode}; see {run_dir / 'webots.log'}")
            run_dirs.append(str(run_dir))
    output = batch / "kick_calibration_pilot.csv"
    subprocess.run([sys.executable, "tools/analyze_kick_calibration.py", *run_dirs, "--csv", str(output)], cwd=PROJECT, check=True)
    print(f"completed_real_cells={len(run_dirs)} csv={output}")


if __name__ == "__main__":
    main()
