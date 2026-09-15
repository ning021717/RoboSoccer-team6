"""
Red Team Main Controller (Master Dispatcher).
This controller should be selected as the controller for ALL Red team robots.
Roles and their specific Behavior Trees will be assigned automatically.
"""

import sys
import os

# ==========================================
# 1. 核心路径装载 (保证能找到 Utils 和 Base)
# ==========================================
current_script_path = os.path.abspath(__file__)
red_controller_dir = os.path.dirname(current_script_path)  
controllers_dir = os.path.dirname(red_controller_dir)      
project_root_dir = os.path.dirname(controllers_dir)        

if project_root_dir not in sys.path:
    sys.path.insert(0, project_root_dir)

from controller import Robot

# ==========================================
# 2. 机器人身份识别
# ==========================================
robot = Robot()
robotName = robot.getName()

print(f"==================================================")
print(f"🤖 [RED TEAM SYSTEM] Booting up robot: {robotName}")

robotController = None

# ==========================================
# 3. 动态加载决策树 (Dynamic Behavior Tree Loading)
# ==========================================
# 优化点：使用按需导入(Try-Except)，如果某个文件名字写错了，
# 它会精确报错告诉你哪个找不到了，而不会让整个队伍崩溃。
try:
    if robotName == "RED_GK":
        from RedGoalkeeper import Goalkeeper
        robotController = Goalkeeper(robot)
        print(f"✅ SUCCESS: [Goalkeeper Behavior Tree] assigned to {robotName}")
        
    elif robotName == "RED_DEF_L":
        from RedDefenderLeft import DefenderLeft
        robotController = DefenderLeft(robot)
        print(f"✅ SUCCESS: [Defender (Left) Behavior Tree] assigned to {robotName}")
        
    elif robotName == "RED_DEF_R":
        from RedDefenderRight import DefenderRight
        robotController = DefenderRight(robot)
        print(f"✅ SUCCESS: [Defender (Right) Behavior Tree] assigned to {robotName}")
        
    else:
        # 默认作为前锋/Striker处理
        from RedForward import Forward
        robotController = Forward(robot)
        print(f"✅ SUCCESS: [Striker Behavior Tree] assigned to {robotName}")

except ImportError as e:
    print(f"❌ FATAL ERROR: Cannot load behavior tree for {robotName}!")
    print(f"🔍 Please check if the file exists and is named correctly. Detail: {e}")
    sys.exit(1) # 严重错误，直接退出该机器人的进程

print(f"==================================================")

# ==========================================
# 4. 执行决策树主循环
# ==========================================
if hasattr(robotController, 'run'):
    # 这里调用的就是我们在各个子文件里写的 run() 方法
    # 包含了开场缓冲、防摔倒、寻球、避障等所有逻辑
    robotController.run()
else:
    print(f"❌ ERROR: The selected controller for {robotName} is missing the run() method!")