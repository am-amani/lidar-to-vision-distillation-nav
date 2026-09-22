# import math
# import os
# import random
# import subprocess
# import time
# from os import path

# import numpy as np
# import rospy
# import sensor_msgs.point_cloud2 as pc2
# from gazebo_msgs.msg import ModelState
# from geometry_msgs.msg import Twist
# from nav_msgs.msg import Odometry
# from sensor_msgs.msg import PointCloud2, LaserScan, Image
# from squaternion import Quaternion
# from std_srvs.srv import Empty
# from visualization_msgs.msg import Marker
# from visualization_msgs.msg import MarkerArray

# from cv_bridge import CvBridge
# from cv_bridge import CvBridgeError
# import cv2



# GOAL_REACHED_DIST = 0.3
# COLLISION_DIST = 0.35
# TIME_DELTA = 0.4


# # Check if the random goal position is located on an obstacle and do not accept it if it is
# def check_pos(x, y):
#     goal_ok = True

#     if -3.8 > x > -6.2 and 6.2 > y > 3.8:
#         goal_ok = False

#     if -1.3 > x > -2.7 and 4.7 > y > -0.2:
#         goal_ok = False

#     if -0.3 > x > -4.2 and 2.7 > y > 1.3:
#         goal_ok = False

#     if -0.8 > x > -4.2 and -2.3 > y > -4.2:
#         goal_ok = False

#     if -1.3 > x > -3.7 and -0.8 > y > -2.7:
#         goal_ok = False

#     if 4.2 > x > 0.8 and -1.8 > y > -3.2:
#         goal_ok = False

#     if 4 > x > 2.5 and 0.7 > y > -3.2:
#         goal_ok = False

#     if 6.2 > x > 3.8 and -3.3 > y > -4.2:
#         goal_ok = False

#     if 4.2 > x > 1.3 and 3.7 > y > 1.5:
#         goal_ok = False

#     if -3.0 > x > -7.2 and 0.5 > y > -1.5:
#         goal_ok = False

#     if x > 4.5 or x < -4.5 or y > 4.5 or y < -4.5:
#         goal_ok = False

#     return goal_ok


# class GazeboEnv:
#     """Superclass for all Gazebo environments."""

#     def __init__(self, launchfile, environment_dim):
#         self.environment_dim = environment_dim
#         self.odom_x = 0
#         self.odom_y = 0

#         self.goal_x = 1
#         self.goal_y = 0.0

#         self.upper = 5.0
#         self.lower = -5.0
#         self.velodyne_data = np.ones(self.environment_dim) * 10
#         self.last_odom = None

#         self.set_self_state = ModelState()
#         self.set_self_state.model_name = "r1"
#         self.set_self_state.pose.position.x = 0.0
#         self.set_self_state.pose.position.y = 0.0
#         self.set_self_state.pose.position.z = 0.0
#         self.set_self_state.pose.orientation.x = 0.0
#         self.set_self_state.pose.orientation.y = 0.0
#         self.set_self_state.pose.orientation.z = 0.0
#         self.set_self_state.pose.orientation.w = 1.0

#         self.scan_data = [] #adeed by me
#         self.camera_data = [] #added by me
#         self.bridge = CvBridge() #added by me


#         self.gaps = [[-np.pi / 2 - 0.03, -np.pi / 2 + np.pi / self.environment_dim]]
#         for m in range(self.environment_dim - 1):
#             self.gaps.append(
#                 [self.gaps[m][1], self.gaps[m][1] + np.pi / self.environment_dim]
#             )
#         self.gaps[-1][-1] += 0.03

#         port = "11311"
#         subprocess.Popen(["roscore", "-p", port])

#         print("Roscore launched!")

#         # Launch the simulation with the given launchfile name
#         rospy.init_node("gym", anonymous=True)
#         if launchfile.startswith("/"):
#             fullpath = launchfile
#         else:
#             fullpath = os.path.join(os.path.dirname(__file__), "assets", launchfile)
#         if not path.exists(fullpath):
#             raise IOError("File " + fullpath + " does not exist")

#         subprocess.Popen(["roslaunch", "-p", port, fullpath])
#         print("Gazebo launched!")

