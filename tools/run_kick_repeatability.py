"""Repeat the best real P3 placement three times before it becomes a baseline."""

import json
import os
import subprocess
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
WEBOTS = Path(os.environ.get("WEBOTS_EXECUTABLE", r"C:\Program Files\Webots\msys64\mingw64\bin\webots.exe"))
ROOT = PROJECT / "evidence" / "p3_kick_repeatability_f014_lm004_t25"
REPEATS = 3


def main():
    if ROOT.exists():
        raise FileExistsError(f"Refusing to overwrite evidence: {ROOT}")
    ROOT.mkdir(parents=True)
    run_dirs = []
    for index in range(1, REPEATS + 1):
        run = ROOT / f"repeat_{index:02d}"
        run.mkdir()
        (run / "run_manifest.json").write_text(json.dumps({
            "scenario": "kick_calibration", "forward_offset_m": 0.14,
            "lateral_offset_m": -0.04, "kick_alignment_tolerance_deg": 25.0,
            "simulated_seconds_requested": 10.0, "repeat_index": index,
            "ball_velocity_injected": False,
        }, indent=2), encoding="utf-8")
        env = os.environ.copy()
        env.update({"ROBOCUP_SCENARIO": "kick_calibration", "ROBOCUP_CALIBRATION_FORWARD_M": "0.14",
                    "ROBOCUP_CALIBRATION_LATERAL_M": "-0.04", "ROBOCUP_KICK_ALIGNMENT_DEG": "25",
                    "ROBOCUP_MATCH_SECONDS": "10", "ROBOCUP_EVIDENCE_DIR": str(run),
                    "ROBOCUP_BALL_SOURCE": "supervisor", "ROBOCUP_USE_RETARGETED_MOTIONS": "1"})
        result = subprocess.run([str(WEBOTS), "--mode=fast", "--stdout", "--stderr", "worlds/nao_soccer.wbt"],
                                cwd=PROJECT, env=env, capture_output=True, text=True,
                                encoding="utf-8", errors="replace", timeout=180)
        (run / "webots.log").write_text(result.stdout + "\n--- STDERR ---\n" + result.stderr, encoding="utf-8")
        if result.returncode:
            raise RuntimeError(f"repeat {index} exited {result.returncode}")
        run_dirs.append(str(run))
    output = ROOT / "repeatability.csv"
    subprocess.run([sys.executable, "tools/analyze_kick_calibration.py", *run_dirs, "--csv", str(output)], cwd=PROJECT, check=True)
    print(f"completed_real_repeats={REPEATS} csv={output}")


if __name__ == "__main__":
    main()
