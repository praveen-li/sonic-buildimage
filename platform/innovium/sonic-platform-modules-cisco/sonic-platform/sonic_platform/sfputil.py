#!/usr/bin/env python                                                                                                                               
#
# sfputil.py
#
# SFP utility functions
#

try:
    import os, fnmatch, subprocess, time
    from sonic_platform_base.sonic_sfp.sfputilbase import SfpUtilBase
    from sonic_platform_base.sonic_sfp.sff8472 import sff8472InterfaceId
    from sonic_platform_base.sonic_sfp.sff8472 import sff8472Dom
    from sonic_platform_base.sonic_sfp.sff8436 import sff8436InterfaceId
    from sonic_platform_base.sonic_sfp.sff8436 import sff8436Dom
    from sonic_platform_base.sonic_sfp.inf8628 import inf8628InterfaceId
    from sonic_platform_base.sonic_sfp.qsfp_dd import qsfp_dd_InterfaceId
    from sonic_platform.qsfp_dd import qsfpddDom
    from sonic_platform.globals import PlatformGlobalData
except ImportError as e:
    raise ImportError (str(e) + "- required module not found")

# definitions of the offset and width for values in QSFP_DD info eeprom
QSFP_DD_TYPE_OFFSET = 0
QSFP_DD_TYPE_WIDTH = 1

QSFP_DD_VENDOR_NAME_OFFSET = 1
QSFP_DD_VENDOR_NAME_WIDTH = 16

QSFP_DD_VENDOR_OUI_OFFSET = 17
QSFP_DD_VENDOR_OUI_WIDTH = 3

QSFP_DD_VENDOR_PN_OFFSET = 20
QSFP_DD_VENDOR_PN_WIDTH = 16

QSFP_DD_HW_REV_OFFSET = 36
QSFP_DD_HW_REV_WIDTH = 2

QSFP_DD_VENDOR_SN_OFFSET = 38
QSFP_DD_VENDOR_SN_WIDTH = 16

QSFP_DD_VENDOR_DATE_OFFSET = 54
QSFP_DD_VENDOR_DATE_WIDTH = 8

QSFP_DD_EXT_TYPE_OFFSET = 72
QSFP_DD_EXT_TYPE_WIDTH = 2

QSFP_DD_CABLE_LENGTH_OFFSET = 74
QSFP_DD_CABLE_LENGTH_WIDTH = 1

QSFP_DD_CONNECTOR_OFFSET = 75
QSFP_DD_CONNECTOR_WIDTH = 1

QSFP_DD_MEDIA_TYPE_OFFSET = 85
QSFP_DD_MEDIA_TYPE_WIDTH = 1

QSFP_DD_FIRST_APPLICATION_LIST_OFFSET = 86
QSFP_DD_FIRST_APPLICATION_LIST_WIDTH = 32

