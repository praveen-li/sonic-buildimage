import os
from sonic_platform.utils import *

LED_PATH = "/sys/class/leds/"

class SystemLed():
    def __init__(self):
        self._green_led_path = os.path.join(LED_PATH, "status:green/brightness")
        self._red_led_path = os.path.join(LED_PATH, "status:red/brightness")

    def get_green_led_path(self):
        return self._green_led_path

    def get_red_led_path(self):
        return self._red_led_path

    def set_status(self, color):
        if color == "green":
            write_file(self.get_green_led_path(), '255')
            write_file(self.get_red_led_path(), '0')
        elif color == "red":
            write_file(self.get_green_led_path(), '0')
            write_file(self.get_red_led_path(), '255')
        elif color == 'amber':
            write_file(self.get_green_led_path(), '255')
            write_file(self.get_red_led_path(), '255')
        elif color == 'off':
            write_file(self.get_green_led_path(), '0')
            write_file(self.get_red_led_path(), '0')

        return True

    def get_status(self):
        green_color_val=read_int_from_file(self.get_green_led_path())
        red_color_val=read_int_from_file(self.get_red_led_path())

        if green_color_val and red_color_val == 0:
            return 'green'
        elif green_color_val == 0 and red_color_val:
            return 'red'
        elif green_color_val and red_color_val:
            return 'amber'
        elif green_color_val == 0 and red_color_val == 0:
            return 'off'
