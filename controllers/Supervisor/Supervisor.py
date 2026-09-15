"""
Supervisor Controller.
"""
# ❶ 完整添加路径配置（无遗漏，动态回溯到项目根目录）
import sys
import os
from pathlib import Path

KICKOFF = {
  "SOCCERBALL": ([0.0, 0.0, 0.08], [0, 0, 1, 0]),

  "RED_GK":     ([-4.2,  0.0, 0.33], [0, 0, 1, 0]),
  "RED_DEF_L":  ([-2.2,  0.6, 0.33], [0, 0, 1, 0]),
  "RED_DEF_R":  ([-2.2, -0.6, 0.33], [0, 0, 1, 0]),
  "RED_FW":     ([-0.6,  0.0, 0.33], [0, 0, 1, 0]),

  "BLUE_GK":    ([ 4.2,  0.0, 0.33], [0, 0, 1, 3.14159]),
  "BLUE_DEF":   ([ 2.2,  0.0, 0.33], [0, 0, 1, 3.14159]),
  "BLUE_FW_L":  ([ 0.6,  0.4, 0.33], [0, 0, 1, 3.14159]),
  "BLUE_FW_R":  ([ 0.6, -0.4, 0.33], [0, 0, 1, 3.14159]),
}


def with_overrides(overrides):
  poses = {name: (list(translation), list(rotation)) for name, (translation, rotation) in KICKOFF.items()}
  for name, translation in overrides.items():
    poses[name] = (translation, poses[name][1])
  return poses


# Deterministic football situations for exercising approach, alignment, kick,
# pass and goalkeeper branches.  They are explicit test fixtures, not scores.
SCENARIOS = {
  "kickoff": KICKOFF,
  "red_close_shot": with_overrides({"SOCCERBALL": [-0.32, 0.0, 0.08], "RED_FW": [-0.62, 0.0, 0.33]}),
  "blue_close_shot": with_overrides({"SOCCERBALL": [0.32, 0.0, 0.08], "BLUE_FW_L": [0.62, 0.0, 0.33]}),
  "red_pass_lane": with_overrides({"SOCCERBALL": [-0.32, 0.0, 0.08], "RED_FW": [-0.62, 0.0, 0.33], "RED_DEF_L": [0.48, 0.58, 0.33]}),
  "red_pass_clear": with_overrides({"SOCCERBALL": [-0.32, 0.0, 0.08], "RED_FW": [-0.62, 0.0, 0.33], "RED_DEF_L": [0.80, 0.90, 0.33], "BLUE_FW_L": [1.30, -2.40, 0.33], "BLUE_FW_R": [1.30, 2.40, 0.33]}),
  "red_penalty_shot": with_overrides({"SOCCERBALL": [3.70, 0.0, 0.08], "RED_FW": [3.40, 0.0, 0.33]}),
  "red_right_foot_shot": with_overrides({"SOCCERBALL": [3.66, -0.10, 0.08], "RED_FW": [3.40, 0.0, 0.33]}),
}


def calibration_scenario():
  """A repeatable physical kick fixture; offsets are relative to RED_FW.

  The runner supplies offsets in metres.  No velocity or force is assigned to
  the ball: a successful sample must come from NAO-foot physics alone.
  """
  forward_offset = float(os.environ.get("ROBOCUP_CALIBRATION_FORWARD_M", "0.26"))
  lateral_offset = float(os.environ.get("ROBOCUP_CALIBRATION_LATERAL_M", "-0.08"))
  if not (0.08 <= forward_offset <= 0.45 and -0.24 <= lateral_offset <= 0.24):
    raise ValueError("calibration offsets outside safe scan bounds")
  poses = with_overrides({
    "RED_FW": [3.40, 0.0, 0.33],
    "SOCCERBALL": [3.40 + forward_offset, lateral_offset, 0.08],
    # Keep the original 4v4 pitch and all robots, while making this test
    # fixture deterministic by parking non-participants away from the ball.
    "BLUE_FW_L": [1.2, -2.4, 0.33],
    "BLUE_FW_R": [1.2, 2.4, 0.33],
  })
  return poses


