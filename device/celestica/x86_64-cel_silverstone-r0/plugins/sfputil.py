#!/usr/bin/env python
#
# Platform-specific SFP transceiver interface for SONiC
# This plugin supports QSFP-DD, QSFP and SFP.

try:
    import syslog
    import time
    import subprocess
    from collections import OrderedDict
    from sonic_platform_base.sonic_sfp.sfputilbase import SfpUtilBase
    from sonic_platform_base.sonic_sfp.sff8024 import type_of_transceiver
    from sonic_platform_base.sonic_sfp.sff8024 import type_of_media_interface
    from sonic_platform_base.sonic_sfp.sff8024 import host_electrical_interface
    from sonic_platform_base.sonic_sfp.sff8024 import nm_850_media_interface
    from sonic_platform_base.sonic_sfp.sff8024 import sm_media_interface
    from sonic_platform_base.sonic_sfp.sff8024 import passive_copper_media_interface
    from sonic_platform_base.sonic_sfp.sff8024 import active_cable_media_interface
    from sonic_platform_base.sonic_sfp.sff8024 import base_t_media_interface
    from sonic_platform_base.sonic_sfp.sff8472 import sff8472InterfaceId, sff8472Dom
    from sonic_platform_base.sonic_sfp.sff8436 import sff8436InterfaceId, sff8436Dom
    from sonic_platform_base.sonic_sfp.inf8628 import inf8628InterfaceId
    from sonic_platform_base.sonic_sfp.qsfp_dd import qsfp_dd_InterfaceId, qsfp_dd_Dom
    from sonic_platform_base.sonic_sfp.sffbase import sffbase
except ImportError as e:
    raise ImportError("%s - required module not found" % str(e))


PLATFORM_ROOT_PATH = '/usr/share/sonic/device'
SONIC_CFGGEN_PATH = '/usr/local/bin/sonic-cfggen'
HWSKU_KEY = 'DEVICE_METADATA.localhost.hwsku'
PLATFORM_KEY = 'DEVICE_METADATA.localhost.platform'

SYSLOG_IDENTIFIER = "sfputil.py"

def log_info(msg, also_print_to_console=False):
    syslog.openlog(SYSLOG_IDENTIFIER)
    syslog.syslog(syslog.LOG_INFO, msg)
    syslog.closelog()

    if also_print_to_console:
        print msg

