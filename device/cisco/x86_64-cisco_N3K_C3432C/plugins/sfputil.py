# sfputilcisco.py
#
# Platform-specific SFP transceiver interface for SONiC
#

try:
    import time
    from sonic_sfp.sfputilbase import SfpUtilBase
    from sonic_eeprom import eeprom_dts
    import sys

#    import syslog
    import os
    path = os.path.abspath(__file__)
    sys.path.append(os.path.dirname(path))
    from qsfpdd import qsfpddDom

except ImportError as e:
    raise ImportError("%s - required module not found" % str(e))

'''
SYSLOG_IDENTIFIER = os.path.basename(__file__)

def log_error(msg, also_print_to_console=False):
    syslog.openlog(SYSLOG_IDENTIFIER)
    syslog.syslog(syslog.LOG_ERR, msg)
    syslog.closelog()

    if also_print_to_console:
        print msg
'''

class SfpUtilCisco(SfpUtilBase):
    """Platform-specific SfpUtil class"""

    XCVR_CHANGE_WAIT_TIME = .2

    XCVR_PRESENCE_FILE = "/sys/class/mifpga/mifpga/xcvr_present"

    _xcvr_presence = None

    # Temporary change for sysfs_sfp_i2c_client_eeprompath in sfpbaseutil
    EEPROM_OFFSET = 50
    
    _eeprom_to_prt_mapping = {}

    def __init__(self):
        
        # Temporary change for sysfs_sfp_i2c_client_eeprompath in sfpbaseutil
        eeprom_path = "/sys/class/i2c-adapter/i2c-{0}/{0}-0050/eeprom"
        
        for prt in range(0, self.port_end + 1):
            epath = eeprom_path.format(prt + self.EEPROM_OFFSET)
            self._eeprom_to_prt_mapping[epath] = prt

        super(SfpUtilCisco, self).__init__()

    # Temporary change for sysfs_sfp_i2c_client_eeprompath in sfpbaseutil
    def _sfp_eeprom_present(self, sysfs_sfp_i2c_client_eeprompath, offset):
        eport = self._eeprom_to_prt_mapping[sysfs_sfp_i2c_client_eeprompath]
        #print("Port: %d Presence: %d" % (eport, self.get_presence(eport)))
        if self.get_presence(eport) == 1:
            return super(SfpUtilCisco, self)._sfp_eeprom_present(sysfs_sfp_i2c_client_eeprompath, offset)

        return False

    # Temporary change for sysfs_sfp_i2c_client_eeprompath in sfpbaseutil
    def _read_eeprom_specific_bytes(self, sysfsfile_eeprom, offset, num_bytes):
        eeprom_raw = []
        for i in range(0, num_bytes):
            eeprom_raw.append("0x00")

        try:
            sysfsfile_eeprom.seek(offset)
            raw = sysfsfile_eeprom.read(num_bytes)
        except IOError:
            #print("Error: reading sysfs file %s" % sysfs_sfp_i2c_client_eeprom_path)
            return None

        try:
            for n in range(0, num_bytes):
                eeprom_raw[n] = hex(ord(raw[n]))[2:].zfill(2)
        except:
            return None

        return eeprom_raw


    def unreset(self, port_num):
        # Check for invalid port_num
        if port_num < self.port_start or port_num > self.port_end:
            return False

        port_reset="/sys/class/mifpga/mifpga/qsfp_%d_reset/value" % (port_num+1)
        with open(port_reset, "w") as x_p_fp:
            x_p_fp.write("0")
        return True

    def get_transceiver_change_event(self, timeout=0):
        
        end_time = time.time() + timeout

        p_dict = {}
        while True:
            try:               
                with open(self.XCVR_PRESENCE_FILE, "r") as xcvr_file:
                    xcvr_status = xcvr_file.read().replace("\n", '')
                    xcvrs = [ int(c) for c in xcvr_status.strip() ]
                    
            except:
                print "Failed to open", self.XCVR_PRESENCE_FILE
                return False, {}
        
            if self._xcvr_presence is not None:
                # Previous state present. Check any change from previous state
                for p in range(0, self.port_end + 1):
                    if self._xcvr_presence[p] != xcvrs[p]:
                        # Add the change to dict
                        p_dict[str(p)] = str(xcvrs[p])
                        # if inserted then unreset
                        if xcvrs[p] == 1 :
                            self.unreset(p)
            
            self._xcvr_presence = xcvrs
            #print(xcvrs)
            #log_error("XCVR-LOG XCVRS: %s" % str(xcvrs), True)
            # if any change got added to dict in the comparison then return
            if p_dict:
                return True, p_dict
            
            cur_time = time.time()
            if cur_time >= end_time and timeout != 0:
                break
            elif (cur_time + self.XCVR_CHANGE_WAIT_TIME) >= end_time and timeout != 0:
                time.sleep(end_time - cur_time)
            else:
                time.sleep(self.XCVR_CHANGE_WAIT_TIME)
        

        return True, {}

    def reset_page(self, port_num, page):
        os.system("/usr/sbin/i2cset -y -f %d 0x50 127 %d b" % (port_num + self.EEPROM_OFFSET, page))
        sysfs_eeprom_file = "/sys/bus/i2c/devices/%d-0050/eeprom" % (port_num + self.EEPROM_OFFSET)

        with open(sysfs_eeprom_file, mode="rb", buffering=0) as sysfs_eeprom :
            sysfs_eeprom.seek(128)
            raw = sysfs_eeprom.read(128)


    def get_eeprom_dict(self, port_num):

        # Ensure page zero is set
        if port_num in self.osfp_ports:
            self.reset_page(port_num, 0)

        sfp_data = super(SfpUtilCisco, self).get_eeprom_dict(port_num)

        if sfp_data is None:
            return sfp_data

        if port_num in self.osfp_ports:
            sfpd_obj = qsfpddDom(port_num, sfp_data)
            if sfpd_obj is not None:
                sfp_data['dom'] = sfpd_obj.get_data_pretty()

        return sfp_data




