import os
import fnmatch

class PlatformGlobalData():
    """Platform specific global parameters"""

    KEY_MIN_TEMP = 'min_temperature'
    KEY_MAX_TEMP = 'max_temperature'
    KEY_MIN_BLUE_FANS_SPEED = 'min_blue_fans_speed'
    KEY_MIN_RED_FANS_SPEED = 'min_red_fans_speed'
    KEY_MAX_BLUE_FANS_SPEED = 'max_blue_fans_speed'
    KEY_MAX_RED_FANS_SPEED = 'max_red_fans_speed'
    KEY_FRONT_PORT_START_INDEX = 'fp_start_index'
    KEY_MAX_FRONT_PORTS = 'max_fp_num'
    KEY_MAX_IOFPGA = 'IOFPGA'
    KEY_MAX_MIFPGA = 'MIFPGA'
    KEY_MAX_BIOS = 'BIOS'
    KEY_FAN_SPEED_TOLERANCE = 'fan_speed_tolerance'
    KEY_FAN_PWM_PATH_FORMAT = 'fan_pwm_path_format'
    KEY_TEMP_SENSORS_PATH_FORMAT = 'sensors_path_format'
    KEY_FORWARD_FAN_CURVE_SLOPE = 'F_fan_curve_slope'
    KEY_REVERSE_FAN_CURVE_SLOPE = 'R_fan_curve_slope'
    KEY_PSU_EEPROM_DATA_FORMAT = 'psu_eeprom_data_format'
    KEY_BLUE_FANS_INLET_TEMP_THRESHOLD = 'blue_fans_inlet_temp_threshold'
    KEY_RED_FANS_INLET_TEMP_THRESHOLD = 'red_fans_inlet_temp_threshold'
    KEY_THERMAL_HIGH_THRESHOLD_HYSTERESIS = 'thermal_high_thresh_hysteresis'
    KEY_THERMAL_CRIT_THRESHOLD_HYSTERESIS = 'thermal_crit_thresh_hysteresis'
    KEY_REBOOT_GPIO_NUM = 'reboot_gpio'
    KEY_SHUTDOWN_GPIO_NUM = 'shutdown_gpio'
    KEY_XCVR_HIGH_POWER_CLASS = 'transceiver_enable_high_power_class'
    KEY_MAX_SUPPLIED_POWER = 'max_supplied_power'


    DICT_GLOBAL_KEY_NOT_AVAILABLE = 'N/A'

    def __init__(self, global_data):
        self._data = global_data

    def set_param(self, param, value):
        if self._data is not None and param in self._data:
            self._data[param] = data

    def get_param(self, param, default=None):
        if self._data is not None and param in self._data:
            return self._data[param]
        return default 
