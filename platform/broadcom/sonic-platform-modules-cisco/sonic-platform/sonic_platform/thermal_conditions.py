from sonic_platform_base.sonic_thermal_control.thermal_condition_base import ThermalPolicyConditionBase
from sonic_platform_base.sonic_thermal_control.thermal_json_object import thermal_json_object
from sonic_platform.chassis import Chassis 
from sonic_platform.globals import PlatformGlobalData

class FanCondition(ThermalPolicyConditionBase):
    def get_fan_info(self, thermal_info_dict):
        from .thermal_infos import FanInfo
        if FanInfo.INFO_NAME in thermal_info_dict and isinstance(thermal_info_dict[FanInfo.INFO_NAME], FanInfo):
            return thermal_info_dict[FanInfo.INFO_NAME]
        else:
            return None

class SensorCondition(ThermalPolicyConditionBase):
    def get_sensor_info(self, thermal_info_dict):
        from .thermal_infos import SensorInfo
        if SensorInfo.INFO_NAME in thermal_info_dict and isinstance(thermal_info_dict[SensorInfo.INFO_NAME], SensorInfo):
            return thermal_info_dict[SensorInfo.INFO_NAME]
        else:
            return None

    def get_chassis_info(self, thermal_info_dict):
        from .thermal_infos import ChassisInfo
        if ChassisInfo.INFO_NAME in thermal_info_dict and isinstance(thermal_info_dict[ChassisInfo.INFO_NAME], ChassisInfo):
            return thermal_info_dict[ChassisInfo.INFO_NAME]
        else:
            return None

    def get_fan_info(self, thermal_info_dict):
        from .thermal_infos import FanInfo
        if FanInfo.INFO_NAME in thermal_info_dict and isinstance(thermal_info_dict[FanInfo.INFO_NAME], FanInfo):
            return thermal_info_dict[FanInfo.INFO_NAME]
        else:
            return None

@thermal_json_object('fan.any.absence')
class AnyFanAbsenceCondition(FanCondition):
    def is_match(self, thermal_info_dict):
        fan_info_obj = self.get_fan_info(thermal_info_dict)
        return len(fan_info_obj.get_absence_fans()) > 0 if fan_info_obj else False


@thermal_json_object('fan.all.absence')
class AllFanAbsenceCondition(FanCondition):
    def is_match(self, thermal_info_dict):
        fan_info_obj = self.get_fan_info(thermal_info_dict)
        return len(fan_info_obj.get_presence_fans()) == 0 if fan_info_obj else False


@thermal_json_object('fan.all.presence')
class AllFanPresenceCondition(FanCondition):
    def is_match(self, thermal_info_dict):
        fan_info_obj = self.get_fan_info(thermal_info_dict)
        return len(fan_info_obj.get_absence_fans()) == 0 if fan_info_obj else False

@thermal_json_object('fan.all.differentdirection')
class AllFanDifferentDirectionCondition(FanCondition):
    def is_match(self, thermal_info_dict):
        fan_info_obj = self.get_fan_info(thermal_info_dict)
        if fan_info_obj is not None:
            n_blue_fans = len(fan_info_obj.get_blue_fans())
            n_red_fans = len(fan_info_obj.get_red_fans())
            if n_blue_fans and n_red_fans:
                return True
            elif n_blue_fans == 0 and n_red_fans == 0:
                return True
            else:
                return False
        return True

@thermal_json_object('fan.all.samedirection')
class AllFanSameDirectionCondition(FanCondition):
    def is_match(self, thermal_info_dict):
        fan_info_obj = self.get_fan_info(thermal_info_dict)
        if fan_info_obj is not None:
            n_blue_fans = len(fan_info_obj.get_blue_fans())
            n_red_fans = len(fan_info_obj.get_red_fans())
            if n_blue_fans and n_red_fans:
                return False
            elif n_blue_fans == 0 and n_red_fans == 0:
                return False
            else:
                return True
        return False

@thermal_json_object('fan.any.fault')
class AnyFanFaultCondition(FanCondition):
    def is_match(self, thermal_info_dict):
        fan_info_obj = self.get_fan_info(thermal_info_dict)
        return len(fan_info_obj.get_fault_fans()) > 0 if fan_info_obj else False

@thermal_json_object('fan.all.fault')
class AnyFanFaultCondition(FanCondition):
    def is_match(self, thermal_info_dict):
        fan_info_obj = self.get_fan_info(thermal_info_dict)
        if fan_info_obj and len(fan_info_obj.get_absence_fans()) == 0:
            if len(fan_info_obj.get_fault_fans()) ==  len(fan_info_obj.get_presence_fans()):
                return True
        return False

@thermal_json_object('fan.all.good')
class AnyFanFaultCondition(FanCondition):
    def is_match(self, thermal_info_dict):
        fan_info_obj = self.get_fan_info(thermal_info_dict)
        if fan_info_obj and len(fan_info_obj.get_absence_fans()) == 0:
            if len(fan_info_obj.get_fault_fans()) ==  0:
                return True
        return False

