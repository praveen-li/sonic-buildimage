import os
from sonic_platform_base.sonic_thermal_control.thermal_manager_base import ThermalManagerBase
from sonic_platform_base.sonic_thermal_control.thermal_policy import ThermalPolicy
from .thermal_actions import *
from .thermal_conditions import *
from .thermal_infos import *


class ThermalManager(ThermalManagerBase):
    @classmethod
    def init_thermal_algorithm(cls, chassis):
        """
        Initialize thermal algorithm according to policy file.
        :param chassis: The chassis object.
        :return:
        """
        if cls._fan_speed_when_suspend is not None:
            for fan in chassis.get_all_fans():
                fan.set_speed(cls._fan_speed_when_suspend)

            for psu in chassis.get_all_psus():
                for fan in psu.get_all_fans():
                    fan.set_speed(cls._fan_speed_when_suspend)      


