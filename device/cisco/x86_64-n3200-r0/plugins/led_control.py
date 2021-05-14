#!/usr/bin/env python
#
# led_control.py
#
# Platform-specific LED control functionality for SONiC
#

try:
    from sonic_led.led_control_base import LedControlBase
except ImportError, e:
    raise ImportError (str(e) + " - required module not found")


class LedControl(LedControlBase):
    """Platform specific LED control class"""

    SONIC_PORT_NAME_PREFIX = "Ethernet"

    GREEN_LED_SYSFS_PATH = "/sys/class/leds/port{0}:green/brightness"
    YELLOW_LED_SYSFS_PATH = "/sys/class/leds/port{0}:yellow/brightness"

    QSFP_START_IDX = 1
    QSFP_END_IDX = 32

    LED_OFF = 0
    LED_ON = 255

    BREAKOUT_PORT_START = 0
    BREAKOUT_PORT_END = 127
    _breakout_port_status = {}

    SFP_START_IDX = 33
    SFP_END_IDX = 34

    NON_BREAKOUT_PORT_START = 128
    NON_BREAKOUT_PORT_END = 129

    # Helper method to map SONiC port name to port number
    def _port_name_to_port_number(self, port_name):
        # Strip "Ethernet" off port name
        if not port_name.startswith(self.SONIC_PORT_NAME_PREFIX):
            return -1

        sonic_port_num = int(port_name[len(self.SONIC_PORT_NAME_PREFIX):])
        if (sonic_port_num < self.BREAKOUT_PORT_START) or (sonic_port_num > self.NON_BREAKOUT_PORT_END):
            return -1

        return sonic_port_num

    # Helper method to map SONiC port name to QSFP index
    def _update_breakout_port_status(self, port_number, state):

        self._breakout_port_status[port_number] = state
        port_lane1 = (int(port_number/4))*4
        port_lane4 = port_lane1 + 3
        summary = "unknown"
        for p in range(port_lane1, port_lane4 + 1):
            if self._breakout_port_status[p] == "up":
                summary = "up"
        return summary

    # Helper method to map SONiC port number to QSFP index
    def _port_number_to_qsfp_index(self, port_number):

        # SONiC port nums are 0-based and increment by 4
        # QSFP indices are 1-based and increment by 1
        if (sonic_port_num < self.NON_BREAKOUT_PORT_START):
            return (int(port_number/4) + 1)
        else:
            return (port_number - self.NON_BREAKOUT_PORT_START + self.SFP_START_IDX)

    # Concrete implementation of port_link_state_change() method
    def port_link_state_change(self, port, state):
        port_number = self._port_name_to_port_number(port)

        # Ignore invalid QSFP indices
        if port_number <= 0:
            return

        qsfp_index = self._port_number_to_qsfp_index(port_number)
        if (qsfp_index < self.SFP_START_IDX):
            summary = self._update_breakout_port_status(port_number, state)
        else:
            summary = state

        green_led_sysfs_path = self.GREEN_LED_SYSFS_PATH.format(qsfp_index)
        yellow_led_sysfs_path = self.YELLOW_LED_SYSFS_PATH.format(qsfp_index)

        green_led_file = open(green_led_sysfs_path, "w")
        yellow_led_file = open(yellow_led_sysfs_path, "w")

        if summary == "up":
            green_led_file.write("%d" % self.LED_ON)
            yellow_led_file.write("%d" % self.LED_OFF)
        else:
            green_led_file.write("%d" % self.LED_OFF)
            yellow_led_file.write("%d" % self.LED_OFF)

        green_led_file.close()
        yellow_led_file.close()

    # Constructor
    def __init__(self):
        # Initialize: Turn all front panel QSFP LEDs off
        for qsfp_index in range(self.QSFP_START_IDX, self.SFP_END_IDX + 1):
            green_led_sysfs_path = self.GREEN_LED_SYSFS_PATH.format(qsfp_index)
            with open(green_led_sysfs_path, 'w') as green_led_file:
                green_led_file.write("%d" % self.LED_OFF)
            yellow_led_sysfs_path = self.YELLOW_LED_SYSFS_PATH.format(qsfp_index)
            with open(yellow_led_sysfs_path, 'w') as yellow_led_file:
                yellow_led_file.write("%d" % self.LED_OFF)
        for x in range(self.BREAKOUT_PORT_START, self.BREAKOUT_PORT_END + 1):
            self._breakout_port_status[x] = "unknown"

