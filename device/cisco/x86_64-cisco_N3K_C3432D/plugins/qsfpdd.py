#! /usr/bin/env python

from __future__ import print_function

try:
    import fcntl
    import struct
    import sys
    import time
    import binascii
    import os
    import getopt
    import types
    from math import log10
    from collections import OrderedDict
    import re
    from sonic_sfp.sffbase import sffbase
except ImportError as e:
    raise ImportError (str(e) + "- required module not found")

def sfp_log(msg):
    #print(msg)
    pass


class qsfpddDom(sffbase):


    version = '1.0'

    dom_ext_calibration_constants = {'RX_PWR_4':
                        {'offset':56,
                         'size':4},
                    'RX_PWR_3':
                        {'offset':60,
                        'size':4},
                        'RX_PWR_2':
                        {'offset':64,
                         'size':4},
                        'RX_PWR_1':
                        {'offset':68,
                         'size':4},
                        'RX_PWR_0':
                        {'offset':72,
                         'size':4},
                        'TX_I_Slope':
                        {'offset':76,
                         'size':2},
                    'TX_I_Offset':
                        {'offset':78,
                         'size':2},
                    'TX_PWR_Slope':
                        {'offset':80,
                         'size':2},
                    'TX_PWR_Offset':
                        {'offset':82,
                         'size':2},
                    'T_Slope':
                        {'offset':84,
                         'size':2},
                    'T_Offset':
                        {'offset':86,
                         'size':2},
                    'V_Slope':
                        {'offset':88,
                         'size':2},
                    'V_Offset':
                        {'offset':90,
                         'size':2}}


    def get_calibration_type(self):
        return self._calibration_type

    def calc_temperature(self, eeprom_data, offset, size):
        try:
            cal_type = self.get_calibration_type()

            msb = int(eeprom_data[offset], 16)
            lsb = int(eeprom_data[offset + 1], 16)

            result = (msb << 8) | (lsb & 0xff)
            result = self.twos_comp(result, 16)

            if cal_type == 1:

                # Internal calibration

                result = float(result / 256.0)
                retval = '%.4f' %result + 'C'
            elif cal_type == 2:

                # External calibration

                # T(C) = T_Slope * T_AD + T_Offset
                off = self.dom_ext_calibration_constants['T_Slope']['offset']
                msb_t = int(eeprom_data[off], 16)
                lsb_t = int(eeprom_data[off + 1], 16)
                t_slope = (msb_t << 8) | (lsb_t & 0xff)

                off = self.dom_ext_calibration_constants['T_Offset']['offset']
                msb_t = int(eeprom_data[off], 16)
                lsb_t = int(eeprom_data[off + 1], 16)
                t_offset = (msb_t << 8) | (lsb_t & 0xff)
                t_offset = self.twos_comp(t_offset, 16)

                result = t_slope * result + t_offset
                result = float(result / 256.0)
                retval = '%.4f' %result + 'C'
            else:
                retval = 'Unknown'
        except Exception as err:
            retval = str(err)

        return retval


    def calc_voltage(self, eeprom_data, offset, size):
        try:
            cal_type = self.get_calibration_type()

            msb = int(eeprom_data[offset], 16)
            lsb = int(eeprom_data[offset + 1], 16)
            result = (msb << 8) | (lsb & 0xff)

            if cal_type == 1:

                # Internal Calibration

                result = float(result * 0.0001)
                #print(indent, name, ' : %.4f' %result, 'Volts')
                retval = '%.4f' %result + 'Volts'
            elif cal_type == 2:

                # External Calibration

                # V(uV) = V_Slope * VAD + V_Offset
                off = self.dom_ext_calibration_constants['V_Slope']['offset']
                msb_v = int(eeprom_data[off], 16)
                lsb_v = int(eeprom_data[off + 1], 16)
                v_slope = (msb_v << 8) | (lsb_v & 0xff)

                off = self.dom_ext_calibration_constants['V_Offset']['offset']
                msb_v = int(eeprom_data[off], 16)
                lsb_v = int(eeprom_data[off + 1], 16)
                v_offset = (msb_v << 8) | (lsb_v & 0xff)
                v_offset = self.twos_comp(v_offset, 16)

                result = v_slope * result + v_offset
                result = float(result * 0.0001)
                #print(indent, name, ' : %.4f' %result, 'Volts')
                retval = '%.4f' %result + 'Volts'
            else:
                #print(indent, name, ' : Unknown')
                retval = 'Unknown'
        except Exception as err:
            retval = str(err)

        return retval


    def calc_bias(self, eeprom_data, offset, size):
        try:
            cal_type = self.get_calibration_type()

            msb = int(eeprom_data[offset], 16)
            lsb = int(eeprom_data[offset + 1], 16)
            result = (msb << 8) | (lsb & 0xff)

            if cal_type == 1:
                # Internal Calibration
                multiplier = self.parse_sff_element(eeprom_data, self.dom_bias_multiplier, 0)
                #print("multiplier: %d" % multiplier)
                result = float(result * multiplier * 0.002)
                #print(indent, name, ' : %.4f' %result, 'mA')
                retval = '%.4f' %result + 'mA'

            elif cal_type == 2:
                # External Calibration

                # I(uA) = I_Slope * I_AD + I_Offset
                off = self.dom_ext_calibration_constants['I_Slope']['offset']
                msb_i = int(eeprom_data[off], 16)
                lsb_i = int(eeprom_data[off + 1], 16)
                i_slope = (msb_i << 8) | (lsb_i & 0xff)

                off = self.dom_ext_calibration_constants['I_Offset']['offset']
                msb_i = int(eeprom_data[off], 16)
                lsb_i = int(eeprom_data[off + 1], 16)
                i_offset = (msb_i << 8) | (lsb_i & 0xff)
                i_offset = self.twos_comp(i_offset, 16)

                result = i_slope * result + i_offset
                result = float(result * 0.002)
                #print(indent, name, ' : %.4f' %result, 'mA')
                retval = '%.4f' %result + 'mA'
            else:
                retval = 'Unknown'
        except Exception as err:
            retval = str(err)

        return retval


    def calc_tx_power(self, eeprom_data, offset, size):
        try:
            cal_type = self.get_calibration_type()

            msb = int(eeprom_data[offset], 16)
            lsb = int(eeprom_data[offset + 1], 16)
            result = (msb << 8) | (lsb & 0xff)

            if cal_type == 1:

                result = float(result * 0.0001)
                #print(indent, name, ' : ', power_in_dbm_str(result))
                retval = self.power_in_dbm_str(result)

            elif cal_type == 2:

                # TX_PWR(uW) = TX_PWR_Slope * TX_PWR_AD + TX_PWR_Offset
                off = self.dom_ext_calibration_constants['TX_PWR_Slope']['offset']
                msb_tx_pwr = int(eeprom_data[off], 16)
                lsb_tx_pwr = int(eeprom_data[off + 1], 16)
                tx_pwr_slope = (msb_tx_pwr << 8) | (lsb_tx_pwr & 0xff)

                off = self.dom_ext_calibration_constants['TX_PWR_Offset']['offset']
                msb_tx_pwr = int(eeprom_data[off], 16)
                lsb_tx_pwr = int(eeprom_data[off + 1], 16)
                tx_pwr_offset = (msb_tx_pwr << 8) | (lsb_tx_pwr & 0xff)
                tx_pwr_offset = self.twos_comp(tx_pwr_offset, 16)

                result = tx_pwr_slope * result + tx_pwr_offset
                result = float(result * 0.0001)
                retval = self.power_in_dbm_str(result)
            else:
                retval = 'Unknown'
        except Exception as err:
                retval = str(err)

        return retval

    def calc_rx_power(self, eeprom_data, offset, size):
        try:
            cal_type = self.get_calibration_type()

            msb = int(eeprom_data[offset], 16)
            lsb = int(eeprom_data[offset + 1], 16)
            result = (msb << 8) | (lsb & 0xff)

            if cal_type == 1:

                # Internal Calibration
                result = float(result * 0.0001)
                #print(indent, name, " : ", power_in_dbm_str(result))
                retval = self.power_in_dbm_str(result)

            elif cal_type == 2:

                # External Calibration

                # RX_PWR(uW) = RX_PWR_4 * RX_PWR_AD +
                #          RX_PWR_3 * RX_PWR_AD +
                #          RX_PWR_2 * RX_PWR_AD +
                #          RX_PWR_1 * RX_PWR_AD +
                #          RX_PWR(0)
                off = self.dom_ext_calibration_constants['RX_PWR_4']['offset']
                rx_pwr_byte3 = int(eeprom_data[off], 16)
                rx_pwr_byte2 = int(eeprom_data[off + 1], 16)
                rx_pwr_byte1 = int(eeprom_data[off + 2], 16)
                rx_pwr_byte0 = int(eeprom_data[off + 3], 16)
                rx_pwr_4 = (rx_pwr_byte3 << 24) | (rx_pwr_byte2 << 16) | (rx_pwr_byte1 << 8) | (rx_pwr_byte0 & 0xff)

                off = self.dom_ext_calibration_constants['RX_PWR_3']['offset']
                rx_pwr_byte3 = int(eeprom_data[off], 16)
                rx_pwr_byte2 = int(eeprom_data[off + 1], 16)
                rx_pwr_byte1 = int(eeprom_data[off + 2], 16)
                rx_pwr_byte0 = int(eeprom_data[off + 3], 16)
                rx_pwr_3 = (rx_pwr_byte3 << 24) | (rx_pwr_byte2 << 16) | (rx_pwr_byte1 << 8) | (rx_pwr_byte0 & 0xff)

                off = self.dom_ext_calibration_constants['RX_PWR_2']['offset']
                rx_pwr_byte3 = int(eeprom_data[off], 16)
                rx_pwr_byte2 = int(eeprom_data[off + 1], 16)
                rx_pwr_byte1 = int(eeprom_data[off + 2], 16)
                rx_pwr_byte0 = int(eeprom_data[off + 3], 16)
                rx_pwr_2 = (rx_pwr_byte3 << 24) | (rx_pwr_byte2 << 16) | (rx_pwr_byte1 << 8) | (rx_pwr_byte0 & 0xff)

                off = self.dom_ext_calibration_constants['RX_PWR_1']['offset']
                rx_pwr_byte3 = int(eeprom_data[off], 16)
                rx_pwr_byte2 = int(eeprom_data[off + 1], 16)
                rx_pwr_byte1 = int(eeprom_data[off + 2], 16)
                rx_pwr_byte0 = int(eeprom_data[off + 3], 16)
                rx_pwr_1 = (rx_pwr_byte3 << 24) | (rx_pwr_byte2 << 16) | (rx_pwr_byte1 << 8) | (rx_pwr_byte0 & 0xff)

                off = self.dom_ext_calibration_constants['RX_PWR_0']['offset']
                rx_pwr_byte3 = int(eeprom_data[off], 16)
                rx_pwr_byte2 = int(eeprom_data[off + 1], 16)
                rx_pwr_byte1 = int(eeprom_data[off + 2], 16)
                rx_pwr_byte0 = int(eeprom_data[off + 3], 16)
                rx_pwr_0 = (rx_pwr_byte3 << 24) | (rx_pwr_byte2 << 16) | (rx_pwr_byte1 << 8) | (rx_pwr_byte0 & 0xff)

                rx_pwr = (rx_pwr_4 * result) + (rx_pwr_3 * result) + (rx_pwr_2 * result) + (rx_pwr_1 * result) + rx_pwr_0

                result = float(result * 0.0001)
                #print(indent, name, " : ", power_in_dbm_str(result))
                retval = self.power_in_dbm_str(result)
            else:
                retval = 'Unknown'
        except Exception as err:
            retval = str(err)

        return retval
    
    def calc_aux1(self, eeprom_data, offset, size):
        retval = 'Unknown'
        return retval

    def calc_aux2(self, eeprom_data, offset, size):
        retval = 'Unknown'
        return retval

    def calc_aux3(self, eeprom_data, offset, size):
        retval = 'Unknown'
        return retval

    def calc_bias_multiplier(self, eeprom_data, offset, size):
        data  = int(eeprom_data[offset], 16)
        data_field = ((data >> 3) & 0x3 )

        if data_field == 0:
            return 1
        elif data_field == 1:
            return 2
        elif data_field == 2:
            return 4

        return 1



    
    dom_temperature_supported_field = {
            'cmis' : { 'upage': 0x1, 'offset': 159, 'bit' : 0 , 'type': 'bitvalue' },
            'cisco': { 'upage': 0x3, 'offset': 154, 'bit' : 3 , 'type': 'bitvalue' },
            }

            
    dom_voltage_supported_field = {
            'cmis' : { 'upage': 0x1, 'offset': 159, 'bit' : 1 , 'type': 'bitvalue' },
            'cisco': { 'upage': 0x3, 'offset': 154, 'bit' : 4 , 'type': 'bitvalue' }
            }

    dom_bias_supported_field = {
            'cmis' : { 'upage': 0x1, 'offset': 160, 'bit' : 0 , 'type': 'bitvalue' },
            'cisco': { 'upage': 0x3, 'offset': 154, 'bit' : 1 , 'type': 'bitvalue' }
            }
            
    dom_tx_power_supported_field = {
            'cmis' : { 'upage': 0x1, 'offset': 160, 'bit' : 1 , 'type': 'bitvalue' },
            'cisco': { 'upage': 0x3, 'offset': 154, 'bit' : 2 , 'type': 'bitvalue' }
            }

    dom_rx_power_supported_field = {
            'cmis' : { 'upage': 0x1, 'offset': 160, 'bit' : 2 , 'type': 'bitvalue' },
            'cisco': { 'upage': 0x3, 'offset': 154, 'bit' : 0 , 'type': 'bitvalue' }
            }
    
    mod_media_type_field = { 'offset': 85, 'type': 'int' }
    appl_adv_apsel1_mid_field = { 'offset': 87, 'type': 'int' }

    ext_id_field = {'offset': 224, 'type': 'int' }

    def channel_skip(self, eeprom_data,  field):
        match = re.match("[TR]X[5-8](Bias|Power)", field)
        if match:
            media_type = self.parse_sff_element(eeprom_data, self.mod_media_type_field, 0)
            mid = self.parse_sff_element(eeprom_data, self.appl_adv_apsel1_mid_field, 0)
            #print("media %d, mid %d" % (media_type, mid))
            if media_type == 0x2 and mid == 0x1C:
                return True
            if self.type_use == 'cisco' and self.parse_sff_element(eeprom_data, self.ext_id_field, 0) == 0x7:
                return True


        return False


    def dom_bias_supported(self, eeprom_data,  eeprom_ele):

        if self.parse_sff_element(eeprom_data, self.dom_bias_supported_field[self.type_use], 0) == "Off":
            #print("%s not supported" % (eeprom_ele['field']))
            return False

        if self.channel_skip(eeprom_data, eeprom_ele['field']):
            #print("%s not supported for DR4" % (eeprom_ele['field']))
            return False

        return True


    def dom_rx_power_supported(self, eeprom_data,  eeprom_ele):

        if self.parse_sff_element(eeprom_data, self.dom_rx_power_supported_field[self.type_use], 0) == "Off":
            #print("%s not supported" % (eeprom_ele['field']))
            return False

        if self.channel_skip(eeprom_data, eeprom_ele['field']):
            #print("%s not supported for DR4" % (eeprom_ele['field']))
            return False

        return True


    def dom_tx_power_supported(self, eeprom_data,  eeprom_ele):
        if self.parse_sff_element(eeprom_data, self.dom_tx_power_supported_field[self.type_use], 0) == "Off":
            #print("%s not supported" % (eeprom_ele['field']))
            return False

        if self.channel_skip(eeprom_data, eeprom_ele['field']):
            #print("%s not supported for DR4" % (eeprom_ele['field']))
            return False

        return True
    
    def dom_temperature_supported(self, eeprom_data,  eeprom_ele):
        if self.parse_sff_element(eeprom_data, self.dom_temperature_supported_field[self.type_use], 0) == "Off":
            #print("Temperature not supported")
            return False

        return True

    def dom_voltage_supported(self, eeprom_data,  eeprom_ele):
        if self.parse_sff_element(eeprom_data, self.dom_voltage_supported_field[self.type_use], 0) == "Off":
            #print("Voltage not supported")
            return False

        return True

    
    dom_bias_multiplier = { 'upage': 0x1,
            'offset': 160, 'size' : 1 , 'type': 'func', 'decode': { 'func': calc_bias_multiplier }}

    dom_module_temperature = OrderedDict([
        ('Temperature', {
            'offset': 14, 'size' : 2 , 'type': 'func', 'decode': { 'func': calc_temperature },
            'impl' : dom_temperature_supported }),
        ])

    dom_module_voltage = OrderedDict([
        ('Vcc', {
            'offset': 16, 'size' : 2 , 'type': 'func', 'decode': { 'func': calc_voltage },
            'impl' : dom_voltage_supported }),
        ])

    dom_channel_monitor_bias_params = OrderedDict([
        ('TX1Bias', { 'field': 'TX1Bias', 'upage': 0x11,
            'offset': 170, 'size' : 2 , 'type': 'func', 'decode': { 'func': calc_bias },
            'impl' : dom_bias_supported }),
        ('TX2Bias', { 'field': 'TX2Bias', 'upage': 0x11,
            'offset': 172, 'size' : 2 , 'type': 'func', 'decode': { 'func': calc_bias },
            'impl' : dom_bias_supported }),
        ('TX3Bias', { 'field': 'TX3Bias', 'upage': 0x11,
            'offset': 174, 'size' : 2 , 'type': 'func', 'decode': { 'func': calc_bias },
            'impl' : dom_bias_supported }),
        ('TX4Bias', { 'field': 'TX4Bias', 'upage': 0x11,
            'offset': 176, 'size' : 2 , 'type': 'func', 'decode': { 'func': calc_bias },
            'impl' : dom_bias_supported }),
        ('TX5Bias', { 'field': 'TX5Bias', 'upage': 0x11,
            'offset': 178, 'size' : 2 , 'type': 'func', 'decode': { 'func': calc_bias },
            'impl' : dom_bias_supported }),
        ('TX6Bias', { 'field': 'TX6Bias', 'upage': 0x11,
            'offset': 180, 'size' : 2 , 'type': 'func', 'decode': { 'func': calc_bias },
            'impl' : dom_bias_supported }),
        ('TX7Bias', { 'field': 'TX7Bias', 'upage': 0x11,
            'offset': 182, 'size' : 2 , 'type': 'func', 'decode': { 'func': calc_bias },
            'impl' : dom_bias_supported }),
        ('TX8Bias', { 'field': 'TX8Bias', 'upage': 0x11,
            'offset': 184, 'size' : 2 , 'type': 'func', 'decode': { 'func': calc_bias },
            'impl' : dom_bias_supported })
        ])

    dom_channel_monitor_tx_power_params = OrderedDict([
        ('TX1Power', { 'field': 'TX1Power', 'upage': 0x11,
            'offset': 154, 'size' : 2 , 'type': 'func', 'decode': { 'func': calc_tx_power },
            'impl' : dom_tx_power_supported }),
        ('TX2Power', { 'field': 'TX2Power', 'upage': 0x11,
            'offset': 156, 'size' : 2 , 'type': 'func', 'decode': { 'func': calc_tx_power },
            'impl' : dom_tx_power_supported }),
        ('TX3Power', { 'field': 'TX3Power', 'upage': 0x11,
            'offset': 158, 'size' : 2 , 'type': 'func', 'decode': { 'func': calc_tx_power },
            'impl' : dom_tx_power_supported }),
        ('TX4Power', { 'field': 'TX4Power', 'upage': 0x11,
            'offset': 160, 'size' : 2 , 'type': 'func', 'decode': { 'func': calc_tx_power },
            'impl' : dom_tx_power_supported }),
        ('TX5Power', { 'field': 'TX5Power', 'upage': 0x11,
            'offset': 162, 'size' : 2 , 'type': 'func', 'decode': { 'func': calc_tx_power },
            'impl' : dom_tx_power_supported }),
        ('TX6Power', { 'field': 'TX6Power', 'upage': 0x11,
            'offset': 164, 'size' : 2 , 'type': 'func', 'decode': { 'func': calc_tx_power },
            'impl' : dom_tx_power_supported }),
        ('TX7Power', { 'field': 'TX7Power', 'upage': 0x11,
            'offset': 166, 'size' : 2 , 'type': 'func', 'decode': { 'func': calc_tx_power },
            'impl' : dom_tx_power_supported }),
        ('TX8Power', { 'field': 'TX8Power', 'upage': 0x11,
            'offset': 168, 'size' : 2 , 'type': 'func', 'decode': { 'func': calc_tx_power },
            'impl' : dom_tx_power_supported })
        ])

    dom_channel_monitor_rx_power_params = OrderedDict([
        ('RX1Power', { 'field': 'RX1Power', 'upage': 0x11,
            'offset': 186, 'size' : 2 , 'type': 'func', 'decode': { 'func': calc_rx_power },
            'impl' : dom_rx_power_supported }),
        ('RX2Power', { 'field': 'RX2Power', 'upage': 0x11,
            'offset': 188, 'size' : 2 , 'type': 'func', 'decode': { 'func': calc_rx_power },
            'impl' : dom_rx_power_supported }),
        ('RX3Power', { 'field': 'RX3Power', 'upage': 0x11,
            'offset': 190, 'size' : 2 , 'type': 'func', 'decode': { 'func': calc_rx_power },
            'impl' : dom_rx_power_supported }),
        ('RX4Power', { 'field': 'RX4Power', 'upage': 0x11,
            'offset': 192, 'size' : 2 , 'type': 'func', 'decode': { 'func': calc_rx_power },
            'impl' : dom_rx_power_supported }),
        ('RX5Power', { 'field': 'RX5Power', 'upage': 0x11,
            'offset': 194, 'size' : 2 , 'type': 'func', 'decode': { 'func': calc_rx_power },
            'impl' : dom_rx_power_supported }),
        ('RX6Power', { 'field': 'RX6Power', 'upage': 0x11,
            'offset': 196, 'size' : 2 , 'type': 'func', 'decode': { 'func': calc_rx_power },
            'impl' : dom_rx_power_supported }),
        ('RX7Power', { 'field': 'RX7Power', 'upage': 0x11,
            'offset': 198, 'size' : 2 , 'type': 'func', 'decode': { 'func': calc_rx_power },
            'impl' : dom_rx_power_supported }),
        ('RX8Power', { 'field': 'RX8Power', 'upage': 0x11,
            'offset': 200, 'size' : 2 , 'type': 'func', 'decode': { 'func': calc_rx_power },
            'impl' : dom_rx_power_supported })
        ])


    dom_temperature_threshold = OrderedDict([
        ('TempHighAlarm', { 'upage': 0x2, 'offset': 128, 'size' : 2 , 'type': 'func', 'decode': { 'func': calc_temperature },
            'impl' : dom_temperature_supported }),
        ('TempLowAlarm', { 'upage': 0x2, 'offset': 130, 'size' : 2 , 'type': 'func', 'decode': { 'func': calc_temperature },
            'impl' : dom_temperature_supported }),
        ('TempHighWarning', { 'upage': 0x2, 'offset': 132, 'size' : 2 , 'type': 'func', 'decode': { 'func': calc_temperature },
            'impl' : dom_temperature_supported }),
        ('TempLowWarning', { 'upage': 0x2, 'offset': 134, 'size' : 2 , 'type': 'func', 'decode': { 'func': calc_temperature },
            'impl' : dom_temperature_supported }),
        ])

    dom_voltage_threshold = OrderedDict([
        ('VoltageHighAlarm', { 'upage': 0x2, 'offset': 136, 'size' : 2 , 'type': 'func', 'decode': { 'func': calc_voltage },
            'impl' : dom_voltage_supported }),
        ('VoltageLowAlarm', { 'upage': 0x2, 'offset': 138, 'size' : 2 , 'type': 'func', 'decode': { 'func': calc_voltage },
            'impl' : dom_voltage_supported }),
        ('VoltageHighWarning', { 'upage': 0x2, 'offset': 140, 'size' : 2 , 'type': 'func', 'decode': { 'func': calc_voltage },
            'impl' : dom_voltage_supported }),
        ('VoltageLowWarning', { 'upage': 0x2, 'offset': 142, 'size' : 2 , 'type': 'func', 'decode': { 'func': calc_voltage },
            'impl' : dom_voltage_supported }),
        ])

    dom_channel_bias_threshold = OrderedDict([
        ('TXBiasHighAlarm', { 'field': 'TXBiasHighAlarm', 'upage': 0x2,
            'offset': 184, 'size' : 2 , 'type': 'func', 'decode': { 'func': calc_bias },
            'impl' : dom_bias_supported }),
        ('TXBiasLowAlarm', { 'field': 'TXBiasLowAlarm', 'upage': 0x2,
            'offset': 186, 'size' : 2 , 'type': 'func', 'decode': { 'func': calc_bias },
            'impl' : dom_bias_supported }),
        ('TXBiasHighWarning', { 'field': 'TXBiasHighWarning', 'upage': 0x2,
            'offset': 188, 'size' : 2 , 'type': 'func', 'decode': { 'func': calc_bias },
            'impl' : dom_bias_supported }),
        ('TXBiasLowWarning', { 'field': 'TXBiasLowWarning', 'upage': 0x2,
            'offset': 190, 'size' : 2 , 'type': 'func', 'decode': { 'func': calc_bias },
            'impl' : dom_bias_supported })
        ])

    dom_channel_tx_power_threshold = OrderedDict([
        ('TXPowerHighAlarm', { 'field': 'TXPowerHighAlarm', 'upage': 0x2,
            'offset': 176, 'size' : 2 , 'type': 'func', 'decode': { 'func': calc_tx_power },
            'impl' : dom_tx_power_supported }),
        ('TXPowerLowAlarm', { 'field': 'TXPowerLowAlarm', 'upage': 0x2,
            'offset': 178, 'size' : 2 , 'type': 'func', 'decode': { 'func': calc_tx_power },
            'impl' : dom_tx_power_supported }),
        ('TXPowerHighWarning', { 'field': 'TXPowerHighWarning', 'upage': 0x2,
            'offset': 180, 'size' : 2 , 'type': 'func', 'decode': { 'func': calc_tx_power },
            'impl' : dom_tx_power_supported }),
        ('TXPowerLowWarning', { 'field': 'TXPowerLowWarning', 'upage': 0x2,
            'offset': 182, 'size' : 2 , 'type': 'func', 'decode': { 'func': calc_tx_power },
            'impl' : dom_tx_power_supported })
        ])

    dom_channel_rx_power_threshold = OrderedDict([
        ('RXPowerHighAlarm', { 'field': 'RXPowerHighAlarm', 'upage': 0x2,
            'offset': 192, 'size' : 2 , 'type': 'func', 'decode': { 'func': calc_rx_power },
            'impl' : dom_rx_power_supported }),
        ('RXPowerLowAlarm', { 'field': 'RXPowerLowAlarm', 'upage': 0x2,
            'offset': 194, 'size' : 2 , 'type': 'func', 'decode': { 'func': calc_rx_power },
            'impl' : dom_rx_power_supported }),
        ('RXPowerHighWarning', { 'field': 'RXPowerHighWarning', 'upage': 0x2,
            'offset': 196, 'size' : 2 , 'type': 'func', 'decode': { 'func': calc_rx_power },
            'impl' : dom_rx_power_supported }),
        ('RXPowerLowWarning', { 'field': 'RXPowerLowWarning', 'upage': 0x2,
            'offset': 198, 'size' : 2 , 'type': 'func', 'decode': { 'func': calc_rx_power },
            'impl' : dom_rx_power_supported })
        ])


    dom_aw_module_thresholds = {
            'TemperatureThreshold': {
                'offset' : 0,
                 'size' : 40,
                 'type' : 'nested',
                 'decode' : dom_temperature_threshold},
            'VoltageThreshold': {
                'offset' : 0,
                 'size' : 40,
                 'type' : 'nested',
                 'decode' : dom_voltage_threshold}}

    dom_aw_channel_thresholds = {
            'TXBiasThreshold': {
                'offset' : 0,
                 'size' : 40,
                 'type' : 'nested',
                 'decode' : dom_channel_bias_threshold},
            'TxPowerThreshold': {
                'offset' : 0,
                 'size' : 40,
                 'type' : 'nested',
                 'decode' : dom_channel_tx_power_threshold},
            'RxPowerThreshold': {
                'offset' : 0,
                 'size' : 40,
                 'type' : 'nested',
                 'decode' : dom_channel_rx_power_threshold}
            }

    dom_module_monitor = {
            'TemperatureMonitor': {
                'offset' : 0,
                 'size' : 40,
                 'type' : 'nested',
                 'decode' : dom_module_temperature},
            'VoltageMonitor': {
                'offset' : 0,
                 'size' : 40,
                 'type' : 'nested',
                 'decode' : dom_module_voltage}}

    dom_channel_monitor = {
            'TXBiasMonitor': {
                'offset' : 0,
                 'size' : 40,
                 'type' : 'nested',
                 'decode' : dom_channel_monitor_bias_params},
            'TxPowerMonitor': {
                'offset' : 0,
                 'size' : 40,
                 'type' : 'nested',
                 'decode' : dom_channel_monitor_tx_power_params},
            'RxPowerMonitor': {
                'offset' : 0,
                 'size' : 40,
                 'type' : 'nested',
                 'decode' : dom_channel_monitor_rx_power_params}
            }

    dom_aw_thresholds = {
            'ModuleThreshold': {
                'offset' : 0,
                 'size' : 40,
                 'type' : 'nested',
                 'decode' : dom_aw_module_thresholds},
            'ChannelThreshold': {
                'offset' : 0,
                 'size' : 40,
                 'type' : 'nested',
                 'decode' : dom_aw_channel_thresholds}}

    dom_monitor = {
            'ModuleMonitor': {
                'offset' : 0,
                 'size' : 40,
                 'type' : 'nested',
                 'decode' : dom_module_monitor},
            'ChannelMonitor': {
                'offset' : 0,
                 'size' : 40,
                 'type' : 'nested',
                 'decode' : dom_channel_monitor}}

    dom_map = {'AwThresholds':
            {'offset' : 0,
             'size' : 40,
             'type' : 'nested',
             'decode' : dom_aw_thresholds},
            'MonitorData':
            {'offset':96,
             'size':10,
             'type' : 'nested',
             'decode': dom_monitor}}


    PORT_START = 50
    def read_bytes(self, sysfs_eeprom_path, offset, num_bytes):
        #offset=128
        #num_bytes=128

        eeprom_raw = []
        for i in range(0, 256):
            eeprom_raw.append("0x00")

        try:

            sysfsfile_eeprom = None
            with open(sysfs_eeprom_path, mode="rb", buffering=0) as sysfsfile_eeprom :
                sysfsfile_eeprom.seek(offset)
                raw = sysfsfile_eeprom.read(num_bytes)
        except IOError:
            if sysfsfile_eeprom is not None:
                print("Error: reading sysfs file %s" % sysfsfile_eeprom.name)
            else:
                print("Error: reading sysfs, file doesn't exist")
            return None

        try:
            for n in range(0, num_bytes):
                eeprom_raw[offset+n] = hex(ord(raw[n]))[2:].zfill(2)
        except:
            return None

        return eeprom_raw

    def get_qsfpdd_page_data(self, eeprom_ele, start_pos):

        sysfs_eeprom_path="/sys/bus/i2c/devices/%d-0050/eeprom" % (self.port + self.PORT_START)

        page = None
        offset=128
        num_bytes=128

        if 'upage' in eeprom_ele:

            page = eeprom_ele.get('upage')

            if page in self.page_data:
                sfp_log("Upper page %d cached" % (page))
                return self.page_data[page]
            
            sfp_log("Upper page %d not cached" % (page)) 

            #set upper page        
            os.system("/usr/sbin/i2cset -y -f %d 0x50 127 %d b" % (self.port + self.PORT_START, page))
        else:
            #Lower page should be already cached 
            if 'lpage' in self.page_data:
                sfp_log("Lower page cached")
                return self.page_data['lpage']
            else:
                #Error no lower page?
                sfp_log("Lower page not cached")
                return None

        eeprom_raw = self.read_bytes(sysfs_eeprom_path, offset, num_bytes)
        if page is not None and eeprom_raw is not None:
            self.page_data[page] = eeprom_raw
            #cache lower page
            #self.page_data['lpage'] = eeprom_raw
        return eeprom_raw


    def parse_sff_element(self, eeprom_data, eeprom_ele, start_pos):
        
        if 'impl' in eeprom_ele:
            #im = self.parse_sff_element(eeprom_data, eeprom_ele['impl'], 0)
            check_support_func = eeprom_ele['impl']
            implemented = check_support_func(self, eeprom_data, eeprom_ele)
            if not implemented:
                #None or 'N/A' when not Supported
                return None


        eeprom_data = self.get_qsfpdd_page_data(eeprom_ele, start_pos)
        if eeprom_data is not None:
            return super(qsfpddDom, self).parse_sff_element(eeprom_data, eeprom_ele, start_pos)
        return None

    def get_lower_page(self):
        sysfs_eeprom_path="/sys/bus/i2c/devices/%d-0050/eeprom" % (self.port + self.PORT_START)
        return self.read_bytes(sysfs_eeprom_path, 0, 128)

    def __init__(self, port, sfp_data=None, eeprom_raw_data=None, calibration_type=1):
        self._calibration_type = calibration_type
        start_pos = 0
            
        self.page_data = {}
        self.sfp_data = sfp_data
        self.type_use = 'cmis'
        
        try:
            if self.sfp_data is not None:
                vendor = self.sfp_data['interface']['data']['Vendor Name'];
                if re.match("^CISCO-", vendor) is not None:
                    self.type_use = 'cisco'
        except KeyError:
            pass

        #print("Use type:%s" % self.type_use)

        self.port = port
        self.page_data['lpage'] = self.get_lower_page()
        
        media_type = self.parse_sff_element(None, self.mod_media_type_field , start_pos)
        if  media_type != 0x1 and media_type != 0x2:
            #print("DOM not supported")
            self.dom_data = None
            return

        self.dom_data = sffbase.parse(self, self.dom_map,
                              eeprom_raw_data, start_pos)
                
        os.system("/usr/sbin/i2cset -y -f %d 0x50 127 0x0 b" % (self.port + self.PORT_START))
        
        #print(self.dom_data)

    def parse(self, eeprom_raw_data, start_pos):
        return sffbase.parse(self, self.dom_map, eeprom_raw_data, start_pos)

    def parse_temperature(self, eeprom_raw_data, start_pos):
        return sffbase.parse(self, self.dom_module_temperature, eeprom_raw_data,
                    start_pos)

    def parse_voltage(self, eeprom_raw_data, start_pos):
        return sffbase.parse(self, self.dom_module_voltage, eeprom_raw_data,
                    start_pos)

    def parse_channel_monitor_params(self, eeprom_raw_data, start_pos):
        return sffbase.parse(self, self.dom_channel_monitor_params, eeprom_raw_data,
                    start_pos)

    def dump_pretty(self):
        if self.dom_data == None:
            print('Object not initialized, nothing to print')
            return
        sffbase.dump_pretty(self, self.dom_data)


    def get_data(self):
        return self.dom_data


    def get_data_pretty(self):
        if self.dom_data is None:
            #print("DOM not supported")
            return {'version' : 'N/A' , 'data': { 'DOM' : 'DOM not supported'}}
        return sffbase.get_data_pretty(self, self.dom_data)

