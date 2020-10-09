#!/usr/bin/env python
#
# Platform-specific SFP transceiver interface for SONiC
# This plugin supports QSFP-DD, QSFP and SFP.

try:
    import time
    from sonic_sfp.sfputilbase import SfpUtilBase
    from sonic_sfp.sff8472 import sff8472InterfaceId, sff8472Dom
    from sonic_sfp.sff8436 import sff8436InterfaceId, sff8436Dom
    from sonic_platform_base.sonic_sfp.inf8628 import inf8628InterfaceId
    from sonic_platform_base.sonic_sfp.qsfp_dd import qsfp_dd_InterfaceId, qsfp_dd_Dom
    from sonic_platform_base.sonic_sfp.sffbase import sffbase
except ImportError as e:
    raise ImportError("%s - required module not found" % str(e))


class QSFPDDDomPaser(qsfp_dd_Dom):

    def __init__(self, eeprom_raw_data):
        start_pos = 0

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
                {'offset': 200,
                 'size': 2,
                 'type': 'func',
                 'decode': {'func': qsfp_dd_Dom.calc_rx_power}},
            'RX7Power':
                {'offset': 198,
                 'size': 2,
                 'type': 'func',
                 'decode': {'func': qsfp_dd_Dom.calc_rx_power}},
            'RX6Power':
                {'offset': 196,
                 'size': 2,
                 'type': 'func',
                 'decode': {'func': qsfp_dd_Dom.calc_rx_power}},
            'RX5Power':
                {'offset': 194,
                 'size': 2,
                 'type': 'func',
                 'decode': {'func': qsfp_dd_Dom.calc_rx_power}},
            'RX4Power':
                {'offset': 192,
                 'size': 2,
                 'type': 'func',
                 'decode': {'func': qsfp_dd_Dom.calc_rx_power}},
            'RX3Power':
                {'offset': 190,
                 'size': 2,
                 'type': 'func',
                 'decode': {'func': qsfp_dd_Dom.calc_rx_power}},
            'RX2Power':
                {'offset': 188,
                 'size': 2,
                 'type': 'func',
                 'decode': {'func': qsfp_dd_Dom.calc_rx_power}},
            'RX1Power':
                {'offset': 186,
                 'size': 2,
                 'type': 'func',
                 'decode': {'func': qsfp_dd_Dom.calc_rx_power}},
            'TX8Bias':
                {'offset': 184,
                 'size': 2,
                 'type': 'func',
                 'decode': {'func': qsfp_dd_Dom.calc_bias}},
            'TX7Bias':
                {'offset': 182,
                 'size': 2,
                 'type': 'func',
                 'decode': {'func': qsfp_dd_Dom.calc_bias}},
            'TX6Bias':
                {'offset': 180,
                 'size': 2,
                 'type': 'func',
                 'decode': {'func': qsfp_dd_Dom.calc_bias}},
            'TX5Bias':
                {'offset': 178,
                 'size': 2,
                 'type': 'func',
                 'decode': {'func': qsfp_dd_Dom.calc_bias}},
            'TX4Bias':
                {'offset': 176,
                 'size': 2,
                 'type': 'func',
                 'decode': {'func': qsfp_dd_Dom.calc_bias}},
            'TX3Bias':
                {'offset': 174,
                 'size': 2,
                 'type': 'func',
                 'decode': {'func': qsfp_dd_Dom.calc_bias}},
            'TX2Bias':
                {'offset': 172,
                 'size': 2,
                 'type': 'func',
                 'decode': {'func': qsfp_dd_Dom.calc_bias}},
            'TX1Bias':
                {'offset': 170,
                 'size': 2,
                 'type': 'func',
                 'decode': {'func': qsfp_dd_Dom.calc_bias}},
            'TX8Power':
                {'offset': 168,
                 'size': 2,
                 'type': 'func',
                 'decode': {'func': qsfp_dd_Dom.calc_tx_power}},
            'TX7Power':
                {'offset': 166,
                 'size': 2,
                 'type': 'func',
                 'decode': {'func': qsfp_dd_Dom.calc_tx_power}},
            'TX6Power':
                {'offset': 164,
                 'size': 2,
                 'type': 'func',
                 'decode': {'func': qsfp_dd_Dom.calc_tx_power}},
            'TX5Power':
                {'offset': 162,
                 'size': 2,
                 'type': 'func',
                 'decode': {'func': qsfp_dd_Dom.calc_tx_power}},
            'TX4Power':
                {'offset': 160,
                 'size': 2,
                 'type': 'func',
                 'decode': {'func': qsfp_dd_Dom.calc_tx_power}},
            'TX3Power':
                {'offset': 158,
                 'size': 2,
                 'type': 'func',
                 'decode': {'func': qsfp_dd_Dom.calc_tx_power}},
            'TX2Power':
                {'offset': 156,
                 'size': 2,
                 'type': 'func',
                 'decode': {'func': qsfp_dd_Dom.calc_tx_power}},
            'TX1Power':
                {'offset': 154,
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

    EEPROM_OFFSET = 9
    PORT_INFO_PATH = '/sys/class/silverstone_fpga'

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
            return None
        else:
            # Read dom eeprom at addr 0x51
            return self._read_eeprom_devid(port_num, self.DOM_EEPROM_ADDR, 256)

    def __init__(self):
        # Override port_to_eeprom_mapping for class initialization
        eeprom_path = '/sys/bus/i2c/devices/i2c-{0}/{0}-0050/eeprom'

        for x in range(self.PORT_START, self.PORT_END+1):
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

    def get_transceiver_change_event(self, timeout=0):
        """
        TBD
        """
        raise NotImplementedError

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
            if sfpi_obj is not None:
                sfp_data['interface'] = sfpi_obj.get_data_pretty()

            sfpd_obj = QSFPDDDomPaser(eeprom_ifraw)
            if sfpd_obj is not None:
                sfp_data['dom'] = sfpd_obj.get_data_pretty()

            return sfp_data
        elif port_num in self.qsfp_ports:
            sfpi_obj = sff8436InterfaceId(eeprom_ifraw)
            if sfpi_obj is not None:
                sfp_data['interface'] = sfpi_obj.get_data_pretty()
            # For Qsfp's the dom data is part of eeprom_if_raw
            # The first 128 bytes

            sfpd_obj = sff8436Dom(eeprom_ifraw)
            if sfpd_obj is not None:
                sfp_data['dom'] = sfpd_obj.get_data_pretty()

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
