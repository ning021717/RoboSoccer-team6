import os, sys
currentdir = os.path.dirname(os.path.realpath(__file__))
parentdir = os.path.dirname(currentdir)
sys.path.append(parentdir)

from Base.SoccerRobotBase import SoccerRobot
from Utils.Consts import TIME_STEP
from Utils import Functions

class Defender(SoccerRobot):
    def run(self):
        self.printSelf()

        HOME_DEF = [0.4, 0.0]  # 蓝队防守站位（调整站位坐标）

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

            # 避开队友，别和 FW_L、FW_R 挤
            self._avoid_teammates(me, min_d=0.45)

            if ball is None:
                self._go_home_and_face_ball(HOME_DEF, None, me)
                continue

            # 球不危险：守站位，不追球（避免抱团）
            if ball[0] > -1.5:
                self._go_home_and_face_ball(HOME_DEF, ball, me)
                continue

            # 球危险（靠近本方半场）：拦截/解围（简单追一下）
            yaw = self.getRollPitchYaw()[2]
            turn = Functions.calculateTurningAngleAccordingToRobotHeading(ball, me, yaw)
            dist = Functions.calculateDistance(ball, me)

            if dist <= 0.32:
                if abs(turn) > 10:
                    tm = self.getTurningMotion(turn)
                    self.applyMotion(tm if tm is not None else self.motions.standInit)
                else:
                    self.applyMotion(self.motions.longShoot)  # 解围
                continue

            if abs(turn) > 75:
                tm = self.getTurningMotion(turn)
                self.applyMotion(tm if tm is not None else self.motions.standInit)
            else:
                self.applyMotion(self.motions.forwards50)

    def _avoid_teammates(self, me, min_d=0.45):
        robots = self.world.get("robots", {})
        for mate in ("BLUE_FW_L", "BLUE_FW_R"):
            p = robots.get(mate, None)
            if p is None:
                continue
            d = Functions.calculateDistance([p[0], p[1]], [me[0], me[1]])
            if d < min_d:
                if p[1] > me[1]:
                    self.applyMotion(self.motions.sideStepRight)
                else:
                    self.applyMotion(self.motions.sideStepLeft)
                return

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
