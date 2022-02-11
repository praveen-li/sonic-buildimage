#!/usr/bin/env python                                                                                                                               
#
# sfputil.py
#
# SFP utility functions
#

try:
    import os
    import fnmatch, subprocess, time
    from sonic_platform_base.sonic_sfp.sfputilbase import SfpUtilBase
    from sonic_platform_base.sonic_sfp.sff8472 import sff8472InterfaceId
    from sonic_platform_base.sonic_sfp.sff8472 import sff8472Dom
    from sonic_platform_base.sonic_sfp.sff8436 import sff8436InterfaceId
    from sonic_platform_base.sonic_sfp.sff8436 import sff8436Dom
    from sonic_platform_base.sonic_sfp.inf8628 import inf8628InterfaceId
    from sonic_platform.globals import PlatformGlobalData
except ImportError as e:
    raise ImportError (str(e) + "- required module not found")

#QSFP temperature and voltage offsets
QSFP_TEMPE_OFFSET = 22
QSFP_TEMPE_WIDTH = 2
QSFP_VOLT_OFFSET = 26
QSFP_VOLT_WIDTH = 2
#SFP temperature and volatage offsets
SFP_TEMPE_OFFSET = 96
SFP_TEMPE_WIDTH = 2
SFP_VOLT_OFFSET = 98
SFP_VOLT_WIDTH = 2

