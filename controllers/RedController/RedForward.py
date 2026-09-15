import os, sys
currentdir = os.path.dirname(os.path.realpath(__file__))
parentdir = os.path.dirname(currentdir)
sys.path.append(parentdir)

from Base.SoccerRobotBase import SoccerRobot
from Utils.Consts import TIME_STEP
from Utils import Functions

class Forward(SoccerRobot):
    def run(self):
        self.printSelf()

        # 完全沿用蓝队的缓冲模式，不加任何死锁
        for _ in range(25):
            if self.robot.step(TIME_STEP) == -1: return
        self.applyMotion(self.motions.standInit)
        for _ in range(15):
            if self.robot.step(TIME_STEP) == -1: return

        while self.robot.step(TIME_STEP) != -1:
            ok = self.getSupervisorData()
            if not ok:
                self.applyMotion(self.motions.forwards50)
                continue

            ball = self.getBallEstimate()
            me = self.getSelfCoordinate()

            if self.isFallen(me):
                self.applyMotion(self.getStandUpMotion())
                continue

            if self.is_near_pitch_boundary(me):
                self.applyMotion(self.boundary_recovery_motion(me))
                continue

            # 避开队友
            self._avoid_teammates(me, min_d=0.40)

            if ball is None:
                self.applyMotion(self.search_ball_motion())
                continue

            yaw = self.getRollPitchYaw()[2]
            turn = Functions.calculateTurningAngleAccordingToRobotHeading(ball, me, yaw)
            dist = Functions.calculateDistance(ball, me)

            # 近距离：站定 -> 踢
            if dist <= 0.32:
                # During contact calibration, a slightly wider *bounded*
                # tolerance avoids turning the support foot into a ball that
                # is already in the right-foot strike corridor.  The default
                # remains the legacy 15 degrees for ordinary matches.
                if abs(turn) > self.kick_alignment_tolerance_deg():
                    tm = self.getTurningMotion(turn)
                    self.applyMotion(tm if tm is not None else self.motions.standInit)
                else:
                    self.applyMotion(self.pick_kick_motion("RED", me, ball))
                continue

            # 中远距离追踪 (35度比蓝队75度更灵活)
            if abs(turn) > 35:
                tm = self.getTurningMotion(turn)
                self.applyMotion(tm if tm is not None else self.motions.standInit)
            else:
                self.applyMotion(self.motions.forwards50)

    def _avoid_teammates(self, me, min_d=0.40):
        robots = self.world.get("robots", {})
        for mate in ("RED_DEF_L", "RED_DEF_R"):
            p = robots.get(mate, None)
            if p is None:
                continue
            d = Functions.calculateDistance([p[0], p[1]], [me[0], me[1]])
            if d < min_d:
                if p[1] > me[1]:
                    self.applyMotion(self.motions.sideStepRight)
                else:
                    self.applyMotion(self.motions.sideStepLeft)
                return True
        return False

    def decideMotion(self, ballCoordinate, selfCoordinate):
        return self.motions.forwards50
