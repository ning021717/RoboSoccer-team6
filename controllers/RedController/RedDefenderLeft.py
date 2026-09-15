import os, sys
currentdir = os.path.dirname(os.path.realpath(__file__))
parentdir = os.path.dirname(currentdir)
sys.path.append(parentdir)

from Base.SoccerRobotBase import SoccerRobot
from Utils.Consts import TIME_STEP
from Utils import Functions

class DefenderLeft(SoccerRobot):
    def run(self):
        self.printSelf()

        for _ in range(25):
            if self.robot.step(TIME_STEP) == -1: return
        self.applyMotion(self.motions.standInit)
        for _ in range(15):
            if self.robot.step(TIME_STEP) == -1: return

        HOME = [-1.6, -0.9] # 左半场防守位

        while self.robot.step(TIME_STEP) != -1:
            ok = self.getSupervisorData()
            if not ok:
                self.applyMotion(self.motions.standInit)
                continue

            ball = self.getBallEstimate()
            me = self.getSelfCoordinate()

            if self.isFallen(me):
                self.applyMotion(self.getStandUpMotion())
                continue

            self._avoid_teammates(me, min_d=0.40)

            if ball is None:
                self._go_home_and_face_ball(HOME, None, me)
                continue

            # 防区判定：如果不在左半场防区，回防
            in_assigned_zone = (ball[1] <= 0.5) and (ball[0] < 1.5)
            if not in_assigned_zone:
                self._go_home_and_face_ball(HOME, ball, me)
                continue

            # 前锋在抢球，回防
            if self._forward_near_ball(ball):
                self._go_home_and_face_ball(HOME, ball, me)
                continue

            # 出击/解围
            yaw = self.getRollPitchYaw()[2]
            turn = Functions.calculateTurningAngleAccordingToRobotHeading(ball, me, yaw)
            dist = Functions.calculateDistance(ball, me)

            if dist <= 0.32:
                if abs(turn) > 15:
                    tm = self.getTurningMotion(turn)
                    self.applyMotion(tm if tm is not None else self.motions.standInit)
                else:
                    self.applyMotion(self.pick_kick_motion("RED", me, ball))
                continue

            if abs(turn) > 35:
                tm = self.getTurningMotion(turn)
                self.applyMotion(tm if tm is not None else self.motions.standInit)
            else:
                self.applyMotion(self.motions.forwards50)

    def _avoid_teammates(self, me, min_d=0.40):
        robots = self.world.get("robots", {})
        for mate in ("RED_FW", "RED_DEF_R"):
            p = robots.get(mate, None)
            if p is None: continue
            d = Functions.calculateDistance([p[0], p[1]], [me[0], me[1]])
            if d < min_d:
                if p[1] > me[1]: self.applyMotion(self.motions.sideStepRight)
                else: self.applyMotion(self.motions.sideStepLeft)
                return True
        return False

    def _forward_near_ball(self, ball):
        robots = self.world.get("robots", {})
        fw = robots.get("RED_FW")
        if fw and fw[2] > 0.20:
            fw_dist = Functions.calculateDistance([ball[0], ball[1]], [fw[0], fw[1]])
            if fw_dist < 1.2: return True
        return False

    def _go_home_and_face_ball(self, home_xy, ball, me_xyz):
        yaw = self.getRollPitchYaw()[2]
        if ball is not None:
            turn_face = Functions.calculateTurningAngleAccordingToRobotHeading(ball, me_xyz, yaw)
            if abs(turn_face) > 35:
                tm = self.getTurningMotion(turn_face)
                self.applyMotion(tm if tm is not None else self.motions.standInit)
                return

        turn = Functions.calculateTurningAngleAccordingToRobotHeading(home_xy, me_xyz, yaw)
        dist = Functions.calculateDistance(home_xy, me_xyz)

        if dist < 0.25:
            self.applyMotion(self.motions.standInit)
            return

        if abs(turn) > 75:
            tm = self.getTurningMotion(turn)
            self.applyMotion(tm if tm is not None else self.motions.standInit)
        else:
            self.applyMotion(self.motions.forwards50)

    def decideMotion(self, ballCoordinate, selfCoordinate):
        return self.motions.standInit