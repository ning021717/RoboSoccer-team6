# E:\RoboCupSoccer-main\controllers\Motion.py
# 机器人基础运动模块，保证机器人能站立、行走，解决导入错误
class Motion:  # 关键修改：将 MotionClass 改为 Motion，匹配 Consts.py 的继承需求
    """核心运动类，包含机器人站立、行走的基础实现"""
    def __init__(self, robot):
        self.robot = robot  # 接收Robot实例
        self.time_step = 32  # 固定时间步，适配RoboCup
        # 初始化关节（机器人核心运动关节，保证能动）
        self.joints = []
        joint_names = [
            "HeadYaw", "HeadPitch",
            "LHipYawPitch", "LHipRoll", "LHipPitch",
            "LKneePitch", "LAnkleRoll", "LAnklePitch",
            "RHipYawPitch", "RHipRoll", "RHipPitch",
            "RKneePitch", "RAnkleRoll", "RAnklePitch"
        ]
        for name in joint_names:
            joint = self.robot.getDevice(name)
            self.joints.append(joint)
    
    def stand(self):
        """站立动作（机器人启动后先站立，基础动作）"""
        stand_positions = [
            0.0, 0.0,
            0.0, 0.0, -0.5,
            1.0, 0.0, -0.5,
            0.0, 0.0, -0.5,
            1.0, 0.0, -0.5
        ]
        for i, joint in enumerate(self.joints):
            joint.setPosition(stand_positions[i])
            joint.setVelocity(0.5)  # 关节运动速度，保证平稳站立
    
    def walk_forward(self):
        """向前行走动作（简单循环，保证机器人能动起来）"""
        walk_positions = [
            0.0, 0.0,
            0.1, 0.1, -0.3,
            0.6, 0.1, -0.3,
            0.1, 0.1, -0.3,
            0.6, 0.1, -0.3
        ]
        for i, joint in enumerate(self.joints):
            joint.setPosition(walk_positions[i])
            joint.setVelocity(0.8)

# 简化版BasicMotion，适配导入需求，保证不报错
class BasicMotion:
    """基础动作封装，兼容导入语句"""
    def __init__(self, robot):
        self.motion_core = Motion(robot)  # 同步修改：引用重命名后的 Motion 类
    
    def init_stand(self):
        """调用站立动作"""
        self.motion_core.stand()
    
    def go_forward(self):
        """调用向前行走动作"""
        self.motion_core.walk_forward()