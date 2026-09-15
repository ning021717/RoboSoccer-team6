import math

# ----------------------------
# Basic geometry helpers
# ----------------------------

def clamp(v, lo, hi):
  return max(lo, min(hi, v))

def normalize_deg(a):
  """Normalize angle to [-180, 180)."""
  while a >= 180:
    a -= 360
  while a < -180:
    a += 360
  return a

def calculateDistance(coordinate1, coordinate2) -> float:
  deltaX = coordinate1[0] - coordinate2[0]
  deltaY = coordinate1[1] - coordinate2[1]
  return math.hypot(deltaX, deltaY)

def calculateAngleAccordingToXAxis(targetCoordinate, robotCoordinate) -> float:
  """Angle between robot->target vector and +x axis, in degrees [0..180]."""
  hypot = calculateDistance(targetCoordinate, robotCoordinate)
  if hypot < 1e-9:
    return 0.0
  deltaX = abs(targetCoordinate[0] - robotCoordinate[0])
  cosTheta = clamp(deltaX / hypot, -1.0, 1.0)
  return math.degrees(math.acos(cosTheta))

def calculateBallRegion(targetCoordinate, robotCoordinate) -> int:
  """Return quadrant of target w.r.t robot: 1=top-right,2=top-left,3=bottom-left,4=bottom-right"""
  if targetCoordinate[0] > robotCoordinate[0]:
    return 1 if targetCoordinate[1] > robotCoordinate[1] else 4
  else:
    return 2 if targetCoordinate[1] > robotCoordinate[1] else 3

def calculateTurningAngleAccordingToRobotHeading(targetCoordinate, robotCoordinate, robotHeadingAngleRad) -> float:
  """
  turningAngle(deg): positive -> turn left, negative -> turn right
  """
  degree = calculateAngleAccordingToXAxis(targetCoordinate, robotCoordinate)
  region = calculateBallRegion(targetCoordinate, robotCoordinate)

  if region == 2:
    degree = 180 - degree
  elif region == 3:
    degree = degree - 180
  elif region == 4:
    degree = -degree

  headingDeg = math.degrees(robotHeadingAngleRad)
  turningAngle = normalize_deg(degree - headingDeg)
  return turningAngle

def heading_to_target_deg(targetXY, selfXYZ, selfHeadingRad):
  return calculateTurningAngleAccordingToRobotHeading(targetXY, selfXYZ, selfHeadingRad)

# ----------------------------
# Ball tracker (velocity + prediction)
# ----------------------------

class BallTracker:
  """
  Keep last ball position and estimate velocity in world XY.
  dt is derived from TIME_STEP (ms) passed in update().
  """
  def __init__(self):
    self.last = None  # (x,y)
    self.v = (0.0, 0.0)
    self.last_t = None

  def reset(self):
    self.last = None
    self.v = (0.0, 0.0)
    self.last_t = None

  def update(self, ballXY, dt_sec: float):
    if ballXY is None:
      return

    if self.last is None or dt_sec <= 1e-6:
      self.last = (ballXY[0], ballXY[1])
      return

    vx = (ballXY[0] - self.last[0]) / dt_sec
    vy = (ballXY[1] - self.last[1]) / dt_sec

    # light smoothing
    self.v = (0.6 * self.v[0] + 0.4 * vx, 0.6 * self.v[1] + 0.4 * vy)
    self.last = (ballXY[0], ballXY[1])

  def speed(self):
    return math.hypot(self.v[0], self.v[1])

  def predict_y_at_x(self, target_x: float, current_ball_xy):
    """
    Predict y where ball crosses target_x using constant velocity model.
    Return None if vx too small or moving away.
    """
    if current_ball_xy is None:
      return None
    vx, vy = self.v
    if abs(vx) < 1e-4:
      return None

    t = (target_x - current_ball_xy[0]) / vx
    if t < 0:
      return None

    return current_ball_xy[1] + vy * t