class SfpUtil(SfpUtilBase):
    """Platform-specific SfpUtil class"""

    XCVR_PRESENCE_FILE = "/sys/class/mifpga/mifpga/xcvr_present"
    EEPROM_OFFSET = 50

    SUPPORTED_SFP_PORT_TYPES = ['SFP', 'SFP+']
    SUPPORTED_QSFP_PORT_TYPES = ['QSFP', 'QSFP+', 'QSFP28']
    SUPPORTED_OSFP_QSFPDD_PORT_TYPES = ['QSFP-DD', 'OSFP']

    _port_to_eeprom_mapping = {}
    _eeprom_to_prt_mapping = {}

    def __init__(self, port_start, num_ports, platform_global_data, sfps_data):

        self.platform_global_data = platform_global_data
        self.sfps_data = sfps_data

        self.PORT_START = port_start - 1
        self.PORT_END = num_ports - 1

        self.SFP_PORTS_IN_BLOCK = set()
        self.QSFP_PORTS_IN_BLOCK = set()
        self.OSFP_QSFPDD_PORTS_IN_BLOCK = set()

        if 'sfp' in sfps_data:
            sfp_data = sfps_data['sfp']
            for sfp_block in sfp_data:
                if 'type' not in sfp_block:
                    continue

                sfp_type = sfp_block['type']
                if sfp_type not in self.SUPPORTED_SFP_PORT_TYPES and sfp_type not in self.SUPPORTED_QSFP_PORT_TYPES and sfp_type not in self.SUPPORTED_OSFP_QSFPDD_PORT_TYPES:
                    continue

                if 'start_index' not in sfp_block:
                    continue

                sfp_start = int(sfp_block['start_index'])
                if sfp_start < 1:
                    continue

                if 'sfp_num' not in sfp_block:
                    continue

                sfp_num_block = int(sfp_block['sfp_num'])
                if sfp_num_block < 1:
                    continue

                if sfp_type in self.SUPPORTED_QSFP_PORT_TYPES:
                    for port_index in range(sfp_start - 1,sfp_num_block):
                        self.QSFP_PORTS_IN_BLOCK.add(port_index)
                elif sfp_type in self.SUPPORTED_SFP_PORT_TYPES:
                    for port_index in range(sfp_start - 1,sfp_num_block):
                        self.SFP_PORTS_IN_BLOCK.add(port_index)
                elif sfp_type in self.SUPPORTED_OSFP_QSFPDD_PORT_TYPES:
                    for port_index in range(sfp_start - 1,sfp_num_block):
                        self.OSFP_QSFPDD_PORTS_IN_BLOCK.add(port_index)

        eeprom_path = "/sys/class/i2c-adapter/i2c-{0}/{0}-0050/eeprom"
        self._xcvr_presence = None
        self.XCVR_CHANGE_WAIT_TIME = .2
        for x in range(self.PORT_START, self.PORT_END):
            epath = eeprom_path.format(x+self.EEPROM_OFFSET)
            self._port_to_eeprom_mapping[x] = epath                                                                                                 
            self._eeprom_to_prt_mapping[epath] = x
        super(SfpUtil, self).__init__()

    @property
    def port_start(self):
        """ Starting index of physical port range """
        return self.PORT_START

    @property
    def port_end(self):
        """ Ending index of physical port range """
        return self.PORT_END

    @property
    def sfp_ports(self):
        """ SFP Ports """
        return self.SFP_PORTS_IN_BLOCK
    
    @property
    def qsfp_ports(self):
        """ QSFP Ports """
        return self.QSFP_PORTS_IN_BLOCK
    
    @property
    def osfp_ports(self):
        """ OSFP/QSFP-DD  Ports """
        return self.OSFP_QSFPDD_PORTS_IN_BLOCK

    def get_presence(self, port_num):
        with open(self.XCVR_PRESENCE_FILE, "r") as x_p_fp:
            xcvr_line = x_p_fp.readline()   ## Only one line of 0 & 1
            xcvrs = [ int(c) for c in xcvr_line.strip() ]
            if xcvrs[port_num]:
                return True
            else:
                return False

    @property
    def port_to_eeprom_mapping(self):
        """ Dictionary (_port_to_eeprom_mapping) 
            where key = physical port index (integer),
            value = path to SFP EEPROM device file (string) """
        return self._port_to_eeprom_mapping

    def get_low_power_mode(self, port_num):
        if self._is_valid_port(port_num) :
            port_lpmode="/sys/class/mifpga/mifpga/qsfp_%d_lp_mode/value" % (port_num+1)
            mode = False
            with open(port_lpmode, "r") as x_p_fp:
                xcvr_line = x_p_fp.readline()
                mode = int(xcvr_line.strip())
                x_p_fp.close()
            return True if mode else False
        else:
            return False #invalid port

    def set_low_power_mode(self, port_num, lpmode):
        if self._is_valid_port(port_num) :
            port_lpmode="/sys/class/mifpga/mifpga/qsfp_%d_lp_mode/value" % (port_num+1)
            with open(port_lpmode, "w") as x_p_fp:
                x_p_fp.write("1" if lpmode else "0")
                x_p_fp.close()
            return True
        else:
            return False #invalid port
    
    def trigger_cmis_init(self, port_num):
        cmis_init_file="/sys/class/mifpga/mifpga/xcvr_cmis_init"

        if not self._is_valid_port(port_num):
            return True

        if not os.path.exists(cmis_init_file):
            return True

        try:
            with open(cmis_init_file, "r+") as xcvr_cmis_init_fp:

                xcvr_cmis_init = xcvr_cmis_init_fp.read().replace("\n",'')
                xcvr_cmis_init_list = [ int(c) for c in xcvr_cmis_init.strip() ]
                xcvr_cmis_init_list[port_num] = 1
                xcvr_cmis_init_string = "".join(map(str,xcvr_cmis_init_list))
                xcvr_cmis_init_fp.seek(0)
                xcvr_cmis_init_fp.write(xcvr_cmis_init_string)
                xcvr_cmis_init_fp.flush()

                time.sleep(2) #large enough for syncd/csaipd to pick this request and start cmis init

                xcvr_cmis_init_list[port_num] = 0
                xcvr_cmis_init_string = "".join(map(str,xcvr_cmis_init_list))
                xcvr_cmis_init_fp.seek(0)
                xcvr_cmis_init_fp.write(xcvr_cmis_init_string)
                xcvr_cmis_init_fp.flush()
        except:
            return False

        return True


    def reset(self, port_num):
        # Check for valid port_num
        if self._is_valid_port(port_num) :

            port_reset="/sys/class/mifpga/mifpga/qsfp_%d_reset/value" % (port_num+1)

            with open(port_reset, "w") as x_p_fp:
                x_p_fp.write("1")

            time.sleep(1)

            with open(port_reset, "w") as x_p_fp:
                x_p_fp.write("0")

            self.trigger_cmis_init(port_num)

            return True
        else:
            return False #invalid port

    def get_transceiver_change_event(self, timeout=0):
        end_time = time.time() + timeout
        p_pres_dict = {}
        while True:
            try:
                with open(self.XCVR_PRESENCE_FILE, "r") as xcvr_file:
                    xcvr_status = xcvr_file.read().replace("\n", '')
                    xcvrs = [ int(c) for c in xcvr_status.strip() ]

            except:
                print ( "Failed to open", self.XCVR_PRESENCE_FILE)
                return False, {}
            if self._xcvr_presence is not None:
                # Previous state present. Check any change from previous state
                for p in range(self.port_start, self.port_end):
                    if self._xcvr_presence[p] != xcvrs[p]:
                        # Add the change to dict
                        d = {str(p) : str(xcvrs[p])}
                        p_pres_dict.update(d)
            else:
                for p in range(self.port_start, self.port_end):
                    # Add the change to dict
                    if xcvrs[p] == 1:
                        d = {str(p) : str(xcvrs[p])}
                        p_pres_dict.update(d)

            self._xcvr_presence = xcvrs

            if len(p_pres_dict) != 0 :
                return True, p_pres_dict

            cur_time = time.time()
            if cur_time >= end_time and timeout != 0:
                break
            elif (cur_time + self.XCVR_CHANGE_WAIT_TIME) >= end_time and timeout != 0:
                time.sleep(end_time - cur_time)
            else:
                time.sleep(self.XCVR_CHANGE_WAIT_TIME)

        return True, {} #we reach here when timeout expire

    def get_temperature(self, port_num):
        if self._is_valid_port(port_num) :
            eeprom_path = self._port_to_eeprom_mapping[port_num]
            if port_num in self.osfp_ports:
                return 'N/A'          #Need to handle it in future
            elif port_num in self.qsfp_ports:
                offset  = 0 + QSFP_TEMPE_OFFSET
                width = QSFP_TEMPE_WIDTH
                sfpd_obj = sff8436Dom()
                if sfpd_obj is None:
                    return None
            else:
                offset = 256 + SFP_TEMPE_OFFSET
                width = SFP_TEMPE_WIDTH
                sfpd_obj = sff8472Dom()
                if sfpd_obj is None:
                    return None
            
            raw_data = self._read_eeprom_specific_bytes(eeprom_path, offset, width)
            if raw_data is not None:
                dom_temperature_data = sfpd_obj.parse_temperature(raw_data, 0)
                return dom_temperature_data['data']['Temperature']['value']
        return None

    def get_voltage(self, port_num):
        if self._is_valid_port(port_num) :
            eeprom_path = self._port_to_eeprom_mapping[port_num]
            if port_num in self.osfp_ports:
                return 'N/A'          #Need to handle it in future
            elif port_num in self.qsfp_ports:
                offset  = 0 + QSFP_VOLT_OFFSET
                width = QSFP_VOLT_WIDTH
                sfpd_obj = sff8436Dom()
                if sfpd_obj is None:
                    return None
            else:
                offset = 256 + SFP_VOLT_OFFSET
                width = SFP_VOLT_WIDTH
                sfpd_obj = sff8472Dom()
                if sfpd_obj is None:
                    return None
            
            raw_data = self._read_eeprom_specific_bytes(eeprom_path, offset, width)
            if raw_data is not None:
                dom_voltage_data = sfpd_obj.parse_voltage(raw_data, 0)
                return dom_voltage_data['data']['Vcc']['value']
        return None

    def get_tx_bias(self, port_num):
        tx_bias_dict_keys = [ 'tx1bias', 'tx2bias', 'tx3bias', 'tx4bias',]
        tx_bias_dict = dict.fromkeys(tx_bias_dict_keys, 'N/A')

        transceiver_dom_info_dict = self.get_transceiver_dom_info_dict(port_num)
        if transceiver_dom_info_dict is not None :
            tx_bias_dict['tx1bias']= transceiver_dom_info_dict['tx1bias']
            tx_bias_dict['tx2bias']= transceiver_dom_info_dict['tx2bias']
            tx_bias_dict['tx3bias']= transceiver_dom_info_dict['tx3bias']
            tx_bias_dict['tx4bias']= transceiver_dom_info_dict['tx4bias']
        return tx_bias_dict

    def get_rx_power(self, port_num):
        rx_power_dict_keys = ['rx1power', 'rx2power',    'rx3power', 'rx4power',]
        rx_power_dict = dict.fromkeys(rx_power_dict_keys, 'N/A')

        transceiver_dom_info_dict = self.get_transceiver_dom_info_dict(port_num)
        if transceiver_dom_info_dict is not None :
            rx_power_dict['rx1power'] =transceiver_dom_info_dict['rx1power']
            rx_power_dict['rx2power'] =transceiver_dom_info_dict['rx2power']
            rx_power_dict['rx3power'] =transceiver_dom_info_dict['rx3power']
            rx_power_dict['rx4power'] =transceiver_dom_info_dict['rx4power']
        return rx_power_dict

    def get_tx_power(self, port_num):
        tx_power_dict_keys = ['tx1power', 'tx2power',    'tx3power', 'tx4power',]
        tx_power_dict = dict.fromkeys(tx_power_dict_keys, 'N/A')

        transceiver_dom_info_dict = self.get_transceiver_dom_info_dict(port_num)
        if transceiver_dom_info_dict is not None :
            tx_power_dict['tx1power'] =transceiver_dom_info_dict['tx1power']
            tx_power_dict['tx2power'] =transceiver_dom_info_dict['tx2power']
            tx_power_dict['tx3power'] =transceiver_dom_info_dict['tx3power']
            tx_power_dict['tx4power'] =transceiver_dom_info_dict['tx4power']
        return tx_power_dict

