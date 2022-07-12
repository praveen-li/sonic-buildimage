#!/usr/bin/env python

#############################################################################
# Cisco
#
# Module contains an implementation of SONiC Platform Base API and
# provides the Thermals status which are available in the platform
#
#############################################################################

import os.path
import fnmatch

try:
    from sonic_platform_base.thermal_base import ThermalBase
    from sonic_py_common.logger import Logger
    from sonic_platform.globals import PlatformGlobalData
    from sonic_platform.chassis import Chassis 
    from sonic_platform.utils import read_int_from_file, read_str_from_file, write_file
except ImportError as e:
    raise ImportError (str(e) + "- required module not found")

# Global logger class instance
logger = Logger()

class Thermal(ThermalBase):
    """Platform-specific Thermal class"""

    #Sensor location categories (to identify inlet/outlet sensors based on Fan direction)
    SENSOR_NEAR_FRONT_PANEL_PORTS = 'near front panel ports'
    SENSOR_NEAR_FANS = 'near Fans'
    SENSOR_NEAR_ASIC = 'near ASIC'      #includes CPU as well
    SENSOR_GENERIC = 'generic'          #sensor not near to any of the defined categories but present in the system

    sensor_location_list = [SENSOR_NEAR_FRONT_PANEL_PORTS, SENSOR_NEAR_FANS, SENSOR_NEAR_ASIC, SENSOR_GENERIC]

    def __init__(self, thl_index,platform_data,temp_data):
        super(Thermal, self).__init__()

        #Thermal index is 1-based
        self.index = thl_index + 1
        self.temp_path = "/sys/bus/i2c/devices/{}-{}/hwmon/"
        self._temp_path = self.temp_path.format(temp_data['bus'],temp_data['addr'])
        self._temp_max_path = "temp{}_max"
        self._temp_input_path = "temp{}_input"
        self.platform_data = platform_data
        
        self.min_recorded = 200.0
        self.max_recorded = -64.0

        if 'minor' in temp_data:
            self.high_threshold = float(temp_data['minor'])
        else:
            self.high_threshold = None

        if 'major' in temp_data:
            self.critical_high_threshold = float(temp_data['major'])
        else:
            self.critical_high_threshold = None

        if (self.platform_data.get_param(PlatformGlobalData.KEY_TEMP_SENSORS_PATH_FORMAT,1) == 2):
            self._temp_input_path = self._temp_input_path.format(1) 
            self._temp_max_path = self._temp_max_path.format(1) 
        else :
            self._temp_input_path = self._temp_input_path.format(self.index) 
            self._temp_max_path = self._temp_max_path.format(self.index)           

        self._temp_name = temp_data['name']
        self._temp_label_path = None
        
        if temp_data['location'] in Thermal.sensor_location_list:
            self.location = temp_data['location']
        else:
            self.location = self.SENSOR_GENERIC

    def get_name(self):
        return self._temp_name

    def get_location(self):
        return self.location

    def get_presence(self):
        #Currently TORs are supported and so return True always
        return True

    def get_model(self):
        if not os.path.exists(self._temp_path):
            return 'N/A' 
        for dirname in os.listdir(self._temp_path):
            if fnmatch.fnmatch(dirname, 'hwmon?'):
                filename = self._temp_path + dirname + '/' + 'name'
                break
        if filename is None:
            return 'N/A'
        temp_val = read_str_from_file(filename)
        return temp_val

    def get_serial(self):
        return 'N/A'

    def get_status(self):
        if not os.path.exists(self._temp_path):
            return False
        for dirname in os.listdir(self._temp_path):
            if fnmatch.fnmatch(dirname, 'hwmon?'):
                filename = self._temp_path + dirname + '/' + self._temp_input_path
                break
        if filename is None:
            return False
        temp_val = read_int_from_file(filename)

        if temp_val and temp_val != -64000:
            return True

        return False

    def get_position_in_parent(self):
        return -1

    def is_replaceable(self):
        return False

    def set_high_threshold(self, temperature):
        #can only be set after stopping pmon and changing device_data.py entries
        return False

    def set_low_threshold(self, temperature):
        #can only be set after stopping pmon and changing device_data.py entries
        return False

    def get_temperature(self):
        if not os.path.exists(self._temp_path):
            return -64.0
        
        for dirname in os.listdir(self._temp_path):
            if fnmatch.fnmatch(dirname, 'hwmon?'):
                filename = self._temp_path + dirname + '/' + self._temp_input_path
                break
        if filename is None:
            return -64.0

        temp_val = read_int_from_file(filename)
        temp = float(temp_val) / 1000

        self.min_recorded = min(temp, self.min_recorded)
        self.max_recorded = max(temp, self.max_recorded)

        return temp

    def get_minimum_recorded(self):
        return self.min_recorded

    def get_maximum_recorded(self):
        return self.max_recorded

    def get_temp_max(self):
        if not os.path.exists(self._temp_path):
            return -64.0 
        for dirname in os.listdir(self._temp_path):
            if fnmatch.fnmatch(dirname, 'hwmon?'):
                filename = self._temp_path + dirname + '/' + self._temp_max_path
                break
        if filename is None:
            return -64.0
        max_val = read_int_from_file(filename)
        #60% of max
        return float(max_val)/1000

    def get_high_threshold(self):
        if self.high_threshold is not None:
            return self.high_threshold

        max_val = self.get_temp_max()
        if max_val:
            #60% of max
            return float(max_val*60)/100

    def get_low_threshold(self):
        return Chassis.DEFAULT_LOW_TEMP_THRESHOLD

    def get_high_critical_threshold(self):
        if self.critical_high_threshold is not None:
            return self.critical_high_threshold

        max_val = self.get_temp_max()
        if max_val:
           #90% of max
           return float(max_val*90)/100

    def get_low_critical_threshold(self):
        low_threshold = self.get_low_threshold()
        pfm_data = self.platform_data

        if pfm_data is None:
            return (low_threshold - Chassis.DEFAULT_TEMP_THRESHOLD_HYSTERESIS)
        else:
            hysteresis = pfm_data.get_param(PlatformGlobalData.KEY_THERMAL_CRIT_THRESHOLD_HYSTERESIS,
                    Chassis.DEFAULT_TEMP_THRESHOLD_HYSTERESIS)
            return (low_threshold - hysteresis)

    def get_hot_threshold(self):
        crit_high_threshold = self.get_high_critical_threshold()
        high_threshold = self.get_high_threshold()
        return ((crit_high_threshold + high_threshold) / 2)


    def get_temp_label(self):
        if self._temp_label_path == None:
            return None

        if not os.path.exists(self._temp_label_path):
            return None

        label = read_str_from_file(self._temp_label_path)
        return label

    def dump_sysfs(self):
        return False

############# test #################
# p1 = Thermal(4, "x86_64-cisco_N3K_C3432C")
# print("Name: {}".format(p1.get_name()))
# print("Temperature: {}".format(p1.get_temperature()))
# print("H_threshold: {}".format(p1.get_high_threshold()))
# print("C_H_threshold: {}".format(p1.get_high_critical_threshold()))
# print("Label: {}".format(p1.get_temp_label()))
# ##################################
