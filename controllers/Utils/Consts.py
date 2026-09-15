from controller import Motion
import math
import os

TIME_STEP = 40
PI = math.pi

INITIAL_TRANSLATIONS = {
  "BALL"      : [ 0.00,  0.00, 0.0798759],
  "RED_GK"    : [-4.00,  0.00, 0.33],
  "RED_DEF_L" : [-2.50,  1.20, 0.33],
  "RED_DEF_R" : [-2.50, -1.20, 0.33],
  "RED_FW"    : [-0.80,  0.00, 0.33],
  "BLUE_GK"   : [ 4.00,  0.00, 0.33],
  "BLUE_DEF"  : [ 3.00,  0.00, 0.33],
  "BLUE_FW_L" : [ 1.40, -1.20, 0.33],
  "BLUE_FW_R" : [ 1.40,  1.20, 0.33]
}

INITIAL_ROTATIONS = {
  "BALL"      : [0, 1, 0, 0.0],
  "RED_GK"    : [0, 1, 0, 0.1],
  "RED_DEF_L" : [0, 1, 0, 0.1],
  "RED_DEF_R" : [0, 1, 0, 0.1],
  "RED_FW"    : [0, 1, 0, 0.1],
  "BLUE_GK"   : [0, 1, 0, 0.1],
  "BLUE_DEF"  : [0, 1, 0, 0.1],
  "BLUE_FW_L" : [0, 1, 0, 0.1],
  "BLUE_FW_R" : [0, 1, 0, 0.1]
}

BALL_POSITIONS = {
  "OUT_R"     : [-3.65, 0, 0.0798759],
  "OUT_B"     : [ 3.65, 0, 0.0798759]
}

MOTION_ROOT = '../../motions/retargeted' if os.environ.get('ROBOCUP_USE_RETARGETED_MOTIONS', '1') == '1' else '../../motions'

def motion_path(filename):
  return f'{MOTION_ROOT}/{filename}'

class Motions:
  def __init__(self):
    self.handWave = MotionBase('handWave', motion_path('HandWave.motion'))
    self.forwards = MotionBase('forwards', motion_path('Forwards.motion'))
    self.forwardsSprint = MotionBase('forwardsSprint', motion_path('ForwardsSprint.motion'))
    self.forwards50 = MotionBase('forwards50', motion_path('Forwards50.motion'))
    self.backwards = MotionBase('backwards', motion_path('Backwards.motion'))

    # kick / pass
    self.shoot = MotionBase('shoot', motion_path('Shoot.motion'))
    self.rightShoot = MotionBase('rightShoot', motion_path('RightShoot.motion'))
    # The supplied asset is a long passing/clearance kick.  Keep the legacy
    # name for existing defence code and expose its tactical meaning too.
    self.longPass = MotionBase('longPass', motion_path('LongPass.motion'))
    self.longShoot = self.longPass
    self.leftSidePass = MotionBase('leftSidePass', motion_path('SidePass_Left.motion'))
    self.rightSidePass = MotionBase('rightSidePass', motion_path('SidePass_Right.motion'))

    # defense moves
    self.sideStepLeft = MotionBase('sideStepLeft', motion_path('SideStepLeft.motion'))
    self.sideStepRight = MotionBase('sideStepRight', motion_path('SideStepRight.motion'))

    # recovery
    self.standUpFromFront = MotionBase('standUpFromFront', motion_path('StandUpFromFront.motion'))
    self.standUpFromBack = MotionBase('standUpFromBack', motion_path('StandUpFromBack.motion'))

    # turning
    self.turnLeft10 = MotionBase('turnLeft10', motion_path('TurnLeft10.motion'))
    self.turnLeft20 = MotionBase('turnLeft20', motion_path('TurnLeft20.motion'))
    self.turnLeft30 = MotionBase('turnLeft30', motion_path('TurnLeft30.motion'))
    self.turnLeft40 = MotionBase('turnLeft40', motion_path('TurnLeft40.motion'))
    self.turnLeft60 = MotionBase('turnLeft60', motion_path('TurnLeft60.motion'))
    self.turnLeft180 = MotionBase('turnLeft180', motion_path('TurnLeft180.motion'))
    self.turnRight10 = MotionBase('turnRight10', motion_path('TurnRight10.motion'))
    self.turnRight10_V2 = MotionBase('turnRight10', motion_path('TurnRight10_V2.motion'))
    self.turnRight40 = MotionBase('turnRight40', motion_path('TurnRight40.motion'))
    self.turnRight60 = MotionBase('turnRight60', motion_path('TurnRight60.motion'))

    self.standInit = MotionBase('standInit', motion_path('StandInit.motion'))

class MotionBase(Motion):
  def __init__(self, name, path):
    super().__init__(path)
    self.name = name