@thermal_json_object('sensor.any.criticalalarm')
class AnySensorCriticalAlarmCondition(SensorCondition):
    def is_match(self, thermal_info_dict):
        sensor_info_obj = self.get_sensor_info(thermal_info_dict)
        return len(sensor_info_obj.get_critical_alarms()) > 0 if sensor_info_obj else False

@thermal_json_object('sensor.any.minoralarm')
class AnySensorMinorAlarmCondition(SensorCondition):
    def is_match(self, thermal_info_dict):
        sensor_info_obj = self.get_sensor_info(thermal_info_dict)
        return len(sensor_info_obj.get_minor_alarms()) > 0 if sensor_info_obj else False

@thermal_json_object('sensor.any.majoralarm')
class AnySensorMajorAlarmCondition(SensorCondition):
    def is_match(self, thermal_info_dict):
        sensor_info_obj = self.get_sensor_info(thermal_info_dict)
        return len(sensor_info_obj.get_major_alarms()) > 0 if sensor_info_obj else False

@thermal_json_object('sensor.any.alarm')
class AnySensorAlarmCondition(SensorCondition):
    def is_match(self, thermal_info_dict):
        sensor_info_obj = self.get_sensor_info(thermal_info_dict)
        minor = 0
        major = 0
        critical = 0

        if sensor_info_obj:
            minor = len(sensor_info_obj.get_minor_alarms())
            major = len(sensor_info_obj.get_major_alarms())
            critical = len(sensor_info_obj.get_critical_alarms())

        if minor or major or critical:
            return True

        return False

@thermal_json_object('sensor.all.good')
class AllSensorGoodCondition(SensorCondition):
    def is_match(self, thermal_info_dict):
        sensor_info_obj = self.get_sensor_info(thermal_info_dict)
        minor = 0
        major = 0
        critical = 0

        if sensor_info_obj:
            minor = len(sensor_info_obj.get_minor_alarms())
            major = len(sensor_info_obj.get_major_alarms())
            critical = len(sensor_info_obj.get_critical_alarms())

        if minor or major or critical:
            return False 

        return True

@thermal_json_object('sensor.ambient.hot')
class AnyAmbientSensorHotCondition(SensorCondition):
    def is_match(self, thermal_info_dict):
        sensor_info_obj = self.get_sensor_info(thermal_info_dict)
        chassis_info_obj = self.get_chassis_info(thermal_info_dict)
        fan_info_obj = self.get_fan_info(thermal_info_dict)

        if fan_info_obj and sensor_info_obj and chassis_info_obj:
            n_blue_fans = len(fan_info_obj.get_blue_fans())
            n_red_fans = len(fan_info_obj.get_red_fans())
            platform_data = chassis_info_obj.get_chassis().get_global_data()

            if platform_data is None:
                return True

            if n_blue_fans and n_red_fans:
                return True 
            elif n_blue_fans == 0 and n_red_fans == 0:
                return True
            elif n_blue_fans:
                ambient_threshold = platform_data.get_param(PlatformGlobalData.KEY_BLUE_FANS_INLET_TEMP_THRESHOLD,
                        Chassis.DEFAULT_AMBIENT_TEMP_THRESHOLD)
            else:
                ambient_threshold = platform_data.get_param(PlatformGlobalData.KEY_RED_FANS_INLET_TEMP_THRESHOLD,
                        Chassis.DEFAULT_AMBIENT_TEMP_THRESHOLD)
            
            ambient_temperature = sensor_info_obj.get_ambient_temperature()
            if (ambient_temperature >= ambient_threshold):
                return True
            else:
                return False
        else:
            return False

@thermal_json_object('sensor.ambient.ok')
class AnyAmbientSensorOkCondition(SensorCondition):
    def is_match(self, thermal_info_dict):
        sensor_info_obj = self.get_sensor_info(thermal_info_dict)
        chassis_info_obj = self.get_chassis_info(thermal_info_dict)
        fan_info_obj = self.get_fan_info(thermal_info_dict)

        if fan_info_obj and sensor_info_obj and chassis_info_obj:
            n_blue_fans = len(fan_info_obj.get_blue_fans())
            n_red_fans = len(fan_info_obj.get_red_fans())
            platform_data = chassis_info_obj.get_chassis().get_global_data()

            if platform_data is None:
                return False 

            if n_blue_fans and n_red_fans:
                return False 
            elif n_blue_fans == 0 and n_red_fans == 0:
                return False
            elif n_blue_fans:
                ambient_threshold = platform_data.get_param(PlatformGlobalData.KEY_BLUE_FANS_INLET_TEMP_THRESHOLD,
                        Chassis.DEFAULT_AMBIENT_TEMP_THRESHOLD)
            else:
                ambient_threshold = platform_data.get_param(PlatformGlobalData.KEY_RED_FANS_INLET_TEMP_THRESHOLD,
                        Chassis.DEFAULT_AMBIENT_TEMP_THRESHOLD)

            ambient_temperature = sensor_info_obj.get_ambient_temperature()
            if (ambient_temperature < ambient_threshold):
                return True
            else:
                return False
        else:
            return False


