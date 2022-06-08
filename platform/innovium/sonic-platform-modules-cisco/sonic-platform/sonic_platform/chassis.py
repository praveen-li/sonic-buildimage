#!/usr/bin/env python

#############################################################################
# CISCO
#
# Module contains an implementation of SONiC Platform Base API and
# provides the Chassis information which are available in the platform
#
#############################################################################

try:
    import sys
    import os
    from sonic_platform_base.chassis_base import ChassisBase
    import sonic_platform.utils as pltm_utils
    from sonic_py_common.logger import Logger
    from sonic_py_common import device_info
    from os import listdir
    from sonic_platform.device_data import DEVICE_DATA
    from sonic_platform.eeprom import Eeprom
    from sonic_platform.component import *
    from sonic_platform.globals import PlatformGlobalData
    from sonic_platform.utils import read_str_from_file
except ImportError as e:
    raise ImportError (str(e) + "- required module not found")


# Global logger class instance
logger = Logger()

class Chassis(ChassisBase):
    """Platform-specific Chassis class"""

    DICT_PLATFORM_KEY_GLOBALS = 'globals'
    DICT_PLATFORM_KEY_FANS = 'fans'
    DICT_PLATFORM_KEY_PSUS = 'psus'
    DICT_PLATFORM_KEY_THERMALS = 'thermals'
    DICT_PLATFORM_KEY_SFPS = 'sfps'
    DEFAULT_AMBIENT_TEMP_THRESHOLD = 35.0
    DEFAULT_TEMP_THRESHOLD_HYSTERESIS = 5.0
    DEFAULT_LOW_TEMP_THRESHOLD = 0.0

    def __init__(self):
        super(Chassis, self).__init__()

        self.name = "Undefined"
        self.model = "Undefined"
        self.serial = "Undefined"
        self.product_name = "Undefined"
        self.board_eeprom_map = None
        self.board_eeprom_code_map = None
        # Initialize Platform name
        self.platform_name = device_info.get_platform()
        self.name = self.platform_name
        self.sfp_init_done = False
        self._watchdog = None
        self._eeprom = None

        self.initialize_globals()
        self.initialize_reboot_shutdown_handlers()
        self.initialize_psu()
        self.initialize_components()
        self.initialize_fan()
        self.initialize_eeprom()
        self.initialize_thermals()
        self.initialize_port_leds()
        self.initialize_sfps()
        self.initizalize_system_led()

        logger.log_info("Chassis loaded successfully")

    def get_watchdog(self):
        try:
            if self._watchdog is None:
                from sonic_platform.watchdog import Watchdog
                self._watchdog = Watchdog()
        except Exception as e:
            logger.log_info("Fail to load watchdog due to {}".format(repr(e)))

        return self._watchdog

    def initialize_psu(self):
        from sonic_platform.psu import Psu
        # Initialize PSU list
        #self.psu_module = Psu
        psu_data = DEVICE_DATA[self.platform_name][Chassis.DICT_PLATFORM_KEY_PSUS]
        psu_num = psu_data['psu_num']
        for index in range(psu_num):
            psud = psu_data['psu'][index]
            psu = Psu(index, self.global_parameters,psud)
            self._psu_list.append(psu)

    def initialize_fan(self):
        #from .device_data import DEVICE_DATA
        from sonic_platform.fan import Fan
        from sonic_platform.fan_drawer import FanDrawer

        fan_drawer_data = DEVICE_DATA[self.platform_name][Chassis.DICT_PLATFORM_KEY_FANS]
        drawer_num = fan_drawer_data['drawer_num']
        for fan_drawer_index in range (drawer_num):
           fan_data = fan_drawer_data['fan_drawer'][fan_drawer_index]
           fan_num_per_drawer = fan_data['fan_num']
           fan_drawerd = FanDrawer(self.global_parameters,fan_drawer_index,fan_data)
           self._fan_drawer_list.append(fan_drawerd)
           for fan_index in range (fan_num_per_drawer):
               fan_per_data = fan_data['fan'][fan_index]
               fan = Fan(fan_index, fan_drawer_index ,self.global_parameters,fan_per_data)
               self._fan_list.append(fan)

    def initialize_eeprom(self):
        from sonic_platform.eeprom import Eeprom
        # Initialize EEPROM
        self._eeprom = Eeprom()
        if self._eeprom is not None:
            # Get chassis name and model from eeprom
            self.model = self._eeprom.get_part_number()
            self.serial = self._eeprom.get_serial_number()
            self.base_mac = self._eeprom.get_base_mac()
            self.board_eeprom_map, self.board_eeprom_code_map =  self._eeprom.read_eeprom_map()

    def initialize_thermals(self):
        from sonic_platform.thermal import Thermal
        # Initialize thermals
        thermal_data = DEVICE_DATA[self.platform_name][Chassis.DICT_PLATFORM_KEY_THERMALS]
        thermal_num = thermal_data['thermal_num']

        for thl_index in range (thermal_num):
            temp_data = thermal_data['temp'][thl_index]
            thl = Thermal(thl_index, self.global_parameters, temp_data)
            self._thermal_list.append(thl)

    def initialize_sfps(self):
        from sonic_platform.sfp import Sfp 
        from sonic_platform.sfputil import SfpUtil

        if self.platform_name not in DEVICE_DATA: 
            return
            
        if Chassis.DICT_PLATFORM_KEY_SFPS not in DEVICE_DATA[self.platform_name]:
            return

        sfps_data = DEVICE_DATA[self.platform_name][Chassis.DICT_PLATFORM_KEY_SFPS]
        if 'fp_start_index' in sfps_data:
            self.fp_index_start = int(sfps_data['fp_start_index'])
            if self.fp_index_start < 1:
                self.fp_index_start = 1 
        else:
            self.fp_index_start = 1 

        if 'fp_num' in sfps_data:
            self.num_fp = int(sfps_data['fp_num'])
            if self.num_fp < 1:
                self.num_fp = 0 
        else:
            self.num_fp = 0 

        self.platform_sfputil=SfpUtil(self.fp_index_start, self.num_fp, self.global_parameters, sfps_data)

        for port_index in range(self.fp_index_start-1, self.num_fp):
            if port_index in self.platform_sfputil.qsfp_ports:
                sfp_type = SfpUtil.SUPPORTED_QSFP_PORT_TYPES[0]
            elif port_index in self.platform_sfputil.sfp_ports:
                sfp_type = SfpUtil.SUPPORTED_SFP_PORT_TYPES[0]
            else:
                sfp_type = SfpUtil.SUPPORTED_OSFP_QSFPDD_PORT_TYPES[0]

            port_data = Sfp(port_index,sfp_type, self.global_parameters, self.platform_sfputil)
            self._sfp_list.append(port_data)

        self.sfp_init_done = True

    def get_platform_sfputil(self):
        return self.platform_sfputil

    def initialize_port_leds(self):
        from sonic_platform.led_control import LedControl
        self._led_control = LedControl(self.global_parameters)

    def initialize_globals(self):
        from sonic_platform.globals import PlatformGlobalData
        if self.platform_name in DEVICE_DATA:
            plat_data = DEVICE_DATA[self.platform_name]
            if plat_data is not None and Chassis.DICT_PLATFORM_KEY_GLOBALS in plat_data:
                global_data = plat_data[Chassis.DICT_PLATFORM_KEY_GLOBALS]
                self.global_parameters  = PlatformGlobalData(global_data)
            else:
                self.global_parameters = None
        else:
            self.global_parameters = None

    def initialize_components(self):
        for iofpga_inst in range (self.global_parameters.get_param(PlatformGlobalData.KEY_MAX_IOFPGA, 0)):
            self._component_list.append(ComponentIOFPGA())
        for mifpga_inst in range (self.global_parameters.get_param(PlatformGlobalData.KEY_MAX_MIFPGA, 0)):
            self._component_list.append(ComponentMIFPGA(mifpga_inst))
        for bios_inst in range (self.global_parameters.get_param(PlatformGlobalData.KEY_MAX_BIOS, 0)):
            self._component_list.append(ComponentBIOS(bios_inst))

    def get_change_event(self, timeout=0):
        p_dict = {'sfp':{}}

        if self.sfp_init_done is False:
           return True, p_dict

        status, p_pres_dict = self.platform_sfputil.get_transceiver_change_event(timeout)
        if status is True and  len(p_pres_dict) != 0 :
            for port_index in p_pres_dict :
                self._sfp_list[int(port_index)].sfp_reinit(p_pres_dict[port_index])
            p_dict['sfp'] = p_pres_dict
        return status, p_dict

    def initizalize_system_led(self):
        from sonic_platform.led import SystemLed
        self._status_led = SystemLed()

    def get_global_data(self):
        return self.global_parameters

    def get_led_control(self):
        return self._led_control

    def get_thermal_manager(self):
        from .thermal_manager import ThermalManager
        return ThermalManager 

    def get_eeprom(self):
        try:
            if self._eeprom is None:
                self._eeprom = Eeprom()
        except Exception as e:
            logger.log_info("Fail to load Eeprom due to {}".format(repr(e)))

        return self._eeprom

    def get_name(self):
        return self.name

    def get_model(self):
        return self.model

    def get_presence(self):
        #currently supporting only TORs and so return TRUE always
        return True

    def get_status(self):
        #currently supporting only TORs and so return TRUE always
        return True

    def get_serial(self):
        return self.serial

    def get_base_mac(self):
        return self.base_mac

    def get_system_eeprom_info(self):
        return self.board_eeprom_code_map

    def get_position_in_parent(self):
        #currently supporting only TORs and so return -1 always
        return -1

    def is_replaceable(self):
        #currently supporting only TORs and so return False always
        return False

    def get_bootstatus(self):
        bootstatus = 0
        
        wdt_name = pltm_utils.get_watchdog_device()
        if wdt_name is None:
            return 0

        try:
            with open("/{}/{}/bootstatus".format(pltm_utils.WDT_SYSFS, wdt_name), 'r') as wdt_f:
                bootstatus =  int(wdt_f.readline().strip())
        except IOError:
            return 0

        return bootstatus

    def get_reboot_cause(self):
        try:
            self.prev_reboot_path = "/host/reboot-cause/reboot-cause.txt"
            if os.path.exists(self.prev_reboot_path) :
                reason = read_str_from_file (self.prev_reboot_path)
                if "reboot" in reason or "Kernel Panic" in reason:
                    return self.REBOOT_CAUSE_NON_HARDWARE, ""
        except Exception as e:
            logger.log_info("Failed to get the reboot.txt file due to {}".format(repr(e)))
        self.bootstatus = self.get_bootstatus()

        if self.bootstatus & 0x04:
            return self.REBOOT_CAUSE_WATCHDOG, "Reboot caused by hardware watchdog reset"
        elif self.bootstatus == 0x00 or self.bootstatus == 0x01:
            return self.REBOOT_CAUSE_NON_HARDWARE, ""
        elif self.bootstatus == 0x80000000:
            return self.REBOOT_CAUSE_POWER_LOSS, "PSU shutdown or powercycle"
        else:
            return self.REBOOT_CAUSE_HARDWARE_OTHER, "Unknown"

    def set_status_led(self, color):
        """
        Sets the state of the system LED
        Args:
            color: A string representing the color with which to set the
                   system LED
        Returns:
            bool: True if system LED state is set successfully, False if not
        """
        return False if self._status_led is None else self._status_led.set_status(color)

    def get_status_led(self):
        """
        Gets the state of the system LED
        Returns:
            A string, one of the valid LED color strings which could be vendor
            specified.
        """
        return None if self._status_led is None else self._status_led.get_status()

    def initialize_reboot_shutdown_handlers(self):
        _reboot_gpio_path = "/sys/class/gpio/gpio{}/value"
        _shutdown_gpio_path = "/sys/class/gpio/gpio{}/value"

        self.reboot_gpio_path = ""
        self.shutdown_gpio_path = ""

        platform_data = self.get_global_data()
        if platform_data is None:
            return

        reboot_gpio_num = platform_data.get_param(PlatformGlobalData.KEY_REBOOT_GPIO_NUM, 0)
        shutdown_gpio_num = platform_data.get_param(PlatformGlobalData.KEY_SHUTDOWN_GPIO_NUM, 0)

        if reboot_gpio_num != 0:
            self.reboot_gpio_path = _reboot_gpio_path.format(reboot_gpio_num)

        if shutdown_gpio_num != 0:
            self.shutdown_gpio_path = _shutdown_gpio_path.format(shutdown_gpio_num)

    def reboot(self):
        """
        Reboots/power-cycle the system immediately
        Returns:
            nothing as it should reboot the system
        """
        pltm_utils.write_file(self.reboot_gpio_path, 1, True)

    def shutdown(self):
        """
        Shuts down / poweroff  the system immediately
        Returns:
            nothing as it should shutdown the system
        """
        pltm_utils.write_file(self.shutdown_gpio_path, 1, True)

