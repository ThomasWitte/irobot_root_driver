#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from gi.repository import GLib

from std_msgs.msg import String
from geometry_msgs.msg import Twist
from irobot_root_driver.irobot_root import RootRobot

def clamp(value, _min, _max):
    if value < _min:
        return _min
    if value > _max:
        return _max
    return value

class RootDriver(Node):

    def __init__(self):
        super().__init__('irobot_root_driver')
        self.twist_subscription = self.create_subscription(Twist, 'cmd_vel', self.twist_callback, 10)
        self.publisher_ = self.create_publisher(String, 'topic', 10)
        timer_period = 0.5  # seconds
        self.timer = self.create_timer(timer_period, self.timer_callback)
        self.i = 0
        self.root_robot = RootRobot()

    def timer_callback(self):
        msg = String()
        msg.data = 'Hello World: %d' % self.i
        self.publisher_.publish(msg)
        self.get_logger().info('Publishing: "%s"' % msg.data)
        self.i += 1


    def twist_callback(self, msg):
        v = msg.linear.x
        rot = msg.angular.z
        width = 0.102 # wheel distance 
        
        left =  clamp((v - rot * width)*1000, -100, 100)
        right = clamp((v + rot * width)*1000, -100, 100)
        
        # set motor speed
        self.root_robot.send_message(RootRobot.Device.MOTORS, 4, list(int(left).to_bytes(4, byteorder = 'big', signed=True) + int(right).to_bytes(4, byteorder = 'big', signed=True)))

def main(args=None):
    rclpy.init(args=args)

    root_driver = RootDriver()

    loop = GLib.MainLoop()

    def spin_root():
        if rclpy.ok():
            rclpy.spin_once(root_driver)
            return True
        else:
            loop.quit()
            return False

    GLib.idle_add(spin_root)
    loop.run()

    rclpy.shutdown()


if __name__ == '__main__':
    main()
