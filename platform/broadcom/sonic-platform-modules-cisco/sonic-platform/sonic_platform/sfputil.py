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
    from sonic_platform_base.sonic_sfp.sffbase import sffbase
    from sonic_platform.globals import PlatformGlobalData
except ImportError as e:
    raise ImportError (str(e) + "- required module not found")

#QSFP temperature and voltage offsets
QSFP_TEMPE_OFFSET = 22
QSFP_TEMPE_WIDTH = 2
QSFP_VOLT_OFFSET = 26
QSFP_VOLT_WIDTH = 2
QSFP_CONTROL_BYTES_OFFSET = 86
QSFP_CONTROL_BYTES_WIDTH = 14
QSFP_NUM_CHANNELS = 4
#SFP temperature and volatage offsets
SFP_TEMPE_OFFSET = 96
SFP_TEMPE_WIDTH = 2
SFP_VOLT_OFFSET = 98
SFP_VOLT_WIDTH = 2
SFP_STATUS_CONTROL_OFFSET   = 110
SFP_STATUS_CONTROL_WIDTH    = 1

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
        self.NUM_PORTS = num_ports

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
        for x in range(self.PORT_START, self.NUM_PORTS):
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
        mode = False
        if not self._is_valid_port(port_num):
            return False 

        if not self.get_presence(port_num):
            return False

        if port_num in self.sfp_ports:
            return False 

        if port_num in self.osfp_ports:
            return False 

        port_lpmode="/sys/class/mifpga/mifpga/qsfp_%d_lp_mode/value" % (port_num+1)
        with open(port_lpmode, "r") as x_p_fp:
            xcvr_line = x_p_fp.readline()
            mode = int(xcvr_line.strip())
            x_p_fp.close()

        return True if mode else False

    def set_low_power_mode(self, port_num, lpmode):
        if not self._is_valid_port(port_num):
            return False 

        if not self.get_presence(port_num):
            return False

        if port_num in self.sfp_ports:
            return False 

        if port_num in self.osfp_ports:
            return False 

        port_lpmode="/sys/class/mifpga/mifpga/qsfp_%d_lp_mode/value" % (port_num+1)
        with open(port_lpmode, "w") as x_p_fp:
            x_p_fp.write("1" if lpmode else "0")
            x_p_fp.close()
        
        if self.platform_global_data.get_param(PlatformGlobalData.KEY_XCVR_HIGH_POWER_CLASS, 0) == 0:
            return True

        return self.enable_power_class(port_num,lpmode)


    def enable_power_class(self, port_num, lpmode) :

        eeprom_path = self._port_to_eeprom_mapping[port_num]
        try:
            sysfsfile_eeprom = open(eeprom_path, mode="rb", buffering=0)
        except IOError:
            print("Error: reading sysfs file %s" % eeprom_path)
            return False 
            
        if not self.get_presence(port_num):
            sysfsfile_eeprom.close()
            return False

        #No need of settings on 40G
        raw_data = self._read_eeprom_specific_bytes(sysfsfile_eeprom, 0, 1)
        if raw_data is not None:
            sfp_type = int(raw_data[0], 16)
            if sfp_type == 0x0d :
                sysfsfile_eeprom.close()
                return True
        else:
            sysfsfile_eeprom.close()
            return False
                
        #No need of settings on 100G-CR4
        raw_data = self._read_eeprom_specific_bytes(sysfsfile_eeprom, 192, 1)
        if raw_data is not None:
            sfp_type = int(raw_data[0], 16)
            if sfp_type == 0x0b :
                sysfsfile_eeprom.close()
                return True
        else:
            sysfsfile_eeprom.close()
            return False

        #check the ext. ID
        data_129 = 0
        data_93 = 0

        raw_data = self._read_eeprom_specific_bytes(sysfsfile_eeprom, 129, 1)
        if raw_data is not None:
            data_129 = int(raw_data[0], 16)
        else:
            data_129 = 0

        raw_data = self._read_eeprom_specific_bytes(sysfsfile_eeprom, 93, 1)
        if raw_data is not None:
            data_93 = int(raw_data[0], 16)
        else:
            data_93 = 0

        if not lpmode:
            #Only for specific ext. IDs, we are enabling high power level
            if data_129 & 0x3:
                data_93 = data_93 | 0x04
                cmd_str = "i2cset -f -y " + str(50 + port_num) + " 0x50 93 " + " " + str(data_93)
                os.system(cmd_str)
        else:
            if data_129 & 0x3:
                data_93 = data_93 & ((~0x04) & 0xFF)
                cmd_str = "i2cset -f -y " + str(50 + port_num) + " 0x50 93 " + " " + str(data_93)
                os.system(cmd_str)
        
        sysfsfile_eeprom.close()
        return True
    
    def reset(self, port_num):
        if not self._is_valid_port(port_num):
            return False 

        if not self.get_presence(port_num):
            return False

        if port_num in self.sfp_ports:
            return False 

        if port_num in self.osfp_ports:
            return False 

        port_reset="/sys/class/mifpga/mifpga/qsfp_%d_reset/value" % (port_num+1)
        with open(port_reset, "w") as x_p_fp:
            x_p_fp.write("1")
            x_p_fp.close()
        time.sleep(1)
        with open(port_reset, "w") as x_p_fp:
            x_p_fp.write("0")
            x_p_fp.close()
        return True

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
                for p in range(self.port_start, self.NUM_PORTS):
                    if self._xcvr_presence[p] != xcvrs[p]:
                        # Add the change to dict
                        d = {str(p) : str(xcvrs[p])}
                        p_pres_dict.update(d)
                        #Reset the XCVR if it is inserted
                        if xcvrs[p] == 1 :
                            self.reset(p)

                if self.platform_global_data.get_param(PlatformGlobalData.KEY_XCVR_HIGH_POWER_CLASS, 0) == 1:
                    if len(p_pres_dict) != 0 :
                        time.sleep(2)
                        for p in p_pres_dict.keys():
                            if p_pres_dict[p] == '1':
                                self.set_low_power_mode(int(p), False)
            else:
                for p in range(self.port_start, self.NUM_PORTS):
                    # Add the change to dict
                    if xcvrs[p] == 1:
                        d = {str(p) : str(xcvrs[p])}
                        p_pres_dict.update(d)
                        self.reset(p)

                if self.platform_global_data.get_param(PlatformGlobalData.KEY_XCVR_HIGH_POWER_CLASS, 0) == 1:
                    if len(p_pres_dict) != 0 :
                        time.sleep(2)
                        for p in p_pres_dict.keys():
                            if p_pres_dict[p] == '1':
                                self.set_low_power_mode(int(p), False)

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

    #helper functions
    def open_port_to_eeprom_path(self, port_num):
        eeprom_path = self._port_to_eeprom_mapping[port_num]
        try:
            port_eeprom_file = open(eeprom_path, mode="rb", buffering=0)
        except IOError:
            print("Error: reading sysfs file %s" % eeprom_path)
            return None 
        return port_eeprom_file

    def close_port_eeprom_path(self, port_eeprom_file):
        try:
            port_eeprom_file.close()
        except IOError:
            print("Error: closing sysfs file %s" % port_eeprom_file)
            return False
        return True

    def is_qsfp(self,port_num, port_eeprom_file):
        if port_num in self.qsfp_ports:
            # Check for Passive QSA adapter
            if port_eeprom_file is None:
                return False
            byte0 = self._read_eeprom_specific_bytes(port_eeprom_file, 0, 1)[0]
            is_qsfp = (byte0 != '03' and byte0 != '0b')
            return is_qsfp
        return False
    #End of helper functions

    def get_rx_los(self, port_num):
        rx_los_state = []

        if not self._is_valid_port(port_num):
            return rx_los_state 

        if not self.get_presence(port_num):
            return rx_los_state

        if port_num in self.osfp_ports:
            #TBD: for QSFP-DD ports
            return rx_los_state 

        eeprom_path = self.open_port_to_eeprom_path(port_num)
        if eeprom_path is None:
            return rx_los_state
            
        if self.is_qsfp(port_num,eeprom_path):
            self.close_port_eeprom_path( eeprom_path)
            return rx_los_state

        raw_data = self._read_eeprom_specific_bytes(eeprom_path, SFP_STATUS_CONTROL_OFFSET, SFP_STATUS_CONTROL_WIDTH)
        if raw_data:
            data = int(raw_data[0], 16)
            rx_los_state.append(sffbase().test_bit(data, 1) != 0)

        self.close_port_eeprom_path( eeprom_path)
        return rx_los_state

    def get_tx_fault(self, port_num):
        tx_fault_state = []

        if not self._is_valid_port(port_num):
            return tx_fault_state 

        if not self.get_presence(port_num):
            return tx_fault_state

        if port_num in self.osfp_ports:
            #TBD: for QSFP-DD ports
            return tx_fault_state 

        eeprom_path = self.open_port_to_eeprom_path(port_num)
        if eeprom_path is None:
            return tx_fault_state
            
        if self.is_qsfp(port_num,eeprom_path):
            self.close_port_eeprom_path( eeprom_path)
            return tx_fault_state

        raw_data = self._read_eeprom_specific_bytes(eeprom_path, SFP_STATUS_CONTROL_OFFSET, SFP_STATUS_CONTROL_WIDTH)
        if raw_data:
            data = int(raw_data[0], 16)
            tx_fault_state.append(sffbase().test_bit(data, 2) != 0)

        self.close_port_eeprom_path( eeprom_path)

        return tx_fault_state

    def get_tx_disable(self, port_num):
        tx_disable_state = []

        if not self._is_valid_port(port_num):
            return tx_disable_state 

        if not self.get_presence(port_num):
            return tx_disable_state

        if port_num in self.osfp_ports:
            #TBD: for QSFP-DD ports
            return tx_disable_state 

        eeprom_path = self.open_port_to_eeprom_path(port_num)
        if eeprom_path is None:
            return tx_disable_state
            
        if self.is_qsfp(port_num,eeprom_path):
            byte86 = self._read_eeprom_specific_bytes(eeprom_path, QSFP_CONTROL_BYTES_OFFSET, QSFP_CONTROL_BYTES_WIDTH)[0]
            if byte86:
                data = int(byte86, 16)
                tx_disable_state.append(sffbase().test_bit(data, 0) != 0)
                tx_disable_state.append(sffbase().test_bit(data, 1) != 0)
                tx_disable_state.append(sffbase().test_bit(data, 2) != 0)
                tx_disable_state.append(sffbase().test_bit(data, 3) != 0)
        else:
            raw_data = self._read_eeprom_specific_bytes(eeprom_path, SFP_STATUS_CONTROL_OFFSET, SFP_STATUS_CONTROL_WIDTH)
            if raw_data:
                data = int(raw_data[0], 16)
                tx_disable_state.append(sffbase().test_bit(data, 7) != 0)

        self.close_port_eeprom_path( eeprom_path)
        return tx_disable_state

    def set_bit(self, n, bitpos):
        try:
            n = n | (1 << bitpos)
            return n
        except Exception:
            return -1

    def clear_bit(self, n, bitpos):
        try:
            n = n & (~(1 << bitpos))
            return n
        except Exception:
            return -1

    def get_tx_disable_channel(self, port_num):
        tx_disable_state = []
        tx_disable_channel = 0
        bit_num = 0

        tx_disable_state = self.get_tx_disable(port_num)
        
        for state in tx_disable_state:
            if state:
                tx_disable_channel = self.set_bit(tx_disable_channel, bit_num)
            else:
                tx_disable_channel = self.clear_bit(tx_disable_channel, bit_num)
            bit_num = bit_num + 1

        return tx_disable_channel

    def get_power_override(self, port_num):
        power_override_state = False

        if not self._is_valid_port(port_num):
            return power_override_state 

        if not self.get_presence(port_num):
            return power_override_state

        if port_num in self.sfp_ports:
            #N/A for SFP+ ports
            return power_override_state 

        if port_num in self.osfp_ports:
            #TBD: for QSFP-DD ports
            return power_override_state

        eeprom_path = self.open_port_to_eeprom_path(port_num)
        if eeprom_path is None:
            return power_override_state
            
        if self.is_qsfp(port_num,eeprom_path):
            byte93 = self._read_eeprom_specific_bytes(eeprom_path, QSFP_CONTROL_BYTES_OFFSET, QSFP_CONTROL_BYTES_WIDTH)[7]
            if byte93:
                data = int(byte93, 16)
                power_override_state = (sffbase().test_bit(data, 0) != 0)

        self.close_port_eeprom_path( eeprom_path)
        return power_override_state

    def set_power_override(self, port_num, power_override, power_set):
        status = False

        if not self._is_valid_port(port_num):
            return status

        if not self.get_presence(port_num):
            return status

        if port_num in self.sfp_ports:
            #N/A for SFP+ ports
            return power_override_state 

        if port_num in self.osfp_ports:
            #TBD: for QSFP-DD ports
            return status

        eeprom_path = self.open_port_to_eeprom_path(port_num)
        if eeprom_path is None:
            return status 
            
        if self.is_qsfp(port_num,eeprom_path):
            byte93 = self._read_eeprom_specific_bytes(eeprom_path, QSFP_CONTROL_BYTES_OFFSET, QSFP_CONTROL_BYTES_WIDTH)[7]
            if byte93:
                data = int(byte93, 16)
                if power_override:
                    data = self.set_bit(data, 0)
                    if power_set:
                        data = self.set_bit(data, 1)
                    else:
                        data = self.clear_bit(data, 1)
                else:
                    data = self.clear_bit(data, 0)

                run_cmd = '/usr/sbin/i2cset -y -f ' + str(self.EEPROM_OFFSET + port_num) + ' 0x' + str(self.EEPROM_OFFSET) + ' ' + str(QSFP_CONTROL_BYTES_OFFSET + 7) + ' ' + str(hex(data)) 
                os.system(run_cmd)
                status = True

        self.close_port_eeprom_path( eeprom_path)
        return status 

    def tx_disable(self, port_num, tx_disable):
        status = False

        if not self._is_valid_port(port_num):
            return status

        if not self.get_presence(port_num):
            return status

        if port_num in self.osfp_ports:
            #TBD: for QSFP-DD ports
            return status

        eeprom_path = self.open_port_to_eeprom_path(port_num)
        if eeprom_path is None:
            return status 
            
        if self.is_qsfp(port_num,eeprom_path):
            byte86 = self._read_eeprom_specific_bytes(eeprom_path, QSFP_CONTROL_BYTES_OFFSET, QSFP_CONTROL_BYTES_WIDTH)[0]
            if byte86:
                data = int(byte86, 16)
                if tx_disable:
                    data = self.set_bit(data, 0)
                    data = self.set_bit(data, 1)
                    data = self.set_bit(data, 2)
                    data = self.set_bit(data, 3)
                else:
                    data = self.clear_bit(data, 0)
                    data = self.clear_bit(data, 1)
                    data = self.clear_bit(data, 2)
                    data = self.clear_bit(data, 3)

                run_cmd = '/usr/sbin/i2cset -y -f ' + str(self.EEPROM_OFFSET + port_num) + ' 0x' + str(self.EEPROM_OFFSET) + ' ' + str(QSFP_CONTROL_BYTES_OFFSET) + ' ' + str(hex(data))
                os.system(run_cmd)
                status = True
        else:
            raw_data = self._read_eeprom_specific_bytes(eeprom_path, SFP_STATUS_CONTROL_OFFSET, SFP_STATUS_CONTROL_WIDTH)
            if raw_data:
                data = int(raw_data[0], 16)
                tx_disable_state = (sffbase().test_bit(data, 7) != 0)
                if tx_disable_state != tx_disable:
                    if tx_disable:
                        data = self.set_bit(data, 6) 
                    else:
                        data = self.clear_bit(data, 6)
                    #Write into soft TX disable select bit @ SFP_STATUS_CONTROL_OFFSET
                    run_cmd = '/usr/sbin/i2cset -y -f ' + str(self.EEPROM_OFFSET + port_num) + ' 0x' + str(self.EEPROM_OFFSET) + ' ' + str(SFP_STATUS_CONTROL_OFFSET) + ' ' + str(hex(data)) 
                    os.system(run_cmd)
                    status = True
        self.close_port_eeprom_path( eeprom_path)
        return status 

    def tx_disable_channel(self, port_num, channel, disable):
        status = False 
        
        if not self._is_valid_port(port_num):
            return status
        
        if not self.get_presence(port_num):
            return status

        if port_num in self.sfp_ports:
            #N/A for SFP+ ports
            return status

        if port_num in self.osfp_ports:
            #TBD: for QSFP-DD ports
            return status

        eeprom_path = self.open_port_to_eeprom_path(port_num)
        if eeprom_path is None:
            return status

        if self.is_qsfp(port_num,eeprom_path):
            byte86 = self._read_eeprom_specific_bytes(eeprom_path, QSFP_CONTROL_BYTES_OFFSET, QSFP_CONTROL_BYTES_WIDTH)[0]
            if byte86:
                data = int(byte86, 16)
                for lane in range(0,QSFP_NUM_CHANNELS):
                    mask = 1 << lane
                    if channel & mask:
                        if disable:
                            data = self.set_bit(data, lane)
                        else:
                            data = self.clear_bit(data, lane)

                run_cmd = '/usr/sbin/i2cset -y -f ' + str(self.EEPROM_OFFSET + port_num) + ' 0x' + str(self.EEPROM_OFFSET) + ' ' + str(QSFP_CONTROL_BYTES_OFFSET) + ' ' + str(hex(data)) 
                os.system(run_cmd)
                status = True

        self.close_port_eeprom_path( eeprom_path)
        return status

    def get_temperature(self, port_num):
        if self._is_valid_port(port_num) :
            if port_num in self.osfp_ports:
                return 'N/A'          #Need to handle it in future
            elif port_num in self.qsfp_ports:
                offset  = 0 + QSFP_TEMPE_OFFSET
                width = QSFP_TEMPE_WIDTH
                sfpd_obj = sff8436Dom()
                if sfpd_obj is None:
                    return 'N/A'
            else:
                offset = 256 + SFP_TEMPE_OFFSET
                width = SFP_TEMPE_WIDTH
                sfpd_obj = sff8472Dom()
                if sfpd_obj is None:
                    return 'N/A'

            eeprom_path = self.open_port_to_eeprom_path(port_num)
            if eeprom_path is None:
                return 'N/A'
           
            temperature_value = None
            raw_data = self._read_eeprom_specific_bytes(eeprom_path, offset, width)
            if raw_data is not None:
                dom_temperature_data = sfpd_obj.parse_temperature(raw_data, 0)
                temperature_value = dom_temperature_data['data']['Temperature']['value']
            self.close_port_eeprom_path( eeprom_path)
        return temperature_value

    def get_voltage(self, port_num):
        if self._is_valid_port(port_num) :
            if port_num in self.osfp_ports:
                return 'N/A'          #Need to handle it in future
            elif port_num in self.qsfp_ports:
                offset  = 0 + QSFP_VOLT_OFFSET
                width = QSFP_VOLT_WIDTH
                sfpd_obj = sff8436Dom()
                if sfpd_obj is None:
                    return 'N/A'
            else:
                offset = 256 + SFP_VOLT_OFFSET
                width = SFP_VOLT_WIDTH
                sfpd_obj = sff8472Dom()
                if sfpd_obj is None:
                    return 'N/A'

            eeprom_path = self.open_port_to_eeprom_path(port_num)
            if eeprom_path is None:
                return 'N/A'
           
            voltage_value = None
            raw_data = self._read_eeprom_specific_bytes(eeprom_path, offset, width)
            if raw_data is not None:
                dom_voltage_data = sfpd_obj.parse_voltage(raw_data, 0)
                voltage_value = dom_voltage_data['data']['Vcc']['value']
            self.close_port_eeprom_path( eeprom_path)
        return voltage_value 

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

