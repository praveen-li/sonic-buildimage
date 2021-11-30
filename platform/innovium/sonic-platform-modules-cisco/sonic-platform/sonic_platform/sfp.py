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
        super(Sfp,self).__init__()
    
    #def reinit(self):
        #self.detect_dom_supported()

    def get_presence(self):
        if self.platform_sfputil is not None:
            return self.platform_sfputil.get_presence(self.port_index)
        return False

    def is_replaceable(self):
        """
        Indicate whether this device is replaceable.
        Returns:
            bool: True if it is replaceable.
        """
        return True

    def get_transceiver_info(self):
        if self.platform_sfputil is not None:
            return self.platform_sfputil.get_transceiver_info_dict(self.port_index)
        return None

    def get_transceiver_threshold_info(self):
        if self.platform_sfputil is not None :
            return self.platform_sfputil.get_transceiver_dom_threshold_info_dict(self.port_index)
        return None
    
    def get_lpmode(self):
        if self.platform_sfputil is not None:
            return self.platform_sfputil.get_low_power_mode(self.port_index)
        return False
    
    def reset(self):
        if self.platform_sfputil is not None:
            return self.platform_sfputil.reset(self.port_index)
        return False
    
    def set_lpmode(self, lpmode):
        if self.platform_sfputil is not None:
            return self.platform_sfputil.set_low_power_mode(self.port_index, lpmode)
        return False
    
    #Below Functions are yet to be define.
    def get_transceiver_bulk_status(self):
        if self.platform_sfputil is not None:
            return self.platform_sfputil.get_transceiver_dom_info_dict(self.port_index)
        return None
        """
        Retrieves transceiver bulk status of this SFP
        Returns:
            A dict which contains following keys/values :
        ========================================================================
        keys                       |Value Format   |Information
        ---------------------------|---------------|----------------------------
        RX LOS                     |BOOLEAN        |RX lost-of-signal status,
                                   |               |True if has RX los, False if not.
        TX FAULT                   |BOOLEAN        |TX fault status,
                                   |               |True if has TX fault, False if not.
        Reset status               |BOOLEAN        |reset status,
                                   |               |True if SFP in reset, False if not.
        LP mode                    |BOOLEAN        |low power mode status,
                                   |               |True in lp mode, False if not.
        TX disable                 |BOOLEAN        |TX disable status,
                                   |               |True TX disabled, False if not.
        TX disabled channel        |HEX            |disabled TX channles in hex,
                                   |               |bits 0 to 3 represent channel 0
                                   |               |to channel 3.
        Temperature                |INT            |module temperature in Celsius
        Voltage                    |INT            |supply voltage in mV
        TX bias                    |INT            |TX Bias Current in mA
        RX power                   |INT            |received optical power in mW
        TX power                   |INT            |TX output power in mW
        ========================================================================
        """
        return False

    def get_reset_status(self):
        return False

    def get_rx_los(self):
        return False

    def get_tx_fault(self):
        return False

    def get_tx_disable(self):
        return False

    def get_tx_disable_channel(self):
        return False

    def get_power_override(self):
        return False

    def get_temperature(self):
        if self.platform_sfputil is not None:
            return self.platform_sfputil.get_temperature(self.port_index)
        return False

    def get_voltage(self):
        if self.platform_sfputil is not None:
            return self.platform_sfputil.get_voltage(self.port_index)
        return False

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
        return False

    def tx_disable_channel(self, channel, disable):
        return False

    def set_power_override(self, power_override, power_set):
        return False
 
