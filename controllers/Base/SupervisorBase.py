"""
SupervisorBase (keep original behavior).
"""

import os, sys
currentdir = os.path.dirname(os.path.realpath(__file__))
parentdir = os.path.dirname(currentdir)
sys.path.append(parentdir)

from controller import Supervisor
import struct
from Utils.Consts import TIME_STEP
from Utils import Functions

class SupervisorBase(Supervisor):
  def __init__(self):
    super().__init__()

    self.emitter = self.getDevice("emitter")
    self.emitter.setChannel(0)

    self.ball = self.getFromDef("SOCCERBALL")

    self.robots = {
      "RED_GK"    : self.getFromDef("RED_GK"),
      "RED_DEF_L" : self.getFromDef("RED_DEF_L"),
      "RED_DEF_R" : self.getFromDef("RED_DEF_R"),
      "RED_FW"    : self.getFromDef("RED_FW"),
      "BLUE_GK"   : self.getFromDef("BLUE_GK"),
      "BLUE_DEF"  : self.getFromDef("BLUE_DEF"),
      "BLUE_FW_L" : self.getFromDef("BLUE_FW_L"),
      "BLUE_FW_R" : self.getFromDef("BLUE_FW_R")
    }

    self.ballPriority = "R"
    self.previousBallLocation = [0, 0, 0.0798759]
    self._cache_initial_poses()
    self.restoreInitialPositions()

  def getBallPosition(self) -> list:
    ballTranslation = self.ball.getField("translation")
    newBallLocation = ballTranslation.getSFVec3f()

    if abs(newBallLocation[0]) < 4.5 and abs(newBallLocation[1]) < 3:
      if (abs(self.previousBallLocation[0] - newBallLocation[0]) > 0.05 or
          abs(self.previousBallLocation[1] - newBallLocation[1]) > 0.05):
        self.ballPriority = "N"
        self.previousBallLocation = newBallLocation

    return newBallLocation

  def setBallPosition(self, ballPosition) -> None:
    self.previousBallLocation = ballPosition
    ballTranslation = self.ball.getField("translation")
    ballTranslation.setSFVec3f(ballPosition)
    self.ball.resetPhysics()

  def getRobotPosition(self, robotName) -> list:
    robotTranslation = self.robots[robotName].getField("translation")
    return robotTranslation.getSFVec3f()

  def getBallOwner(self) -> str:
    ballPosition = self.getBallPosition()
    ballOwnerRobotName = "RED_GK"
    minDistance = Functions.calculateDistance(ballPosition, self.getRobotPosition(ballOwnerRobotName))
    for key in self.robots:
      tempDistance = Functions.calculateDistance(ballPosition, self.getRobotPosition(key))
      if tempDistance < minDistance:
        minDistance = tempDistance
        ballOwnerRobotName = key

    if len(ballOwnerRobotName) < 9:
      ballOwnerRobotName = ballOwnerRobotName + ('*' * (9 - len(ballOwnerRobotName)))
    return ballOwnerRobotName

  def sendSupervisorData(self) -> None:
    ballPosition = self.getBallPosition()
    ballOwner = bytes(self.getBallOwner(), 'utf-8')
    ballPriority = bytes(self.ballPriority, 'utf-8')

    redGk = self.getRobotPosition("RED_GK")
    redDefLeft = self.getRobotPosition("RED_DEF_L")
    redDefRight = self.getRobotPosition("RED_DEF_R")
    redFw = self.getRobotPosition("RED_FW")
    blueGk = self.getRobotPosition("BLUE_GK")
    blueDef = self.getRobotPosition("BLUE_DEF")
    blueFwLeft = self.getRobotPosition("BLUE_FW_L")
    blueFwRight = self.getRobotPosition("BLUE_FW_R")

    data = struct.pack(
      'dd9ss24d',
      ballPosition[0], ballPosition[1], ballOwner, ballPriority,
      redGk[0], redGk[1], redGk[2],
      redDefLeft[0], redDefLeft[1], redDefLeft[2],
      redDefRight[0], redDefRight[1], redDefRight[2],
      redFw[0], redFw[1], redFw[2],
      blueGk[0], blueGk[1], blueGk[2],
      blueDef[0], blueDef[1], blueDef[2],
      blueFwLeft[0], blueFwLeft[1], blueFwLeft[2],
      blueFwRight[0], blueFwRight[1], blueFwRight[2]
    )
    self.emitter.send(data)

  def setBallPriority(self, priority):
    self.ballPriority = priority

  def resetSimulation(self):
    self.previousBallLocation = [0, 0, 0.0798759]
    self.simulationReset()
    for robot in self.robots.values():
      robot.resetPhysics()

  def stopSimulation(self):
    self.simulationSetMode(self.SIMULATION_MODE_PAUSE)
  def _cache_initial_poses(self):
      self._init_ball_t = self.ball.getField("translation").getSFVec3f()
      self._init_ball_r = self.ball.getField("rotation").getSFRotation()

      self._init_robot_poses = {}
      for name, node in self.robots.items():
        t = node.getField("translation").getSFVec3f()
        r = node.getField("rotation").getSFRotation()
        self._init_robot_poses[name] = (t, r)

  def restoreInitialPositions(self):
    # ball
    self.ball.getField("translation").setSFVec3f(self._init_ball_t)
    self.ball.getField("rotation").setSFRotation(self._init_ball_r)
    self.ball.resetPhysics()
    self.previousBallLocation = [self._init_ball_t[0], self._init_ball_t[1], self._init_ball_t[2]]
    self.ballPriority = "R"

    # robots
    for name, node in self.robots.items():
      t, r = self._init_robot_poses[name]
      node.getField("translation").setSFVec3f(t)
      node.getField("rotation").setSFRotation(r)
      node.resetPhysics()
