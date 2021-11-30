

try:
    from sonic_platform_base.platform_base import PlatformBase
    from sonic_platform.chassis import Chassis
except ImportError as e:
    raise ImportError (str(e) + "- required module not found")


class Platform(PlatformBase):
    """ Platform class"""

    def __init__(self):
        super(Platform, self).__init__()
        self._chassis = Chassis()
        self._chassis.initialize_globals()
        self._chassis.initialize_psu()
        self._chassis.initialize_fan()
        self._chassis.initialize_eeprom()
        self._chassis.initialize_thermals()
        self._chassis.initialize_port_leds()
        self._chassis.initialize_sfps()