#         # Set up the ROS publishers and subscribers
#         self.vel_pub = rospy.Publisher("/r1/cmd_vel", Twist, queue_size=1)
#         self.set_state = rospy.Publisher(
#             "gazebo/set_model_state", ModelState, queue_size=10
#         )
#         self.unpause = rospy.ServiceProxy("/gazebo/unpause_physics", Empty)
#         self.pause = rospy.ServiceProxy("/gazebo/pause_physics", Empty)
#         self.reset_proxy = rospy.ServiceProxy("/gazebo/reset_world", Empty)
#         self.publisher = rospy.Publisher("goal_point", MarkerArray, queue_size=3)
#         self.publisher2 = rospy.Publisher("linear_velocity", MarkerArray, queue_size=1)
#         self.publisher3 = rospy.Publisher("angular_velocity", MarkerArray, queue_size=1)
#         self.velodyne = rospy.Subscriber(
#             "/velodyne_points", PointCloud2, self.velodyne_callback, queue_size=1)
#         self.odom = rospy.Subscriber(
#             "/r1/odom", Odometry, self.odom_callback, queue_size=1)
#         self.scan_subscriber = rospy.Subscriber("/r1/front_laser/scan", LaserScan, self.scan_callback, queue_size=1)    #added by me
#         self.camera_subscriber = rospy.Subscriber("/r1/front_camera/image_raw", Image, self.camera_callback, queue_size=1) #added by me


#     def camera_callback(self, data):
#         try:
#             cv_image = self.bridge.imgmsg_to_cv2(data, "bgr8")
#             if np.any(cv_image):  # Check if any pixel is non-zero
#                 #print("Image size before resizing:", cv_image.shape)
#                 resized_image = cv2.resize(cv_image, (128, 64))
#                 grayscale_image = cv2.cvtColor(resized_image, cv2.COLOR_BGR2GRAY)
#                 grayscale_image = np.expand_dims(grayscale_image, axis=-1)
#                 grayscale_image = grayscale_image.astype(np.uint8)
#                 self.camera_data = grayscale_image
#                 #print("Image size after resizing:", self.camera_data.shape)
#             else:
#                 print("Received blank image, not updating camera data.")
#         except CvBridgeError as e:
#             print(e)

#     def scan_callback(self, data):  #added by me
#         self.scan_data = np.array(data.ranges)
#         #size of scan_data
#         #print("scan_data.size():", self.scan_data.size)
#         self.scan_data [np.isinf(self.scan_data)] = 10
#         self.scan_data [np.isnan(self.scan_data)] = 0 #added by meD*A&SD*()))") #added by me

#     def get_scan_data(self):
#         # scan data received
#         # print("scan data received")
#         return self.scan_data

#     def get_camera_data(self):
#         # camera data received
#         # print("camera data received")
#         return self.camera_data

#     # Read velodyne pointcloud and turn it into distance data, then select the minimum value for each angle
#     # range as state representation
#     def velodyne_callback(self, v):
#         data = list(pc2.read_points(v, skip_nans=False, field_names=("x", "y", "z")))
#         self.velodyne_data = np.ones(self.environment_dim) * 10
#         for i in range(len(data)):
#             if data[i][2] > -0.2:
#                 dot = data[i][0] * 1 + data[i][1] * 0
#                 mag1 = math.sqrt(math.pow(data[i][0], 2) + math.pow(data[i][1], 2))
#                 mag2 = math.sqrt(math.pow(1, 2) + math.pow(0, 2))
#                 beta = math.acos(dot / (mag1 * mag2)) * np.sign(data[i][1])
#                 dist = math.sqrt(data[i][0] ** 2 + data[i][1] ** 2 + data[i][2] ** 2)

#                 for j in range(len(self.gaps)):
#                     if self.gaps[j][0] <= beta < self.gaps[j][1]:
#                         self.velodyne_data[j] = min(self.velodyne_data[j], dist)
#                         break

#     def odom_callback(self, od_data):
#         self.last_odom = od_data

#     # Perform an action and read a new state
#     def step(self, action):
#         target = False

#         # Publish the robot action
#         vel_cmd = Twist()
#         vel_cmd.linear.x = action[0]
#         vel_cmd.angular.z = action[1]
#         self.vel_pub.publish(vel_cmd)
#         self.publish_markers(action) #commented  by me

#         rospy.wait_for_service("/gazebo/unpause_physics")
#         try:
#             self.unpause()
#         except (rospy.ServiceException) as e:
#             print("/gazebo/unpause_physics service call failed")

#         # propagate state for TIME_DELTA seconds
#         time.sleep(TIME_DELTA)

#         rospy.wait_for_service("/gazebo/pause_physics")
#         try:
#             pass
#             self.pause()
#         except (rospy.ServiceException) as e:
#             print("/gazebo/pause_physics service call failed")

#         # read velodyne laser state
#         done, collision, min_laser = self.observe_collision(self.velodyne_data)
#         v_state = []
#         v_state[:] = self.velodyne_data[:]
#         laser_state = [v_state]

