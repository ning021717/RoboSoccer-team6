from controller import Robot
from BlueGoalkeeper import Goalkeeper
from BlueDefender import Defender
from BlueForwardLeft import ForwardLeft
from BlueForwardRight import ForwardRight

robot = Robot()
robotName = robot.getName()

if robotName == "BLUE_GK":
    robotController = Goalkeeper(robot)
elif robotName == "BLUE_DEF":
    robotController = Defender(robot)
elif robotName == "BLUE_FW_L":
    robotController = ForwardLeft(robot)
else:
    robotController = ForwardRight(robot)

robotController.run()
