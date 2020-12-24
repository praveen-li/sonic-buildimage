#! /usr/bin/python

'''
This daemon (Flow Capture Daemon: FCD) polls the CONFIG_DB for Innovium Telemetry session
configuration and program the Innovium device for Innovium Telemetry session.
'''
import argparse
import time
import os
import subprocess
import swsssdk
import sys
import atexit
import syslog
import copy
from datetime import datetime
import pdb
import time
from abc import ABCMeta, abstractmethod, abstractproperty
# import enum
import inspect
import re
import traceback
import threading
import __main__


# config knobs
DAEMON_NAME = 'FCD'
FCD_VERSION = '0.5.0'
POLL_INTERVAL = 5000
SLOW_START_INTERVAL = 0
DEBUG = False
DRY_RUN = False
TRACE_FILE = False
ALL_PORTS = True


# CONFIG SCHEMA for  SWITCH_ID

'''
{
    "IVM_SWITCH_ID": {
        "0x1234": {}
        }
}

'''
CONFIG_ROOT_SWITCH = 'IVM_SWITCH_ID'


# CONFIG SCHEMA for BDC

'''
{
    "IVM_BDC_SESSION": {
        "session": {
            "dip": "100.0.0.61", #mandatory
            "sip": "10.1.0.32", #mandatory
            "ttl": "254",
            "dscp" : "5",
            "tc" : "0",
            "df" : "0",
            "sampler_mode": "1",
            "capture_rate":"12000",
            "cos": "4-6"  #mandatory
        }
    }
}

'''

# CONFIG SCHEMA for HDC

'''
{
    "IVM_HDC_SESSION": {
        "session": {
            "dip": "100.100.100.10",
            "sip": "10.1.0.31",
            "ttl": "254",
            "dscp" : "6",
            "tc" : "0",
            "df" : "0",
            "sampler_mode": "2",
            "capture_rate":"12000",
            "cos": "4-6",
            "delay_threshold" : "1000",
            "ports" : ["Ethernet0,Ethernet4,Ethernet251"]
        }
    }
}

'''


CONFIG_ROOT_BDC = 'IVM_BDC_SESSION'
CONFIG_ROOT_HDC = 'IVM_HDC_SESSION'
CONFIG_ROOT_SESSION_COLLECTOR_DST_IP = 'dip'
CONFIG_ROOT_SESSION_SRC_IP = 'sip'
CONFIG_ROOT_SESSION_TTL = 'ttl'
CONFIG_ROOT_SESSION_DSCP = 'dscp'
CONFIG_ROOT_SESSION_TC = 'tc'
CONFIG_ROOT_SESSION_SAMPLER_MODE = 'sampler_mode'
CONFIG_ROOT_SESSION_CAPTURE_RATE = 'capture_rate'
CONFIG_ROOT_SESSION_DF = 'df'
CONFIG_ROOT_SESSION_AVG_PACKET_RATE = 'max_packet_rate'
CONFIG_ROOT_SESSION_MAX_PACKETS_PER_BURST = 'max_packets_per_burst'
CONFIG_ROOT_SESSION_QUEUES = 'cos'
CONFIG_ROOT_PORTS = 'ports'
CONFIG_ROOT_DELAY_THRESHOLD = 'delay_threshold'
CONFIG_ROOT_CPU_QUEUE = 'cpu_queue'
CONFIG_ROOT_SESSION_CPU_QUEUE_RATE = 'cpu_queue_rate'
CONFIG_ROOT_SESSION_CPU_QUEUE_BURST_SIZE = 'cpu_queue_burst_size'
ROUTE_CMD_TEMPLATE = "ip route list match  \"{dst_ip}\""


# Rationale for deciding whether a param is mandatory is to simplify user
# configuration.
BASE_MANDATORY_CONFIGS = [
    CONFIG_ROOT_SESSION_COLLECTOR_DST_IP,
    CONFIG_ROOT_SESSION_SRC_IP,
    CONFIG_ROOT_SESSION_QUEUES]

BDC_MANDATORY_CONFIGS = []
HDC_MANDATORY_CONFIGS = [CONFIG_ROOT_PORTS, CONFIG_ROOT_DELAY_THRESHOLD]


BASE_DEFAULT_VALUES = {
    CONFIG_ROOT_SESSION_TTL: '255',
    CONFIG_ROOT_SESSION_DSCP: '0',
    CONFIG_ROOT_SESSION_TC: '0',
    CONFIG_ROOT_SESSION_DF: '0',
    CONFIG_ROOT_SESSION_SAMPLER_MODE: '2',
}

HDC_DEFAULT_VALUES = {
    # CONFIG_ROOT_DELAY_THRESHOLD = '2000'
}

BDC_DEFAULT_VALUES = {
}


BASE_SONIC_TO_IFCS_TRANSLATION = {
    CONFIG_ROOT_SESSION_COLLECTOR_DST_IP: 'dip',
    CONFIG_ROOT_SESSION_SRC_IP: 'sip',
    CONFIG_ROOT_SESSION_TTL: 'ttl',
    CONFIG_ROOT_SESSION_DSCP: 'dscp',
    CONFIG_ROOT_SESSION_TC: 'tc',
    CONFIG_ROOT_SESSION_SAMPLER_MODE: 'sampler_mode',
    CONFIG_ROOT_SESSION_CAPTURE_RATE: 'capture_rate',
    CONFIG_ROOT_SESSION_DF: 'df',
    CONFIG_ROOT_SESSION_AVG_PACKET_RATE: 'avg_packet_rate',
    CONFIG_ROOT_SESSION_MAX_PACKETS_PER_BURST: 'max_packets_per_burst',
    CONFIG_ROOT_SESSION_QUEUES: 'queue',
    CONFIG_ROOT_SESSION_CPU_QUEUE_RATE: 'cpu_rate',
    CONFIG_ROOT_SESSION_CPU_QUEUE_BURST_SIZE: 'cpu_burst_size',
}

BDC_SONIC_TO_IFCS_TRANSLATION = {
    CONFIG_ROOT_CPU_QUEUE: 'dev_port 0 -cpu_queue',
}
BDC_SONIC_TO_IFCS_TRANSLATION.update(BASE_SONIC_TO_IFCS_TRANSLATION)

HDC_SONIC_TO_IFCS_TRANSLATION = {
    CONFIG_ROOT_DELAY_THRESHOLD: 'delay_threshold',
    CONFIG_ROOT_CPU_QUEUE: 'devport 0 -cpu_queue',
}
HDC_SONIC_TO_IFCS_TRANSLATION.update(BASE_SONIC_TO_IFCS_TRANSLATION)


SAMPLER_MODE_1_DEFAULT_VALUES = {
    CONFIG_ROOT_SESSION_CAPTURE_RATE: '10000',
}

SAMPLER_MODE_2_DEFAULT_VALUES = {
    CONFIG_ROOT_SESSION_AVG_PACKET_RATE: '8192',
    CONFIG_ROOT_SESSION_MAX_PACKETS_PER_BURST: '256',
}

# Defaults if telemetry packets are to be sent to local collector (CPU_QUEUE)
CPU_QUEUE_DEFAULT_VALUES = {
    CONFIG_ROOT_SESSION_CPU_QUEUE_RATE: '60000',
    CONFIG_ROOT_SESSION_CPU_QUEUE_BURST_SIZE: '512',
}

def param_check_ip(ip_str):
    ip_regex = '''^(25[0-5]|2[0-4][0-9]|[0-1]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[0-1]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[0-1]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[0-1]?[0-9][0-9]?)'''
    if(re.search(ip_regex, ip_str)):
        return True
    return False


def param_check_queues(queue_list):
    qs = re.split("-|,", queue_list)
    return all([int(q) >= 0 and int(q) <= 7 for q in qs])


def param_check_max_packets_per_burst(burst_size_str):
    burst_size = int(burst_size_str)
    if burst_size < 64 or burst_size > 16384:
        return False
    if burst_size % 64:
        return False
    return True

# Function to embed IP address in MAC address
def get_reserved_mac_using_ip(ip_addr):
    ip = ip_addr.split('.')
    ip = [hex(int(x)).split('x')[-1] for x in ip]
    mac = "00:00:" + ip[0] + ":" + ip[1] + ":" + ip[2] + ":" + ip[3]
    return mac

