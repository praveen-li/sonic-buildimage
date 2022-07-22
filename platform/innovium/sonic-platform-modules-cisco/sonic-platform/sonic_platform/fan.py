#!/usr/bin/env python

#############################################################################
# Cisco
#
# Module contains an implementation of SONiC Platform Base API and
# provides the FANs status which are available in the platform
#
#############################################################################

import os.path
import subprocess
import fnmatch
try:
    from sonic_platform_base.fan_base import FanBase
    from sonic_platform.globals import PlatformGlobalData
    from sonic_platform.utils import read_int_from_file, read_str_from_file, write_file
except ImportError as e:
    raise ImportError (str(e) + "- required module not found")

PWM_MAX = 255
pwm_arr = ['pwm1', 'pwm2', 'pwm1', 'pwm3']
fan_pwm = [2, 1]
platform_dict_fan = {'x86_64-cisco_N3K_C3432D': 0}


class Fan(FanBase):
    """Platform-specific Fan class"""

    def __init__(self, fan_index, fan_drawer_index , platform_data, fan_data,  psu_fan = False, psu = None):
        super(Fan, self).__init__()

        self.max_speed = 255
        self.min_speed = 0
        self._target_speed = None
        self.is_psu_fan = psu_fan
        self.psu = psu
        self.platform_data = platform_data
        self._fan_path = "/sys/bus/i2c/devices/{}-{}/hwmon/"
        self._status_path = "fan{}_alarm"
        self._speed_path = "fan{}_input"
        self._pwm_path = "pwm{}"
        self._led_path = "/sys/class/leds/{}"
        self._g_led_path = "/sys/class/leds/fan{}:green/brightness"
        self._r_led_path = "/sys/class/leds/fan{}:amber/brightness"
        self._gpio_path = "/sys/class/gpio/gpio{}/value"
        #Fan index is 1-based
        self.index = fan_index + 1
        self.position = fan_index + 1
        self.drawer_index = fan_drawer_index + 1
        self.fan_speed_tolerance = self.platform_data.get_param(PlatformGlobalData.KEY_FAN_SPEED_TOLERANCE, 10)
        self.fan_pwm_path_format = self.platform_data.get_param(PlatformGlobalData.KEY_FAN_PWM_PATH_FORMAT, 1)

        if self.is_psu_fan:
            self.fan_path = self._fan_path.format(psu['bus'], psu['addr'])
            self.status_path = self._status_path.format(1)
            self.speed_path  = self._speed_path.format(1)
            self._name = "PSU{}-FAN{}".format(self.index, 1)
            self.pwm_path = None
            self.pre_path = self._gpio_path.format(psu['gpio'])
            self.dir_path = None;
            self.g_led_path = None
            self.r_led_path = None
            self.is_fan_sw_controllable = psu['is_fan_sw_controllable']
            self.psu_bus = psu['bus']
            self.psu_addr = psu['addr']
            self.fan_cmd = "3b"
        else:
            self.fan_path = self._fan_path.format(fan_data['bus'], fan_data['addr'])
            self.status_path = self._status_path.format(fan_data['input_index'])
            self.speed_path  = self._speed_path.format(fan_data['input_index'])
            self.pwm_path = None
            self.pre_path = self._gpio_path.format(fan_data['gpio_presence'])
            self.dir_path = self._gpio_path.format(fan_data['gpio_direction'])
            self.g_led_path = self._g_led_path.format(self.drawer_index)
            self.r_led_path = self._r_led_path.format(self.drawer_index)
            self._name = "FAN {}-{}".format(self.drawer_index,self.index)
            self.pwm_path = self._pwm_path.format(fan_pwm[(self.drawer_index % 2)])

    def get_name(self):
        return self._name

    def get_presence(self):
        if not os.path.exists(self.pre_path):
            return False
        presence = read_int_from_file(self.pre_path)
        return True if (presence) else False

    def get_direction(self):
        if self.is_psu_fan:
            return FanBase.FAN_DIRECTION_NOT_APPLICABLE
        else:
            if not os.path.exists(self.dir_path):
                return False

            direction = read_int_from_file(self.dir_path)
            return FanBase.FAN_DIRECTION_EXHAUST if (direction) else FanBase.FAN_DIRECTION_INTAKE

    def get_status(self):
        status = 0
        if self.get_presence() :
            if self.is_psu_fan and self.psu is not None and self.psu['is_fan_sw_controllable'] == False:
                    return True
            for dirname in os.listdir(self.fan_path):
                if fnmatch.fnmatch(dirname, 'hwmon?'):
                    filename = self.fan_path + dirname + '/' + self.status_path
                    break
            if filename is None:
                return False
            status = read_int_from_file(filename)
            return False if (status) else True
        else :
            return False

    def get_speed_rpm(self):
        speed = 0
        if self.get_presence() :
            if self.is_psu_fan and self.psu is not None and self.psu['is_fan_sw_controllable'] == False:
                    return "N/A"
            for dirname in os.listdir(self.fan_path):
                if fnmatch.fnmatch(dirname, 'hwmon?'):
                    filename = self.fan_path + dirname + '/' + self.speed_path
                    break
            if filename is None:
                return False
            speed = read_int_from_file(filename)

        return speed

    #Platform specific code
    def rpm2pwm(self, rpm):
        pwm = 0                                                                                  
        if (self.index%2) == 1:
            f_fan_curve_slope = self.platform_data.get_param(PlatformGlobalData.KEY_FORWARD_FAN_CURVE_SLOPE,1)
            pwm = int(rpm / f_fan_curve_slope)
        else:
            r_fan_curve_slope = self.platform_data.get_param(PlatformGlobalData.KEY_REVERSE_FAN_CURVE_SLOPE,1)
            pwm = int(rpm / r_fan_curve_slope)

        #clamp to 100
        if (pwm > 100):
            pwm = 100

        return pwm

    def get_speed(self):
        speed = 0
        pwm = 0
        if self.get_presence() :
            if self.is_psu_fan:
                if self.psu is None:
                    return "N/A"
                if self.psu['is_fan_sw_controllable'] == False:
                    return "N/A"
                try:
                    cmd = '/usr/sbin/i2cget -y -f ' + str(self.psu_bus) + ' 0x' + str(self.psu_addr) + ' 0x' + self.fan_cmd + ' w'
                    ph = subprocess.Popen([cmd],
                                  stdout=subprocess.PIPE,
                                  shell=True, stderr=subprocess.STDOUT)
                    cmdout = ph.communicate()[0]
                    ph.wait()
                except OSError as e:
                    raise OSError("Unable to get PSU fan speed ")
                    return "N/A"

                speed = cmdout.decode("utf-8", errors="ignore")
                pwm = int(speed,16)
                if (pwm > 100):
                    pwm = 100
            else :
                #Get speed/rpm
                for dirname in os.listdir(self.fan_path):
                    if fnmatch.fnmatch(dirname, 'hwmon?'):
                        filename = self.fan_path + dirname + '/' + self.speed_path
                        break
                if filename is None:
                    return False
                speed = read_int_from_file(filename)
                pwm = self.rpm2pwm(speed)

        return pwm

    def get_target_speed(self):
        if self.get_presence() :
            if self._target_speed is not None:
                return self._target_speed

            if self.is_psu_fan:
                if self.psu is None:
                    return "N/A"
                if self.psu['is_fan_sw_controllable'] == False:
                    return "N/A"
                try:
                    cmd = '/usr/sbin/i2cget -y -f ' + str(self.psu_bus) + ' 0x' + str(self.psu_addr) + ' 0x' + self.fan_cmd + ' w'
                    ph = subprocess.Popen([cmd],
                                  stdout=subprocess.PIPE,
                                  shell=True, stderr=subprocess.STDOUT)
                    cmdout = ph.communicate()[0]
                    ph.wait()
                except OSError as e:
                    raise OSError("Unable to get PSU fan speed ")
                    return "N/A"

                speed = cmdout.decode("utf-8", errors="ignore")
                pwm = int(speed, 16)
                if (pwm > 100):
                    pwm = 100
                return pwm
            else:
                for dirname in os.listdir(self.fan_path):
                    if fnmatch.fnmatch(dirname, 'hwmon?'):
                        filename = self.fan_path + dirname + '/' + self.pwm_path
                        break
                if filename is None:
                    return None
                if not os.path.exists(filename):
                    return None
                pwm = read_int_from_file(filename)
                pwm = int(int(pwm) * 100 / PWM_MAX)
                return pwm
        else :
            return None


    def set_speed(self, speed):
        status = True
        if self.get_presence() :
            if self.is_psu_fan:
                if self.psu is None:
                    return False
                if self.psu['is_fan_sw_controllable'] == False:
                    return False
                run_cmd = '/usr/sbin/i2cset -y -f ' + str(self.psu_bus) + ' 0x' + str(self.psu_addr) + ' 0x' + self.fan_cmd + ' ' + str(hex(speed)) + ' w'
                os.system(run_cmd)
                self._target_speed = int(speed)
                return status
            else:
                for dirname in os.listdir(self.fan_path):
                    if fnmatch.fnmatch(dirname, 'hwmon?'):
                        filename = self.fan_path + dirname + '/' + self.pwm_path
                        break
                if filename is None:
                    return False
                if not os.path.exists(filename):
                    return False
                self._target_speed = int(speed)
                pwm = int(PWM_MAX * int(speed) / 100)
                status = write_file(filename, pwm)
                return status
        else :
            return False

    def get_speed_tolerance(self):
        """
        Retrieves the speed tolerance of the fan

        Returns:
            An integer, the percentage of variance from target speed which is
                 considered tolerable
        """
        if self.is_psu_fan and self.psu is not None and self.psu['is_fan_sw_controllable'] == False:
            return None
        return self.fan_speed_tolerance

    def get_position_in_parent(self):
        """
        Retrieves 1-based relative physical position in parent device
        Returns:
            integer: The 1-based relative physical position in parent device
        """
        return self.position

    def is_replaceable(self):
        """
        Indicate whether this device is replaceable.
        Returns:
            bool: True if it is replaceable.
        """
        return True

    def set_status_led(self,color):
        if self.is_psu_fan:
            return True #silently fail

        if not self.get_presence():
            return True

        if color == "red":
           if  os.path.exists(self.r_led_path):
               write_file(self.r_led_path,255)
           if  os.path.exists(self.g_led_path):
               write_file(self.g_led_path,0)
        elif color == "green":
           if  os.path.exists(self.r_led_path):
               write_file(self.r_led_path,0)
           if  os.path.exists(self.g_led_path):
               write_file(self.g_led_path,255)
        elif color == "amber":
           if  os.path.exists(self.r_led_path):
               write_file(self.r_led_path,255)
           if  os.path.exists(self.g_led_path):
               write_file(self.g_led_path,255)
        elif color == "off":
           if  os.path.exists(self.r_led_path):
               write_file(self.r_led_path,0)
           if  os.path.exists(self.g_led_path):
               write_file(self.g_led_path,0)
        else:
            return False

        return True

    def get_status_led(self):
        if self.is_psu_fan:
            if self.get_presence():
                return 'green'
            else:
                return 'off'

        if not self.get_presence():
            return 'off'

        red_color_val = 0
        green_color_val = 0
        if os.path.exists(self.g_led_path):
            green_color_val=read_int_from_file(self.g_led_path)
        if os.path.exists(self.r_led_path):
            red_color_val=read_int_from_file(self.r_led_path)

        if green_color_val and red_color_val == 0:
            return 'green'
        elif green_color_val == 0 and red_color_val:
            return 'red'
        elif green_color_val and red_color_val:
            return 'amber'
        elif green_color_val == 0 and red_color_val == 0:
            return 'off'

    def get_model(self):
        #TOR switches doesn't have IDPROM data for Fans
        #further FAN inside PSU doesn't have IDPROM data for its own as well
        return 'N/A'

    def get_serial(self):
        #TOR switches doesn't have IDPROM data for Fans
        #further FAN inside PSU doesn't have IDPROM data for its own as well
        return 'N/A'



########### Test #################
# 
# p1 = Fan(2, "x86_64-cisco_N3K_C3432D")
# print("Name: {}".format(p1.get_name()))
# print("Presence: {}".format(p1.get_presence()))
# print("Direction: {}".format(p1.get_direction()))
# print("Status: {}".format(p1.get_status()))
# print("Speed: {}".format(p1.get_speed()))
# print("Led: {}".format(p1.get_status_led()))
# print("Tolerance: {}".format(p1.get_speed_tolerance()))
# print("Position: {}".format(p1.get_position_in_parent()))
# print("Replaceable: {}".format(p1.is_replaceable()))
###############################
