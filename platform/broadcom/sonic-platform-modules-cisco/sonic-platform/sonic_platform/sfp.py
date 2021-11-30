#!/usr/bin/env python                                                                                                                               
#
# sfp.py
#
# Platform-specific SFP transceiver interface for SONiC
#


try:
    import subprocess, time
    from sonic_py_common.logger import Logger
    from sonic_platform_base.sfp_base import SfpBase
except ImportError as e:
    raise ImportError("%s - required module not found" % str(e))


class Sfp(SfpBase):
    def __init__(self, port_index, sfp_type, platform_data, platform_sfputil):
        self.platform_sfputil = platform_sfputil
        self.port_index = port_index
        self.sfp_type = sfp_type
        self.sfp_transceiver_info = None

        super(Sfp,self).__init__()
    
    #def reinit(self):
        #self.detect_dom_supported()

    def get_presence(self):
        if self.platform_sfputil is not None:
            return self.platform_sfputil.get_presence(self.port_index)
        return False

    def get_name(self):
        return 'FrontPort-' + str(self.port_index + 1)

    def get_model(self):
        if self.get_presence():
            if self.sfp_transceiver_info is not None:
                return self.sfp_transceiver_info['model']
            else:
                self.get_transceiver_info()
                if self.sfp_transceiver_info is not None:
                    return self.sfp_transceiver_info['model']

        return 'N/A'

    def get_serial(self):
        if self.get_presence():
            if self.sfp_transceiver_info is not None:
                return self.sfp_transceiver_info['serial']
            else:
                self.get_transceiver_info()
                if self.sfp_transceiver_info is not None:
                    return self.sfp_transceiver_info['serial']
        return 'N/A'

    def is_replaceable(self):
        """
        Indicate whether this device is replaceable.
        Returns:
            bool: True if it is replaceable.
        """
        return True

    def get_transceiver_info(self):
        if self.get_presence():
            if self.platform_sfputil is not None:
                self.sfp_transceiver_info = self.platform_sfputil.get_transceiver_info_dict(self.port_index)
                return self.sfp_transceiver_info

        return None

    def get_transceiver_threshold_info(self):
        if self.get_presence():
            if self.platform_sfputil is not None :
                return self.platform_sfputil.get_transceiver_dom_threshold_info_dict(self.port_index)
        return None
    
    def get_lpmode(self):
        if self.platform_sfputil is not None:
            if self.port_index in self.platform_sfputil.sfp_ports:
                return False
            return self.platform_sfputil.get_low_power_mode(self.port_index)
        return False
    
    def reset(self):
        if self.platform_sfputil is not None:
            if self.port_index in self.platform_sfputil.sfp_ports:
                return False
            return self.platform_sfputil.reset(self.port_index)
        return False
    
    def set_lpmode(self, lpmode):
        if self.platform_sfputil is not None:
            if self.port_index in self.platform_sfputil.sfp_ports:
                return False
            return self.platform_sfputil.set_low_power_mode(self.port_index, lpmode)
        return False
    
    def get_transceiver_bulk_status(self):
        transceiver_dom_info_dict_keys = ['rx_los',       'tx_fault',
                'reset_status', 'power_lpmode', 'lp_mode',
                'tx_disable',   'tx_disable_channel',
                'temperature',  'voltage',
                'rx1power',     'rx2power',
                'rx3power',     'rx4power',
                'tx1bias',      'tx2bias',
                'tx3bias',      'tx4bias',
                'tx1power',     'tx2power',
                'tx3power',     'tx4power']

        transceiver_dom_info_dict = dict.fromkeys(transceiver_dom_info_dict_keys, 'N/A')

        transceiver_dom_info_dict['temperature']        = self.get_temperature()
        transceiver_dom_info_dict['voltage']            = self.get_voltage()
        transceiver_dom_info_dict['reset_status']       = self.get_reset_status()
        transceiver_dom_info_dict['rx_los']             = self.get_rx_los()
        transceiver_dom_info_dict['tx_fault']           = self.get_tx_fault()
        transceiver_dom_info_dict['tx_disable']         = self.get_tx_disable()
        transceiver_dom_info_dict['tx_disable_channel'] = self.get_tx_disable_channel()
        transceiver_dom_info_dict['lp_mode']            = self.get_lpmode()
        transceiver_dom_info_dict['power_lpmode']       = self.get_power_override()

        tx_bias_dict                                    = self.get_tx_bias()
        if tx_bias_dict:
            transceiver_dom_info_dict['tx1bias']            = tx_bias_dict['tx1bias']
            transceiver_dom_info_dict['tx2bias']            = tx_bias_dict['tx2bias']
            transceiver_dom_info_dict['tx3bias']            = tx_bias_dict['tx3bias']
            transceiver_dom_info_dict['tx4bias']            = tx_bias_dict['tx4bias']

        tx_power_dict                                   = self.get_tx_power()
        if tx_power_dict:
            transceiver_dom_info_dict['tx1power']           = tx_power_dict['tx1power']
            transceiver_dom_info_dict['tx2power']           = tx_power_dict['tx2power']
            transceiver_dom_info_dict['tx3power']           = tx_power_dict['tx3power']
            transceiver_dom_info_dict['tx4power']           = tx_power_dict['tx4power']

        rx_power_dict                                   = self.get_rx_power()
        if rx_power_dict:
            transceiver_dom_info_dict['rx1power']           = rx_power_dict['rx1power']
            transceiver_dom_info_dict['rx2power']           = rx_power_dict['rx2power']
            transceiver_dom_info_dict['rx3power']           = rx_power_dict['rx3power']
            transceiver_dom_info_dict['rx4power']           = rx_power_dict['rx4power']
        return transceiver_dom_info_dict

    def get_reset_status(self):
        if self.port_index in self.platform_sfputil.sfp_ports:
            return False
        return True 

    def get_rx_los(self):
        rx_los_state = []
        if self.platform_sfputil is not None:
            rx_los_state =  self.platform_sfputil.get_rx_los(self.port_index)
        return rx_los_state

    def get_tx_fault(self):
        tx_fault_state = []
        if self.platform_sfputil is not None:
            tx_fault_state =  self.platform_sfputil.get_tx_fault(self.port_index)
        return tx_fault_state

    def get_tx_disable(self):
        tx_disable_state = []
        if self.platform_sfputil is not None:
            tx_disable_state =  self.platform_sfputil.get_tx_disable(self.port_index)
        return tx_disable_state

    def get_tx_disable_channel(self):
        tx_disable_channel = 0
        if self.platform_sfputil is not None:
            tx_disable_channel =  self.platform_sfputil.get_tx_disable_channel(self.port_index)
        return tx_disable_channel

    def get_power_override(self):
        if self.platform_sfputil is not None:
            return self.platform_sfputil.get_power_override(self.port_index)
        return False

    def get_temperature(self):
        if self.get_presence():
            if self.platform_sfputil is not None:
                return self.platform_sfputil.get_temperature(self.port_index)
        return 'N/A'

    def get_voltage(self):
        if self.get_presence():
            if self.platform_sfputil is not None:
                return self.platform_sfputil.get_voltage(self.port_index)
        return 'N/A'

    def get_tx_bias(self):
        if self.platform_sfputil is not None:
            return self.platform_sfputil.get_tx_bias(self.port_index)
        return {}
    
    def get_rx_power(self):
        if self.platform_sfputil is not None:
            return self.platform_sfputil.get_rx_power(self.port_index)
        return {}

    def get_tx_power(self):
        if self.platform_sfputil is not None:
            return self.platform_sfputil.get_tx_power(self.port_index)
        return {}

    def tx_disable(self, tx_disable):
        if self.platform_sfputil is not None:
            return self.platform_sfputil.tx_disable(self.port_index,tx_disable)
        return False

    def tx_disable_channel(self, channel, disable):
        if self.platform_sfputil is not None:
            return self.platform_sfputil.tx_disable_channel(self.port_index, channel, disable)
        return False

    def set_power_override(self, power_override, power_set):
        if self.platform_sfputil is not None:
            return self.platform_sfputil.set_power_override(self.port_index, power_override, power_set)
        return False