BASE_PARAM_CHECKS = {
    CONFIG_ROOT_SESSION_COLLECTOR_DST_IP: param_check_ip,
    CONFIG_ROOT_SESSION_SRC_IP: param_check_ip,
    CONFIG_ROOT_SESSION_TTL: (lambda ttl: 0 < int(ttl) < 256),
    CONFIG_ROOT_SESSION_DSCP: (lambda dscp: 0 <= int(dscp) < 64),
    CONFIG_ROOT_SESSION_TC: (lambda tc: 0 <= int(tc) <= 15),
    CONFIG_ROOT_SESSION_SAMPLER_MODE: (lambda mode: mode in ['0', '1', '2']),
    CONFIG_ROOT_SESSION_CAPTURE_RATE: (lambda rate: 10 <= int(rate) <= 16777215),
    CONFIG_ROOT_SESSION_DF: (lambda df: df in ['0', '1']),
    CONFIG_ROOT_SESSION_AVG_PACKET_RATE: (lambda rate: 122 <= int(rate) <= 100000),
    CONFIG_ROOT_SESSION_MAX_PACKETS_PER_BURST: param_check_max_packets_per_burst,
    CONFIG_ROOT_SESSION_QUEUES: param_check_queues,
    CONFIG_ROOT_CPU_QUEUE: (lambda cpu_q: 0 <= int(cpu_q) <= 47),
    CONFIG_ROOT_SESSION_CPU_QUEUE_RATE: (lambda cpu_q_rate: 122 <= int(cpu_q_rate) < 60000000),
    CONFIG_ROOT_SESSION_CPU_QUEUE_BURST_SIZE: (lambda cpu_q_burst: 1 <= int(cpu_q_burst) <= 1000000000),
}

HDC_PARAM_CHECKS = {
    CONFIG_ROOT_SESSION_SAMPLER_MODE: (lambda mode: mode in ['1', '2']),
    CONFIG_ROOT_DELAY_THRESHOLD: (lambda dt: 100 <= int(dt) <= 16000000),
}

BDC_PARAM_CHECKS = {}


# globals

LOCAL_LOG = None
VERBOSE = None


# class logLevel(enum.Enum):
class logLevel():
    info = syslog.LOG_INFO
    err = syslog.LOG_ERR
    trace = 'TRACE'
    trace_file = 'TRACE_FILE'
    prin = "PRINT"


class Operation():
    NONE = 0
    CREATE = 1
    DELETE = 2
    UPDATE = 3
    UPDATE_INCREMENTAL = 4


class State():
    INIT = 0
    CONFIGURED = 1
    NOT_CONFIGURED = 2


def _oid_val(oid_str):
    '''
    "oid:0x5000000000809" return "0x5000000000809"
    '''
    return oid_str.split(':')[1]


def expand_hyphenated_list(range_str):
    r = []
    for i in range_str.split(','):
        if '-' not in i:
            r.append(int(i))
        else:
            l, h = map(int, i.split('-'))
            r += range(l, h + 1)
    return r