QSFP_DD_PAGE_OFFSET = 127
QSFP_DD_PAGE_WIDTH = 1

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
    SUPPORTED_OSFP_QSFPDD_PORT_TYPES = ['QSFP_DD', 'OSFP']

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

    def reset_page(self, port_num, page):
        if self._is_valid_port(port_num) :
            os.system("/usr/sbin/i2cset -y -f %d 0x50 %d %d b" % (port_num + self.EEPROM_OFFSET, QSFP_DD_PAGE_OFFSET, page))

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

    def read_eeprom_specific_bytes(self, port_num, offset, width):
        file_path = self.port_to_eeprom_mapping[port_num]
        if not self._sfp_eeprom_present(file_path, 0):
            print("Error, file %d doesn't exist" % file_path)
            return None

        try:
            with open(file_path, mode="rb", buffering=0) as sysfsfile_eeprom:
                eeprom_bytes = self._read_eeprom_specific_bytes(sysfsfile_eeprom, offset, width)
        except IOError:
            print("Error: reading sysfs file %s" % file_path)
            return None
        return eeprom_bytes

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

    def _convert_string_to_num(self, value_str):
        if "-inf" in value_str:
            return 'N/A'
        elif "Unknown" in value_str:
            return 'N/A'
        elif 'dBm' in value_str:
            t_str = value_str.rstrip('dBm')
            return float(t_str)
        elif 'mA' in value_str:
            t_str = value_str.rstrip('mA')
            return float(t_str)
        elif 'C' in value_str:
            t_str = value_str.rstrip('C')
            return float(t_str)
        elif 'Volts' in value_str:
            t_str = value_str.rstrip('Volts')
            return float(t_str)
        else:
            return 'N/A'

    def get_transceiver_info_dict(self, port_num):
        if self.get_presence(port_num) is False:
            return None

        if port_num in self.osfp_ports:
            transceiver_info_dict = {}
            offset = 128

            # Reset xcvr eeprom page
            self.reset_page(port_num, 0)
            sfpi_obj = qsfp_dd_InterfaceId()
            if sfpi_obj is None:
                print("Error: sfp_object open failed")
                return None

            sfp_type_raw = self.read_eeprom_specific_bytes(port_num, (offset + QSFP_DD_TYPE_OFFSET),QSFP_DD_TYPE_WIDTH)
            if sfp_type_raw is not None:
                sfp_type_data = sfpi_obj.parse_sfp_type(sfp_type_raw, 0)
            else:
                return None

            sfp_vendor_name_raw = self.read_eeprom_specific_bytes(port_num, (offset + QSFP_DD_VENDOR_NAME_OFFSET), QSFP_DD_VENDOR_NAME_WIDTH)
            if sfp_vendor_name_raw is not None:
                sfp_vendor_name_data = sfpi_obj.parse_vendor_name(sfp_vendor_name_raw, 0)
            else:
                return None

            sfp_vendor_pn_raw = self.read_eeprom_specific_bytes(port_num, (offset + QSFP_DD_VENDOR_PN_OFFSET), QSFP_DD_VENDOR_PN_WIDTH)
            if sfp_vendor_pn_raw is not None:
                sfp_vendor_pn_data = sfpi_obj.parse_vendor_pn(sfp_vendor_pn_raw, 0)
            else:
                return None

            sfp_vendor_rev_raw = self.read_eeprom_specific_bytes(port_num, (offset + QSFP_DD_HW_REV_OFFSET), QSFP_DD_HW_REV_WIDTH)
            if sfp_vendor_rev_raw is not None:
                sfp_vendor_rev_data = sfpi_obj.parse_vendor_rev(sfp_vendor_rev_raw, 0)
            else:
                return None

            sfp_vendor_sn_raw = self.read_eeprom_specific_bytes(port_num, (offset + QSFP_DD_VENDOR_SN_OFFSET), QSFP_DD_VENDOR_SN_WIDTH)
            if sfp_vendor_sn_raw is not None:
                sfp_vendor_sn_data = sfpi_obj.parse_vendor_sn(sfp_vendor_sn_raw, 0)
            else:
                return None

            sfp_vendor_oui_raw = self.read_eeprom_specific_bytes(port_num, (offset + QSFP_DD_VENDOR_OUI_OFFSET), QSFP_DD_VENDOR_OUI_WIDTH)
            if sfp_vendor_oui_raw is not None:
                sfp_vendor_oui_data = sfpi_obj.parse_vendor_oui(sfp_vendor_oui_raw, 0)
            else:
                return None

            sfp_vendor_date_raw = self.read_eeprom_specific_bytes(port_num, (offset + QSFP_DD_VENDOR_DATE_OFFSET), QSFP_DD_VENDOR_DATE_WIDTH)
            if sfp_vendor_date_raw is not None:
                sfp_vendor_date_data = sfpi_obj.parse_vendor_date(sfp_vendor_date_raw, 0)
            else:
                return None

            sfp_connector_raw = self.read_eeprom_specific_bytes(port_num, (offset + QSFP_DD_CONNECTOR_OFFSET), QSFP_DD_CONNECTOR_WIDTH)
            if sfp_connector_raw is not None:
                sfp_connector_data = sfpi_obj.parse_connector(sfp_connector_raw, 0)
            else:
                return None

            sfp_ext_identifier_raw = self.read_eeprom_specific_bytes(port_num, (offset + QSFP_DD_EXT_TYPE_OFFSET), QSFP_DD_EXT_TYPE_WIDTH)
            if sfp_ext_identifier_raw is not None:
                sfp_ext_identifier_data = sfpi_obj.parse_ext_iden(sfp_ext_identifier_raw, 0)
            else:
                return None

            sfp_cable_len_raw = self.read_eeprom_specific_bytes(port_num, (offset + QSFP_DD_CABLE_LENGTH_OFFSET), QSFP_DD_CABLE_LENGTH_WIDTH)
            if sfp_cable_len_raw is not None:
                sfp_cable_len_data = sfpi_obj.parse_cable_len(sfp_cable_len_raw, 0)
            else:
                return None

            sfp_media_type_raw = self.read_eeprom_specific_bytes(port_num, QSFP_DD_MEDIA_TYPE_OFFSET, QSFP_DD_MEDIA_TYPE_WIDTH)
            if sfp_media_type_raw is not None:
                sfp_media_type_dict = sfpi_obj.parse_media_type(sfp_media_type_raw, 0)
                host_media_list = ""
                sfp_application_type_first_list = self.read_eeprom_specific_bytes(port_num, (QSFP_DD_FIRST_APPLICATION_LIST_OFFSET), QSFP_DD_FIRST_APPLICATION_LIST_WIDTH)
                possible_application_count = 8
                if sfp_application_type_first_list is not None:
                    sfp_application_type_list = sfp_application_type_first_list
                else:
                    return None

                for i in range(0, possible_application_count):
                    if sfp_application_type_list[i * 4] == 'ff' or sfp_media_type_dict is None:
                        break
                    host_electrical, media_interface = sfpi_obj.parse_application(sfp_media_type_dict, sfp_application_type_list[i * 4], sfp_application_type_list[i * 4 + 1])
                    host_media_list = host_media_list + host_electrical + ' - ' + media_interface + '\n\t\t\t\t   '
            else:
                return None

            transceiver_info_dict['type'] = str(sfp_type_data['data']['type']['value'])
            transceiver_info_dict['manufacturer'] = str(sfp_vendor_name_data['data']['Vendor Name']['value'])
            transceiver_info_dict['model'] = str(sfp_vendor_pn_data['data']['Vendor PN']['value'])
            transceiver_info_dict['hardware_rev'] = str(sfp_vendor_rev_data['data']['Vendor Rev']['value'])
            transceiver_info_dict['serial'] = str(sfp_vendor_sn_data['data']['Vendor SN']['value'])
            transceiver_info_dict['vendor_oui'] = str(sfp_vendor_oui_data['data']['Vendor OUI']['value'])
            transceiver_info_dict['vendor_date'] = str(sfp_vendor_date_data['data']['VendorDataCode(YYYY-MM-DD Lot)']['value'])
            transceiver_info_dict['connector'] = str(sfp_connector_data['data']['Connector']['value'])
            transceiver_info_dict['encoding'] = "Not supported for CMIS cables"
            transceiver_info_dict['ext_identifier'] = str(sfp_ext_identifier_data['data']['Extended Identifier']['value'])
            transceiver_info_dict['ext_rateselect_compliance'] = "Not supported for CMIS cables"
            transceiver_info_dict['specification_compliance'] = '{}'
            transceiver_info_dict['cable_type'] = "Length Cable Assembly(m)"
            transceiver_info_dict['cable_length'] = str(sfp_cable_len_data['data']['Length Cable Assembly(m)']['value'])
            transceiver_info_dict['nominal_bit_rate'] = "Not supported for CMIS cables"
            transceiver_info_dict['application_advertisement'] = str(host_media_list)
        else:
            transceiver_info_dict = super(SfpUtil, self).get_transceiver_info_dict(port_num)
        return transceiver_info_dict

    def get_transceiver_dom_info_dict(self, port_num):
        if self.get_presence(port_num) is False:
            return None

        if port_num in self.osfp_ports:

            dom_info_dict_keys = ['temperature',    'voltage',
                                  'rx1power',       'rx2power',
                                  'rx3power',       'rx4power',
                                  'rx5power',       'rx6power',
                                  'rx7power',       'rx8power',
                                  'tx1bias',        'tx2bias',
                                  'tx3bias',        'tx4bias',
                                  'tx5bias',        'tx6bias',
                                  'tx7bias',        'tx8bias',
                                  'tx1power',       'tx2power',
                                  'tx3power',       'tx4power',
                                  'tx5power',       'tx6power',
                                  'tx7power',       'tx8power'
                                 ]
            transceiver_dom_info_dict = dict.fromkeys(dom_info_dict_keys, 'N/A')
            offset = 0
            sfp_data = self.get_eeprom_dict(port_num)
            if sfp_data is None:
                return transceiver_dom_info_dict
            sfpd_obj = qsfpddDom(port_num, sfp_data)
            if sfpd_obj is None:
                return transceiver_dom_info_dict

            dom_data = sfpd_obj.get_data_pretty()
            if dom_data is None:
                return transceiver_dom_info_dict

            dom_monitor_data = dom_data['data'].get('MonitorData')

            if dom_monitor_data is None:
                return transceiver_dom_info_dict

            dom_temperature_data = dom_monitor_data['ModuleMonitor']['TemperatureMonitor']
            if dom_temperature_data is not None:
                temp = self._convert_string_to_num(dom_temperature_data['Temperature'])
                if temp is not None:
                    transceiver_dom_info_dict['temperature'] = temp

            dom_voltage_data = dom_monitor_data['ModuleMonitor']['VoltageMonitor']
            if dom_voltage_data is not None:
                temp = self._convert_string_to_num(dom_voltage_data['Vcc'])
                if temp is not None:
                    transceiver_dom_info_dict['voltage'] = temp

            dom_channel_monitor_data = dom_monitor_data['ChannelMonitor']
            if dom_channel_monitor_data is not None:

                dom_tx_power_monitor = dom_channel_monitor_data['TxPowerMonitor']
                if dom_tx_power_monitor is not None:
                    transceiver_dom_info_dict['tx1power'] = str(self._convert_string_to_num(dom_tx_power_monitor['TX1Power']))
                    transceiver_dom_info_dict['tx2power'] = str(self._convert_string_to_num(dom_tx_power_monitor['TX2Power']))
                    transceiver_dom_info_dict['tx3power'] = str(self._convert_string_to_num(dom_tx_power_monitor['TX3Power']))
                    transceiver_dom_info_dict['tx4power'] = str(self._convert_string_to_num(dom_tx_power_monitor['TX4Power']))
                    transceiver_dom_info_dict['tx5power'] = str(self._convert_string_to_num(dom_tx_power_monitor['TX5Power']))
                    transceiver_dom_info_dict['tx6power'] = str(self._convert_string_to_num(dom_tx_power_monitor['TX6Power']))
                    transceiver_dom_info_dict['tx7power'] = str(self._convert_string_to_num(dom_tx_power_monitor['TX7Power']))
                    transceiver_dom_info_dict['tx8power'] = str(self._convert_string_to_num(dom_tx_power_monitor['TX8Power']))

                dom_rx_power_monitor = dom_channel_monitor_data['RxPowerMonitor']
                if dom_rx_power_monitor is not None:
                    transceiver_dom_info_dict['rx1power'] = str(self._convert_string_to_num(dom_rx_power_monitor['RX1Power']))
                    transceiver_dom_info_dict['rx2power'] = str(self._convert_string_to_num(dom_rx_power_monitor['RX2Power']))
                    transceiver_dom_info_dict['rx3power'] = str(self._convert_string_to_num(dom_rx_power_monitor['RX3Power']))
                    transceiver_dom_info_dict['rx4power'] = str(self._convert_string_to_num(dom_rx_power_monitor['RX4Power']))
                    transceiver_dom_info_dict['rx5power'] = str(self._convert_string_to_num(dom_rx_power_monitor['RX5Power']))
                    transceiver_dom_info_dict['rx6power'] = str(self._convert_string_to_num(dom_rx_power_monitor['RX6Power']))
                    transceiver_dom_info_dict['rx7power'] = str(self._convert_string_to_num(dom_rx_power_monitor['RX7Power']))
                    transceiver_dom_info_dict['rx8power'] = str(self._convert_string_to_num(dom_rx_power_monitor['RX8Power']))

                dom_tx_bias_monitor = dom_channel_monitor_data['TXBiasMonitor']
                if dom_tx_bias_monitor is not None:
                    transceiver_dom_info_dict['tx1bias'] = str(dom_tx_bias_monitor['TX1Bias'])
                    transceiver_dom_info_dict['tx2bias'] = str(dom_tx_bias_monitor['TX2Bias'])
                    transceiver_dom_info_dict['tx3bias'] = str(dom_tx_bias_monitor['TX3Bias'])
                    transceiver_dom_info_dict['tx4bias'] = str(dom_tx_bias_monitor['TX4Bias'])
                    transceiver_dom_info_dict['tx5bias'] = str(dom_tx_bias_monitor['TX5Bias'])
                    transceiver_dom_info_dict['tx6bias'] = str(dom_tx_bias_monitor['TX6Bias'])
                    transceiver_dom_info_dict['tx7bias'] = str(dom_tx_bias_monitor['TX7Bias'])
                    transceiver_dom_info_dict['tx8bias'] = str(dom_tx_bias_monitor['TX8Bias'])
        else:
            transceiver_dom_info_dict = super(SfpUtil, self).get_transceiver_dom_info_dict(port_num)
        return transceiver_dom_info_dict

    def get_transceiver_dom_threshold_info_dict(self, port_num):
        if self.get_presence(port_num) is False:
            return None

        if port_num in self.osfp_ports:

            transceiver_dom_threshold_info_dict = {}

            dom_info_dict_keys = ['temphighalarm',    'temphighwarning',
                                  'templowalarm',     'templowwarning',
                                  'vcchighalarm',     'vcchighwarning',
                                  'vcclowalarm',      'vcclowwarning',
                                  'rxpowerhighalarm', 'rxpowerhighwarning',
                                  'rxpowerlowalarm',  'rxpowerlowwarning',
                                  'txpowerhighalarm', 'txpowerhighwarning',
                                  'txpowerlowalarm',  'txpowerlowwarning',
                                  'txbiashighalarm',  'txbiashighwarning',
                                  'txbiaslowalarm',   'txbiaslowwarning'
                                 ]
            transceiver_dom_threshold_info_dict = dict.fromkeys(dom_info_dict_keys, 'N/A')
            offset = 0
            sfp_data = self.get_eeprom_dict(port_num)
            if sfp_data is None:
                return transceiver_dom_threshold_info_dict
            sfpd_obj = qsfpddDom(port_num, sfp_data)
            if sfpd_obj is None:
                return transceiver_dom_threshold_info_dict

            dom_data = sfpd_obj.get_data_pretty()
            if dom_data is None:
                return transceiver_dom_threshold_info_dict

            dom_threshold_data = dom_data['data'].get('AwThresholds')
            if dom_threshold_data is None:
                return transceiver_dom_threshold_info_dict

            # Threshold Data
            dom_module_threshold_data = dom_threshold_data['ModuleThreshold']
            if dom_module_threshold_data is not None:
                dom_temperature_threshold_data = dom_module_threshold_data['TemperatureThreshold']
                if dom_temperature_threshold_data is not None:
                    transceiver_dom_threshold_info_dict['temphighalarm'] = dom_temperature_threshold_data['TempHighAlarm']
                    transceiver_dom_threshold_info_dict['temphighwarning'] = dom_temperature_threshold_data['TempHighWarning']
                    transceiver_dom_threshold_info_dict['templowalarm'] = dom_temperature_threshold_data['TempLowAlarm']
                    transceiver_dom_threshold_info_dict['templowwarning'] = dom_temperature_threshold_data['TempLowWarning']

                dom_voltage_threshold_data = dom_module_threshold_data['VoltageThreshold']
                if dom_voltage_threshold_data is not None:
                    transceiver_dom_threshold_info_dict['vcchighalarm'] = dom_voltage_threshold_data['VoltageHighAlarm']
                    transceiver_dom_threshold_info_dict['vcchighwarning'] = dom_voltage_threshold_data['VoltageHighWarning']
                    transceiver_dom_threshold_info_dict['vcclowalarm'] = dom_voltage_threshold_data['VoltageLowAlarm']
                    transceiver_dom_threshold_info_dict['vcclowwarning'] = dom_voltage_threshold_data['VoltageLowWarning']

            dom_channel_threshold_data = dom_threshold_data['ChannelThreshold']
            if dom_channel_threshold_data is not None:
                dom_rx_power_threshold_data = dom_channel_threshold_data['RxPowerThreshold']
                if dom_rx_power_threshold_data is not None:
                    transceiver_dom_threshold_info_dict['rxpowerhighalarm'] = dom_rx_power_threshold_data['RXPowerHighAlarm']
                    transceiver_dom_threshold_info_dict['rxpowerhighwarning'] = dom_rx_power_threshold_data['RXPowerHighWarning']
                    transceiver_dom_threshold_info_dict['rxpowerlowalarm'] = dom_rx_power_threshold_data['RXPowerLowAlarm']
                    transceiver_dom_threshold_info_dict['rxpowerlowwarning'] = dom_rx_power_threshold_data['RXPowerLowWarning']

                dom_tx_bias_threshold_data = dom_channel_threshold_data['TXBiasThreshold']
                if dom_tx_bias_threshold_data is not None:
                    transceiver_dom_threshold_info_dict['txbiashighalarm'] = dom_tx_bias_threshold_data['TXBiasHighAlarm']
                    transceiver_dom_threshold_info_dict['txbiashighwarning'] = dom_tx_bias_threshold_data['TXBiasHighWarning']
                    transceiver_dom_threshold_info_dict['txbiaslowalarm'] = dom_tx_bias_threshold_data['TXBiasLowAlarm']
                    transceiver_dom_threshold_info_dict['txbiaslowwarning'] = dom_tx_bias_threshold_data['TXBiasLowWarning']

                dom_tx_power_threshold_data = dom_channel_threshold_data['TxPowerThreshold']
                if dom_tx_power_threshold_data is not None:
                    transceiver_dom_threshold_info_dict['txpowerhighalarm'] = dom_tx_power_threshold_data['TXPowerHighAlarm']
                    transceiver_dom_threshold_info_dict['txpowerhighwarning'] = dom_tx_power_threshold_data['TXPowerHighWarning']
                    transceiver_dom_threshold_info_dict['txpowerlowalarm'] = dom_tx_power_threshold_data['TXPowerLowAlarm']
                    transceiver_dom_threshold_info_dict['txpowerlowwarning'] = dom_tx_power_threshold_data['TXPowerLowWarning']

        else:
            transceiver_dom_threshold_info_dict = super(SfpUtil, self).get_transceiver_dom_threshold_info_dict(port_num)
        return transceiver_dom_threshold_info_dict