# sfputil.py
#
# Platform-specific SFP transceiver interface for SONiC
#

#try:
#    import time
#    from cisco_sfp.sfputilcisco import SfpUtilCisco
#    from sonic_eeprom import eeprom_dts
#except ImportError as e:
#    raise ImportError("%s - required module not found" % str(e))

def sfp_log(msg):
    #print(msg)
    pass

class SfpUtil(SfpUtilCisco):
    """Platform-specific SfpUtil class"""

    PORT_START = 0
    PORT_END = 33 
    PORTS_IN_BLOCK = 34

    QSFP_PORT_START = 0
    QSFP_PORT_END = 31
    SFP_PORT_START = 32
    SFP_PORT_END = 33
    XCVR_PRESENCE_FILE = "/sys/class/mifpga/mifpga/xcvr_present"

    EEPROM_OFFSET = 50

    _port_to_eeprom_mapping = {}

    port_type_done = False
    qsfp_port_list = []
    qsfp_dd_port_list = []

    @property
    def port_start(self):
        return self.PORT_START

    @property
    def port_end(self):
        return self.PORT_END

    @property
    def qsfp_ports(self):
        self.qsfp_find_port_type_all()
        return self.qsfp_port_list
        #return range(0, self.PORTS_IN_BLOCK + 1)

    @property
    def osfp_ports(self):
        self.qsfp_find_port_type_all()
        return self.qsfp_dd_port_list
        #return range(0, self.PORTS_IN_BLOCK)
    
    @property
    def qsfp_port_start(self):
        return self.QSFP_PORT_START

    @property
    def qsfp_port_end(self):
        return self.QSFP_PORT_END

    @property
    def sfp_port_start(self):
        return self.SFP_PORT_START

    @property
    def sfp_port_end(self):
        return self.SFP_PORT_END

    @property
    def port_to_eeprom_mapping(self):
        return self._port_to_eeprom_mapping
    
    def get_presence(self, port_num):


        # Check for invalid port_num
        if port_num < self.PORT_START or port_num > self.PORT_END:
            return False

        #TO DO SFP PORTS
        if port_num >= self.SFP_PORT_START and port_num <= self.SFP_PORT_END:
            #return True
            port_present="/sys/class/mifpga/mifpga/sfp_%d_present/value" % (port_num+1)
        else:
            port_present="/sys/class/mifpga/mifpga/qsfp_%d_present/value" % (port_num+1)

        present = False
        with open(port_present, "r") as x_p_fp:
            xcvr_line = x_p_fp.readline()   ## Only one line of 0 & 1
            present = int(xcvr_line.strip())
        return present

        '''
        with open(self.XCVR_PRESENCE_FILE, "r") as x_p_fp:
            xcvr_line = x_p_fp.readlines()[0]   ## Only one line of 0 & 1
            xcvrs = [ int(c) for c in xcvr_line.strip() ]
            if xcvrs[port_num-1]:
                return True
        except:
            print "Failed to open", self.XCVR_PRESENCE_FILE
        '''

    def qsfp_find_port_type(self, p, offset=0):

        if (p < self.QSFP_PORT_START) or (p > self.QSFP_PORT_END):
            sfp_log("Port:%d out of qsfp range" % p)
            return

   
        if self.get_presence(p) == False:
            sfp_log("Port:%d not present" % p) 
            return

        eeprom_ifraw = self.get_eeprom_raw(p)
        #sfp_log(eeprom_ifraw)
        if eeprom_ifraw is None:
            return

        qsfp_off_id = int(eeprom_ifraw[offset], 16)
        
        if qsfp_off_id == 0x18:
            
            if p not in self.qsfp_dd_port_list:
                #sfp_log("port:%d %x offset %d" % (p, qsfp_off_id, offset))
                self.qsfp_dd_port_list.append(p)
            if p in self.qsfp_port_list:
                self.qsfp_port_list.remove(p)
        else:

            if p not in self.qsfp_port_list:
                #sfp_log("port:%d %x offset %d" % (p, qsfp_off_id, offset))
                self.qsfp_port_list.append(p)
            if p in self.qsfp_dd_port_list:
                self.qsfp_dd_port_list.remove(p)

    def qsfp_find_port_type_all(self):

        if self.port_type_done:
            return

        for p in range(0, self.QSFP_PORT_END + 1):
            self.qsfp_find_port_type(p)
        self.port_type_done = True

    def sfp_tx_enable(self, port_num):
        
        if self.get_presence(port_num) == False:
            sfp_log("sfp tx enable port:%d not present" % port_num)
            return

        tx_enable_path = "/sys/class/mifpga/mifpga/sfp_%d_tx_disable/value" % (port_num + 1)
                
        with open(tx_enable_path, "w") as x_p_fp:
            x_p_fp.write("1")



    def __init__(self):
        eeprom_path = "/sys/class/i2c-adapter/i2c-{0}/{0}-0050/eeprom"

        for x in range(0, self.PORT_END + 1):
            self._port_to_eeprom_mapping[x] = eeprom_path.format(x + self.EEPROM_OFFSET)
            #if x >= self.SFP_PORT_START and x <= self.SFP_PORT_END:
            #    self.sfp_tx_enable(x)

        super(SfpUtil, self).__init__()


    def reset(self, port_num):
        # Check for invalid port_num
        if port_num < self.QSFP_PORT_START or port_num > self.QSFP_PORT_END:
            return False

        port_reset="/sys/class/mifpga/mifpga/qsfp_%d_reset/value" % (port_num+1)
        with open(port_reset, "w") as x_p_fp:
            x_p_fp.write("1")
        return True

    def get_low_power_mode(self, port_num):
        # Check for invalid port_num
        if port_num < self.QSFP_PORT_START or port_num > self.QSFP_PORT_END:
            return False
        port_lpmode="/sys/class/mifpga/mifpga/qsfp_%d_lp_mode/value" % (port_num+1)
        mode = False
        with open(port_lpmode, "r") as x_p_fp:
            xcvr_line = x_p_fp.readline()   ## Only one line of 0 & 1
            mode = int(xcvr_line.strip())
        return True if mode else False

    def set_low_power_mode(self, port_num, lpmode):
        # Check for invalid port_num
        if port_num < self.QSFP_PORT_START or port_num > self.QSFP_PORT_END:
            return False
        port_lpmode="/sys/class/mifpga/mifpga/qsfp_%d_lp_mode/value" % (port_num+1)
        with open(port_lpmode, "w") as x_p_fp:
            x_p_fp.write("1" if lpmode else "0")
        return True
            
    def get_transceiver_change_event(self, timeout=0):
        
        status, p_dict = super(SfpUtil, self).get_transceiver_change_event(timeout)
        
        #FOR TEST  
        #time.sleep(1)
        #status, p_dict = True, {'13': '1', '15': '1' , '16':'0' , '25':'1', '32':'1', '-1':"1"}
        #status, p_dict = True, {'13': '1', '15': '1' , '16':'0' , '25':'1', '32':'1'}

        #Wait before reading data
        time.sleep(.1)
        if (status == True) and (p_dict is not None) and p_dict:
            for port, event in p_dict.iteritems():
                if event == '1':
                    sfp_log("Port:%s event:%s" % (port, event))
                    self.qsfp_find_port_type(int(port), 128)
                    if int(port) >= self.SFP_PORT_START and int(port) <= self.SFP_PORT_END:
                        self.sfp_tx_enable(int(port))

        
        sfp_log("qsfp:%s" % str(self.qsfp_port_list))
        sfp_log("qsfp dd:%s" % str(self.qsfp_dd_port_list))
        
        return status, p_dict



