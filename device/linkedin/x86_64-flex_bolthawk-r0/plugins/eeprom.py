#!/usr/bin/env python

#################################################################################
# Linkedin open19 Bolt eeprom plugin						#
# Platform and model specific eeprom subclass, inherits from the base class	#
# and provides the followings:							#
#	- the eeprom format definition						#
# Obtain the proper eeprom information from BMC API				#
#################################################################################
from __future__ import print_function
from __future__ import absolute_import

try:
    import os
    import exceptions
    import subprocess
    import json
    import requests
    import sys
    sys.path.append(os.path.join(os.path.dirname(__file__), '.'))
    from urlheader import UrlList
    from syslog_helper import LogHelper

except ImportError, e:
    raise ImportError (str(e) + "- required module not found")

SYSLOG_IDENTIFIER = "eeprom"


# ========================== Methods for printing ==========================

class board(UrlList):

    def __init__(self, path, start, status, ro):
        self.cache_name = None
        self.cache_update_needed = False
        self.lock_file = None
	super(board, self).__init__()

    def get_respose(self):

	# get respose from url with or without authentication after verification
	data_dict = UrlList().url_respose("eeprom")
	if self.PLATFM_STATE in data_dict.keys():
		platform_info = {k:v for k,v in data_dict[self.PLATFM_STATE][0].items()}
		return platform_info
	else:
		LogHelper(SYSLOG_IDENTIFIER).log_error("{} key is not available".format(self.PLATFM_STATE))
		raise KeyError("{} key is not available".format(self.PLATFM_STATE))

    def read_eeprom(self):
        self.cmd_dict = {}
        self.cmd_dict = self.get_respose()
        return self.cmd_dict

    def decode_eeprom(self, e):
        print("    Name                            Value    ")
        print("----------------------------  ---------------")
        for name in e.keys():
            print( "%-30s  %s" % (name, e[name]))

    def is_checksum_valid(self, e):
	"""TODO: BMC needs to provide this in the rest API result,
	 and the code here will be changed accordingly."""
        return (True, 0)

    def serial_number_str(self, e):
	serial_key = [v for k,v in e.iteritems() if 'system serial number' in k.lower()]
        if serial_key:
		return serial_key[0]
	else:
		LogHelper(SYSLOG_IDENTIFIER).log_error("serial_key is not available in the API")
		raise IndexError("serial_key is not available in the API")

    def mgmtaddrstr(self,e):
	if "BMC MAC" in e.keys():
		return e["BMC MAC"]
	else:
		LogHelper(SYSLOG_IDENTIFIER).log_error("MAC INFO is not available")
		raise KeyError("MAC INFO is not available")

    def set_cache_name(self, name):
        self.cache_name = name

    def check_status(self):
        return 'ok'