class Telemetrycfg(object):
    '''
    Abstract Base class for Innovium Proprietary Telemetry configuration.
    Interfaces with SONiC databases
    '''
    __metaclass__ = ABCMeta

    def __init__(self):

        self.config_db = swsssdk.ConfigDBConnector()
        self.config_db.connect()

        self.asic_db = swsssdk.SonicV2Connector(host='127.0.0.1')
        self.asic_db.connect(self.asic_db.ASIC_DB)

        self.counters_db = swsssdk.SonicV2Connector(host='127.0.0.1')
        self.counters_db.connect(self.counters_db.COUNTERS_DB)
        # connect APP DB for clear notifications
        self.app_db = swsssdk.SonicV2Connector(host='127.0.0.1')
        self.app_db.connect(self.app_db.APPL_DB)

        #self.session_info = None
        #self.prev_session_info = None
        self.operation = Operation.NONE
        self.state = State.INIT
        '''
        # PARAM Dict struct:
        {
            'CONFIG' : Entire config_db table,
            'GLOBAL' : global key values selected from CONFIG,
            'PORTS' : [(port_i: delay_th),(port_j: delay_th)...],
            }
        '''
        self.PROGRAMMED_CONFIG = {}  # configuration programmed in the device
        self.DESIRED_CONFIG = {}  # user config; i.e. configuration in CONFIG_DB
        self.selected_prefix = ''
        self.selected_nexthop = ''
        self.mandatory_params = []
        self.default_values = {}
        self.param_checks = {}
        self.mandatory_params.extend(BASE_MANDATORY_CONFIGS)
        self.default_values.update(BASE_DEFAULT_VALUES)
        self.param_checks.update(BASE_PARAM_CHECKS)

    @abstractmethod
    def telemetry_type(self):
        pass

    def set_selected_prefix(self, prefix):
        self.selected_prefix = prefix

    def get_selected_prefix(self):
        return self.selected_prefix

    def set_selected_nexthop(self, nexthop):
        self.selected_nexthop = nexthop

    def get_selected_nexthop(self):
        return self.selected_nexthop

    def check_config_present(self):
        return self.DESIRED_CONFIG.get('GLOBAL')

    def check_parse(func):
        def decorated(self):
            if not self.DESIRED_CONFIG['GLOBAL']:
                FCD.log(logLevel.err, "parse not called")
                sys.exit(-1)
            return func(self)
        return decorated

    @check_parse
    def get_dst_ip(self):
        return self.DESIRED_CONFIG['GLOBAL'][CONFIG_ROOT_SESSION_COLLECTOR_DST_IP]

    @check_parse
    def get_src_ip(self):
        return self.DESIRED_CONFIG['GLOBAL'][CONFIG_ROOT_SESSION_SRC_IP]

    @check_parse
    def get_ttl(self):
        return self.DESIRED_CONFIG['GLOBAL'][CONFIG_ROOT_SESSION_TTL]

    @check_parse
    def get_dscp(self):
        return self.DESIRED_CONFIG['GLOBAL'][CONFIG_ROOT_SESSION_DSCP]

    @check_parse
    def get_cpu_queue(self):
        return self.DESIRED_CONFIG['GLOBAL'].get(CONFIG_ROOT_CPU_QUEUE, None)

    def get_cpu_queue_programmed(self):
        return self.PROGRAMMED_CONFIG['GLOBAL'].get(CONFIG_ROOT_CPU_QUEUE, None)

    def load_config(self, target):
        session_keys = self.config_db.get_keys(self.config_root)
        session_info = self.config_db.get_entry(
            self.config_root, session_keys[0])
        target['CONFIG'] = session_info
        target['GLOBAL'] = session_info
        target['PORTS'] = {}

    def verify_config(self):
        error = None
        for mandatory_key in self.mandatory_params:
            value = self.DESIRED_CONFIG['CONFIG'].get(mandatory_key, None)
            if not value:
                err_str = "Missing mandatory param:" + mandatory_key
                FCD.log(logLevel.err, err_str)
                raise Exception(err_str)

    def add_defaults(self, default_dict, overwrite):
        '''
        if overwrite:
            session_keys = self.config_db.get_keys(self.config_root)
            self.session_info = self.config_db.get_entry(
                self.config_root, session_keys[0])
        '''
        for key in default_dict.keys():
            self.DESIRED_CONFIG['GLOBAL'][key] = self.DESIRED_CONFIG['GLOBAL'].get(
                key, default_dict.get(key))

    def add_conditional_defaults(self):
        capture_mode = self.DESIRED_CONFIG['GLOBAL'][CONFIG_ROOT_SESSION_SAMPLER_MODE]
        if capture_mode == '1':
            self.add_defaults(SAMPLER_MODE_1_DEFAULT_VALUES, False)
        elif capture_mode == '2':
            self.add_defaults(SAMPLER_MODE_2_DEFAULT_VALUES, False)
        if (self.DESIRED_CONFIG['GLOBAL'].get(CONFIG_ROOT_CPU_QUEUE) is not None):
            self.add_defaults(CPU_QUEUE_DEFAULT_VALUES, False)

    def remove_invalid_params(self, inv_param_dict):
        for key in inv_param_dict.keys():
            if (self.DESIRED_CONFIG['GLOBAL'].pop(key, None)):
                pass

    def prune_notapplicable_params(self):
        capture_mode = self.DESIRED_CONFIG['GLOBAL'][CONFIG_ROOT_SESSION_SAMPLER_MODE]
        if capture_mode == '0':
            self.remove_invalid_params(SAMPLER_MODE_1_DEFAULT_VALUES)
            self.remove_invalid_params(SAMPLER_MODE_2_DEFAULT_VALUES)
        elif capture_mode == '1':
            self.remove_invalid_params(SAMPLER_MODE_2_DEFAULT_VALUES)
        elif capture_mode == '2':
            self.remove_invalid_params(SAMPLER_MODE_1_DEFAULT_VALUES)
        if (self.DESIRED_CONFIG['GLOBAL'].get(CONFIG_ROOT_CPU_QUEUE) is None):
            self.remove_invalid_params(CPU_QUEUE_DEFAULT_VALUES)

    def check_no_params(self, inv_param_dict):
        for key in inv_param_dict.keys():
            if (self.DESIRED_CONFIG['GLOBAL'].get(key, None)):
                err_str = "Param={} should not be specified for this sampler_mode".format(
                    key)
                FCD.log(logLevel.err, err_str)
                raise Exception(err_str)

    def check_conditional_invalid_params(self):
        capture_mode = self.DESIRED_CONFIG['GLOBAL'][CONFIG_ROOT_SESSION_SAMPLER_MODE]
        if capture_mode == '0':
            self.check_no_params(SAMPLER_MODE_1_DEFAULT_VALUES)
            self.check_no_params(SAMPLER_MODE_2_DEFAULT_VALUES)
            return
        if capture_mode == '1':
            self.check_no_params(SAMPLER_MODE_2_DEFAULT_VALUES)
            return
        if capture_mode == '2':
            self.check_no_params(SAMPLER_MODE_1_DEFAULT_VALUES)
            return

    def check_param_values(self):
        try:
            for key in set(
                    self.DESIRED_CONFIG['GLOBAL'].keys() +
                    self.DESIRED_CONFIG['CONFIG'].keys()):
                value = self.DESIRED_CONFIG['GLOBAL'].get(key, None)
                if not value:
                    value = self.DESIRED_CONFIG['CONFIG'].get(key, None)
                check_fn = self.param_checks.get(key, lambda x: True)
                if not check_fn(value):
                    err_str = "Invalid Param {}:{}".format(
                        key, value)
                    FCD.log(logLevel.err, err_str)
                    raise Exception(err_str)
            return (True, None)
        except Exception as e:
            try:
                FCD.log(
                    logLevel.trace,
                    "Parameter:" +
                    e.message)
            except BaseException:
                pass
            return (False, e.message)

    def parse_config(self):
        self.operation = Operation.NONE
        session_keys = self.config_db.get_keys(self.config_root)
        if (len(session_keys) == 0):
            err_str = self.config_root + ": No session configured;"
            FCD.log(logLevel.trace, err_str)
            if (self.state == State.CONFIGURED):
                self.operation = Operation.DELETE
            else:
                self.operation = Operation.NONE
            return

        if (len(session_keys) > 1):
            err_str = self.config_root + \
                ": only one session supported; Configured= " + \
                ' '.join(session_keys)
            FCD.log(logLevel.err, err_str)
            self.operation = Operation.NONE
            raise Exception(err_str)

        #prev_session_info = self.DESIRED_CONFIG['GLOBAL']
        self.load_config(self.DESIRED_CONFIG)
        self.verify_config()
        #self.prev_session_info = prev_session_info
        self.add_defaults(self.default_values, True)
        self.add_conditional_defaults()
        self.prune_notapplicable_params()
        self.check_conditional_invalid_params()
        rc, err = self.check_param_values()
        if not rc:
            err_str = "Invalid Params: " + err
            FCD.log(logLevel.err, err_str)
            self.operation = Operation.NONE
            raise Exception(err_str)

        if (not self.DESIRED_CONFIG['GLOBAL']):
            self.operation = Operation.NONE
            return

        if (self.state != State.CONFIGURED):  # new configuration
            FCD.log(logLevel.trace, "Apply config :" +
                    str(self.DESIRED_CONFIG['GLOBAL'].items()))
            self.operation = Operation.CREATE
            return

        # existing configuration is modified : global update
        current_config = copy.deepcopy(
            self.PROGRAMMED_CONFIG.get('GLOBAL', {}))
        for field in ['dev_port', 'devport', 'smac', 'dmac']:
            current_config.pop(field, None)

        if (current_config and sorted(current_config.items()) !=
                sorted(self.DESIRED_CONFIG['GLOBAL'].items())):
            removed = {item[0]: item[1] for item in current_config.items(
            ) if self.DESIRED_CONFIG['GLOBAL'].get(item[0], {}) != item[1]}
            added = {item[0]: item[1] for item in self.DESIRED_CONFIG['GLOBAL'].items(
            ) if current_config.get(item[0], {}) != item[1]}
            FCD.log(logLevel.info, "Removed = {}".format(str(removed)))
            FCD.log(logLevel.info, "Added = {}".format(str(added)))
            FCD.log(logLevel.info, "Config changed: Programmed=" +
                    str(current_config.items()) +
                    " Configured=" +
                    str(self.DESIRED_CONFIG['GLOBAL'].items()))
            self.operation = Operation.UPDATE
            return

        # No-OP
        self.operation = Operation.NONE
        return

    '''
    Route string examples:
    default proto 186 src 10.1.0.32 metric 20
    10.0.0.0/31 dev Ethernet0 proto kernel scope link src 10.0.0.0
    10.60.0.0/16 dev eth0 proto kernel scope link src 10.60.4.188
    100.1.0.1 via 10.0.0.1 dev Ethernet0 proto 186 src 10.1.0.32 metric 20
    192.168.0.1 proto 186 src 10.1.0.32 metric 20
    192.168.199.241 proto 186 src 10.1.0.32 metric 20
    200.0.1.0/26 proto 186 src 10.1.0.32 metric 20
    240.127.1.0/24 dev docker0 proto kernel scope link src 240.127.1.1 linkdown
    '''

    def parse_route(self, route_output):
        routes = re.findall(
            r"(^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}/\d{1,3}(?:\b))",
            route_output,
            re.MULTILINE)
        exact_route = re.findall(
            r"(^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3} )",
            route_output,
            re.MULTILINE)
        default_route = re.findall(r"^default ", route_output)
        if exact_route:
            return exact_route[0]
        if not routes:
            return "0.0.0.0/0"
        # pick the longest
        longest = 0
        lpm_route = ''
        for route in routes:
            length = int(re.match(r'^.*/(\d{1,3})', route).group(1))
            if length > longest:
                lpm_route = route
                longest = length
        return lpm_route

    '''
    TBD: We should use FRR socket to get the nexthop of the collector ip,
    so it will be consistent with hardware forwarding action
    '''
    def get_route_for_ip(self, ip, vrf=None):
        route_cmd = ROUTE_CMD_TEMPLATE.format(dst_ip=ip)
        route_output = os.popen(route_cmd).read()
        FCD.log(logLevel.trace, route_output)
        if route_output == '':
            err_str = 'No matching route for {}'.format(ip)
            raise Exception(err_str)
        route = self.parse_route(route_output)
        FCD.log(logLevel.trace, "\"{date}\": route for {ip} is {route}  \n".format(
            date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"), ip=ip, route=route))
        return route

    def get_default_vr_oid(self):
        '''"ASIC_STATE:SAI_OBJECT_TYPE_VIRTUAL_ROUTER"'''
        keys = self.asic_db.keys(
            self.asic_db.ASIC_DB,
            'ASIC_STATE:SAI_OBJECT_TYPE_VIRTUAL_ROUTER:oid:*')
        if (not keys):
            raise Exception("VR not found")

        if (len(keys) != 1):
            FCD.log(
                logLevel.err,
                "Need one virtual router: got=> " +
                ','.join(keys))
            raise Exception("failed to get default VR")

        vr_oid_match = re.match(
            r'ASIC_STATE:SAI_OBJECT_TYPE_VIRTUAL_ROUTER:oid:(.*)\b', keys[0])
        return vr_oid_match.group(1)

    def get_default_switch_oid(self):
        '''"ASIC_STATE:SAI_OBJECT_TYPE_SWITCH:oid:0x21000000000000"'''
        keys = self.asic_db.keys(self.asic_db.ASIC_DB,
                                 'ASIC_STATE:SAI_OBJECT_TYPE_SWITCH:oid:*')
        if (len(keys) != 1):
            FCD.log(logLevel.err, "Need one switch: got=> " + ','.join(keys))
            raise Exception("failed to get switch-id")

        switch_oid_match = re.match(
            r'ASIC_STATE:SAI_OBJECT_TYPE_SWITCH:oid:(.*)\b', keys[0])
        return switch_oid_match.group(1)

    def create_route_key(self, route_prefix):
        ''' given a route_prefix say "193.1.128.128/25", returns the key as
            ASIC_STATE:SAI_OBJECT_TYPE_ROUTE_ENTRY:{\"dest\":\"193.1.128.128/25\",\"switch_id\":\"oid:0x21000000000000\",\"vr\":\"oid:0x300000000048c\"}"
        '''
        key_template = 'ASIC_STATE:SAI_OBJECT_TYPE_ROUTE_ENTRY:{{"dest":"{prefix}","switch_id":"oid:{switch_oid}","vr":"oid:{vr_oid}"}}'
        return key_template.format(
            prefix=route_prefix,
            switch_oid=self.get_default_switch_oid(),
            vr_oid=self.get_default_vr_oid())

    def create_nh_group_key(self, nh_oid):
        ''' given a  nh oid such as '0x5000000000809' returns
        "ASIC_STATE:SAI_OBJECT_TYPE_NEXT_HOP_GROUP:oid:0x500000000080a"
        '''
        key_template = "ASIC_STATE:SAI_OBJECT_TYPE_NEXT_HOP_GROUP:oid:{nh_oid}"
        return key_template.format(nh_oid=nh_oid)

    def create_nh_key(self, nh_oid):
        ''' given a  nh oid such as '0x5000000000809' returns
        "ASIC_STATE:SAI_OBJECT_TYPE_NEXT_HOP:oid:0x5000000000809"
        '''
        key_template = 'ASIC_STATE:SAI_OBJECT_TYPE_NEXT_HOP:oid:{nh_oid}'
        return key_template.format(nh_oid=nh_oid)

    def create_rif_key(self, rif_oid):
        ''' given a  rif oid such as '0x5000000000809' returns
        "ASIC_STATE:SAI_OBJECT_TYPE_ROUTER_INTERFACE:oid:0x5000000000809"
        '''
        key_template = 'ASIC_STATE:SAI_OBJECT_TYPE_ROUTER_INTERFACE:oid:{rif_oid}'
        return key_template.format(rif_oid=rif_oid)

    def create_port_key(self, port_oid):
        key_template = "ASIC_STATE:SAI_OBJECT_TYPE_PORT:oid:{port_oid}"
        return key_template.format(port_oid=port_oid)

    def create_lag_key(self, lag_oid):
        key_template = "ASIC_STATE:SAI_OBJECT_TYPE_LAG:oid:{lag_oid}"
        return key_template.format(lag_oid=lag_oid)

    def get_port_from_lag(self, lag_group_oid):
        ''' given an lag_group_oid, select one member lag and return oid :

            If the given lag_group_oid is a port, just return the port.

            Walk through all lag_group_members("ASIC_STATE:SAI_OBJECT_TYPE_LAG_MEMBER:oid:*'
            and filter based on its
            "SAI_LAG_MEMBER_ATTR_LAG_ID"
            TBD: do we need to skip down ports? SONiC eventually prunes the members that are down..
            TBD: optmize this!!

        '''

        # if it is already a port,just return it.
        keys = self.asic_db.keys(self.asic_db.ASIC_DB,
                                 self.create_port_key(lag_group_oid))
        if keys:
            return lag_group_oid

        keys = self.asic_db.keys(self.asic_db.ASIC_DB,
                                 "ASIC_STATE:SAI_OBJECT_TYPE_LAG_MEMBER:oid:*")
        for key in keys:
            value = self.asic_db.get_all(self.asic_db.ASIC_DB, key)
            lagm_grp_oid = value["SAI_LAG_MEMBER_ATTR_LAG_ID"]
            if _oid_val(lagm_grp_oid) == lag_group_oid:
                return _oid_val(value["SAI_LAG_MEMBER_ATTR_PORT_ID"])

        FCD.log(
            logLevel.err,
            "Could not find lag Group member for group" +
            lag_group_oid)
        raise Exception(
            "Could not find lag Group member for group" + lag_group_oid)

    def get_nh_from_nh_group(self, nh_group_oid):
        ''' given an nh_group_oid, select one member nh and return oid :

            Walk through all nh_group_members("ASIC_STATE:SAI_OBJECT_TYPE_NEXT_HOP_GROUP_MEMBER:oid: )
            and filter based on its
            "SAI_NEXT_HOP_GROUP_MEMBER_ATTR_NEXT_HOP_GROUP_ID"
            TBD: optmize this!!

        '''
        keys = self.asic_db.keys(
            self.asic_db.ASIC_DB,
            "ASIC_STATE:SAI_OBJECT_TYPE_NEXT_HOP_GROUP_MEMBER:oid*")
        for key in keys:
            value = self.asic_db.get_all(self.asic_db.ASIC_DB, key)
            nhm_grp_oid = value['SAI_NEXT_HOP_GROUP_MEMBER_ATTR_NEXT_HOP_GROUP_ID']
            if _oid_val(nhm_grp_oid) == nh_group_oid:
                return _oid_val(
                    value["SAI_NEXT_HOP_GROUP_MEMBER_ATTR_NEXT_HOP_ID"])

        FCD.log(
            logLevel.err,
            "Could not find NH Group member for group" +
            nh_group_oid)
        raise Exception(
            "Could not find NH Group member for group" + nh_group_oid)

    def get_nh_rif(self, nh_oid):
        value = self.asic_db.get_all(
            self.asic_db.ASIC_DB, self.create_nh_key(nh_oid))
        return _oid_val(value["SAI_NEXT_HOP_ATTR_ROUTER_INTERFACE_ID"])

    def get_nh_ip(self, nh_oid):
        value = self.asic_db.get_all(
            self.asic_db.ASIC_DB, self.create_nh_key(nh_oid))
        return _oid_val(value["SAI_NEXT_HOP_ATTR_ROUTER_INTERFACE_ID"])

    def get_route_rif_and_ip(self, route_prefix, dst_ip):
        value = self.asic_db.get_all(
            self.asic_db.ASIC_DB, self.create_route_key(route_prefix))

        if not value:
            err_str = "Route={} for IP={} not yet in ASIC DB".format(
                route_prefix, dst_ip)
            FCD.log(logLevel.trace, err_str)
            raise Exception(err_str)

        if not value.get('SAI_ROUTE_ENTRY_ATTR_NEXT_HOP_ID', None):
            err_str = "Route={} for IP={} does not have NH, {}".format(
                route_prefix, dst_ip, str(value))
            FCD.log(logLevel.trace, err_str)
            raise Exception(err_str)

        nh_oid = _oid_val(value['SAI_ROUTE_ENTRY_ATTR_NEXT_HOP_ID'])
        # if it is  ip2me, i.e. this is port, then abort
        keys = self.asic_db.keys(self.asic_db.ASIC_DB,
                                 self.create_port_key(nh_oid))
        if keys:
            err_str = "Route is IP2ME Route={}, Port={}; not supported".format(
                route_prefix, nh_oid)
            FCD.log(logLevel.trace, err_str)
            raise Exception(err_str)

        # if it is directly connected, then return RIF
        keys = self.asic_db.keys(self.asic_db.ASIC_DB,
                                 self.create_rif_key(nh_oid))
        if keys:
            FCD.log(
                logLevel.trace,
                "Directly connected: rif={}, rt={},neighbor={}".format(
                    nh_oid,
                    route_prefix,
                    dst_ip))
            # this is the RIF OID; route prefix is the neighbor IP
            return (nh_oid, dst_ip)

        #  if this oid is SAI_OBJECT_TYPE_NEXT_HOP_GROUP
        keys = self.asic_db.keys(self.asic_db.ASIC_DB,
                                 self.create_nh_group_key(nh_oid))
        if keys:
            FCD.log(logLevel.info, "ECMP route={}".format(route_prefix))
            nh_oid = self.get_nh_from_nh_group(
                nh_oid)  # nh_oid passed is a nh_group

        value = self.asic_db.get_all(
            self.asic_db.ASIC_DB, self.create_nh_key(nh_oid))

        if (not value):
            err_str = 'nh={} for rt={} not found in ASIC DB'.format(
                nh_oid, route_prefix)
            FCD.log(logLevel.trace, err_str)
            raise Exception(err_str)

        if (not value.get("SAI_NEXT_HOP_ATTR_IP", None)):
            err_str = 'nh={}, has no IP. NH values={}'.format(
                nh_oid, str(value))
            FCD.log(logLevel.trace, err_str)
            raise Exception(err_str)

        ip = value["SAI_NEXT_HOP_ATTR_IP"]
        FCD.log(
            logLevel.trace,
            "route={} via neighbor {}".format(
                route_prefix,
                ip))
        return (self.get_nh_rif(nh_oid), ip)

    def get_rif_smac(self, rif_oid):
        value = self.asic_db.get_all(
            self.asic_db.ASIC_DB, self.create_rif_key(rif_oid))
        return value["SAI_ROUTER_INTERFACE_ATTR_SRC_MAC_ADDRESS"]

    def get_neighbor_dmac(self, rif_oid, ip):
        key_template = 'ASIC_STATE:SAI_OBJECT_TYPE_NEIGHBOR_ENTRY:{{"ip":"{ip}","rif":"oid:{rif_oid}","switch_id":"oid:{switch_oid}"}}'
        key = key_template.format(
            ip=ip, rif_oid=rif_oid, switch_oid=self.get_default_switch_oid())
        value = self.asic_db.get_all(self.asic_db.ASIC_DB, key)
        return value["SAI_NEIGHBOR_ENTRY_ATTR_DST_MAC_ADDRESS"]

    def get_rif_port(self, rif_oid, dmac):
        '''
        Find the rif type:

        /** Port or LAG Router Interface Type */
        SAI_ROUTER_INTERFACE_TYPE_PORT,
            >> resolve if LAG

        /** VLAN Router Interface Type */
        SAI_ROUTER_INTERFACE_TYPE_VLAN,
            >> choose port from FDB; resolve port if it is Lag.

         The below are unsupported.
        SAI_ROUTER_INTERFACE_TYPE_LOOPBACK,
        SAI_ROUTER_INTERFACE_TYPE_MPLS_ROUTER,
        SAI_ROUTER_INTERFACE_TYPE_SUB_PORT,
        SAI_ROUTER_INTERFACE_TYPE_BRIDGE,
        SAI_ROUTER_INTERFACE_TYPE_QINQ_PORT,
            '''
        value = self.asic_db.get_all(
            self.asic_db.ASIC_DB, self.create_rif_key(rif_oid))
        rif_type = value["SAI_ROUTER_INTERFACE_ATTR_TYPE"]

        if rif_type not in [
            'SAI_ROUTER_INTERFACE_TYPE_PORT',
                'SAI_ROUTER_INTERFACE_TYPE_VLAN']:
            err_str = "RIF OID={}, type={} not supported".format(
                rif_oid, rif_type)
            FCD.log(logLevel.trace, err_str)
            raise Exception(err_str)

        if rif_type == 'SAI_ROUTER_INTERFACE_TYPE_PORT':
            return _oid_val(value["SAI_ROUTER_INTERFACE_ATTR_PORT_ID"])

        if rif_type == 'SAI_ROUTER_INTERFACE_TYPE_VLAN':
            err_str = "RIF OID={}, type={} NOT YET IMPLEMENTED".format(
                rif_oid, rif_type)
            FCD.log(logLevel.trace, err_str)
            raise Exception(err_str)
            pass

        err_str = "unknown case: None #should not reach here; rif={}, type={}, dmac={}".format(
            rif_oid, rif_type, dmac)
        FCD.log(logLevel.trace, err_str)
        raise Exception(err_str)

    def get_devport_from_port_vid(self, port_vid_oid):
        '''
         convert port VID to RID.
          hget  "VIDTORID" 'oid:0x1000000000258' "oid:0x1b00000d3e20000d"
         Extract the lower bits to get devport.
         SAI port oid:0x1b00000d3e20000d
           sysport = 0x3e20000d
           devport = 0x0d
        '''

        port_rid = _oid_val(self.asic_db.get_all(
            self.asic_db.ASIC_DB, "VIDTORID")["oid:" + port_vid_oid])
        # return hex(int(port_rid, 16) & 0xFF)
        return (int(port_rid, 16) & 0xFF)

    def get_devport_from_ifname(self, ifname):
        '''
         convert interface name (eg Ethernet80) to SDK devport id.
         127.0.0.1:6379[4]> hget "PORT|Ethernet80" "lanes"
         "169,170,171,172"
         The first lane is the devport number. In the above case it is 169.
        '''
        return self.config_db.get_entry("PORT", ifname)['lanes'].split(',')[0]

    def get_front_panel_ifnames(self):
        '''
         get all front-panel interfaces
         returns a list of interface names
         eg: [u'Ethernet184', u'Ethernet76', u'Ethernet60']
        '''
        return self.config_db.get_keys("PORT")

    def parse_switch_config(self):
        session_keys = self.config_db.get_keys(CONFIG_ROOT_SWITCH)
        if (not session_keys or not len(session_keys)):
            return

        switch_id_str = session_keys[0]
        base = 16 if switch_id_str.startswith('0x') else 10
        switch_id = int(switch_id_str, base)
        if switch_id > 0xFFFF:
            FCD.log(logLevel.err, "Invalid value: {} for {}: max is 0xFFFF",
                    switch_id, CONFIG_ROOT_SWITCH)
            return  # ignore and continue
        cmd = 'ifcs set node switch_id  {}'.format(switch_id)

        try:
            rc, cmd_output = InnoShellCmds.exec_ivm_command(cmd)
        except BaseException:
            try:
                FCD.log(
                    logLevel.err,
                    "Setting switch_id failed;cmd={}; output={}".format(
                        cmd,
                        cmd_output))
            except BaseException:
                pass
        return


class BDC_Telemetrycfg(Telemetrycfg):

    def __init__(self):
        Telemetrycfg.__init__(self)
        self.config_root = CONFIG_ROOT_BDC
        self.param_checks.update(BDC_PARAM_CHECKS)
        self.mandatory_params.extend(BDC_MANDATORY_CONFIGS)
        self.default_values.update(BDC_DEFAULT_VALUES)

    def telemetry_type(self):
        return 'BDC'


class HDC_Telemetrycfg(Telemetrycfg):

    def __init__(self):
        Telemetrycfg.__init__(self)
        self.config_root = CONFIG_ROOT_HDC
        self.param_checks.update(HDC_PARAM_CHECKS)
        self.mandatory_params.extend(HDC_MANDATORY_CONFIGS)
        self.default_values.update(HDC_DEFAULT_VALUES)

    def telemetry_type(self):
        return 'HDC'

    def load_config(self, target):
        Telemetrycfg.load_config(self, target)
        target['GLOBAL'] = {
            item[0]: item[1] for item in target['CONFIG'].items() if item[0] not in [
                'delay_threshold', 'ports']}
        delay_th = target['CONFIG']['delay_threshold']
        target['PORTS'] = {}
        target_port_list = target['CONFIG']['ports']
        if target_port_list == ['*']:
            if ALL_PORTS:
                target_port_list = '*'
            else:
                target_port_list = self.get_front_panel_ifnames()
        for port in target_port_list:
            target['PORTS'][port] = delay_th


class InnoShellCmds:

    '''
    Interfaces with InnoCLI to access the Innovium SDK bypassing SAI.
    Collection of methods to access the InnoCLI.
    Note: This is not thread-safe with SAI. So InnoCLI must not modify objects
    that are modified by SAI.
    '''
    @staticmethod
    def exec_ivm_command(cmdstr):
        #"return tuple of (rc, output)"
        FCD.log(logLevel.info, "CMD=" + cmdstr)
        if DRY_RUN:
            return 0, None

        wd = os.getcwd()
        output = ''
        try:
            os.chdir("/innovium")
            output = subprocess.check_output(
                ['/innovium/remote_shell.sh', '-n', '-r', '9999', '-C', cmdstr], stderr=subprocess.STDOUT)
            rc = 0
        # except subprocess.CalledProcessError as e:
        except Exception as e:
            try:
                err_str = "CMD={} failed with exception={}".format(
                    cmdstr, str(e))
                FCD.log(logLevel.err, err_str)
            except Exception:
                pass
            rc = 1
        finally:
            os.chdir(wd)
        return rc, output

    @staticmethod
    def extract_ivm_cmd_output(output):
        '''
        Output is of this format:
        '\t\tConnected to Innovium Shell Server\r\nBDC Collector is already exist\r\n\r\nScript started, file is ifcsrshell.Apr022020_092951317.log\nScript started, file is ifcsrshell.Apr022020_092951317.log\nScript done, file is ifcsrshell.Apr022020_092951317.log\nExiting shell, backup is ifcsrshell.log.bkup\n'

        So extract:
        '\t\tConnected to Innovium Shell Server\r\n{XXXX}\r\nScript started
        '''

        if DRY_RUN:
            return None
        match = re.match(
            r'\t\tConnected to Innovium Shell Server\n(.*)',
            output,
            re.MULTILINE)
        if match:
            return match.group(1)
        return None

    @staticmethod
    def remove_telemetry_bdc(error_log=False):
        cmd = 'config bdc delete_instance'
        FCD.log(logLevel.info, "Remove BDC session config!")
        rc, output = InnoShellCmds.exec_ivm_command(cmd)
        if rc:
            err_str = "Remove BDC session failed"
            FCD.log(logLevel.err if error_log else logLevel.trace, err_str)
            raise Exception(err_str)
        FCD.log(logLevel.trace, output)
        return

    @staticmethod
    def add_telemetry_bdc(bdc_params, error_log):
        bdc_global_params = bdc_params['GLOBAL']
        cmd = 'config bdc create_instance '
        for key in bdc_global_params:
            # translate key to IFCS CLI keyword
            cli_key = BDC_SONIC_TO_IFCS_TRANSLATION.get(key, key)
            cmd = cmd + \
                '-{key} {value} '.format(key=cli_key, value=bdc_global_params[key])
        FCD.log(logLevel.info, "Add BDC session config!")
        rc, output = InnoShellCmds.exec_ivm_command(cmd)
        fail = False
        msg = ''
        # handle error checks.
        if rc:
            fail = True
        else:
            msg = InnoShellCmds.extract_ivm_cmd_output(output)
            if msg:
                fail = True
        if fail:
            # cleanup intermediate objects
            try:
                InnoShellCmds.remove_telemetry_bdc(error_log)
            except BaseException:
                pass
            err_str = "Add BDC session failed for params:{}:{}".format(
                str(bdc_global_params), msg)
            FCD.log(logLevel.err if error_log else logLevel.trace, err_str)
            raise Exception(err_str)
        else:
            FCD.log(logLevel.trace, "Success: cmd output=" + str(output))
        return

    @staticmethod
    def remove_telemetry_hdc(error_log=False):
        cmd = 'config hdc delete_instance'
        FCD.log(logLevel.info, "Remove HDC session config!")
        rc, output = InnoShellCmds.exec_ivm_command(cmd)
        if DRY_RUN:
            return

        if not rc:
            msg = InnoShellCmds.extract_ivm_cmd_output(output)
        failed = False
        '''
         For HDC CLI, all genuine error messages will have 'rc: <num>' printed.
         <num> will always be non-zero.
         There are benign messages that we need to ignore.
        '''
        if rc or ' rc:' in msg:
            failed = True
        if failed:
            err_str = "Remove HDC session failed. Error={}".format(msg)
            FCD.log(logLevel.err if error_log else logLevel.trace, err_str)
            raise Exception(err_str)
        FCD.log(logLevel.trace, output)
        return

    @staticmethod
    def add_telemetry_hdc(hdc_params, error_log):
        hdc_global_params = hdc_params['GLOBAL']
        cmd = 'config hdc create_instance '
        for key in hdc_global_params:
            if key in ['devports', 'ports', 'cos', 'delay_threshold']:
                continue
            # translate key to IFCS CLI keyword
            cli_key = HDC_SONIC_TO_IFCS_TRANSLATION.get(key, key)
            cmd = cmd + \
                '-{key} {value} '.format(key=cli_key, value=hdc_global_params[key])
        FCD.log(logLevel.info, "Add HDC session config!")
        rc, output = InnoShellCmds.exec_ivm_command(cmd)
        if DRY_RUN:
            return
        fail = False
        msg = ''
        # handle error checks.
        if rc:
            fail = True
        else:
            '''
             For HDC CLI, all genuine error messages will have 'rc: <num>' printed.
             <num> will always be non-zero.
            '''
            msg = InnoShellCmds.extract_ivm_cmd_output(output)
            if msg and msg != '':
                fail = True
        if fail:
            # cleanup intermediate objects
            try:
                InnoShellCmds.remove_telemetry_hdc(error_log)
            except BaseException:
                pass
            err_str = "Add HDC session failed for params:{}:{}".format(
                str(hdc_params), msg)
            FCD.log(logLevel.err if error_log else logLevel.trace, err_str)
            raise Exception(err_str)
        else:
            FCD.log(logLevel.trace, "Success: cmd output=" + str(output))
        return

    @staticmethod
    def add_telemetry(telemetry_type, sdk_params, error_log=False):
        if telemetry_type == 'BDC':
            return InnoShellCmds.add_telemetry_bdc(
                sdk_params, error_log=error_log)
        else:
            return InnoShellCmds.add_telemetry_hdc(
                sdk_params, error_log=error_log)

    @staticmethod
    def get_queue_status(telemetry_type, devport, cos):
        if telemetry_type == 'BDC':
            # Does not depend on Q
            return True

        cmd = 'config hdc get_queue_status -queue {} -devport {}'.format(
            cos, devport)
        FCD.log(logLevel.info, cmd)
        rc, output = InnoShellCmds.exec_ivm_command(cmd)
        if DRY_RUN:
            return True

        fail = False
        msg = ''
        # handle error checks.
        if rc:
            return False

        msg = InnoShellCmds.extract_ivm_cmd_output(output)
        if 'True' in msg:
            return True
        return False

    @staticmethod
    def apply_queue(
            telemetry_type,
            enable,
            cos,
            devport=None,
            delay_threshold=None, error_log=False):
        if telemetry_type == 'BDC':
            # Does not depend on Q
            return True

        cmd = 'config hdc apply_instance -queue {fcos} -{fdevport} -{fenable} {fdelay}'.format(
            fcos=cos,
            fdevport='devport {}'.format(devport) if devport else 'devport_all',
            fenable='enable' if enable else 'disable',
            fdelay='-delay_threshold={}'.format(delay_threshold) if delay_threshold else '')
        FCD.log(logLevel.info, "Apply HDC instance")
        rc, output = InnoShellCmds.exec_ivm_command(cmd)
        if DRY_RUN:
            return
        fail = False
        msg = ''
        # handle error checks.
        if rc:
            fail = True
        else:
            msg = InnoShellCmds.extract_ivm_cmd_output(output)
            if msg:
                fail = True
        if fail:
            err_str = "Apply HDC instance failed:{};returns:{}".format(
                cmd, msg)
            FCD.log(logLevel.err if error_log else logLevel.trace, err_str)
            raise Exception(err_str)
        else:
            FCD.log(logLevel.trace, "Success: cmd output=" + str(output))
        return

    @staticmethod
    def remove_telemetry(telemetry_type, error_log=False):
        if telemetry_type == 'BDC':
            return InnoShellCmds.remove_telemetry_bdc(error_log=error_log)
        else:
            return InnoShellCmds.remove_telemetry_hdc(error_log=error_log)

    @staticmethod
    def is_warm_reboot():
        with open('/proc/cmdline') as f:
            data = f.read()
            match = re.search(r'SONIC_BOOT_TYPE=warm', data, re.MULTILINE)
            return match


_lock = threading.Lock()


class FCD:
    last_message = ''
    last_timestamp = None
    _bdc_telemetrycfg = None
    _hdc_telemetrycfg = None
    sdk_ready = False

    @staticmethod
    def process_config_under_lock(telemetrycfg, error_log=False):
        with _lock:
            FCD.process_config(telemetrycfg, error_log=error_log)

    @staticmethod
    def remove_telemetry(telemetrycfg, error_log=False):
        InnoShellCmds.apply_queue(
            telemetrycfg.telemetry_type(),
            False,
            telemetrycfg.PROGRAMMED_CONFIG['GLOBAL']['cos'],
            error_log=error_log)
        telemetrycfg.PROGRAMMED_CONFIG['PORTS'] = {}

        InnoShellCmds.remove_telemetry(
            telemetrycfg.telemetry_type(),
            error_log=error_log)
        telemetrycfg.state = State.NOT_CONFIGURED
        telemetrycfg.PROGRAMMED_CONFIG = {}
        return

    @staticmethod
    def is_same_cpu_queue(telemetrycfg, error_log=False):
        # This config has cpu_queue. Multiple telemetry sessions (BDC, HDC) must
        # not have the same cpu_queue.
        if (telemetrycfg.telemetry_type() == 'BDC'):
            other_config = FCD._hdc_telemetrycfg
        elif (telemetrycfg.telemetry_type() == 'HDC'):
            other_config = FCD._bdc_telemetrycfg
        else:
            err_str = "Unidentified telemetry type {}".format(telemetrycfg.telemetry_type())
            FCD.log(logLevel.err if error_log else logLevel.trace, err_str)
            raise Exception(err_str)

        if other_config.PROGRAMMED_CONFIG.get('GLOBAL') is not None:
            if (other_config.get_cpu_queue_programmed() == telemetrycfg.get_cpu_queue()):
                err_str = "Cannot configure same cpu_queue for BDC and HDC"
                FCD.log(logLevel.err if error_log else logLevel.trace, err_str)
                raise Exception(err_str)

    @staticmethod
    def process_config(telemetrycfg, error_log=False):
        """
        @summary: Fetch config from CONFIG_DB and program the ASIC.
        @param telemetrycfg: TelemetryCfg object
        """
        telemetrycfg.parse_config()
        FCD.log(
            logLevel.trace,
            " telemetrycfg.operation={},telemetrycfg.state={}".format(
                telemetrycfg.operation,
                telemetrycfg.state))

        # Deletion case
        if telemetrycfg.operation == Operation.DELETE:
            FCD.log(
                logLevel.info,
                " {} session config removed! Deleting in SDK.".format(
                    telemetrycfg.telemetry_type()))
            FCD.remove_telemetry(telemetrycfg, error_log=error_log)
            return

        if telemetrycfg.operation not in [
                Operation.CREATE,
                Operation.UPDATE,
                Operation.UPDATE_INCREMENTAL] and telemetrycfg.state in [
                State.INIT,
                State.NOT_CONFIGURED]:
            FCD.log(logLevel.trace, "Nothing configured; nothing to do.")
            return

        # Either configuration could have changed telemetrycfg.operation in CREATE, UPDATE,
        # or network topology could have changed.
        # Verify config is present, and recompute path and match against
        # programmed configs.


        # Form the SDK programming params by:
        # 1)  First get the static config info
        new_sdk_params = copy.deepcopy(telemetrycfg.DESIRED_CONFIG)
        # 2) Append the 'network derived state info

        # Devport is implicitly set as 0 while sending the inno shell command
        # if the collector is local (cpu_queue set in BDC session in config_db)
        # Derive the deport only if the collector is remote.
        # Other fields like smac, dmac are also derived from Src IP and Dst IP
        # only in case of remote collector.
        if (telemetrycfg.get_cpu_queue() is None):
            collector_ip = telemetrycfg.get_dst_ip()
            FCD.log(logLevel.trace, collector_ip)
            route_prefix = telemetrycfg.get_route_for_ip(collector_ip)

            '''
            In order to program the device, the SDK needs the information about the front panel port on which the collector is reached, and the source MAC and destination MAC address of the next hop. The daemon identifies this information by the following steps:
                Look up the kernel routing table (ip route list match <dip>) to identify the Longest Prefix match route
                Look up the REDIS ASIC_DB ASIC_STATE:SAI_OBJECT_TYPE_ROUTE_ENTRY entries to identify the RIF and Neighbor IP in case of directly connected routes
                Look up the REDIS ASIC_DB ASIC_STATE:SAI_OBJECT_TYPE_ROUTE_ENTRY entries to identify the Nexthop and Neighbor IP in case of nexthop routes. If the route points to an ECMP group (i.e NEXTHOP_GROUP), a member nexthop is selected.
                The neighbor is selected from ASIC_STATE:SAI_OBJECT_TYPE_NEIGHBOR_ENTRY using the RIF and neighbor IP.
                The port and source MAC address is obtained from the RIF, and the destination MAC address is obtained from the neighbor entry.
                If the RIF is a part of a port-channel, a random member of the port-channel is chosen as the port.
            '''

            FCD.log(logLevel.trace, "route: " + route_prefix)
            if route_prefix != telemetrycfg.get_selected_prefix():
                FCD.log(logLevel.info, "collector ip: {} is matching prefix: {}".format(collector_ip, route_prefix))
                telemetrycfg.set_selected_prefix(route_prefix)

            rif, ip = telemetrycfg.get_route_rif_and_ip(route_prefix, collector_ip)
            if ip != telemetrycfg.get_selected_nexthop():
                FCD.log(logLevel.info, "collector ip: {} is using nexthop: {}".format(collector_ip, ip))
                telemetrycfg.set_selected_nexthop(ip)

            smac = telemetrycfg.get_rif_smac(rif)
            dmac = telemetrycfg.get_neighbor_dmac(rif, ip)
            port_oid = telemetrycfg.get_rif_port(rif, dmac)
            port_oid = telemetrycfg.get_port_from_lag(port_oid)
            devport = telemetrycfg.get_devport_from_port_vid(port_oid)
            new_sdk_params['GLOBAL']['dev_port' if telemetrycfg.telemetry_type() == 'BDC' else 'devport'] = devport
        else:
        # This config has cpu_queue. Multiple telemetry sessions (BDC, HDC) must
        # not have the same cpu_queue.
            FCD.is_same_cpu_queue(telemetrycfg, error_log=error_log)

            # For local collector, we embed the src and dst ip in the MACs.
            smac = get_reserved_mac_using_ip(telemetrycfg.get_src_ip())
            dmac = get_reserved_mac_using_ip(telemetrycfg.get_dst_ip())

        new_sdk_params['GLOBAL']['smac'] = smac
        new_sdk_params['GLOBAL']['dmac'] = dmac
        FCD.log(
            logLevel.trace,
            "{} params = ".format(
                telemetrycfg.telemetry_type()) +
            str(new_sdk_params['GLOBAL']))

        if new_sdk_params['PORTS']:
            FCD.log(
                logLevel.trace,
                "{} ports = ".format(
                    telemetrycfg.telemetry_type()) +
                str(new_sdk_params['PORTS']))

        # Creation case
        if not telemetrycfg.PROGRAMMED_CONFIG.get('GLOBAL', None):
            assert(telemetrycfg.operation == Operation.CREATE)
            FCD.add_telemetry(
                telemetrycfg,
                new_sdk_params,
                error_log=error_log)
            telemetrycfg.state = State.CONFIGURED
            if new_sdk_params['PORTS']:
                FCD.apply_telemetry(
                    telemetrycfg,
                    new_sdk_params,
                    error_log=error_log)
            return

        # Update cases:
        #       route change: global update
        #       global config change: global update
        #       port config change : incremental update

        # Global update: either route change or Global config change
        if telemetrycfg.PROGRAMMED_CONFIG.get('GLOBAL', None) and (
            sorted(
                new_sdk_params['GLOBAL'].items()) != sorted(
                telemetrycfg.PROGRAMMED_CONFIG['GLOBAL'].items())):
            if telemetrycfg.operation == Operation.UPDATE:
                FCD.log(
                    logLevel.info,
                    "User Config changed: Need to reprogram {} session globally!".format(
                        telemetrycfg.telemetry_type()))
            else:
                FCD.log(
                    logLevel.info,
                    "Route to collector changed: Need to reprogram {} session globally!".format(
                        telemetrycfg.telemetry_type()))

            if telemetrycfg.PROGRAMMED_CONFIG.get('PORTS', None):
                InnoShellCmds.apply_queue(
                    telemetrycfg.telemetry_type(),
                    False,
                    telemetrycfg.PROGRAMMED_CONFIG['GLOBAL']['cos'],
                    error_log=error_log)
                telemetrycfg.PROGRAMMED_CONFIG['PORTS'] = {}

            InnoShellCmds.remove_telemetry(
                telemetrycfg.telemetry_type(), error_log=error_log)
            telemetrycfg.PROGRAMMED_CONFIG = {}
            telemetrycfg.state = State.NOT_CONFIGURED
            FCD.add_telemetry(
                telemetrycfg, new_sdk_params, error_log=error_log)
            telemetrycfg.PROGRAMMED_CONFIG['GLOBAL'] = new_sdk_params['GLOBAL']
            telemetrycfg.state = State.CONFIGURED
            if new_sdk_params['PORTS']:
                FCD.apply_telemetry(
                    telemetrycfg,
                    new_sdk_params,
                    error_log=error_log)
            return

        if (sorted(
                new_sdk_params.get('PORTS', {}).items()) != sorted(
                telemetrycfg.PROGRAMMED_CONFIG.get('PORTS', {}).items())):
            FCD.log(
                logLevel.info,
                "Need to reprogram {} session on port(s)!".format(
                    telemetrycfg.telemetry_type()))
            FCD.apply_telemetry(
                telemetrycfg,
                new_sdk_params,
                error_log=error_log)

    @staticmethod
    def add_telemetry(telemetrycfg, new_sdk_params, error_log=False):
        InnoShellCmds.add_telemetry(
            telemetrycfg.telemetry_type(), new_sdk_params, error_log=error_log)
        telemetrycfg.PROGRAMMED_CONFIG['GLOBAL'] = new_sdk_params['GLOBAL']

    @staticmethod
    def apply_telemetry(telemetrycfg, new_sdk_params, error_log=False):
        if not new_sdk_params['CONFIG']['ports']:
            return

        remove_list = [item for item in telemetrycfg.PROGRAMMED_CONFIG.get(
            'PORTS', {}).items() if item not in new_sdk_params['PORTS'].items()]
        add_list = [item for item in new_sdk_params['PORTS'].items(
        ) if item not in telemetrycfg.PROGRAMMED_CONFIG.get('PORTS', {}).items()]
        for item in remove_list:
            FCD.log(
                logLevel.info,
                "Disable Delay Threshold={} on port:{}".format(
                    item[1],
                    item[0]))
            try:
                port = item[0]
                delay_th = item[1]
                kwargs = {}
                if port != '*':
                    devport = telemetrycfg.get_devport_from_ifname(port)
                    kwargs['devport'] = devport

                InnoShellCmds.apply_queue(
                    telemetrycfg.telemetry_type(),
                    False,
                    new_sdk_params['GLOBAL']['cos'],
                    **kwargs)
                telemetrycfg.PROGRAMMED_CONFIG['PORTS'].pop(port)
            except Exception as e:
                FCD.log(
                    logLevel.err if error_log else logLevel.trace,
                    "Failed to disable HDC on port{}, delay_threshold={}".format(
                        item[0],
                        item[1]))

        for item in add_list:
            ready = False
            FCD.log(
                logLevel.info,
                "Enable Delay Threshold={} on port:{}".format(
                    item[1],
                    item[0]))
            try:
                port_wildcard = False
                port = item[0]
                if port == '*':
                    # check if any one port is ready
                    port = telemetrycfg.get_front_panel_ifnames()[0]
                    port_wildcard = True
                delay_th = item[1]
                devport = 'Not found'
                devport = telemetrycfg.get_devport_from_ifname(port)
                ready = InnoShellCmds.get_queue_status(
                    telemetrycfg.telemetry_type(), devport, new_sdk_params['GLOBAL']['cos'])
                if ready:
                    kwargs = {}
                    if not port_wildcard:
                        kwargs['devport'] = devport
                    kwargs['delay_threshold'] = delay_th
                    kwargs['error_log'] = error_log
                    InnoShellCmds.apply_queue(
                        telemetrycfg.telemetry_type(),
                        True,
                        new_sdk_params['GLOBAL']['cos'],
                        **kwargs)
                    if not telemetrycfg.PROGRAMMED_CONFIG.get('PORTS', None):
                        telemetrycfg.PROGRAMMED_CONFIG['PORTS'] = {}
                    if port_wildcard:
                        port = '*'
                    telemetrycfg.PROGRAMMED_CONFIG['PORTS'][port] = delay_th
                    FCD.log(
                        logLevel.trace,
                        "Applied telemetry on {} queues {} with delay_threshold {}".format(
                            port,
                            new_sdk_params['GLOBAL']['cos'],
                            delay_th))

            except Exception as e:
                FCD.log(
                    logLevel.err if error_log else logLevel.trace,
                    "Skipped telemetry on {}:devport-{}, queues {}  delay_threshold {}:{}".format(
                        port,
                        devport,
                        new_sdk_params['GLOBAL']['cos'],
                        delay_th,
                        str(e)))
                continue

    @staticmethod
    def clean_up_telemetry(telemetrycfg, error_log=False):
        with _lock:
            if not telemetrycfg.PROGRAMMED_CONFIG or telemetrycfg.state == State.NOT_CONFIGURED:
                return
            try:
                FCD.remove_telemetry(telemetrycfg, error_log)
                telemetrycfg.PROGRAMMED_CONFIG = {}
                telemetrycfg.state = State.NOT_CONFIGURED
            except Exception as e:
                pass

    @staticmethod
    def log(level, message):
        if level in [logLevel.info, logLevel.err, logLevel.trace]:
            sl = None
            if level == logLevel.info:
                sl = syslog.LOG_INFO
            elif level == logLevel.err:
                sl = syslog.LOG_ERR
            elif (level == logLevel.trace):
                if VERBOSE:
                    sl = syslog.LOG_DEBUG  # in verbose mode promote trace to ssyslog
                elif TRACE_FILE:
                    LOCAL_LOG.write(
                        "\"{date}\":{mesg}\n".format(
                            date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            mesg=message))

            if sl:
                if (FCD.last_message != message) or (
                        (datetime.now() - FCD.last_timestamp).seconds > 60):
                    try:
                        syslog.syslog(sl, message)
                    except BaseException:
                        pass
                    FCD.last_message = message
                    FCD.last_timestamp = datetime.now()
        elif TRACE_FILE and level == logLevel.trace_file:
            LOCAL_LOG.write(
                "\"{date}\":{mesg}\n".format(
                    date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    mesg=message))
        if level == logLevel.prin and DEBUG:
            print "\"{date}\":{mesg}: Line #={ln}\n".format(date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"), mesg=message, ln=inspect.currentframe().f_back.f_lineno)

    @staticmethod
    def cleanup():
        FCD.log(logLevel.info, "cleanup")
        syslog.closelog()
        FCD.log("TRACE", "atexit()")
        LOCAL_LOG.flush()
        LOCAL_LOG.close()

    @staticmethod
    def wait_for_syncd_init():
        FCD.log(logLevel.info, "Waiting for SDK init")
        cmd = 'ifcs show node'
        while True:
            try:
                rc, cmd_output = InnoShellCmds.exec_ivm_command(cmd)
                # match = re.search(r'pt02\s+:\s+(\d+)', cmd_output, re.MULTILINE)
                # if match.group(1) == '2':
                match = re.search(r'enable :\s+TRUE', cmd_output, re.MULTILINE)
                if match:
                    FCD.log(logLevel.info, "SDK init done")
                    return
            except BaseException:
                pass
            FCD.log(logLevel.trace, "SDK not ready")
            time.sleep(POLL_INTERVAL / 1000)

    @staticmethod
    def wait_for_cpu_queue():
        FCD.log(logLevel.info, "Waiting for CPU Queues")
        cmd = 'ifcs show cpu_queue'
        while True:
            try:
                rc, cmd_output = InnoShellCmds.exec_ivm_command(cmd)
                match = re.search(r'Total cpu_queue count: 48', cmd_output, re.MULTILINE)
                if match:
                    FCD.log(logLevel.info, "CPU Queues Ready")
                    return
            except BaseException:
                pass
            FCD.log(logLevel.trace, "CPU Queues not ready")
            time.sleep(POLL_INTERVAL / 1000)

    @staticmethod
    def is_another_instance_running():
        try:
            output = subprocess.check_output(
                "ps -ef | grep python | grep '[" +
                __main__.__file__[0] +
                "]" +
                __main__.__file__[
                    1:] +
                "' | wc -l",
                stderr=subprocess.STDOUT,
                shell=True)
            return (int(output.strip()) > 1)
        except Exception as e:
            FCD.log(
                logLevel.err,
                "Not able to see if another instance is running: " +
                str(e))
            return 0

    @staticmethod
    def wait_for_syncd_run():
        # Check for node attr 'enable' to be 'true'
        FCD.wait_for_syncd_init()

        # Check for cpu_queue to be created. Needed for route creation and local
        # collector.
        FCD.wait_for_cpu_queue()
        FCD.sdk_ready = True


def main():
    atexit.register(FCD.cleanup)
    FCD.log(logLevel.info, "started {}".format(sys.argv))

    bdc_telemetrycfg = BDC_Telemetrycfg()
    hdc_telemetrycfg = HDC_Telemetrycfg()
    FCD._bdc_telemetrycfg = bdc_telemetrycfg
    FCD._hdc_telemetrycfg = hdc_telemetrycfg
    time.sleep(SLOW_START_INTERVAL / 1000)
    # Wait for syncd init and SDK init.
    if not DRY_RUN:
        t0 = threading.Thread(target=FCD.wait_for_syncd_run())
        t0.daemon = True
        t0.start()
        while not FCD.sdk_ready:
            time.sleep(0.5)

    bdc_telemetrycfg.parse_switch_config()

    '''
    if None and InnoShellCmds.is_warm_reboot():  # No warmboot support for now
        try:
            InnoShellCmds.remove_telemetry()
        except:
            pass
    '''
    '''
    # Process configuration added before we registered for notifications.
    for telemetrycfg in [bdc_telemetrycfg, hdc_telemetrycfg]:
        try:
            FCD.process_config_under_lock(telemetrycfg, error_log=True)
        except Exception as e:
            try:
                FCD.clean_up_telemetry(telemetrycfg, error_log=True)
                stk = traceback.format_exc()
                FCD.log(
                    logLevel.err,
                    "Could not configure Collector due to error: {}; Traceback={}.".format(
                        str(e),
                        stk))
            except Exception as ie:
                pass
    '''

    #  If user has specified a poll interval, continue fallback polling.
    while True:
        for telemetrycfg in [bdc_telemetrycfg, hdc_telemetrycfg]:
            try:
                FCD.process_config_under_lock(telemetrycfg, error_log=True)
            except Exception as e:
                try:
                    FCD.clean_up_telemetry(telemetrycfg)
                    stk = traceback.format_exc()
                    FCD.log(
                        logLevel.info,
                        "Could not configure Collector due to error: {}; Traceback={}. Retry in {}millisecs".format(
                            str(e),
                            stk,
                            POLL_INTERVAL))
                except Exception as ie:
                    pass
        time.sleep(POLL_INTERVAL / 1000)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Innovium Flashlight Config Daemon (FCD)',
        version=FCD_VERSION,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        epilog="""
""")
    parser.add_argument('-V', '--verbose', action='store_true',
                        help='verbose  Syslog output', default=False)
    parser.add_argument('-d', '--debug', action='store_true',
                        help=argparse.SUPPRESS,
                        # help='print logs on console  output',
                        default=False)
    parser.add_argument('-L', '--log_to_file', action='store_true',
                        help=argparse.SUPPRESS,
                        # help='store debug logs to file ',
                        default=False)
    parser.add_argument('-s', '--start', action='store_true',
                        help='start the daemon', default=True)
    parser.add_argument(
        '-p',
        '--poll_interval',
        # help=argparse.SUPPRESS,
        help='polling interval in milliseconds; when specified REDIS keyspace notification handling will be disabled',
        type=float,
        default=POLL_INTERVAL)

    parser.add_argument(
        '-D',
        '--dry_run',
        action='store_true',
        help=argparse.SUPPRESS,
        # help='no device  programming; just parse config and log actions',
        default=False)
    parser.add_argument(
        '-S',
        '--slow_start_delay',
        help=argparse.SUPPRESS,
        # help='slow start; sleep before beginning processing in milliseconds',
        type=float,
        default=SLOW_START_INTERVAL)
    parser.add_argument('--disable_all_ports', action='store_true',
                        help="do not apply HDC on all ports simultaneously",
                        default=not ALL_PORTS)

    args = parser.parse_args()
    FCD.last_timestamp = datetime.now()
    FCD.last_message = ''

    syslog.openlog(DAEMON_NAME)
    if FCD.is_another_instance_running():
        FCD.log(
            logLevel.err,
            "Cannot start {};  another instance is already running;".format(
                sys.argv))
        sys.exit()


    LOCAL_LOG = open("/tmp/{}.log".format(DAEMON_NAME), "w")

    if args.debug:
        DEBUG = True

    if args.log_to_file:
        TRACE_FILE = True

    if args.poll_interval:
        POLL_INTERVAL = args.poll_interval

    if args.slow_start_delay:
        SLOW_START_INTERVAL = args.slow_start_delay

    if args.verbose:
        VERBOSE = True

    if args.dry_run:
        DRY_RUN = True

    if args.disable_all_ports:
        ALL_PORTS = False

    if args.start:
        main()