# 获取当前脚本（supervisor.py）的绝对路径
current_script_path = os.path.abspath(__file__)
# 逐级回溯：supervisor/ → controllers/ → RoboCupSoccer-main/（项目根目录）
script_dir = os.path.dirname(current_script_path)  # supervisor/ 目录
controllers_dir = os.path.dirname(script_dir)     # controllers/ 目录
project_root = os.path.dirname(controllers_dir)   # 项目根目录

# ❷ 优先将项目根目录加入sys.path（确保controllers被识别为顶层模块）
if project_root not in sys.path:
    sys.path.insert(0, project_root)  # insert(0)确保优先搜索，避免冲突

# ❸ 改为完整绝对导入（解决ModuleNotFoundError）
from controller import Supervisor
from controllers.Base.SupervisorBase import SupervisorBase
from controllers.Utils.Consts import TIME_STEP
from Scoreboard import Scoreboard
from MatchTelemetry import MatchTelemetry

# 后续原有业务代码不变

from Base.SupervisorBase import SupervisorBase
from Utils.Consts import (TIME_STEP, Motions)
from Scoreboard import Scoreboard

supervisor = SupervisorBase()
scoreboard = Scoreboard()

# A finite window is used only by automation.  Opening the world normally
# leaves the original real-time match behaviour untouched.
test_seconds = float(os.environ.get("ROBOCUP_MATCH_SECONDS", "0"))
evidence_dir = Path(os.environ.get("ROBOCUP_EVIDENCE_DIR", project_root + "/evidence/latest"))
telemetry = MatchTelemetry(evidence_dir)
movie_path = os.environ.get("ROBOCUP_MOVIE_PATH")
movie_started = False
if movie_path:
  movie_target = Path(movie_path)
  movie_target.parent.mkdir(parents=True, exist_ok=True)
  # Webots Python returns None on successful start; treat exceptions, not the
  # return value, as failure so ``movieStopRecording`` always executes.
  supervisor.movieStartRecording(str(movie_target), 1280, 720, 0, 95, 1, False)
  movie_started = True
  print(f"[MOVIE] start=True path={movie_target}")

def reset_to_kickoff(supervisor, poses):
  def set_pose(def_name, t, r):
    node = supervisor.getFromDef(def_name)
    if node is None:
      print(f"[RESET] DEF not found: {def_name}")
      return
    node.getField("translation").setSFVec3f(t)
    node.getField("rotation").setSFRotation(r)
    node.resetPhysics()

  for def_name, (t, r) in poses.items():
    set_pose(def_name, t, r)
scenario = os.environ.get("ROBOCUP_SCENARIO", "kickoff")
if scenario == "kick_calibration":
  selected_poses = calibration_scenario()
elif scenario in SCENARIOS:
  selected_poses = SCENARIOS[scenario]
else:
  raise ValueError(f"Unknown ROBOCUP_SCENARIO={scenario}; choose from {sorted(SCENARIOS)}")
print(f"[SCENARIO] {scenario}")
reset_to_kickoff(supervisor, selected_poses)

while supervisor.step(TIME_STEP) != -1:
    # The following code must be run to send the ball data to robots via emitter.
    # print("Robot RED_FW: ", supervisor.getRobotPosition("RED_FW"))
    scoreboard.updateScoreboard(supervisor)
    supervisor.sendSupervisorData()
    telemetry.sample(supervisor, scoreboard)
    for event in scoreboard.consume_events():
      telemetry.event(event)
    if test_seconds > 0 and supervisor.getTime() >= test_seconds:
      break
    #print("Supervisor: ", supervisor.getBallPosition())

if movie_started:
  supervisor.movieStopRecording()
  ready_steps = 0
  while not supervisor.movieIsReady() and ready_steps < 400:
    if supervisor.step(TIME_STEP) == -1:
      break
    ready_steps += 1
  print(f"[MOVIE] ready={supervisor.movieIsReady()} wait_steps={ready_steps}")
telemetry.close()
if test_seconds > 0:
  print(f"[MATCH] completed simulated_seconds={supervisor.getTime():.2f} score=RED {scoreboard.redTeamScore} - {scoreboard.blueTeamScore} BLUE")
  supervisor.simulationQuit(0)
