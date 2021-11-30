#############################################################################
# eeprom.py contains implementation of SONiC Platform Base API
#############################################################################
import os
import sys
import re
import subprocess
import time

from sonic_py_common.logger import Logger

try:
    import sys
    import redis
    from sonic_platform.eeprom_tlv import Eeprom_Tlv
except ImportError as e:
    raise ImportError (str(e) + "- required module not found")

logger = Logger()

class Eeprom(Eeprom_Tlv):
    def __init__(self):
        self.name_map = {
            "Product Name":"PID",
            "Serial Number":"S/N",
            "Base MAC Address":"MAC_BASE",
            "MAC Addresses":"NUMBER_MAC",
            "Part Number":"Part_Number",
            "Part Revision":"Part_Revision",
            "Hardware Revision":"HW_Revision",
            "Hardware Change Bit":"HW_Change_Bit",
            "Card Index":"CARD_INDEX",
        }

        # Need to modify this
        self.code_map = {
            self._TLV_CODE_CISCO_PRODUCT_NAME:"PID",
            self._TLV_CODE_CISCO_SERIAL_NUMBER:"S/N",
            self._TLV_CODE_CISCO_MAC_BASE:"MAC_BASE",
            self._TLV_CODE_CISCO_MAC_SIZE:"NUMBER_MAC",
            self._TLV_CODE_CISCO_PART_NUMBER:"Part_Number",
            self._TLV_CODE_CISCO_PART_REVISION:"Part_Revision",
            self._TLV_CODE_CISCO_HW_REVISION:"HW_Revision",
            self._TLV_CODE_CISCO_HW_CHANGE_BIT:"HW_Change_Bit",
            self._TLV_CODE_CISCO_CARD_INDEX:"CARD_INDEX",
        }
        self._eeprom_map = None
        self._eeprom_code_map = None
        self.platform_eeprom_path = "/etc/sonic/platform_eeprom_data"
        self.read_eeprom()

    def read_pfm_util(self, arg):
        pfm_dict = {}
        if os.path.exists(self.platform_eeprom_path):
            with open(self.platform_eeprom_path,"r") as eeprom_fp:
                lines=eeprom_fp.readlines()
        else:
            try:
                ph = subprocess.Popen(['/usr/local/bin/pfm_util', arg],
                                  stdout=subprocess.PIPE,
                                  shell=False, stderr=subprocess.STDOUT)
                cmdout = ph.communicate()[0]
                ph.wait()
            except OSError as e:
                raise OSError("cannot access pfm_util")

            str_img = cmdout.decode("utf-8", errors="ignore")
            lines = str_img.splitlines()

        for line in lines:
            line = line.rstrip('\n\r')
            name = line.split(': ')[0].rstrip(' ')
            value = line.split(': ')[1]
            pfm_dict[name] = value

        return pfm_dict

    def read_eeprom_map(self):
        pfm_util_map = self.read_pfm_util('-d')
        pfm_util_map.update(self.read_pfm_util('-r'))

        eeprom_map = {key: pfm_util_map[self.name_map[key]] for key in self.name_map.keys()}
        eeprom_code_map = {key: pfm_util_map[self.code_map[key]] for key in self.code_map.keys()}

        return eeprom_map, eeprom_code_map

    def read_eeprom(self):
        if self._eeprom_map is None:
            self._eeprom_map, self._eeprom_code_map = self.read_eeprom_map()
        return self._eeprom_map

    def get_base_mac(self):
        """
        Retrieves the base MAC address for the chassis

        Returns:
            A string containing the MAC address in the format
            'XX:XX:XX:XX:XX:XX'
        """
        if self._eeprom_map is None:
            self._eeprom_map, self._eeprom_code_map = self.read_eeprom_map()
        return self._eeprom_map["Base MAC Address"]

    def get_serial_number(self):
        """
        Retrieves the hardware serial number for the chassis

        Returns:
            A string containing the hardware serial number for this chassis.
        """
        if self._eeprom_map is None:
            self._eeprom_map, self._eeprom_code_map = self.read_eeprom_map()
        return self._eeprom_map["Serial Number"]

    def get_product_name(self):
        """
        Retrieves the hardware product name for the chassis

        Returns:
            A string containing the hardware product name for this chassis.
        """
        if self._eeprom_map is None:
            self._eeprom_map, self._eeprom_code_map = self.read_eeprom_map()
        return self._eeprom_map["Product Name"]

    def get_part_number(self):
        """
        Retrieves the hardware part number for the chassis

        Returns:
            A string containing the hardware part number for this chassis.
        """
        if self._eeprom_map is None:
            self._eeprom_map, self._eeprom_code_map = self.read_eeprom_map()
        return self._eeprom_map["Part Number"]

    def update_eeprom_db(self, eeprom):
        '''
        Decode the contents of the EEPROM and update the contents to database
        '''
        if self._eeprom_code_map is None:
            self._eeprom_map, self._eeprom_code_map = self.read_eeprom_map()

        return self.helper_update_eeprom_db(self._eeprom_code_map)

########################################
#   Test
########################################
# 
# e1 = Eeprom()
# print(e1.get_base_mac())
# print(e1.get_serial_number())
# print(e1.get_product_name())
# print(e1.get_part_number())
# ee = e1.read_eeprom()
#print("ee: {}\n".format(ee))
# e1.update_eeprom_db(ee)
# e1.helper_read_eeprom()
# e1.decode_eeprom(ee)