class QSFPDDDomPaser(qsfp_dd_Dom):

    def __init__(self, eeprom_raw_data):

        start_pos = 0
        dom_offset = 256

        dom_module_monitor_values = {
            'Temperature':
                {'offset': 14,
                 'size': 2,
                 'type': 'func',
                 'decode': {'func': qsfp_dd_Dom.calc_temperature}},
            'Vcc':
                {'offset': 16,
                 'size': 2,
                 'type': 'func',
                 'decode': {'func': qsfp_dd_Dom.calc_voltage}}
        }

        dom_channel_monitor_params = {
            'RX8Power':
                {'offset': 72 + dom_offset,
                 'size': 2,
                 'type': 'func',
                 'decode': {'func': qsfp_dd_Dom.calc_rx_power}},
            'RX7Power':
                {'offset': 70 + dom_offset,
                 'size': 2,
                 'type': 'func',
                 'decode': {'func': qsfp_dd_Dom.calc_rx_power}},
            'RX6Power':
                {'offset': 68 + dom_offset,
                 'size': 2,
                 'type': 'func',
                 'decode': {'func': qsfp_dd_Dom.calc_rx_power}},
            'RX5Power':
                {'offset': 66 + dom_offset,
                 'size': 2,
                 'type': 'func',
                 'decode': {'func': qsfp_dd_Dom.calc_rx_power}},
            'RX4Power':
                {'offset': 64 + dom_offset,
                 'size': 2,
                 'type': 'func',
                 'decode': {'func': qsfp_dd_Dom.calc_rx_power}},
            'RX3Power':
                {'offset': 62 + dom_offset,
                 'size': 2,
                 'type': 'func',
                 'decode': {'func': qsfp_dd_Dom.calc_rx_power}},
            'RX2Power':
                {'offset': 60 + dom_offset,
                 'size': 2,
                 'type': 'func',
                 'decode': {'func': qsfp_dd_Dom.calc_rx_power}},
            'RX1Power':
                {'offset': 58 + dom_offset,
                 'size': 2,
                 'type': 'func',
                 'decode': {'func': qsfp_dd_Dom.calc_rx_power}},
            'TX8Bias':
                {'offset': 56 + dom_offset,
                 'size': 2,
                 'type': 'func',
                 'decode': {'func': qsfp_dd_Dom.calc_bias}},
            'TX7Bias':
                {'offset': 54 + dom_offset,
                 'size': 2,
                 'type': 'func',
                 'decode': {'func': qsfp_dd_Dom.calc_bias}},
            'TX6Bias':
                {'offset': 52 + dom_offset,
                 'size': 2,
                 'type': 'func',
                 'decode': {'func': qsfp_dd_Dom.calc_bias}},
            'TX5Bias':
                {'offset': 50 + dom_offset,
                 'size': 2,
                 'type': 'func',
                 'decode': {'func': qsfp_dd_Dom.calc_bias}},
            'TX4Bias':
                {'offset': 48 + dom_offset,
                 'size': 2,
                 'type': 'func',
                 'decode': {'func': qsfp_dd_Dom.calc_bias}},
            'TX3Bias':
                {'offset': 46 + dom_offset,
                 'size': 2,
                 'type': 'func',
                 'decode': {'func': qsfp_dd_Dom.calc_bias}},
            'TX2Bias':
                {'offset': 44 + dom_offset,
                 'size': 2,
                 'type': 'func',
                 'decode': {'func': qsfp_dd_Dom.calc_bias}},
            'TX1Bias':
                {'offset': 42 + dom_offset,
                 'size': 2,
                 'type': 'func',
                 'decode': {'func': qsfp_dd_Dom.calc_bias}},
            'TX8Power':
                {'offset': 40 + dom_offset,
                 'size': 2,
                 'type': 'func',
                 'decode': {'func': qsfp_dd_Dom.calc_tx_power}},
            'TX7Power':
                {'offset': 38 + dom_offset,
                 'size': 2,
                 'type': 'func',
                 'decode': {'func': qsfp_dd_Dom.calc_tx_power}},
            'TX6Power':
                {'offset': 36 + dom_offset,
                 'size': 2,
                 'type': 'func',
                 'decode': {'func': qsfp_dd_Dom.calc_tx_power}},
            'TX5Power':
                {'offset': 34 + dom_offset,
                 'size': 2,
                 'type': 'func',
                 'decode': {'func': qsfp_dd_Dom.calc_tx_power}},
            'TX4Power':
                {'offset': 32 + dom_offset,
                 'size': 2,
                 'type': 'func',
                 'decode': {'func': qsfp_dd_Dom.calc_tx_power}},
            'TX3Power':
                {'offset': 30 + dom_offset,
                 'size': 2,
                 'type': 'func',
                 'decode': {'func': qsfp_dd_Dom.calc_tx_power}},
            'TX2Power':
                {'offset': 28 + dom_offset,
                 'size': 2,
                 'type': 'func',
                 'decode': {'func': qsfp_dd_Dom.calc_tx_power}},
            'TX1Power':
                {'offset': 26 + dom_offset,
                 'size': 2,
                 'type': 'func',
                 'decode': {'func': qsfp_dd_Dom.calc_tx_power}}
        }

        dom_map = {
            'ModuleMonitorValues':
                {'type': 'nested',
                 'decode': dom_module_monitor_values},
            'ChannelMonitorValues':
                {'type': 'nested',
                 'decode': dom_channel_monitor_params}
        }

        self.dom_data = sffbase.parse(
            self, dom_map, eeprom_raw_data, start_pos)

    def get_data_pretty(self):
        return sffbase.get_data_pretty(self, self.dom_data)

