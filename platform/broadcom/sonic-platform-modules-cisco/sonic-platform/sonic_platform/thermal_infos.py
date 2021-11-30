from sonic_platform_base.sonic_thermal_control.thermal_info_base import ThermalPolicyInfoBase
from sonic_platform_base.sonic_thermal_control.thermal_json_object import thermal_json_object
from sonic_platform_base.fan_base import FanBase
from sonic_platform.thermal import Thermal

@thermal_json_object('fan_info')
class FanInfo(ThermalPolicyInfoBase):
    """
    Fan information needed by thermal policy
    """

    # Fan information name
    INFO_NAME = 'fan_info'

    def __init__(self):
        self._absence_fans = set()
        self._presence_fans = set()
        self._fault_fans = set()
        self._blue_fans = set()
        self._red_fans = set()
        self._status_changed = False

    def collect(self, chassis):
        """
        Collect absence and presence fans.
        :param chassis: The chassis object
        :return:
        """
        self._status_changed = False
        for fan_drawer in chassis.get_all_fan_drawers():
            for fan in fan_drawer.get_all_fans():
                presence = fan.get_presence()
                status = fan.get_status()
                direction = fan.get_direction()

                if presence and fan not in self._presence_fans:
                    self._presence_fans.add(fan)
                    self._status_changed = True
                    if fan in self._absence_fans:
                        self._absence_fans.remove(fan)
                elif not presence and fan not in self._absence_fans:
                    self._absence_fans.add(fan)
                    self._status_changed = True
                    if fan in self._presence_fans:
                        self._presence_fans.remove(fan)

                if presence:
                    if direction == FanBase.FAN_DIRECTION_INTAKE and fan not in self._red_fans:
                        self._red_fans.add(fan)
                        self._status_changed = True
                        if fan in self._blue_fans:
                            self._blue_fans.remove(fan)
                    elif direction == FanBase.FAN_DIRECTION_EXHAUST and fan not in self._blue_fans:
                        self._blue_fans.add(fan)
                        self._status_changed = True
                        if fan in self._red_fans:
                            self._red_fans.remove(fan)
                else:
                    if fan in self._blue_fans:
                        self._blue_fans.remove(fan)
                        self._status_changed = True

                    if fan in self._red_fans:
                        self._red_fans.remove(fan)
                        self._status_changed = True

                if not status and fan not in self._fault_fans:
                    self._fault_fans.add(fan)
                    self._status_changed = True
                elif status and fan in self._fault_fans:
                    self._fault_fans.remove(fan)
                    self._status_changed = True
                    

    def get_absence_fans(self):
        """
        Retrieves absence fans
        :return: A set of absence fans
        """
        return self._absence_fans

    def get_presence_fans(self):
        """
        Retrieves presence fans
        :return: A set of presence fans
        """
        return self._presence_fans

    def get_fault_fans(self):
        """
        Retrieves fault fans
        :return: A set of fault fans
        """
        return self._fault_fans

    def get_blue_fans(self):
        """
        Retrieves port side exhaust fans
        :return: A set of blue fans
        """
        return self._blue_fans

    def get_red_fans(self):
        """
        Retrieves port side intake fans
        :return: A set of red fans
        """
        return self._red_fans

    def is_status_changed(self):
        """
        Retrieves if the status of fan information changed
        :return: True if status changed else False
        """
        return self._status_changed


@thermal_json_object('chassis_info')
class ChassisInfo(ThermalPolicyInfoBase):
    """
    Chassis information needed by thermal policy
    """
    INFO_NAME = 'chassis_info'

    def __init__(self):
        self._chassis = None

    def collect(self, chassis):
        """
        Collect platform chassis.
        :param chassis: The chassis object
        :return:
        """
        self._chassis = chassis

    def get_chassis(self):
        """
        Retrieves platform chassis object
        :return: A platform chassis object.
        """
        return self._chassis

