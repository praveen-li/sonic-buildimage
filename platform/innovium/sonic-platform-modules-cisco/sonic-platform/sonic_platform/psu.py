#!/usr/bin/env python
#
# psu.py
#
# Platform-specific LED control functionality for SONiC
#

try:
    import fnmatch
    import os.path
    from sonic_platform_base.psu_base import PsuBase
    from sonic_platform.globals import PlatformGlobalData
    from sonic_platform.fan import Fan
    from sonic_py_common.logger import Logger
    from sonic_platform.utils import read_int_from_file
except ImportError as e:
    raise ImportError (str(e) + "- required module not found")

# Global logger class instance
logger = Logger()

psu_list = []

psu_dict =  {'x86_64-cisco_N3K_C3432D':0}

psu_eeprom = [
        {
            'model_offset' : 33,
            'model_len'    : 19,
            'serial_offset': 52,
            'serial_len'   : 11,
            'vendor_offset': 14,
            'vendor_len'   : 20,
        }
]

class Psu(PsuBase):
    """Platform-specific PSU class"""

    """We can extend class based on platform name"""
    def __init__(self, psu_index, platform_data, psu_data):
        PsuBase.__init__(self)

        self.psu_path = "/sys/bus/i2c/devices/{}-{}/hwmon/"
        self.psu_path_eeprom = "/sys/bus/platform/drivers/cisco_iofpga_auto_poll/cisco_iofpga_auto_poll/psu{}"
        self.psu_oper_status = "in1_input"
        self.psu_voltage = "in1_input"
        self.psu_current = "curr1_input"
        self.psu_power = "power1_input"
        self.psu_presence = "/sys/class/gpio/gpio{}/value"
        self.platform_data = platform_data

        self.psu_eeprom_data_format = self.platform_data.get_param(PlatformGlobalData.KEY_PSU_EEPROM_DATA_FORMAT, 0)

        self.index = psu_index + 1
        self._name_psu = "PSU{}".format(self.index)
        self._bus_psu  = psu_data['bus']
        self._addr_psu = psu_data['addr']
        self._addr_psu_eeprom = psu_data['eeprom_addr']
        self._path_psu = self.psu_path.format(self._bus_psu, self._addr_psu)
        self._path_psu_eeprom = self.psu_path_eeprom.format(self.index)
        self._presence_psu = self.psu_presence.format(psu_data['gpio'])
        self._psu_temp_path = "temp1_input"
        self.eeprom_dict = psu_eeprom[self.psu_eeprom_data_format]
        self.psu_data = psu_data
        self.is_fan_sw_controllable = self.psu_data['is_fan_sw_controllable']
        if psu_data['fan_num']:
            fan = Fan(psu_index,0, platform_data,None,True, psu_data)
            self._fan_list.append(fan)

    def get_name(self):
        return self._name_psu

    def get_status(self):
        status = 0
        filename = None

        if not os.path.exists(self._path_psu):
            return False
        
        for dirname in os.listdir(self._path_psu):
            if fnmatch.fnmatch(dirname, 'hwmon?'):
                filename = self._path_psu + dirname + '/' + self.psu_oper_status
                break
        if filename is None:
             return False
        
        if not os.path.exists(filename):
            return False
        
        status = read_int_from_file(filename)
        if status == 0:
            return False
        else:
            status = 1
        return status == 1

    def get_powergood_status(self):
        status = 0
        filename = None

        if not os.path.exists(self._path_psu):
            return False
        
        for dirname in os.listdir(self._path_psu):
            if fnmatch.fnmatch(dirname, 'hwmon?'):
                filename = self._path_psu + dirname + '/' + self.psu_oper_status
                break
        if filename is None:
            return False
        if not os.path.exists(filename):
            return False

        status = read_int_from_file(filename)
        if status == 0:
            return False
        else:
            status = 1
        return status == 1

    def get_presence(self):
        status = 0

        if not os.path.exists(self._presence_psu):
            return False
        status = read_int_from_file(self._presence_psu)
        if status == 0:
            return False
        else:
            status = 1
        return status == 1

    def get_voltage(self):
        filename = None
        if self.psu_voltage is not None and self.get_powergood_status():
            if not os.path.exists(self._path_psu):
                return 0.0
        
            for dirname in os.listdir(self._path_psu):
                if fnmatch.fnmatch(dirname, 'hwmon?'):
                     filename = self._path_psu + dirname + '/' + self.psu_voltage
                     break
            if filename is None:
                return 0.0
            if not os.path.exists(filename):
                return 0.0
            
            voltage = read_int_from_file(filename)            
            return float(voltage) / 1000
        else:
            return 0.0

    def get_model(self):
        if self.get_presence():
            if not os.path.exists(self._path_psu_eeprom):
                return None
            model_offset=self.eeprom_dict['model_offset']
            model_len=self.eeprom_dict['model_len']
            with open(self._path_psu_eeprom, 'r',encoding="latin-1") as fileobj:
                data_eeprom = str(fileobj.read().strip())
                model = data_eeprom[model_offset:(model_offset+model_len)]
                return model
        else:
            return None

    def get_current(self):
        filename = None
        if self.psu_current is not None and self.get_powergood_status():
            if not os.path.exists(self._path_psu):
                return 0.0
        
            for dirname in os.listdir(self._path_psu):
                if fnmatch.fnmatch(dirname, 'hwmon?'):
                     filename = self._path_psu + dirname + '/' + self.psu_current
                     break
            if filename is None:
                return 0.0
            if not os.path.exists(filename):
                return 0.0
            current = read_int_from_file(filename)            
            return float(current) / 1000
        else:
            return 0.0

    def get_serial(self):
        if self.get_presence():
            if not os.path.exists(self._path_psu_eeprom):
                return None
            serial_offset = self.eeprom_dict['serial_offset']
            serial_len = self.eeprom_dict['serial_len']
            with open(self._path_psu_eeprom, 'r',encoding="latin-1") as fileobj:
                data_eeprom = str(fileobj.read().strip())            
                serial_num = data_eeprom[serial_offset:(serial_offset+serial_len)]
                return serial_num
        else:
            return None

    def get_power(self):
        filename = None
        if self.psu_power is not None and self.get_powergood_status():
            if not os.path.exists(self._path_psu):
                return 0.0
        
            for dirname in os.listdir(self._path_psu):
                if fnmatch.fnmatch(dirname, 'hwmon?'):
                     filename = self._path_psu + dirname + '/' + self.psu_power
                     break
            if filename is None:
                return 0.0
            if not os.path.exists(filename):
                return 0.0
            power = read_int_from_file(filename)            
            return float(power) / 1000000
        else:
            return 0.0

        
    def get_mfr_id(self):
        if self.get_presence():
            if not os.path.exists(self._path_psu_eeprom):
                return None
            vendor_offset = self.eeprom_dict['vendor_offset'] 
            vendor_len = self.eeprom_dict['vendor_len']  
            with open(self._path_psu_eeprom, 'r',encoding="latin-1") as fileobj:
                data_eeprom = str(fileobj.read().strip())
                vendor = data_eeprom[vendor_offset:(vendor_offset+vendor_len)]
                return vendor
        else:
            return None
    def get_temperature(self):
        invalid_temp=-64.0
        if self.get_presence():
            if not os.path.exists(self._path_psu):
                return invalid_temp
            filename = None
            for dirname in os.listdir(self._path_psu):
                if fnmatch.fnmatch(dirname, 'hwmon?'):
                     filename = self._path_psu + dirname + '/' + self._psu_temp_path
                     break
            if filename is None:
                return invalid_temp
            if not os.path.exists(filename):
                return invalid_temp 
            status = read_int_from_file(filename)
            return float(status)/1000
        else:
            return invalid_temp 

    def get_voltage_high_threshold(self):
        return None

    def get_voltage_low_threshold(self):
        return None

    def get_temperature_high_threshold(self):
        return None

    def is_replaceable(self):
        return True
    def set_status_led(self, color):
        return None
################## test ###############
# p1 = Psu(1, "x86_64-cisco_N3K_C3432C")
# print(p1.get_num_psus())
# print(p1.get_name())
# print(p1.get_status())
# print(p1.get_presence())
# print(p1.get_voltage())
#################################
