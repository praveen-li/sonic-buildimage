#!/usr/bin/python

#################################################################
#								#
# Platform-specific sensor util					#
# Integrate 'sensors' command for SONiC and BMC CPU		#
#################################################################

from __future__ import print_function
from __future__ import absolute_import

try:
	import subprocess
	import sys
	import os
	import json
	from syslog_helper import LogHelper
	from sonic_sensor.sensor_base import SensorBase
except ImportError, e:
    raise ImportError (str(e) + "- required module not found")

SYSLOG_IDENTIFIER = "sensorutil"

# ========================== Methods for printing ==========================

class SensorUtil(SensorBase):

	# constants for this class
        HELPER_FILE = 'helper_data.json'

	def __init__(self):
		SensorBase.__init__(self)
		self.sensor_cmd = 'sensors'

	def get_data_api(self):
		dir_path = os.path.dirname(os.path.abspath(__file__))
		helper_file_loc = os.path.join(dir_path, self.HELPER_FILE)
		if os.path.isfile(helper_file_loc):
			with open(helper_file_loc, 'r') as myfile:
				data=myfile.read()
			obj = json.loads(data)

			# get values from json
			BMC_HOST = str(obj['URL_DATA']['BMC_HOST'])
			USER = str(obj['SSH_DATA']['USER'])
			print("*************** BMC CPU OUTPUT ***********")
			try:
				command = " sudo ssh {}@{} {}".format(USER, BMC_HOST, self.sensor_cmd)
				proc = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True, stderr=subprocess.STDOUT)
				stdout, stderr = proc.communicate()
				proc.wait()
				result = stdout.rstrip('\n')
				print(result)
			except subprocess.CalledProcessError:
				LogHelper(SYSLOG_IDENTIFIER).log_error('Error -> {}'.format(stderr))
				raise CalledProcessError('Error -> {}'.format(stderr))
		else:
			LogHelper(SYSLOG_IDENTIFIER).log_error('{} file is NOT FOUND'.format(self.HELPER_FILE))
			raise FileNotFoundError('{} file is NOT FOUND'.format(self.HELPER_FILE))

		# Get local sonic CPU Information
		self.get_local_data()