class SfpUtil(SfpUtilBase):
    """Platform-specific SfpUtil class"""

    PORT_START = 1
    PORT_END = 34
    OSFP_PORT_START = 1
    OSFP_PORT_END = 32
    SFP_PORT_START = 33
    SFP_PORT_END = 34

    NUM_OSFP = 32

    EEPROM_OFFSET = 9
    PORT_INFO_PATH = '/sys/class/silverstone_fpga'
    QSFP_DD_DOM_OFFSET = 2304

    # polling interval in seconds
    POLL_INTERVAL = 1

    _port_name = ""
    _port_to_eeprom_mapping = {}
    _port_to_i2cbus_mapping = {}

    @property
    def port_start(self):
        return self.PORT_START

    @property
    def port_end(self):
        return self.PORT_END

    @property
    def qsfp_ports(self):
        return []

    @property
    def osfp_ports(self):
        return range(self.OSFP_PORT_START, self.OSFP_PORT_END + 1)

    @property
    def port_to_eeprom_mapping(self):
        return self._port_to_eeprom_mapping

    @property
    def port_to_i2cbus_mapping(self):
        return self._port_to_i2cbus_mapping

    def get_port_name(self, port_num):
        if port_num in self.osfp_ports:
            self._port_name = "QSFP" + str(port_num - self.OSFP_PORT_START + 1)
        else:
            self._port_name = "SFP" + str(port_num - self.SFP_PORT_START + 1)
        return self._port_name

    def get_eeprom_dom_raw(self, port_num):
        if port_num in self.osfp_ports:
            # QSFP DOM EEPROM is also at addr 0x50 and thus also stored in eeprom_ifraw
            return self._read_eeprom_devid(port_num, self.IDENTITY_EEPROM_ADDR, self.QSFP_DD_DOM_OFFSET, 128)
        else:
            # Read dom eeprom at addr 0x51
            return self._read_eeprom_devid(port_num, self.DOM_EEPROM_ADDR, 256)

    def __init__(self):
        self.inf8628 = inf8628InterfaceId()

        self.mod_presence = {}
        self.mod_failure = {}
        self.mod_inited = {}
        for x in range(self.PORT_START, self.PORT_END + 1):
            self.mod_inited[x] = False
            self.mod_failure[x] = 0
            self.mod_presence[x] = False

        self.hwsku = None
        try:
            proc = subprocess.Popen([SONIC_CFGGEN_PATH, '-d', '-v', HWSKU_KEY],
                                    stdout=subprocess.PIPE,
                                    shell=False,
                                    stderr=subprocess.STDOUT)
            stdout = proc.communicate()[0]
            proc.wait()
            self.hwsku = stdout.rstrip('\n')
        except:
            log_info("Cannot detect HwSku")

        # Override port_to_eeprom_mapping for class initialization
        eeprom_path = '/sys/bus/i2c/devices/i2c-{0}/{0}-0050/eeprom'

        for x in range(self.PORT_START, self.PORT_END + 1):
            self.port_to_i2cbus_mapping[x] = (x + self.EEPROM_OFFSET)
            self.port_to_eeprom_mapping[x] = eeprom_path.format(
                x + self.EEPROM_OFFSET)
        SfpUtilBase.__init__(self)

    def get_presence(self, port_num):
        # Check for invalid port_num
        if port_num not in range(self.port_start, self.port_end + 1):
            return False

        # Get path for access port presence status
        port_name = self.get_port_name(port_num)
        sysfs_filename = "qsfp_modprs" if port_num in self.osfp_ports else "sfp_modabs"
        reg_path = "/".join([self.PORT_INFO_PATH, port_name, sysfs_filename])

        # Read status
        try:
            reg_file = open(reg_path)
            content = reg_file.readline().rstrip()
            reg_value = int(content)
        except IOError as e:
            print "Error: unable to open file: %s" % str(e)
            return False

        # Module present is active low
        if reg_value == 0:
            return True

        return False

    def get_low_power_mode(self, port_num):
        # Check for invalid QSFP port_num
        if port_num not in self.osfp_ports:
            return False

        try:
            port_name = self.get_port_name(port_num)
            reg_file = open("/".join([self.PORT_INFO_PATH,
                                      port_name, "qsfp_lpmode"]))
        except IOError as e:
            print "Error: unable to open file: %s" % str(e)
            return False

        # Read status
        content = reg_file.readline().rstrip()
        reg_value = int(content)
        # low power mode is active high
        if reg_value == 0:
            return False

        return True

    def set_low_power_mode(self, port_num, lpmode):
        # Check for invalid QSFP port_num
        if port_num not in self.osfp_ports:
            return False

        try:
            port_name = self.get_port_name(port_num)
            reg_file = open("/".join([self.PORT_INFO_PATH,
                                      port_name, "qsfp_lpmode"]), "r+")
        except IOError as e:
            print "Error: unable to open file: %s" % str(e)
            return False

        content = hex(lpmode)

        reg_file.seek(0)
        reg_file.write(content)
        reg_file.close()

        return True

    def reset(self, port_num):
        # Check for invalid QSFP port_num
        if port_num not in self.osfp_ports:
            return False

        try:
            port_name = self.get_port_name(port_num)
            reg_file = open("/".join([self.PORT_INFO_PATH,
                                      port_name, "qsfp_reset"]), "w")
        except IOError as e:
            print "Error: unable to open file: %s" % str(e)
            return False

        # Convert our register value back to a hex string and write back
        reg_file.seek(0)
        reg_file.write(hex(0))
        reg_file.close()

        # Sleep 1 second to allow it to settle
        time.sleep(1)

        # Flip the bit back high and write back to the register to take port out of reset
        try:
            reg_file = open(
                "/".join([self.PORT_INFO_PATH, port_name, "qsfp_reset"]), "w")
        except IOError as e:
            print "Error: unable to open file: %s" % str(e)
            return False

        reg_file.seek(0)
        reg_file.write(hex(1))
        reg_file.close()

        return True

    def _page_to_flat(self, addr, page = -1):
        flat = 0
        if addr < 128:
            flat = addr
        else:
            flat = ((page + 1) << 7) | (addr & 0x7f)
        return flat

    def _write_byte(self, port_num, devid, page, off, val):
        eeprom_path = self._get_port_eeprom_path(port_num, devid)
        addr = self._page_to_flat(off, page)
        try:
            f = open(eeprom_path, "wb", 0)
            f.seek(addr)
            f.write(chr(val))
        except Exception as ex:
            log_info("PORT {0}: pg={1}, ofs={2}: write failed: {3}".format(port_num, page, off, ex))
        finally:
            f.close()

    def _get_application_advertisements(self, eeprom_ifraw=None, offset=85):
        adv = OrderedDict()
        if eeprom_ifraw is None:
            return adv

        tbl = self.parse_media_type(eeprom_ifraw, offset)
        if tbl is None:
            return adv

        app = 1
        hid = int(eeprom_ifraw[1 + offset], 16)
        while (app <= 8) and (hid != 0) and (hid != 0xff):
            (ht, mt) = self.parse_application(tbl, eeprom_ifraw[1 + offset], eeprom_ifraw[2 + offset])
            adv[app] = "{0} | {1}".format(ht, mt)
            app += 1
            offset += 4
            hid = int(eeprom_ifraw[1 + offset], 16)

        return adv

    def _get_application_code(self, port_num, host_intf):
        buf = self._read_eeprom_devid(port_num, self.IDENTITY_EEPROM_ADDR, 85, 36)
        if buf is None:
            return 1

        app = 1
        dict = self._get_application_advertisements(buf, 0)
        for k in dict:
            h = dict[k].split('|')[0].strip()
            if h in host_intf:
                app = k
                log_info("PORT {0}: selecting {1}#{2}".format(port_num, app, h))
                break
        return app

    def _init_cmis4_module(self, port_num, xcvr, hwsku):

        log_info("PORT {0}: {1}: _init_cmis4_module".format(port_num, xcvr))

        # Allow 1s for software reset
        self._write_byte(port_num, self.IDENTITY_EEPROM_ADDR, -1, 26, 0x58)
        time.sleep(1)
        # Deinitialize datapath
        self._write_byte(port_num, self.IDENTITY_EEPROM_ADDR, 0x10, 128, 0xff)
        time.sleep(0.5)
        # Hi-Power
        self._write_byte(port_num, self.IDENTITY_EEPROM_ADDR, -1, 26, 0x00)
        # Application selection
        app = 1
        if '128x100' in hwsku:
            app = self._get_application_code(port_num, '100GAUI-2 C2M (Annex 135G),100GBASE-CR2 (Clause 136)')
        if app != 1:
            self._write_byte(port_num, self.IDENTITY_EEPROM_ADDR, 0x10, 145, (app << 4) | 0x01)
            self._write_byte(port_num, self.IDENTITY_EEPROM_ADDR, 0x10, 146, (app << 4) | 0x01)
            self._write_byte(port_num, self.IDENTITY_EEPROM_ADDR, 0x10, 147, (app << 4) | 0x05)
            self._write_byte(port_num, self.IDENTITY_EEPROM_ADDR, 0x10, 148, (app << 4) | 0x05)
            self._write_byte(port_num, self.IDENTITY_EEPROM_ADDR, 0x10, 149, (app << 4) | 0x09)
            self._write_byte(port_num, self.IDENTITY_EEPROM_ADDR, 0x10, 150, (app << 4) | 0x09)
            self._write_byte(port_num, self.IDENTITY_EEPROM_ADDR, 0x10, 151, (app << 4) | 0x0d)
            self._write_byte(port_num, self.IDENTITY_EEPROM_ADDR, 0x10, 152, (app << 4) | 0x0d)
        else:
            self._write_byte(port_num, self.IDENTITY_EEPROM_ADDR, 0x10, 145, 0x11)
            self._write_byte(port_num, self.IDENTITY_EEPROM_ADDR, 0x10, 146, 0x11)
            self._write_byte(port_num, self.IDENTITY_EEPROM_ADDR, 0x10, 147, 0x11)
            self._write_byte(port_num, self.IDENTITY_EEPROM_ADDR, 0x10, 148, 0x11)
            self._write_byte(port_num, self.IDENTITY_EEPROM_ADDR, 0x10, 149, 0x11)
            self._write_byte(port_num, self.IDENTITY_EEPROM_ADDR, 0x10, 150, 0x11)
            self._write_byte(port_num, self.IDENTITY_EEPROM_ADDR, 0x10, 151, 0x11)
            self._write_byte(port_num, self.IDENTITY_EEPROM_ADDR, 0x10, 152, 0x11)
        self._write_byte(port_num, self.IDENTITY_EEPROM_ADDR, 0x10, 143, 0xff)
        # Initialize datapath
        self._write_byte(port_num, self.IDENTITY_EEPROM_ADDR, 0x10, 128, 0x00)

        # Validate configuration status
        err = '00000000'
        for t in range(10):
            time.sleep(1)
            buf = self._read_eeprom_devid(port_num, self.IDENTITY_EEPROM_ADDR, self._page_to_flat(202, 0x11), 4)
            err = "".join(buf)
            if err == '11111111':
                log_info("PORT {0}: it took {1} secs for config ready".format(port_num, t + 1))
                break
        if err != '11111111':
            log_info("PORT {0}: ConfigErr={1}".format(port_num, err))
            return False

        return True

    def _init_cmis_module(self, port_num):
        buf = self._read_eeprom_devid(port_num, self.IDENTITY_EEPROM_ADDR, 0x80, 48)
        if buf is None:
            log_info("PORT {0}: unable to read PAGE0".format(port_num))
            return False

        # Skip, in case of QSFP28
        if buf[0] not in "18,19":
            log_info("PORT {0}: skipped, it's not a QSFPDD".format(port_num))
            return True

        # Decode the transceiver ids
        name = self.inf8628.parse_vendor_name(buf, 1)['data']['Vendor Name']['value']
        part = self.inf8628.parse_vendor_pn(buf, 20)['data']['Vendor PN']['value']
        #log_info("_init_cmis_module: p={0}, id='{1}', name='{2}', part='{3}'".format(port_num, buf[0], name, part))
        xcvr = name.upper() + " " + part.upper()

        # Dispatch as per the CMIS revision id
        buf = self._read_eeprom_devid(port_num, self.IDENTITY_EEPROM_ADDR, 0x0, 4)
        rev = 0x30
        if buf is not None:
            rev = int(buf[1], 16)
        if rev >= 0x40:
            return self._init_cmis4_module(port_num, xcvr, self.hwsku)

        return True

    def get_transceiver_change_event(self, timeout=0):
        """
        :param timeout in milliseconds. The method is a blocking call. When timeout is 
         zero, it only returns when there is change event, i.e., transceiver plug-in/out
         event. When timeout is non-zero, the function can also return when the timer expires.
         When timer expires, the return status is True and events is empty.
        :returns: (status, events)
        :status: Boolean, True if call successful and no system level event/error occurred, 
         False if call not success or system level event/error occurred.
        :events: dictionary for physical port index and the SFP status,
         status='1' represent plug in, '0' represent plug out like {'0': '1', '31':'0'}
         when it comes to system level event/error, the index will be '-1',
         and status can be 'system_not_ready', 'system_become_ready', 'system_fail',
         like {'-1':'system_not_ready'}.
        """
        int_sfp = {}
        end_time = time.time() + (float(timeout) / 1000.0)
        while end_time > time.time():
            for x in range(self.PORT_START, self.PORT_END + 1):
                flag = self.get_presence(x)
                if flag != self.mod_presence[x]:
                    int_sfp[str(x)] = '1' if flag else '0'
                    self.mod_inited[x] = False
                    self.mod_failure[x] = 0
                    self.mod_presence[x] = flag

                # skip the following logic in case of module absent
                if not flag:
                    continue

                # monitor the QSFP-DD module state, and initiate software reset when failure count > 5
                buf = self._read_eeprom_devid(x, self.IDENTITY_EEPROM_ADDR, 0x0, 4)
                if buf is None:
                    log_info("PORT {0}: unable to get module state".format(x))
                    continue
                # skip, in case of QSFP28
                if buf[0] not in "18,19":
                    continue
                # skip, in case that CMIS < v3.0
                cmis = int(buf[1], 16)
                if cmis < 0x30:
                    continue
                # skip the init sequence for CMIS3
                if cmis < 0x40:
                    self.mod_inited[x] = True
                # advance the failure counter if state == ModuleLowPwr and CMIS < v4.0
                if (cmis < 0x40) and (((int(buf[3], 16) >> 1) & 0x7) == 1):
                    # fetch the module media type
                    buf = self._read_eeprom_devid(x, self.IDENTITY_EEPROM_ADDR, 85, 1)
                    if buf is None:
                        log_info("PORT {0}: unable to get module media type".format(x))
                    # perform a software reset only if it's not a DAC (Passive Copper)
                    elif int(buf[0], 16) != 0x03:
                        self.mod_failure[x] += 1
                else:
                    self.mod_failure[x] = 0
                # initiate QSFP-DD software reset if failure count > 5
                if self.mod_failure[x] > 5:
                    self.mod_failure[x] = 0
                    # This is actually a hotfix for 'Eoptolink EOLD-134HG-02-M6, QSFPDD CMIS v3',
                    # its module state could get stuck at ModuleLowPwr upon reinsertion, and a software
                    # reset is necessary to get it recovered.
                    log_info("PORT {0}: issuing a software reset".format(x))
                    self._write_byte(x, self.IDENTITY_EEPROM_ADDR, -1, 26, 0x08)
                    time.sleep(1)

                # monitor the QSFP-DD initialization state, and reinitiate it if necessary
                if self.mod_inited[x]:
                    continue
                buf = self._read_eeprom_devid(x, self.IDENTITY_EEPROM_ADDR, self._page_to_flat(202, 0x11), 4)
                if buf is None:
                    continue
                err = "".join(buf)
                if err != '11111111':
                    if not self._init_cmis_module(x):
                        log_info("PORT {0}: Unable to initialize the module".format(x))
                    else:
                        self.mod_inited[x] = True

            # break if the SFP change event is not empty
            if len(int_sfp) > 0:
                break

            time.sleep(1)
        return True, int_sfp

    def get_qsfp_data(self, eeprom_ifraw):
        sfp_data = {}
        sfpi_obj = sff8436InterfaceId(eeprom_ifraw)
        sfpd_obj = sff8436Dom(eeprom_ifraw) if sfpi_obj else {}

        sfp_data['interface'] = sfpi_obj.get_data_pretty() if sfpi_obj else {}
        sfp_data['dom'] = sfpd_obj.get_data_pretty() if sfpd_obj else {}
        return sfp_data

    def parse_media_type(self, eeprom_data, offset):
        media_type_code = eeprom_data[offset]
        dict_name = type_of_media_interface[media_type_code]
        if dict_name == "nm_850_media_interface":
            return nm_850_media_interface
        elif dict_name == "sm_media_interface":
            return sm_media_interface
        elif dict_name == "passive_copper_media_interface":
            return passive_copper_media_interface
        elif dict_name == "active_cable_media_interface":
            return active_cable_media_interface
        elif dict_name == "base_t_media_interface":
            return base_t_media_interface
        else:
             return None

    def parse_application(self, sfp_media_type_dict, host_interface, media_interface):
        host_result = host_electrical_interface[host_interface]
        media_result = sfp_media_type_dict[media_interface]
        return host_result, media_result

    def get_eeprom_dict(self, port_num):
        """Returns dictionary of interface and dom data.
        format: {<port_num> : {'interface': {'version' : '1.0', 'data' : {...}},
                               'dom' : {'version' : '1.0', 'data' : {...}}}}
        """

        sfp_data = {}

        eeprom_ifraw = self.get_eeprom_raw(port_num)
        eeprom_domraw = self.get_eeprom_dom_raw(port_num)

        if eeprom_ifraw is None:
            return None

        if port_num in self.osfp_ports:
            sfpi_obj = inf8628InterfaceId(eeprom_ifraw)
            if sfpi_obj:
                sfp_data['interface'] = sfpi_obj.get_data_pretty()

                # check if it is a 100G module
                if sfp_data['interface']['data']['Identifier'] not in [type_of_transceiver['18'], type_of_transceiver['19']]:
                    return self.get_qsfp_data(eeprom_ifraw)

                # decode application advertisement
                apps = ""
                dict = self._get_application_advertisements(eeprom_ifraw, 85)
                for a in dict:
                    apps += "\n                {0}: {1}".format(a, dict[a])
                if len(apps) > 0:
                    sfp_data['interface']['data']['Application Advertisement'] = apps

                # decode the running application code
                sel = 1
                eeprom_data = self._read_eeprom_devid(port_num, self.IDENTITY_EEPROM_ADDR, 0x880, 32)
                if eeprom_data is not None:
                    sel = int(eeprom_data[145 - 128], 16) >> 4
                    if sel < 1 or sel > len(dict):
                        sel = 1
                sfp_data['interface']['data']['Application Selected'] = "{0}".format(sel)

            sfpd_obj = QSFPDDDomPaser(
                eeprom_ifraw + eeprom_domraw) if eeprom_domraw else None
            sfp_data['dom'] = sfpd_obj.get_data_pretty() if sfpd_obj else {}

            return sfp_data
        else:
            sfpi_obj = sff8472InterfaceId(eeprom_ifraw)
            if sfpi_obj is not None:
                sfp_data['interface'] = sfpi_obj.get_data_pretty()
                cal_type = sfpi_obj.get_calibration_type()

            if eeprom_domraw is not None:
                sfpd_obj = sff8472Dom(eeprom_domraw, cal_type)
                if sfpd_obj is not None:
                    sfp_data['dom'] = sfpd_obj.get_data_pretty()

            return sfp_data
        return