#         # Calculate robot heading from odometry data
#         self.odom_x = self.last_odom.pose.pose.position.x
#         self.odom_y = self.last_odom.pose.pose.position.y
#         quaternion = Quaternion(
#             self.last_odom.pose.pose.orientation.w,
#             self.last_odom.pose.pose.orientation.x,
#             self.last_odom.pose.pose.orientation.y,
#             self.last_odom.pose.pose.orientation.z,
#         )
#         euler = quaternion.to_euler(degrees=False)
#         angle = round(euler[2], 4)

#         # Calculate distance to the goal from the robot
#         distance = np.linalg.norm(
#             [self.odom_x - self.goal_x, self.odom_y - self.goal_y]
#         )

#         # Calculate the relative angle between the robots heading and heading toward the goal
#         skew_x = self.goal_x - self.odom_x
#         skew_y = self.goal_y - self.odom_y
#         dot = skew_x * 1 + skew_y * 0
#         mag1 = math.sqrt(math.pow(skew_x, 2) + math.pow(skew_y, 2))
#         mag2 = math.sqrt(math.pow(1, 2) + math.pow(0, 2))
#         beta = math.acos(dot / (mag1 * mag2))
#         if skew_y < 0:
#             if skew_x < 0:
#                 beta = -beta
#             else:
#                 beta = 0 - beta
#         theta = beta - angle
#         if theta > np.pi:
#             theta = np.pi - theta
#             theta = -np.pi - theta
#         if theta < -np.pi:
#             theta = -np.pi - theta
#             theta = np.pi - theta

#         # Detect if the goal has been reached and give a large positive reward
#         if distance < GOAL_REACHED_DIST:
#             target = True
#             done = True

#         robot_state = [distance, theta, action[0], action[1]]
#         state = np.append(laser_state, robot_state)
#         reward = self.get_reward(target, collision, action, min_laser)
#         return state, reward, done, target#self.camera_data, self.scan_data added by me

#     def reset(self):

#         # Resets the state of the environment and returns an initial observation.
#         rospy.wait_for_service("/gazebo/reset_world")
#         try:
#             self.reset_proxy()

#         except rospy.ServiceException as e:
#             print("/gazebo/reset_simulation service call failed")

#         angle = np.random.uniform(-np.pi, np.pi)
#         quaternion = Quaternion.from_euler(0.0, 0.0, angle)
#         object_state = self.set_self_state

#         x = 0
#         y = 0
#         position_ok = False
#         while not position_ok:
#             x = np.random.uniform(-4.5, 4.5)
#             y = np.random.uniform(-4.5, 4.5)
#             position_ok = check_pos(x, y)
#         object_state.pose.position.x = x
#         object_state.pose.position.y = y
#         # object_state.pose.position.z = 0.
#         object_state.pose.orientation.x = quaternion.x
#         object_state.pose.orientation.y = quaternion.y
#         object_state.pose.orientation.z = quaternion.z
#         object_state.pose.orientation.w = quaternion.w
#         self.set_state.publish(object_state)

#         self.odom_x = object_state.pose.position.x
#         self.odom_y = object_state.pose.position.y

#         # set a random goal in empty space in environment
#         self.change_goal()
#         # randomly scatter boxes in the environment
#         self.random_box()
#         self.publish_markers([0.0, 0.0])

#         rospy.wait_for_service("/gazebo/unpause_physics")
#         try:
#             self.unpause()
#         except (rospy.ServiceException) as e:
#             print("/gazebo/unpause_physics service call failed")

#         time.sleep(TIME_DELTA)

#         rospy.wait_for_service("/gazebo/pause_physics")
#         try:
#             self.pause()
#         except (rospy.ServiceException) as e:
#             print("/gazebo/pause_physics service call failed")
#         v_state = []
#         v_state[:] = self.velodyne_data[:]
#         laser_state = [v_state]

#         distance = np.linalg.norm(
#             [self.odom_x - self.goal_x, self.odom_y - self.goal_y]
#         )

#         skew_x = self.goal_x - self.odom_x
#         skew_y = self.goal_y - self.odom_y

#         dot = skew_x * 1 + skew_y * 0
#         mag1 = math.sqrt(math.pow(skew_x, 2) + math.pow(skew_y, 2))
#         mag2 = math.sqrt(math.pow(1, 2) + math.pow(0, 2))
#         beta = math.acos(dot / (mag1 * mag2))

#         if skew_y < 0:
#             if skew_x < 0:
#                 beta = -beta
#             else:
#                 beta = 0 - beta
#         theta = beta - angle