@thermal_json_object('sensor_info')
class SensorInfo(ThermalPolicyInfoBase):
    """
    Sensors information needed by thermal policy
    """
    INFO_NAME = 'sensor_info'

    def __init__(self):
        self._sensors = None
        self._num_sensors = 0
        self._fan_direction = FanBase.FAN_DIRECTION_NOT_APPLICABLE

    def collect(self, chassis):
        """
        Collect platform sensors.
        :param chassis: The chassis object
        :return:
        """
        n_blue_fans = 0
        n_red_fans = 0

        self._sensors = chassis.get_all_thermals()
        self._num_sensors = chassis.get_num_thermals()

        for fan_drawer in chassis.get_all_fan_drawers():
            for fan in fan_drawer.get_all_fans():
                presence = fan.get_presence()
                direction = fan.get_direction()
                if presence and direction == FanBase.FAN_DIRECTION_EXHAUST:
                    n_blue_fans = n_blue_fans + 1
                elif presence and direction == FanBase.FAN_DIRECTION_INTAKE:
                    n_red_fans = n_red_fans + 1

        if n_red_fans and n_blue_fans == 0:
            self._fan_direction = FanBase.FAN_DIRECTION_INTAKE
        elif n_red_fans == 0 and n_blue_fans:
            self._fan_direction = FanBase.FAN_DIRECTION_EXHAUST
        else:
            self._fan_direction = FanBase.FAN_DIRECTION_NOT_APPLICABLE

    def get_fan_direction(self):
        return self._fan_direction

    def get_inlet_temperature(self):
        """
        Retrieves inlet / ambient temperature from the Chassis
        :return: temperature in float type
        """
        temperature_list = [-64.0]

        if self.get_fan_direction() == FanBase.FAN_DIRECTION_EXHAUST:
            for sensor in self._sensors:
                if sensor.get_location() == Thermal.SENSOR_NEAR_FANS:
                    temperature_list.append(sensor.get_temperature())
        elif self.get_fan_direction() == FanBase.FAN_DIRECTION_INTAKE:
            for sensor in self._sensors:
                if sensor.get_location() == Thermal.SENSOR_NEAR_FRONT_PANEL_PORTS:
                    temperature_list.append(sensor.get_temperature())

        return max(temperature_list)

    def get_max_chassis_temperature(self):
        """
        Retrieves maximum temperature inside Chassis
        :return: temperature in float type
        """
        temperature_list = [-64.0]
        for sensor in self._sensors:
            temperature_list.append(sensor.get_temperature())

        return max(temperature_list)

    def get_minor_alarms(self):
        """
        Retrieves minor temperature alarms inside Chassis
        :return: minor alarm sensors list
        """
        minor_alarm_sensors = []

        for sensor in self._sensors:
            temperature = sensor.get_temperature()
            high_threshold = sensor.get_high_threshold()
            hot_threshold = sensor.get_hot_threshold()
            if (temperature >= high_threshold and temperature < hot_threshold):
                minor_alarm_sensors.append(sensor)

        return minor_alarm_sensors 

    def get_major_alarms(self):
        """
        Retrieves major temperature alarms inside Chassis
        :return: major alarm sensors list
        """
        major_alarm_sensors = []

        for sensor in self._sensors:
            temperature = sensor.get_temperature()
            hot_threshold = sensor.get_hot_threshold()
            high_crit_threshold = sensor.get_high_critical_threshold()
            if (temperature >= hot_threshold and temperature < high_crit_threshold):
                major_alarm_sensors.append(sensor)

        return major_alarm_sensors 

    def get_critical_alarms(self):
        """
        Retrieves critical temperature alarms inside Chassis
        :return: critical alarm sensors list
        """
        critical_alarm_sensors = []

        for sensor in self._sensors:
            temperature = sensor.get_temperature()
            high_crit_threshold = sensor.get_high_critical_threshold()
            if (temperature >= high_crit_threshold):
                critical_alarm_sensors.append(sensor)

        return critical_alarm_sensors 


