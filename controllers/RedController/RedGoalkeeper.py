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

        X_GOAL = -4.45   # 红队球门的x坐标
        Y_LIMIT = 0.95   # 门框的y范围

        while self.robot.step(TIME_STEP) != -1:
            if not self.isNewBallDataAvailable():
                self.applyMotion(self.motions.standInit)
                continue

            self.getSupervisorData()
            ball = self.getBallEstimate()
            me = self.getSelfCoordinate()

            if ball is None:
                self.applyMotion(self.motions.standInit)
                continue

            if self.isFallen(me):
                self.applyMotion(self.getStandUpMotion())
                continue

            vx, vy = self.getBallVelocityEstimate()
            dist = Functions.calculateDistance(ball, me)

            # 1) 如果球离守门员非常近，进行大脚解围
            if dist < 0.35:
                self.applyMotion(self.motions.longShoot)  # 大脚解围
                continue

            # 2) 判断球是否朝红门飞来
            coming_to_goal = (vx < -0.05) and (ball[0] < -2.0)

            if coming_to_goal:
                # 预测球到达门线的y坐标
                if abs(vx) < 1e-3:  # 如果vx非常小，避免除以零
                    y_pred = ball[1]
                else:
                    t = (X_GOAL - ball[0]) / vx  # 计算球到达门线的时间
                    y_pred = ball[1] + vy * t  # 预测y坐标

                # 限制y坐标在门框范围内
                if y_pred > Y_LIMIT:
                    y_pred = Y_LIMIT
                if y_pred < -Y_LIMIT:
                    y_pred = -Y_LIMIT

                # 目标点：门线上的拦截点
                target = [X_GOAL + 0.15, y_pred]  # 稍微站在门线前一点
                yaw = self.getRollPitchYaw()[2]
                turn = Functions.calculateTurningAngleAccordingToRobotHeading(target, me, yaw)

                # 如果需要转向目标
                if abs(turn) > 20:
                    tm = self.getTurningMotion(turn)
                    self.applyMotion(tm if tm is not None else self.motions.standInit)
                else:
                    # 根据y差值决定往哪侧移
                    dy = target[1] - me[1]
                    if dy > 0.12:
                        self.applyMotion(self.motions.sideStepLeft)
                    elif dy < -0.12:
                        self.applyMotion(self.motions.sideStepRight)
                    else:
                        self.applyMotion(self.motions.standInit)

                # 如果球非常接近，可以添加扑救动作（例如扑向左或右）
                if dist < 0.35:
                    # 示例：如果球离门很近，可以执行扑救动作
                    # if abs(dy) > 0.35 and dist < 0.8: play diveLeft or diveRight motion
                    pass

            else:
                # 球不危险：守门员回到中路站位
                dy = 0.0 - me[1]
                if dy > 0.12:
                    self.applyMotion(self.motions.sideStepLeft)
                elif dy < -0.12:
                    self.applyMotion(self.motions.sideStepRight)
                else:
                    self.applyMotion(self.motions.standInit)

    def decideMotion(self, ballCoordinate, selfCoordinate):
        return self.motions.standInit