#         if theta > np.pi:
#             theta = np.pi - theta
#             theta = -np.pi - theta
#         if theta < -np.pi:
#             theta = -np.pi - theta
#             theta = np.pi - theta

#         robot_state = [distance, theta, 0.0, 0.0]
#         state = np.append(laser_state, robot_state)
#         return state

#     def change_goal(self):
#         # Place a new goal and check if its location is not on one of the obstacles
#         if self.upper < 10:
#             self.upper += 0.004
#         if self.lower > -10:
#             self.lower -= 0.004

#         goal_ok = False

#         while not goal_ok:
#             self.goal_x = self.odom_x + random.uniform(self.upper, self.lower)
#             self.goal_y = self.odom_y + random.uniform(self.upper, self.lower)
#             goal_ok = check_pos(self.goal_x, self.goal_y)

#     def random_box(self):
#         # Randomly change the location of the boxes in the environment on each reset to randomize the training
#         # environment
#         for i in range(4):
#             name = "cardboard_box_" + str(i)

#             x = 0
#             y = 0
#             box_ok = False
#             while not box_ok:
#                 x = np.random.uniform(-6, 6)
#                 y = np.random.uniform(-6, 6)
#                 box_ok = check_pos(x, y)
#                 distance_to_robot = np.linalg.norm([x - self.odom_x, y - self.odom_y])
#                 distance_to_goal = np.linalg.norm([x - self.goal_x, y - self.goal_y])
#                 if distance_to_robot < 1.5 or distance_to_goal < 1.5:
#                     box_ok = False
#             box_state = ModelState()
#             box_state.model_name = name
#             box_state.pose.position.x = x
#             box_state.pose.position.y = y
#             box_state.pose.position.z = 0.0
#             box_state.pose.orientation.x = 0.0
#             box_state.pose.orientation.y = 0.0
#             box_state.pose.orientation.z = 0.0
#             box_state.pose.orientation.w = 1.0
#             self.set_state.publish(box_state)

#     def publish_markers(self, action):
#         # Publish visual data in Rviz
#         markerArray = MarkerArray()
#         marker = Marker()
#         marker.header.frame_id = "odom"
#         marker.type = marker.CYLINDER
#         marker.action = marker.ADD
#         marker.scale.x = 0.1
#         marker.scale.y = 0.1
#         marker.scale.z = 0.01
#         marker.color.a = 1.0
#         marker.color.r = 0.0
#         marker.color.g = 1.0
#         marker.color.b = 0.0
#         marker.pose.orientation.w = 1.0
#         marker.pose.position.x = self.goal_x
#         marker.pose.position.y = self.goal_y
#         marker.pose.position.z = 0

#         markerArray.markers.append(marker)

#         self.publisher.publish(markerArray)

#         markerArray2 = MarkerArray()
#         marker2 = Marker()
#         marker2.header.frame_id = "odom"
#         marker2.type = marker.CUBE
#         marker2.action = marker.ADD
#         marker2.scale.x = abs(action[0])
#         marker2.scale.y = 0.1
#         marker2.scale.z = 0.01
#         marker2.color.a = 1.0
#         marker2.color.r = 1.0
#         marker2.color.g = 0.0
#         marker2.color.b = 0.0
#         marker2.pose.orientation.w = 1.0
#         marker2.pose.position.x = 5
#         marker2.pose.position.y = 0
#         marker2.pose.position.z = 0

#         markerArray2.markers.append(marker2)
#         self.publisher2.publish(markerArray2)

#         markerArray3 = MarkerArray()
#         marker3 = Marker()
#         marker3.header.frame_id = "odom"
#         marker3.type = marker.CUBE
#         marker3.action = marker.ADD
#         marker3.scale.x = abs(action[1])
#         marker3.scale.y = 0.1
#         marker3.scale.z = 0.01
#         marker3.color.a = 1.0
#         marker3.color.r = 1.0
#         marker3.color.g = 0.0
#         marker3.color.b = 0.0
#         marker3.pose.orientation.w = 1.0
#         marker3.pose.position.x = 5
#         marker3.pose.position.y = 0.2
#         marker3.pose.position.z = 0

#         markerArray3.markers.append(marker3)
#         self.publisher3.publish(markerArray3)

#     @staticmethod
#     def observe_collision(laser_data):
#         # Detect a collision from laser data
#         min_laser = min(laser_data)
#         if min_laser < COLLISION_DIST:
#             return True, True, min_laser
#         return False, False, min_laser

