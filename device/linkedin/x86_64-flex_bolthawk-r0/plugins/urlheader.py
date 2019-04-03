#!/usr/bin/env python
#################################################################################
# This is a common URL Header File                                              #
# All the URLs should be declared here                                          #
#                                                                               #
#################################################################################

try:
	import requests
	import json
	import sys
	import os
        from syslog_helper import LogHelper
except ImportError, e:
	raise ImportError (str(e) + "- required module not found")

SYSLOG_IDENTIFIER = "urlheader"

class UrlList(object):

	# constants for this class
	HELPER_FILE = 'helper_data.json'

        def __init__(self):
                self.EEPROM = 'platform'
                self.PLATFM_STATE = "PlatformState"
		self.REST_HOST = ''
		self.REST_PROTO = ''
		self.PROTO_FORMAT = ''
		self.REST_PORT = ''
		self.ROOT_PATH = ''
		self.AUTH_TOKEN =''
		self.FULL_URL_PLATFM = ''

	def read_json_data(self, path):
		dir_path = os.path.dirname(os.path.abspath(__file__))
                helper_file_loc = os.path.join(dir_path, self.HELPER_FILE)
		if os.path.isfile(helper_file_loc):
			with open(helper_file_loc, 'r') as myfile:
				data=myfile.read()
			obj = json.loads(data)

			# get values from json
			self.REST_HOST = str(obj['URL_DATA']['BMC_HOST'])
			self.REST_PROTO = str(obj['URL_DATA']['PROTO_FORMAT'])
			self.PROTO_FORMAT = str(obj['URL_DATA']['PROTO_FORMAT'])
			self.REST_PORT = str(obj['URL_DATA']['REST_PORT'])
			self.ROOT_PATH = str(obj['URL_DATA']['ROOT_PATH'])
			self.AUTH_TOKEN = str(obj['URL_DATA']['AUTH_TOKEN'])

			# create url
			self.REST_URL = self.REST_PROTO + '://' + self.REST_HOST + ':' + self.REST_PORT + self.ROOT_PATH
			if path == "eeprom":
				self.FULL_URL_PLATFM = self.REST_URL + self.EEPROM
				return self.FULL_URL_PLATFM
			else:
				LogHelper(SYSLOG_IDENTIFIER).log_error("{} API is not implemented yet".format(path))
				raise NotImplementedError("{} API is not implemented yet".format(path))
		else:
			LogHelper(SYSLOG_IDENTIFIER).log_error('{} file is NOT FOUND'.format(self.HELPER_FILE))
			raise FileNotFoundError('{} file is NOT FOUND'.format(self.HELPER_FILE))

        def url_respose(self, path):
		url = self.read_json_data(path)
                if self.REST_PROTO == 'http':
                        response_for_url = requests.get(url)
                elif self.REST_PROTO == 'https':
                        response_for_url = requests.get(url, headers={'Authorization': 'Basic %s' %  self.AUTH_TOKEN})
                else:
                        LogHelper(SYSLOG_IDENTIFIER).log_error('Unable to identify rest api {}'.format(url))
                        raise Exception('Unable to identify rest api {}'.format(url))

                if response_for_url.status_code == 200:
                        data_dict = json.loads(response_for_url.text)
                        return data_dict
                else:
                        LogHelper(SYSLOG_IDENTIFIER).log_error('Unable to access provided rest api {}'.format(self.FULL_URL_PLATFM))
                        raise Exception('rest API {} failed with code: {}'.format(self.FULL_URL_PLATFM, response.get('status')))
