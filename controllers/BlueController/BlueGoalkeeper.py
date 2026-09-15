import os, sys
currentdir = os.path.dirname(os.path.realpath(__file__))
parentdir = os.path.dirname(currentdir)
sys.path.append(parentdir)

from Base.SoccerRobotBase import SoccerRobot
from Utils.Consts import TIME_STEP
from Utils import Functions

class Goalkeeper(SoccerRobot):
    def run(self):
        self.printSelf()

        GOAL_X = -4.2         # 红队球门的x坐标
        LIMIT_Y = 1.2         # 门将横向活动的最大范围

        while self.robot.step(TIME_STEP) != -1:
            ok = self.getSupervisorData()
            if not ok:
                self.applyMotion(self.motions.standInit)
                continue

            ball = self.getBallEstimate()
            if ball is None:
                self.applyMotion(self.motions.standInit)
                continue

            me = self.getSelfCoordinate()
            if self.isFallen(me):
                self.applyMotion(self.getStandUpMotion())
                continue

            # 1) 球离门太远，守门员回到门前并面朝球
            if ball[0] > -2.5:
                yaw = self.getRollPitchYaw()[2]
                turn = Functions.calculateTurningAngleAccordingToRobotHeading(ball, me, yaw)
                if abs(turn) > 60:
                    tm = self.getTurningMotion(turn)
                    self.applyMotion(tm if tm is not None else self.motions.standInit)
                else:
                    self.applyMotion(self.motions.standInit)
                continue

            # 2) 球靠近禁区时，守门员横向调整位置
            dy = ball[1] - me[1]

            # 太靠上/下，做横向侧移
            if dy > 0.15 and me[1] < LIMIT_Y:
                self.applyMotion(self.motions.sideStepLeft)   # 注意：你的 motion 左右可能相反，必要时交换
                continue
            if dy < -0.15 and me[1] > -LIMIT_Y:
                self.applyMotion(self.motions.sideStepRight)
                continue

            # 3) 球非常近时，执行大脚解围
            yaw = self.getRollPitchYaw()[2]
            turn = Functions.calculateTurningAngleAccordingToRobotHeading(ball, me, yaw)
            dist = Functions.calculateDistance(ball, me)

            if dist <= 0.35:
                if abs(turn) > 10:
                    tm = self.getTurningMotion(turn)
                    self.applyMotion(tm if tm is not None else self.motions.standInit)
                else:
                    # 解围：尽量使用 longShoot 踢向远方
                    self.applyMotion(self.motions.longShoot)
                continue

            # 4) 否则保持站位
            self.applyMotion(self.motions.standInit)

    def decideMotion(self, ballCoordinate, selfCoordinate):
        return self.motions.standInit