#     @staticmethod
#     def get_reward(target, collision, action, min_laser):
#         if target:
#             return 100.0
#         elif collision:
#             return -100.0
#         else:
#             r3 = lambda x: 1 - x if x < 1 else 0.0
#             return action[0] / 2 - abs(action[1]) / 2 - r3(min_laser) / 2



import math
import os
import random
import subprocess
import time
from os import path

import numpy as np
import rospy
import sensor_msgs.point_cloud2 as pc2
from gazebo_msgs.msg import ModelState
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from sensor_msgs.msg import PointCloud2, LaserScan, Image
from squaternion import Quaternion
from std_srvs.srv import Empty
from visualization_msgs.msg import Marker
from visualization_msgs.msg import MarkerArray

from cv_bridge import CvBridge
from cv_bridge import CvBridgeError
import cv2



GOAL_REACHED_DIST = 0.3
COLLISION_DIST = 0.225
TIME_DELTA = 0.3


# Check if the random goal position is located on an obstacle and do not accept it if it is
def check_pos(x, y):
    goal_ok = True

    if -3.8 > x > -6.2 and 6.2 > y > 3.8:
        goal_ok = False

    if -1.3 > x > -2.7 and 4.7 > y > -0.2:
        goal_ok = False

    if -0.3 > x > -4.2 and 2.7 > y > 1.3:
        goal_ok = False

    if -0.8 > x > -4.2 and -2.3 > y > -4.2:
        goal_ok = False

    if -1.3 > x > -3.7 and -0.8 > y > -2.7:
        goal_ok = False

    if 4.2 > x > 0.8 and -1.8 > y > -3.2:
        goal_ok = False

    if 4 > x > 2.5 and 0.7 > y > -3.2:
        goal_ok = False

    if 6.2 > x > 3.8 and -3.3 > y > -4.2:
        goal_ok = False

    if 4.2 > x > 1.3 and 3.7 > y > 1.5:
        goal_ok = False

    if -3.0 > x > -7.2 and 0.5 > y > -1.5:
        goal_ok = False

    if x > 4.5 or x < -4.5 or y > 4.5 or y < -4.5:
        goal_ok = False

    return goal_ok


