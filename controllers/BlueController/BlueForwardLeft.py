import os, sys
currentdir = os.path.dirname(os.path.realpath(__file__))
parentdir = os.path.dirname(currentdir)
sys.path.append(parentdir)

from Base.SoccerRobotBase import SoccerRobot
from Utils.Consts import TIME_STEP
from Utils import Functions

class ForwardLeft(SoccerRobot):
    def run(self):
        self.printSelf()

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

            # 避开队友，别和 DEF / FW_R 挤
            self._avoid_teammates(me, min_d=0.40)

            # Camera-only mode may legitimately lose the ball.  Search safely
            # instead of dereferencing a missing estimate or falling back to
            # Supervisor truth.
            if ball is None:
                self.applyMotion(self.search_ball_motion())
                continue

            # 只有我在追球，其他机器人不追球
            if not self._am_i_the_chaser(ball, me):
                self._go_home_and_face_ball([1.2, 0.0], ball, me)
                continue

            # 执行追球逻辑
            yaw = self.getRollPitchYaw()[2]
            turn = Functions.calculateTurningAngleAccordingToRobotHeading(ball, me, yaw)
            dist = Functions.calculateDistance(ball, me)

            # 如果距离球很近，则准备踢球
            if dist <= 0.30:
                if abs(turn) > 10:
                    tm = self.getTurningMotion(turn)
                    self.applyMotion(tm if tm is not None else self.motions.standInit)
                else:
                    self.applyMotion(self.pick_kick_motion("BLUE", me, ball))
                continue

            if abs(turn) > 75:
                tm = self.getTurningMotion(turn)
                self.applyMotion(tm if tm is not None else self.motions.standInit)
            else:
                self.applyMotion(self.motions.forwards50)

    def _am_i_the_chaser(self, ball, me):
        robots = self.world.get("robots", {})
        other = robots.get("BLUE_FW_R", None)
        if other is None:
            return True  # 如果没有右前锋机器人，允许左前锋追球

        my_dist = Functions.calculateDistance(ball, me)
        other_dist = Functions.calculateDistance([ball[0], ball[1]], [other[0], other[1], other[2]])
        return my_dist < other_dist

    def _avoid_teammates(self, me, min_d=0.40):
        robots = self.world.get("robots", {})
        for mate in ("BLUE_FW_R", "BLUE_DEF"):
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
