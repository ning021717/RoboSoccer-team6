"""Re-run exactly one physical candidate with controller contact telemetry."""

import json
import os
import subprocess
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
WEBOTS = Path(os.environ.get("WEBOTS_EXECUTABLE", r"C:\Program Files\Webots\msys64\mingw64\bin\webots.exe"))
RUN = PROJECT / "evidence" / "p3_kick_contact_confirmation_f018_lm006_r3_t25"


def main():
    if RUN.exists():
        raise FileExistsError(f"Refusing to overwrite evidence: {RUN}")
    RUN.mkdir(parents=True)
    (RUN / "run_manifest.json").write_text(json.dumps({
        "scenario": "kick_calibration", "forward_offset_m": 0.18,
        "lateral_offset_m": -0.06, "simulated_seconds_requested": 14.0,
        "purpose": "repeat_candidate_with_native_toe_contact_and_joint_telemetry",
        "kick_alignment_tolerance_deg": 25.0,
        "ball_velocity_injected": False,
    }, indent=2), encoding="utf-8")
    env = os.environ.copy()
    env.update({"ROBOCUP_SCENARIO": "kick_calibration", "ROBOCUP_CALIBRATION_FORWARD_M": "0.18",
                "ROBOCUP_CALIBRATION_LATERAL_M": "-0.06", "ROBOCUP_MATCH_SECONDS": "14",
                "ROBOCUP_EVIDENCE_DIR": str(RUN), "ROBOCUP_BALL_SOURCE": "supervisor",
                "ROBOCUP_USE_RETARGETED_MOTIONS": "1", "ROBOCUP_MOVIE_PATH": str(RUN / "complete_kick_flow.mp4")})
    env["ROBOCUP_KICK_ALIGNMENT_DEG"] = "25"
    result = subprocess.run([str(WEBOTS), "--mode=fast", "--stdout", "--stderr", "worlds/nao_soccer.wbt"], cwd=PROJECT, env=env,
                            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180)
    (RUN / "webots.log").write_text(result.stdout + "\n--- STDERR ---\n" + result.stderr, encoding="utf-8")
    if result.returncode:
        raise RuntimeError(f"Webots exited {result.returncode}")
    output = RUN / "contact_confirmation.csv"
    subprocess.run([sys.executable, "tools/analyze_kick_calibration.py", str(RUN), "--csv", str(output)], cwd=PROJECT, check=True)


if __name__ == "__main__":
    main()
