import os
import subprocess

from sonic_platform_base.sonic_thermal_control.thermal_action_base import ThermalPolicyActionBase
from sonic_platform_base.sonic_thermal_control.thermal_json_object import thermal_json_object
from sonic_platform_base.fan_base import FanBase
from sonic_platform.thermal_infos import *
from sonic_platform.globals import PlatformGlobalData


class SetFanSpeedAction(ThermalPolicyActionBase):
    """
    Base thermal action class to set speed for fans
    """
    # JSON field definition
    JSON_FIELD_SPEED = 'speed'

    def __init__(self):
        """
        Constructor of SetFanSpeedAction which actually do nothing.
        """
        self.speed = None

    def load_from_json(self, json_obj):
        """
        Construct SetFanSpeedAction via JSON. JSON example:
            {
                "type": "fan.all.set_speed"
                "speed": "100"
            }
        :param json_obj: A JSON object representing a SetFanSpeedAction action.
        :return:
        """
        if SetFanSpeedAction.JSON_FIELD_SPEED in json_obj:
            speed = float(json_obj[SetFanSpeedAction.JSON_FIELD_SPEED])
            if speed < 0 or speed > 100:
                raise ValueError('SetFanSpeedAction invalid speed value {} in JSON policy file, valid value should be [0, 100]'.
                        format(speed))
            self.speed = float(json_obj[SetFanSpeedAction.JSON_FIELD_SPEED])
        else:
            raise ValueError('SetFanSpeedAction missing mandatory field {} in JSON policy file'.
                    format(SetFanSpeedAction.JSON_FIELD_SPEED))


@thermal_json_object('fan.all.set_speed')
class SetAllFanSpeedAction(SetFanSpeedAction):
    """
    Action to set speed for all fans
    """
    def execute(self, thermal_info_dict):
        """
        Set speed for all fans
        :param thermal_info_dict: A dictionary stores all thermal information.
        :return:
        """
        from .thermal_infos import FanInfo
        if FanInfo.INFO_NAME in thermal_info_dict and isinstance(thermal_info_dict[FanInfo.INFO_NAME], FanInfo):
            fan_info_obj = thermal_info_dict[FanInfo.INFO_NAME]
            for fan in fan_info_obj.get_presence_fans():
                fan.set_speed(self.speed)

@thermal_json_object('switch.power_cycle')
class SwitchRebootAction(ThermalPolicyActionBase):
    def execute(self, thermal_info_dict):
        """
        Take action when thermal condition matches. For example, power cycle the switch.
        :param thermal_info_dict: A dictionary stores all thermal information.
        :return:
        """
        if ChassisInfo.INFO_NAME in thermal_info_dict and isinstance(thermal_info_dict[ChassisInfo.INFO_NAME], ChassisInfo):
            chassis_info_obj = thermal_info_dict[ChassisInfo.INFO_NAME]

        if chassis_info_obj is not None:
            chassis = chassis_info_obj.get_chassis()
            if chassis is not None:
                chassis.reboot()

@thermal_json_object('switch.shutdown')
class SwitchShutdownAction(ThermalPolicyActionBase):
    def execute(self, thermal_info_dict):
        """
        Take action when thermal condition matches. For example, shutdown/poweroff the switch.
        :param thermal_info_dict: A dictionary stores all thermal information.
        :return:
        """
        if ChassisInfo.INFO_NAME in thermal_info_dict and isinstance(thermal_info_dict[ChassisInfo.INFO_NAME], ChassisInfo):
            chassis_info_obj = thermal_info_dict[ChassisInfo.INFO_NAME]

        if chassis_info_obj is not None:
            chassis = chassis_info_obj.get_chassis()
            if chassis is not None:
                chassis.shutdown()

@thermal_json_object('thermal_control.active')
class ThermalControlActiveAction(ThermalPolicyActionBase):
    THERMAL_DEFAULT_MIN_TEMP = 55.0
    THERMAL_DEFAULT_MAX_TEMP = 85.0
    THERMAL_DEFAULT_MIN_SPEED = 50
    THERMAL_DEFAULT_MAX_SPEED = 100

    def execute(self, thermal_info_dict):

        if SensorInfo.INFO_NAME in thermal_info_dict and isinstance(thermal_info_dict[SensorInfo.INFO_NAME], SensorInfo):
            sensor_info_obj = thermal_info_dict[SensorInfo.INFO_NAME]

        if ChassisInfo.INFO_NAME in thermal_info_dict and isinstance(thermal_info_dict[ChassisInfo.INFO_NAME], ChassisInfo):
            chassis_info_obj = thermal_info_dict[ChassisInfo.INFO_NAME]

        if FanInfo.INFO_NAME in thermal_info_dict and isinstance(thermal_info_dict[FanInfo.INFO_NAME], FanInfo):
            fan_info_obj = thermal_info_dict[FanInfo.INFO_NAME]

        temperature = sensor_info_obj.get_max_chassis_temperature()
        fan_direction = sensor_info_obj.get_fan_direction()
        new_fan_speed = 0

        platform_globals = chassis_info_obj.get_chassis().get_global_data()
        if platform_globals is not None:
            min_temperature_threshold = platform_globals.get_param(PlatformGlobalData.KEY_MIN_TEMP, 
                    ThermalControlActiveAction.THERMAL_DEFAULT_MIN_TEMP)
            max_temperature_threshold = platform_globals.get_param(PlatformGlobalData.KEY_MAX_TEMP, 
                    ThermalControlActiveAction.THERMAL_DEFAULT_MAX_TEMP)
            if fan_direction == FanBase.FAN_DIRECTION_INTAKE:
                min_fan_speed = platform_globals.get_param(PlatformGlobalData.KEY_MIN_BLUE_FANS_SPEED,
                        ThermalControlActiveAction.THERMAL_DEFAULT_MIN_SPEED)
                max_fan_speed = platform_globals.get_param(PlatformGlobalData.KEY_MAX_BLUE_FANS_SPEED, 
                        ThermalControlActiveAction.THERMAL_DEFAULT_MAX_SPEED)
            elif fan_direction == FanBase.FAN_DIRECTION_EXHAUST:
                min_fan_speed = platform_globals.get_param(PlatformGlobalData.KEY_MIN_RED_FANS_SPEED,
                        ThermalControlActiveAction.THERMAL_DEFAULT_MIN_SPEED)
                max_fan_speed = platform_globals.get_param(PlatformGlobalData.KEY_MAX_RED_FANS_SPEED, 
                        ThermalControlActiveAction.THERMAL_DEFAULT_MAX_SPEED)
        else:
            min_temperature_threshold = ThermalControlActiveAction.THERMAL_DEFAULT_MIN_TEMP
            max_temperature_threshold = ThermalControlActiveAction.THERMAL_DEFAULT_MAX_TEMP
            min_fan_speed = ThermalControlActiveAction.THERMAL_DEFAULT_MIN_SPEED
            max_fan_speed = ThermalControlActiveAction.THERMAL_DEFAULT_MAX_SPEED

        if temperature < min_temperature_threshold:
            new_fan_speed = min_fan_speed
        elif temperature >= max_temperature_threshold:
            new_fan_speed = max_fan_speed
        else:
            new_fan_speed = min_fan_speed + ((temperature - min_temperature_threshold) * (max_fan_speed - min_fan_speed) / (max_temperature_threshold - min_temperature_threshold))

        for fan_drawer in chassis_info_obj.get_chassis().get_all_fan_drawers():
            for fan in fan_drawer.get_all_fans():
                presence = fan.get_presence()
                if presence:
                    fan.set_speed(new_fan_speed)


