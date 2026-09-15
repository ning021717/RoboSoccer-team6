import os, sys
from abc import ABC, abstractmethod
import struct
import math
import json
from pathlib import Path

currentdir = os.path.dirname(os.path.realpath(__file__))
parentdir = os.path.dirname(currentdir)
if parentdir not in sys.path:
  sys.path.append(parentdir)

from controller import Motion
from Utils.Consts import TIME_STEP, Motions
from Utils import Functions
from Utils.BallPerception import CameraBallDetector

ROBOT_ORDER = [
  "RED_GK",
  "RED_DEF_L",
  "RED_DEF_R",
  "RED_FW",
  "BLUE_GK",
  "BLUE_DEF",
  "BLUE_FW_L",
  "BLUE_FW_R",
]

class SoccerRobot(ABC):
  def __init__(self, robot):
    self.robot = robot
    self.name = robot.getName()

    # Devices
    self.gps = robot.getDevice("gps")
    self.gps.enable(TIME_STEP)

    self.receiver = robot.getDevice("receiver")
    self.receiver.enable(TIME_STEP)
    self.receiver.setChannel(0)   
    self.emitter = robot.getDevice("emitter")
    self.emitter.setChannel(0)    
    self.inertialUnit = robot.getDevice("inertial unit")
    self.inertialUnit.enable(TIME_STEP)

    self.ultrasound = [robot.getDevice("Sonar/Left"), robot.getDevice("Sonar/Right")]
    self.ultrasound[0].enable(TIME_STEP)
    self.ultrasound[1].enable(TIME_STEP)

    self.supervisorData = None
    self.world = {"ball": None, "robots": {}}

    self.bumpers = {
      "bumperLL": robot.getDevice('LFoot/Bumper/Left'),
      "bumperLR": robot.getDevice('LFoot/Bumper/Right'),
      "bumperRL": robot.getDevice('RFoot/Bumper/Left'),
      "bumperRR": robot.getDevice('RFoot/Bumper/Right')
    }
    for b in self.bumpers.values():
      b.enable(TIME_STEP)

    # P3 evidence is controller-side sensing, not Supervisor truth.  Toe
    # bumpers provide the contact attribution that an embedded NAO hierarchy
    # cannot expose through ``getFromProtoDef``; joint sensors preserve the
    # hip/knee/ankle state at the same time.
    self.footForceSensors = {
      "left_fsr": robot.getDevice("LFsr"),
      "right_fsr": robot.getDevice("RFsr"),
    }
    for sensor in self.footForceSensors.values():
      sensor.enable(TIME_STEP)
    self.kickJointSensors = {
      name: robot.getDevice(name) for name in (
        "LHipPitchS", "LKneePitchS", "LAnklePitchS", "LAnkleRollS",
        "RHipPitchS", "RKneePitchS", "RAnklePitchS", "RAnkleRollS",
      )
    }
    for sensor in self.kickJointSensors.values():
      sensor.enable(TIME_STEP)

    self.cameraTop = robot.getDevice("CameraTop")
    self.cameraBottom = robot.getDevice("CameraBottom")
    self.cameraTop.enable(TIME_STEP)
    self.cameraBottom.enable(TIME_STEP)

    # Ball truth remains available only to the Supervisor evaluation recorder.
    # The default preserves the legacy playable demo; use ``camera`` for P1.
    self.ball_source = os.environ.get("ROBOCUP_BALL_SOURCE", "supervisor").lower()
    if self.ball_source not in {"supervisor", "camera", "fused"}:
      raise ValueError("ROBOCUP_BALL_SOURCE must be supervisor, camera, or fused")
    self.ballDetectors = [
      CameraBallDetector(self.cameraTop),
      CameraBallDetector(self.cameraBottom),
    ]
    self.lastPerception = None
    self._perceptionStep = 0
    self._evaluationBallTruth = None
    self._perceptionLog = self._open_perception_log()
    self._actionLog = self._open_action_log()
    self._contactLog = self._open_contact_log()
    self.lastTacticalAction = "initialise"

    # Motions / queue
    self.motions = Motions()
    self.currentlyMoving = None
    self.motionQueue = [self.motions.standInit]

    # World data
    self.world = {
      "ball": None,          # [x,y]
      "robots": {},          # name -> (x,y,z)
      "ballOwner": "",
      "ballPriority": "N",
    }

    self.ballTracker = Functions.BallTracker()

    # Start initial pose
    self.startMotion()

  # ------------ abstract ------------
  @abstractmethod
  def decideMotion(self, ballCoordinate, selfCoordinate) -> Motion:
    pass

  # ------------ helpers ------------
  def printSelf(self) -> None:
    print("Hello! This is robot", self.name)

  def getSelfCoordinate(self) -> list:
    v = self.gps.getValues()
    return [v[0], v[1], v[2]]

  def getRollPitchYaw(self) -> list:
    return self.inertialUnit.getRollPitchYaw()

  def isNewBallDataAvailable(self) -> bool:
    return self.receiver.getQueueLength() > 0

  def getBallData(self) -> list:
    if self.world["ball"] is None:
      return [0.0, 0.0]
    return self.world["ball"]

  def _open_perception_log(self):
    """Create one controller-owned evidence stream when explicitly requested."""
    evidence_root = os.environ.get("ROBOCUP_EVIDENCE_DIR")
    if not evidence_root:
      return None
    path = Path(evidence_root) / "perception"
    path.mkdir(parents=True, exist_ok=True)
    return (path / f"{self.name}_camera.jsonl").open("w", encoding="utf-8")

  def _log_perception(self, detection, estimate):
    if self._perceptionLog is None:
      return
    truth = self._evaluationBallTruth
    record = {
      "time_s": round(self.robot.getTime(), 4),
      "source": self.ball_source,
      "detected": detection is not None,
      "detection": detection,
      "estimate_xy": estimate,
      # Kept strictly as labelled evaluation truth, never read by motion code.
      "evaluation_truth_xy": truth,
    }
    self._perceptionLog.write(json.dumps(record, ensure_ascii=False) + "\n")
    self._perceptionLog.flush()

  def _open_action_log(self):
    evidence_root = os.environ.get("ROBOCUP_EVIDENCE_DIR")
    if not evidence_root:
      return None
    path = Path(evidence_root) / "actions"
    path.mkdir(parents=True, exist_ok=True)
    return (path / f"{self.name}_actions.jsonl").open("w", encoding="utf-8")

  def _open_contact_log(self):
    evidence_root = os.environ.get("ROBOCUP_EVIDENCE_DIR")
    if not evidence_root:
      return None
    path = Path(evidence_root) / "contacts"
    path.mkdir(parents=True, exist_ok=True)
    return (path / f"{self.name}_foot_contacts.jsonl").open("w", encoding="utf-8")

  @staticmethod
  def _sensor_value(sensor):
    try:
      # Webots exposes a ctypes pointer from TouchSensor.getValues().  Only a
      # FORCE3D sensor uses it; bumpers and position sensors use getValue().
      if hasattr(sensor, "getType") and sensor.getType() == 2:
        return [round(float(v), 6) for v in sensor.getValues()[:3]]
      return round(float(sensor.getValue()), 6)
    except Exception:
      return None

  def _log_foot_kinematics(self):
    """Record native contact and joint evidence for physical kick studies."""
    if self._contactLog is None:
      return
    bumper_values = {name: self._sensor_value(sensor) for name, sensor in self.bumpers.items()}
    record = {
      "time_s": round(self.robot.getTime(), 4),
      "active_motion": self.currentlyMoving.name if self.currentlyMoving else None,
      "toe_bumpers": bumper_values,
      "foot_forces": {name: self._sensor_value(sensor) for name, sensor in self.footForceSensors.items()},
      "joint_angles_rad": {name: self._sensor_value(sensor) for name, sensor in self.kickJointSensors.items()},
    }
    self._contactLog.write(json.dumps(record, ensure_ascii=False) + "\n")
    self._contactLog.flush()

  def _log_action(self, motion):
    if self._actionLog is None:
      return
    self._actionLog.write(json.dumps({
      "time_s": round(self.robot.getTime(), 4),
      "motion": motion.name,
      "tactical_action": self.lastTacticalAction,
      "ball_source": self.ball_source,
    }, ensure_ascii=False) + "\n")
    self._actionLog.flush()

  def getBallOwner(self) -> str:
    return self.world.get("ballOwner", "")

  def getBallPriority(self) -> str:
    return self.world.get("ballPriority", "N")

  def getRobotFromSupervisor(self, robotName: str):
    return self.world["robots"].get(robotName, None)

  def getLeftSonarValue(self) -> float:
    return self.ultrasound[0].getValue()

  def getRightSonarValue(self) -> float:
    return self.ultrasound[1].getValue()

  # ------------ fall / goal ------------
  def isFallen(self, selfCoordinate) -> bool:
    return selfCoordinate[2] < 0.2

  def getStandUpMotion(self):
    if self.getLeftSonarValue() == 2.55 and self.getRightSonarValue() == 2.55:
      return self.motions.standUpFromBack
    return self.motions.standUpFromFront

  def checkGoal(self) -> int:
    ball = self.getBallEstimate()
    if ball is None:
      return 0

    if abs(ball[0]) > 4.5 and abs(ball[1]) < 1.35:
      if ball[0] > 4.5:
        return 1 if self.name.startswith("R") else -1
      else:
        return 1 if self.name.startswith("B") else -1
    return 0

  # ------------ motion queue ------------
  def interruptMotion(self) -> None:
    if self.currentlyMoving and (not self.currentlyMoving.isOver()):
      self.currentlyMoving.stop()

  def startMotion(self) -> None:
    if (self.currentlyMoving is None) or self.currentlyMoving.isOver():
      if len(self.motionQueue) > 0:
        m = self.motionQueue.pop(0)
        m.play()
        self.currentlyMoving = m

  def addMotionToQueue(self, motion) -> None:
    self.motionQueue.append(motion)

  def clearMotionQueue(self) -> None:
    self.motionQueue.clear()

  def isNewMotionValid(self, newMotion) -> bool:
    if newMotion is None:
      return False
    if self.currentlyMoving and (not self.currentlyMoving.isOver()) and newMotion.name == self.currentlyMoving.name:
      return False
    return True

  def applyMotion(self, decidedMotion):
    if not self.isNewMotionValid(decidedMotion):
      self.startMotion()
      return
    self.clearMotionQueue()
    self.addMotionToQueue(decidedMotion)
    self._log_action(decidedMotion)
    self.startMotion()

  # ------------ turning / align ------------
  def getTurningMotion(self, turningAngleDeg):
  # 小角度：轻微调整，避免原地转圈
    if turningAngleDeg > 55:
      return self.motions.turnLeft60
    elif turningAngleDeg > 25:
      return self.motions.turnLeft20
    elif turningAngleDeg > 10:
      return self.motions.turnLeft10

    elif turningAngleDeg < -55:
      return self.motions.turnRight60
    elif turningAngleDeg < -25:
      return self.motions.turnRight40
    elif turningAngleDeg < -10:
      return self.motions.turnRight10_V2

    return None



  def align_to_target(self, targetXY, selfXYZ, tolerance_deg=12.0):
    yaw = self.getRollPitchYaw()[2]
    turn = Functions.calculateTurningAngleAccordingToRobotHeading(targetXY, selfXYZ, yaw)
    if abs(turn) <= tolerance_deg:
      return self.motions.standInit
    m = self.getTurningMotion(turn)
    return m if m is not None else self.motions.standInit

  def kick_alignment_tolerance_deg(self):
    """A bounded calibration parameter; defaults to the legacy 15 degrees."""
    value = float(os.environ.get("ROBOCUP_KICK_ALIGNMENT_DEG", "15"))
    return max(5.0, min(30.0, value))

  def is_near_pitch_boundary(self, selfXYZ, x_limit=4.15, y_limit=2.75):
    return abs(selfXYZ[0]) >= x_limit or abs(selfXYZ[1]) >= y_limit

  def boundary_recovery_motion(self, selfXYZ):
    """Turn toward the pitch centre rather than walking out after a vision loss."""
    self.lastTacticalAction = "boundary_recovery"
    turn = Functions.calculateTurningAngleAccordingToRobotHeading([0.0, 0.0], selfXYZ, self.getRollPitchYaw()[2])
    if abs(turn) > 15:
      motion = self.getTurningMotion(turn)
      return motion if motion is not None else self.motions.standInit
    return self.motions.forwards50

  def search_ball_motion(self):
    """Bounded search motion used only when camera-based perception is empty."""
    self.lastTacticalAction = "search_ball"
    return self.motions.turnLeft20 if int(self.robot.getTime()) % 2 == 0 else self.motions.turnRight10_V2

  # ------------ supervisor data ------------
  def getSupervisorData(self):
    #  队列空就直接返回
    if self.receiver.getQueueLength() == 0:
      return False

    msg = self.receiver.getBytes()

    fmt = 'dd9ss24d'
    expected = struct.calcsize(fmt)  # 应该是 224
    if len(msg) != expected:
      self.receiver.nextPacket()
      return False

    data = struct.unpack(fmt, msg)
    self.supervisorData = data
    self.receiver.nextPacket()

    # Supervisor truth is evaluation-only when P1 camera mode is selected.
    ball_x = float(data[0])
    ball_y = float(data[1])
    self._evaluationBallTruth = [ball_x, ball_y]

    #  更新机器人坐标（24d = 8 robots * 3d）
    # data 的前面 dd + 9s + s = 2 + 2 = 4 个字段，所以 24d 从 index=4 开始
    base = 4
    robots = {}
    for i, name in enumerate(ROBOT_ORDER):
      x = float(data[base + i*3 + 0])
      y = float(data[base + i*3 + 1])
      z = float(data[base + i*3 + 2])
      robots[name] = (x, y, z)
    self.world["robots"] = robots

    # （可选）如果你原项目有 ballOwner / ballPriority，这里再解析设置
    # self.world["ballOwner"] = ...
    # self.world["ballPriority"] = ...

    self._perceptionStep += 1
    detection = self.lastPerception
    if self._perceptionStep % 3 == 0:
      detections = [detector.detect() for detector in self.ballDetectors]
      detections = [candidate for candidate in detections if candidate is not None]
      detection = max(detections, key=lambda candidate: candidate["confidence"]) if detections else None
      self.lastPerception = detection

    estimate = None
    if detection is not None:
      estimate = CameraBallDetector.estimate_world_xy(
        detection, self.getSelfCoordinate(), self.getRollPitchYaw()[2]
      )

    if self.ball_source == "camera":
      self.world["ball"] = estimate
    elif self.ball_source == "fused":
      self.world["ball"] = estimate if estimate is not None else [ball_x, ball_y]
    else:
      self.world["ball"] = [ball_x, ball_y]

    if self.world["ball"] is not None:
      self.ballTracker.update(self.world["ball"], TIME_STEP / 1000.0)
    self._log_perception(detection, estimate)
    self._log_foot_kinematics()

    return True


  # ------------ kick chooser ------------
  def pick_kick_motion(self, team: str, selfXYZ, ballXY):
    receiver = self.select_pass_receiver(team, ballXY)
    if receiver is not None:
      self.lastTacticalAction = f"pass_to_{receiver}"
      return self.motions.longPass

    opp_goal_x = -4.5 if team == "BLUE" else 4.5
    dist_to_goal = abs(opp_goal_x - ballXY[0])
    if dist_to_goal > 2.5:
      self.lastTacticalAction = "long_clearance"
      return self.motions.longShoot
    self.lastTacticalAction = "shoot"
    if ballXY[1] < selfXYZ[1]:
      return self.motions.rightShoot
    return self.motions.shoot

  @staticmethod
  def _point_to_segment_distance(point, start, end):
    dx, dy = end[0] - start[0], end[1] - start[1]
    norm = dx * dx + dy * dy
    if norm < 1e-8:
      return Functions.calculateDistance(point, start)
    ratio = max(0.0, min(1.0, ((point[0] - start[0]) * dx + (point[1] - start[1]) * dy) / norm))
    closest = [start[0] + ratio * dx, start[1] + ratio * dy]
    return Functions.calculateDistance(point, closest)

  def select_pass_receiver(self, team, ball_xy):
    """Choose an advancing teammate only when the pass corridor is clear."""
    direction = -1.0 if team == "BLUE" else 1.0
    teammates = []
    for name, pose in self.world.get("robots", {}).items():
      if name == self.name or not name.startswith(team):
        continue
      progress = (pose[0] - ball_xy[0]) * direction
      distance = Functions.calculateDistance([pose[0], pose[1]], ball_xy)
      if progress > 0.45 and 0.55 < distance < 3.6:
        teammates.append((progress - 0.18 * distance, name, pose))
    if not teammates:
      return None

    opponents = [pose for name, pose in self.world.get("robots", {}).items() if not name.startswith(team)]
    for _score, name, pose in sorted(teammates, reverse=True):
      if all(self._point_to_segment_distance([opponent[0], opponent[1]], ball_xy, pose) > 0.42 for opponent in opponents):
        return name
    return None
  def getBallEstimate(self):
    # 1) Current perception or the explicitly selected legacy source.
    if self.world.get("ball") is not None:
      return self.world["ball"]

    # Camera-only control must report loss rather than silently using truth.
    if self.ball_source == "camera":
      return None

    # 2) Fallback prediction for non-camera legacy mode.
    if hasattr(self, "ballTracker") and self.ballTracker is not None:
      # BallTracker 里一般会存 last position/velocity；没有就返回 None
      if hasattr(self.ballTracker, "last") and self.ballTracker.last is not None:
        p = self.ballTracker.last
        return [float(p[0]), float(p[1])]

    return None
  def compute_target_avoid_opponents(self, ball, me, opponent_prefix, repel_radius=0.8, repel_gain=0.9):
    # opponent_prefix: "BLUE" 或 "RED"
    robots = self.world.get("robots", {})
    rx, ry = 0.0, 0.0

    for name, (x, y, z) in robots.items():
      if not name.startswith(opponent_prefix):
        continue
      dx = me[0] - x
      dy = me[1] - y
      d2 = dx*dx + dy*dy
      if d2 < 1e-6:
        continue
      d = math.sqrt(d2)
      if d > repel_radius:
        continue

      # 越近排斥越强
      w = repel_gain * (repel_radius - d) / repel_radius
      rx += (dx / d) * w
      ry += (dy / d) * w

    # 目标点：球位置 + 排斥偏移（让你绕开人再接近球）
    return [ball[0] + rx, ball[1] + ry]
  def getBallVelocityEstimate(self):
    # BallTracker exposes a smoothed (vx, vy) pair as ``v``.
    if hasattr(self, "ballTracker") and hasattr(self.ballTracker, "v"):
      v = self.ballTracker.v
      return [float(v[0]), float(v[1])]

    # 否则差分
    if not hasattr(self, "_last_ball"):
      self._last_ball = None
      return [0.0, 0.0]

    dt = TIME_STEP / 1000.0
    if self._last_ball is None or self.world.get("ball") is None:
      self._last_ball = self.world.get("ball")
      return [0.0, 0.0]

    vx = (self.world["ball"][0] - self._last_ball[0]) / dt
    vy = (self.world["ball"][1] - self._last_ball[1]) / dt
    self._last_ball = self.world["ball"]
    return [vx, vy]