class GazeboEnv:
    """Superclass for all Gazebo environments."""

    def __init__(self, launchfile, environment_dim):
        self.environment_dim = environment_dim
        self.odom_x = 0
        self.odom_y = 0

        self.goal_x = 1
        self.goal_y = 0.0

        self.upper = 5.0
        self.lower = -5.0
        #self.velodyne_data = np.ones(self.environment_dim) * 10
        self.laser_data = np.ones(self.environment_dim) * 10

        self.last_odom = None

        self.set_self_state = ModelState()
        self.set_self_state.model_name = "r1"
        self.set_self_state.pose.position.x = 0.0
        self.set_self_state.pose.position.y = 0.0
        self.set_self_state.pose.position.z = 0.0
        self.set_self_state.pose.orientation.x = 0.0
        self.set_self_state.pose.orientation.y = 0.0
        self.set_self_state.pose.orientation.z = 0.0
        self.set_self_state.pose.orientation.w = 1.0

        self.scan_data = [] #adeed by me
        self.camera_data = [] #added by me
        self.bridge = CvBridge() #added by me


        self.gaps = [[-np.pi / 2 - 0.03, -np.pi / 2 + np.pi / self.environment_dim]]
        for m in range(self.environment_dim - 1):
            self.gaps.append(
                [self.gaps[m][1], self.gaps[m][1] + np.pi / self.environment_dim]
            )
        self.gaps[-1][-1] += 0.03

        port = "11311"
        subprocess.Popen(["roscore", "-p", port])

        print("Roscore launched!")

        # Launch the simulation with the given launchfile name
        rospy.init_node("gym", anonymous=True)
        if launchfile.startswith("/"):
            fullpath = launchfile
        else:
            fullpath = os.path.join(os.path.dirname(__file__), "assets", launchfile)
        if not path.exists(fullpath):
            raise IOError("File " + fullpath + " does not exist")

        subprocess.Popen(["roslaunch", "-p", port, fullpath])
        print("Gazebo launched!")

        # Set up the ROS publishers and subscribers
        self.vel_pub = rospy.Publisher("/r1/cmd_vel", Twist, queue_size=1)
        self.set_state = rospy.Publisher(
            "gazebo/set_model_state", ModelState, queue_size=10
        )
        self.unpause = rospy.ServiceProxy("/gazebo/unpause_physics", Empty)
        self.pause = rospy.ServiceProxy("/gazebo/pause_physics", Empty)
        self.reset_proxy = rospy.ServiceProxy("/gazebo/reset_world", Empty)
        self.publisher = rospy.Publisher("goal_point", MarkerArray, queue_size=3)
        self.publisher2 = rospy.Publisher("linear_velocity", MarkerArray, queue_size=1)
        self.publisher3 = rospy.Publisher("angular_velocity", MarkerArray, queue_size=1)
        #self.velodyne = rospy.Subscriber("/velodyne_points", PointCloud2, self.velodyne_callback, queue_size=1)
        self.odom = rospy.Subscriber(
            "/r1/odom", Odometry, self.odom_callback, queue_size=1)
        self.scan_subscriber = rospy.Subscriber("/r1/front_laser/scan", LaserScan, self.scan_callback, queue_size=1)    #added by me
        self.camera_subscriber = rospy.Subscriber("/r1/front_camera/image_raw", Image, self.camera_callback, queue_size=1) #added by me

        # Gazebo start-up time varies (slow machines, containers); block until the
        # robot publishes odometry instead of relying on the callers' fixed sleep.
        rospy.wait_for_message("/r1/odom", Odometry, timeout=300)


    def camera_callback(self, data):
        try:
            cv_image = self.bridge.imgmsg_to_cv2(data, "bgr8")
            if np.any(cv_image):  # Check if any pixel is non-zero
                #print("Image size before resizing:", cv_image.shape)
                resized_image = cv2.resize(cv_image, (128, 64))
                grayscale_image = cv2.cvtColor(resized_image, cv2.COLOR_BGR2GRAY)
                grayscale_image = np.expand_dims(grayscale_image, axis=-1)
                grayscale_image = grayscale_image.astype(np.uint8)
                self.camera_data = grayscale_image
                #print("Image size after resizing:", self.camera_data.shape)
            else:
                print("Received blank image, not updating camera data.")
        except CvBridgeError as e:
            print(e)

    def scan_callback(self, data):  #added by me
        self.scan_data = np.array(data.ranges)
        #size of scan_data
        #print("scan_data.size():", self.scan_data.size)
        self.scan_data [np.isinf(self.scan_data)] = 12
        self.scan_data [np.isnan(self.scan_data)] = 0.08 #added by meD*A&SD*()))") #added by me

        num_sectors = 20
        ranges = np.array(data.ranges)
        sector_width = len(ranges) // num_sectors
        self.laser_data = np.ones(num_sectors) * 10
        for i in range(num_sectors):
            start_idx = i * sector_width
            end_idx = start_idx + sector_width
            # Ensure we don't go out of bounds on the last sector
            if end_idx > len(ranges):
                end_idx = len(ranges)
            self.laser_data[i] = np.min(ranges[start_idx:end_idx])

    def get_scan_data(self):
        # scan data received
        # print("scan data received")
        # return self.laser_data
        return self.scan_data

    def get_camera_data(self):
        # camera data received
        # print("camera data received")
        return self.camera_data

    # Read velodyne pointcloud and turn it into distance data, then select the minimum value for each angle
    # range as state representation
    # def velodyne_callback(self, v):
    #     data = list(pc2.read_points(v, skip_nans=False, field_names=("x", "y", "z")))
    #     self.velodyne_data = np.ones(self.environment_dim) * 10
    #     for i in range(len(data)):
    #         if data[i][2] > -0.2:
    #             dot = data[i][0] * 1 + data[i][1] * 0
    #             mag1 = math.sqrt(math.pow(data[i][0], 2) + math.pow(data[i][1], 2))
    #             mag2 = math.sqrt(math.pow(1, 2) + math.pow(0, 2))
    #             beta = math.acos(dot / (mag1 * mag2)) * np.sign(data[i][1])
    #             dist = math.sqrt(data[i][0] ** 2 + data[i][1] ** 2 + data[i][2] ** 2)

    #             for j in range(len(self.gaps)):
    #                 if self.gaps[j][0] <= beta < self.gaps[j][1]:
    #                     self.velodyne_data[j] = min(self.velodyne_data[j], dist)
    #                     break

    def odom_callback(self, od_data):
        self.last_odom = od_data

    # Perform an action and read a new state
    def step(self, action):
        target = False

        # Publish the robot action
        vel_cmd = Twist()
        vel_cmd.linear.x = action[0]
        vel_cmd.angular.z = action[1]
        self.vel_pub.publish(vel_cmd)
        # self.publish_markers(action) #commented  by me

        rospy.wait_for_service("/gazebo/unpause_physics")
        try:
            self.unpause()
        except (rospy.ServiceException) as e:
            print("/gazebo/unpause_physics service call failed")

        # propagate state for TIME_DELTA seconds
        time.sleep(TIME_DELTA)

        rospy.wait_for_service("/gazebo/pause_physics")
        try:
            pass
            self.pause()
        except (rospy.ServiceException) as e:
            print("/gazebo/pause_physics service call failed")

        # read velodyne laser state
        done, collision, min_laser = self.observe_collision(self.laser_data)
        v_state = []
        v_state[:] = self.laser_data[:]
        laser_state = [v_state]

        # Calculate robot heading from odometry data
        self.odom_x = self.last_odom.pose.pose.position.x
        self.odom_y = self.last_odom.pose.pose.position.y
        quaternion = Quaternion(
            self.last_odom.pose.pose.orientation.w,
            self.last_odom.pose.pose.orientation.x,
            self.last_odom.pose.pose.orientation.y,
            self.last_odom.pose.pose.orientation.z,
        )
        euler = quaternion.to_euler(degrees=False)
        angle = round(euler[2], 4)

        # Calculate distance to the goal from the robot
        distance = np.linalg.norm(
            [self.odom_x - self.goal_x, self.odom_y - self.goal_y]
        )

        # Calculate the relative angle between the robots heading and heading toward the goal
        skew_x = self.goal_x - self.odom_x
        skew_y = self.goal_y - self.odom_y
        dot = skew_x * 1 + skew_y * 0
        mag1 = math.sqrt(math.pow(skew_x, 2) + math.pow(skew_y, 2))
        mag2 = math.sqrt(math.pow(1, 2) + math.pow(0, 2))
        beta = math.acos(dot / (mag1 * mag2))
        if skew_y < 0:
            if skew_x < 0:
                beta = -beta
            else:
                beta = 0 - beta
        theta = beta - angle
        if theta > np.pi:
            theta = np.pi - theta
            theta = -np.pi - theta
        if theta < -np.pi:
            theta = -np.pi - theta
            theta = np.pi - theta

        # Detect if the goal has been reached and give a large positive reward
        if distance < GOAL_REACHED_DIST:
            target = True
            done = True

        robot_state = [distance, theta, action[0], action[1]]
        state = np.append(laser_state, robot_state)
        reward = self.get_reward(target, collision, action, min_laser)
        return state, reward, done, target, self.camera_data, self.scan_data #added by me

    def reset(self):

        # Resets the state of the environment and returns an initial observation.
        rospy.wait_for_service("/gazebo/reset_world")
        try:
            self.reset_proxy()

        except rospy.ServiceException as e:
            print("/gazebo/reset_simulation service call failed")

        angle = np.random.uniform(-np.pi, np.pi)
        quaternion = Quaternion.from_euler(0.0, 0.0, angle)
        object_state = self.set_self_state

        x = 0
        y = 0
        position_ok = False
        while not position_ok:
            x = np.random.uniform(-4.5, 4.5)
            y = np.random.uniform(-4.5, 4.5)
            position_ok = check_pos(x, y)
        object_state.pose.position.x = x
        object_state.pose.position.y = y
        # object_state.pose.position.z = 0.
        object_state.pose.orientation.x = quaternion.x
        object_state.pose.orientation.y = quaternion.y
        object_state.pose.orientation.z = quaternion.z
        object_state.pose.orientation.w = quaternion.w
        self.set_state.publish(object_state)

        self.odom_x = object_state.pose.position.x
        self.odom_y = object_state.pose.position.y

        # set a random goal in empty space in environment
        self.change_goal()
        # randomly scatter boxes in the environment
        self.random_box()
        self.publish_markers([0.0, 0.0])

        rospy.wait_for_service("/gazebo/unpause_physics")
        try:
            self.unpause()
        except (rospy.ServiceException) as e:
            print("/gazebo/unpause_physics service call failed")

        time.sleep(TIME_DELTA)

        rospy.wait_for_service("/gazebo/pause_physics")
        try:
            self.pause()
        except (rospy.ServiceException) as e:
            print("/gazebo/pause_physics service call failed")
        v_state = []
        v_state[:] = self.laser_data[:]
        laser_state = [v_state]

        distance = np.linalg.norm(
            [self.odom_x - self.goal_x, self.odom_y - self.goal_y]
        )

        skew_x = self.goal_x - self.odom_x
        skew_y = self.goal_y - self.odom_y

        dot = skew_x * 1 + skew_y * 0
        mag1 = math.sqrt(math.pow(skew_x, 2) + math.pow(skew_y, 2))
        mag2 = math.sqrt(math.pow(1, 2) + math.pow(0, 2))
        beta = math.acos(dot / (mag1 * mag2))

        if skew_y < 0:
            if skew_x < 0:
                beta = -beta
            else:
                beta = 0 - beta
        theta = beta - angle

        if theta > np.pi:
            theta = np.pi - theta
            theta = -np.pi - theta
        if theta < -np.pi:
            theta = -np.pi - theta
            theta = np.pi - theta

        robot_state = [distance, theta, 0.0, 0.0]
        state = np.append(laser_state, robot_state)
        return state

    def change_goal(self):
        # Place a new goal and check if its location is not on one of the obstacles
        if self.upper < 10:
            self.upper += 0.004
        if self.lower > -10:
            self.lower -= 0.004

        goal_ok = False

        while not goal_ok:
            self.goal_x = self.odom_x + random.uniform(self.upper, self.lower)
            self.goal_y = self.odom_y + random.uniform(self.upper, self.lower)
            goal_ok = check_pos(self.goal_x, self.goal_y)

    def random_box(self):
        # Randomly change the location of the boxes in the environment on each reset to randomize the training
        # environment
        for i in range(4):
            name = "cardboard_box_" + str(i)

            x = 0
            y = 0
            box_ok = False
            while not box_ok:
                x = np.random.uniform(-6, 6)
                y = np.random.uniform(-6, 6)
                box_ok = check_pos(x, y)
                distance_to_robot = np.linalg.norm([x - self.odom_x, y - self.odom_y])
                distance_to_goal = np.linalg.norm([x - self.goal_x, y - self.goal_y])
                if distance_to_robot < 1.5 or distance_to_goal < 1.5:
                    box_ok = False
            box_state = ModelState()
            box_state.model_name = name
            box_state.pose.position.x = x
            box_state.pose.position.y = y
            box_state.pose.position.z = 0.0
            box_state.pose.orientation.x = 0.0
            box_state.pose.orientation.y = 0.0
            box_state.pose.orientation.z = 0.0
            box_state.pose.orientation.w = 1.0
            self.set_state.publish(box_state)

    def publish_markers(self, action):
        # Publish visual data in Rviz
        markerArray = MarkerArray()
        marker = Marker()
        marker.header.frame_id = "odom"
        marker.type = marker.CYLINDER
        marker.action = marker.ADD
        marker.scale.x = 0.1
        marker.scale.y = 0.1
        marker.scale.z = 0.01
        marker.color.a = 1.0
        marker.color.r = 0.0
        marker.color.g = 1.0
        marker.color.b = 0.0
        marker.pose.orientation.w = 1.0
        marker.pose.position.x = self.goal_x
        marker.pose.position.y = self.goal_y
        marker.pose.position.z = 0

        markerArray.markers.append(marker)

        self.publisher.publish(markerArray)

        markerArray2 = MarkerArray()
        marker2 = Marker()
        marker2.header.frame_id = "odom"
        marker2.type = marker.CUBE
        marker2.action = marker.ADD
        marker2.scale.x = abs(action[0])
        marker2.scale.y = 0.1
        marker2.scale.z = 0.01
        marker2.color.a = 1.0
        marker2.color.r = 1.0
        marker2.color.g = 0.0
        marker2.color.b = 0.0
        marker2.pose.orientation.w = 1.0
        marker2.pose.position.x = 5
        marker2.pose.position.y = 0
        marker2.pose.position.z = 0

        markerArray2.markers.append(marker2)
        self.publisher2.publish(markerArray2)

        markerArray3 = MarkerArray()
        marker3 = Marker()
        marker3.header.frame_id = "odom"
        marker3.type = marker.CUBE
        marker3.action = marker.ADD
        marker3.scale.x = abs(action[1])
        marker3.scale.y = 0.1
        marker3.scale.z = 0.01
        marker3.color.a = 1.0
        marker3.color.r = 1.0
        marker3.color.g = 0.0
        marker3.color.b = 0.0
        marker3.pose.orientation.w = 1.0
        marker3.pose.position.x = 5
        marker3.pose.position.y = 0.2
        marker3.pose.position.z = 0

        markerArray3.markers.append(marker3)
        self.publisher3.publish(markerArray3)

    @staticmethod
    def observe_collision(laser_data):
        # Detect a collision from laser data
        min_laser = min(laser_data)
        if min_laser < COLLISION_DIST:
            return True, True, min_laser
        return False, False, min_laser

    @staticmethod
    def get_reward(target, collision, action, min_laser):
        if target:
            return 100.0
        elif collision:
            return -100.0
        else:
            r3 = lambda x: 1 - x if x < 1 else 0.0
            return action[0] / 2 - abs(action[1]) / 2 - r3(min_laser) / 2
