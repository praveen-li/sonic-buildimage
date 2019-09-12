#!/usr/bin/env python
# Copyright 2018 Cisco Systems

"""
Cisco Nexus N9K/N3K eeprom plugin
Uses the pfm_util in the platform-module-n9200
to obtain the act2 eeprom information
"""

import StringIO

try:
    import os
    import exceptions
    import subprocess
except ImportError, e:
    raise ImportError (str(e) + "- required module not found")

class board(object):

    def __init__(self, path, start, status, ro):
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
        self.cache_name = None
        self.cache_update_needed = False
        self.lock_file = None

    def read_pfm_util(self, arg):

        pfm_dict = {}

        try:
            ph = subprocess.Popen(['/usr/local/bin/pfm_util', arg],
                                  stdout=subprocess.PIPE,
                                  shell=False, stderr=subprocess.STDOUT)
            cmdout = ph.communicate()[0]
            ph.wait()
        except OSError, e:
            raise OSError("cannot access pfm_util")

        lines = cmdout.splitlines()

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
        return eeprom_map

    def read_eeprom(self):
        return self.read_eeprom_map()

    def decode_eeprom(self, e):
        print "    Name                   Value    "
        print "--------------------  ---------------"
        for name in self.name_map.keys():
            value = e[name];
            print "%-20s  %s" % (name, value)

    def is_checksum_valid(self, e):
        return (True, 0)

    def serial_number_str(self, e):
        return e["Serial Number"]

    def mgmtaddrstr(self,e):
        return e["Base MAC Address"]

    def set_cache_name(self, name):
        self.cache_name = name

    def check_status(self):
        return 'ok'
