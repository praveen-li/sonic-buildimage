#!/usr/bin/env python

#############################################################################
# Linkedin open19 Bolt switch sfputil plugin (class SfpUtil)
#############################################################################
try:
    import os
    import binascii
    import shlex
    import subprocess
    from sonic_sfp.sfputilbase import SfpUtilBase
except ImportError as e:
    raise ImportError("%s - required module not found" % str(e))

class SfpUtil(SfpUtilBase):
    """Platform-specific SfpUtil class"""
    PORT_NUM_OFFSET   = 24
    QSFP_I2C_MUX_ADDR = "0x70"
    QSFP_EEPROM_ADDR  = "0x50"
    QSFP_EEPROM_OFFSET= "0x00"
    QSFP_EEPROM_SIZE  = 0x100

    #indexed by internal qsfp_port (0 - 7)
    _eeprom_port2channel = [0x2, 0x1, 0x8, 0x4, 0x20, 0x10, 0x80, 0x40]

    QSFP_STATE_MUX_ADDR       = "0x74"

    QSFP_PRESENCE_RXLOSS_CH   = "0x01"
    QSFP_PRESENCE_RXLOSS_ADDR = "0x20"
    QSFP_PRESENCE_OFFSET      = "0x00"
    QSFP_PRESENCE_BYTES       = 1
    QSFP_PRESENCE_ACT_LOW     = 1
    QSFP_RXLOSS_OFFSET        = "0x01"
    QSFP_RXLOSS_BYTES         = 1
    QSFP_RXLOSS_ACT_LOW       = 0

    QSFP_RESET_LPMODE_CH      = "0x02"
    QSFP_RESET_LPMODE_ADDR    = "0x21"
    QSFP_RESET_OFFSET         = "0x00"
    QSFP_RESET_BYTES          = 1
    QSFP_RESET_ACT_LOW        = 1
    QSFP_LPMODE_OFFSET        = "0x01"
    QSFP_LPMODE_BYTES         = 1
    QSFP_LPMODE_ACT_LOW       = 0

    #below are all indexed by port (0-7), value is bit position (0 based)
    _presence_bitmap = [1, 0, 3, 2, 5, 4, 7, 6]
    _rxloss_bitmap   = [7, 6, 5, 4, 3, 2, 1, 0]
    _reset_bitmap    = [7, 6, 5, 4, 3, 2, 1, 0]
    _lpmode_bitmap   = [1, 0, 3, 2, 5, 4, 7, 6]

    EEPROM_FILE = "/tmp/.qsfp{}_eeprom"
    _qsfps_presence = 0
    _qsfps_lpmode = 0

    PORTS_IN_BLOCK = 8
    PORT_START = PORT_NUM_OFFSET
    PORT_END = PORT_NUM_OFFSET + PORTS_IN_BLOCK - 1

    _port_to_eeprom_mapping = {}
    _qsfp_ports = range(PORT_START, PORT_START + PORTS_IN_BLOCK)

    _sfp_ports = []
    for x in range(PORT_START, PORT_END + 1):
        _sfp_ports.append(x)

    @property
    def sfp_ports(self):
        return self._sfp_ports

    @property
    def port_start(self):
        return self.PORT_START

    @property
    def port_end(self):
        return self.PORT_END

    @property
    def qsfp_ports(self):
        return self._qsfp_ports

    @property
    def port_to_eeprom_mapping(self):
        return self._port_to_eeprom_mapping

    def _i2c_write_command(self, addr, channel):
        cmd = "/usr/bin/bcmcmd 'i2c write {} {}'".format(addr, channel)
        p = subprocess.Popen(shlex.split(cmd), shell=False, stdout=subprocess.PIPE)
        (_, err) = p.communicate()
        if err:
            raise IOError("could not communicate to I2C driver")

    def _i2c_read_command(self, addr, offset, size):
        cmd = "/usr/bin/bcmcmd 'i2c read {} {} {}'".format(addr, offset, size)
        p = subprocess.Popen(shlex.split(cmd), shell=False, stdout=subprocess.PIPE)
        (output, err) = p.communicate()
        if err:
            raise IOError("could not communicate to I2C driver")
        return output


    """ output example for EEPROM:
    i2c read 0x50 0xA0 0x100

    00: 20 20 20 20 1f 00 25 63 4c 55 58 34 32 36 30 34
    10: 42 4f 20 20 20 20 20 20 42 20 66 58 0b b8 00 ca
    20: 07 07 ff 3a 31 36 33 36 30 30 31 32 31 39 20 20
    30: 20 20 20 20 31 36 30 39 30 38 20 20 0c 18 68 08
    40: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
    50: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
    60: 11 07 00 00 00 00 00 00 00 00 00 00 00 00 00 00
    70: 00 00 00 00 00 00 23 43 00 00 7c ba 00 00 00 00
    80: 00 00 1a e2 1a 28 22 64 20 b2 69 f5 69 f5 69 f5
    90: 69 f5 17 a0 19 44 1a be 1a 94 00 00 00 00 00 00
    a0: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
    b0: 00 00 00 00 00 00 00 aa aa 00 00 00 00 00 00 00
    c0: 00 00 ff 00 00 00 00 00 00 00 00 00 00 00 00 00
    d0: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
    e0: 11 cc 0c 80 00 00 00 00 00 00 00 05 ff 02 02 00
    f0: 00 00 00 40 4c 55 58 54 45 52 41 20 20 20 20 20

    drivshell>
    """

    """ Output sample for other registers
    i2c read 0x20 0 1

    00: 10

    drivshell>
    """
    def _shell_text_strip(self, output):
        string_list = output.split("\r")
        # expect more than 4 lines, the first 2 and last 2 will be skipped
        if (len(string_list) <= 4):
            raise IOError("Read Error from Shell")
        return string_list[2:-2]

    def _parse_i2c_text_to_hex(self, output):
        output_content = self._shell_text_strip(output)
        string_list1 = []
        # split each line by ":", only right side is used
        for item in output_content:
            item1 = item.split(":")
            if (len(item1) == 2):
                string_list1.append(item1[1])
        # concatenate the string and remove all spaces
        hexstring = "".join(string_list1).replace(" ", "")
        return hexstring

    def _parse_eeprom_text_to_hex(self, output, data_size):
        hexstring = self._parse_i2c_text_to_hex(output)
        hex_output = binascii.a2b_hex(hexstring)
        data_len = len(hex_output)
        # Either specified data size or no data was returned
        if (data_len != data_size and data_len != 0):
            raise RuntimeError("Parse error for the data")
        return hex_output

    # Read EEPROM data from driver and write it to a file for CLI to use
    def _read_qsfp_eeprom_to_file(self, qsfp_port):
        # select i2c mux and channel for I2C eeprom
        self._i2c_write_command(self.QSFP_I2C_MUX_ADDR, self._eeprom_port2channel[qsfp_port])

        # read data
        out = self._i2c_read_command(self.QSFP_EEPROM_ADDR, self.QSFP_EEPROM_OFFSET, self.QSFP_EEPROM_SIZE)
        output_hex = self._parse_eeprom_text_to_hex(out, self.QSFP_EEPROM_SIZE)
        with open(self.EEPROM_FILE.format(qsfp_port), "wb") as file:
            file.write(output_hex)
        file.close()
        return

    # Get data from driver as integer
    def _parse_i2c_text_to_int(self, output, data_size):
        hexstring = self._parse_i2c_text_to_hex(output)
        # Hexstring size is double of bytes number
        if (len(hexstring) != 2*data_size):
            raise RuntimeError("Parse error for the data")
        int_data = int (hexstring, 16)
        return int_data

    def _read_qsfps_presence(self):
        # select i2c mux and channel for presence io
        self._i2c_write_command(self.QSFP_STATE_MUX_ADDR, self.QSFP_PRESENCE_RXLOSS_CH)

        # read data
        out = self._i2c_read_command(self.QSFP_PRESENCE_RXLOSS_ADDR, self.QSFP_PRESENCE_OFFSET, self.QSFP_PRESENCE_BYTES)
        data = self._parse_i2c_text_to_int(out, self.QSFP_PRESENCE_BYTES)
        return data

    def _get_qsfp_presence(self, data, qsfp_port):
        port_bit = (data >> self._presence_bitmap[qsfp_port]) & 0x01
        if self.QSFP_PRESENCE_ACT_LOW:
            retval = 1 - port_bit
        else:
            retval = port_bit
        return (retval)

    def _read_qsfps_lpmode(self):
        # select i2c mux and channel for presence io
        self._i2c_write_command(self.QSFP_STATE_MUX_ADDR, self.QSFP_RESET_LPMODE_CH)

        # read data
        out = self._i2c_read_command(self.QSFP_RESET_LPMODE_ADDR, self.QSFP_LPMODE_OFFSET, self.QSFP_LPMODE_BYTES)
        data = self._parse_i2c_text_to_int(out, self.QSFP_LPMODE_BYTES)
        return data

    def _get_qsfp_lpmode(self, data, qsfp_port):
        port_bit = (data >> self._lpmode_bitmap[qsfp_port]) & 0x01
        if self.QSFP_LPMODE_ACT_LOW:
            retval = 1 - port_bit
        else:
            retval = port_bit
        return (retval)

    def _get_qsfp_port_from_port(self, port_num):
        return port_num - self.PORT_NUM_OFFSET

    def __init__(self):
        # Save the values for presence and lpmode of all ports to be used later
        self._qsfps_presence = self._read_qsfps_presence()
        self._qsfps_lpmode = self._read_qsfps_lpmode()

        # Override port_to_eeprom_mapping for class initialization
        for x in range(self.PORT_START, self.PORT_END + 1):
            qsfp_port = self._get_qsfp_port_from_port(x)
            eeprom_file = self.EEPROM_FILE.format(qsfp_port)
            if os.path.isfile(eeprom_file):
                os.remove(eeprom_file)
            if (self._get_qsfp_presence(self._qsfps_presence, qsfp_port)):
                self._read_qsfp_eeprom_to_file(qsfp_port)
            self.port_to_eeprom_mapping[x] = eeprom_file

        SfpUtilBase.__init__(self)

    # Get the QSFP presence @port_num
    def get_presence(self, port_num):
        # Check for port number range
        if port_num < self.port_start or port_num > self.port_end:
            raise RuntimeError("port number is invalid")

        qsfp_port = self._get_qsfp_port_from_port(port_num)
        qsfp_presence = self._get_qsfp_presence(self._qsfps_presence, qsfp_port)
        return qsfp_presence

    # Get the low power mode @port_num
    def get_low_power_mode(self, port_num):
        # Check for port number range
        if port_num < self.port_start or port_num > self.port_end:
            raise RuntimeError("port number is invalid")

        qsfp_port = self._get_qsfp_port_from_port(port_num)
        qsfp_lpmode = self._get_qsfp_lpmode(self._qsfps_lpmode, qsfp_port)
        return qsfp_lpmode

    # Set the low power mode @port_num
    def set_low_power_mode(self, port_num, lpmode):
        raise NotImplementedError

    # Reset the QSFP @port_num
    def reset(self, port_num):
        raise NotImplementedError

    def get_transceiver_change_event(self, timeout=0):
        raise NotImplementedError
