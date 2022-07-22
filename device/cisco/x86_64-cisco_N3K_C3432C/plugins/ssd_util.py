#
# ssd_util.py
#
# Cisco specific implementation of the SSD health API

try:
    import re
    import subprocess
    from sonic_platform_base.sonic_ssd.ssd_base import SsdBase
    from ssd_util_wrapper import SsdInfo,ssd_get_params
except ImportError as e:
    raise ImportError (str(e) + "- required module not found")

NOT_AVAILABLE = "N/A"

class SsdUtil(SsdBase):
    """
    Generic implementation of the SSD health API
    """
    model = NOT_AVAILABLE
    serial = NOT_AVAILABLE
    firmware = NOT_AVAILABLE
    temperature = NOT_AVAILABLE
    health = NOT_AVAILABLE
    ssd_info = NOT_AVAILABLE
    vendor_ssd_info = NOT_AVAILABLE

    def __init__(self, diskdev):

        self.dev = diskdev
        self.ssdinfo = None

        ssdinfo = SsdInfo()
        ssd_get_params(ssdinfo)

        self.dev = diskdev
        self.model = ssdinfo.model
        self.serial = ssdinfo.serial
        self.firmware = ssdinfo.firmware
        self.vendor = ssdinfo.vendor
        self.health = ssdinfo.health
        self.temperature = ssdinfo.temperature

        self.ssdinfo = ssdinfo

    def get_health(self):
        """
        Retrieves current disk health in percentages
        Returns:
            A float number of current ssd health
            e.g. 83.5
        """
        return self.health

    def get_temperature(self):
        """
        Retrieves current disk temperature in Celsius
        Returns:
            A float number of current temperature in Celsius
            e.g. 40.1
        """
        return self.temperature

    def get_model(self):
        """
        Retrieves model for the given disk device
        Returns:
            A string holding disk model as provided by the manufacturer
        """
        return self.model

    def get_firmware(self):
        """
        Retrieves firmware version for the given disk device
        Returns:
            A string holding disk firmware version as provided by the manufacturer
        """
        return self.firmware

    def get_serial(self):
        """
        Retrieves serial number for the given disk device
        Returns:
            A string holding disk serial number as provided by the manufacturer
        """
        return self.serial

    def get_vendor_output(self):
        """
        Retrieves vendor specific data for the given disk device
        Returns:
            A string holding some vendor specific disk information
        """
        return self.vendor

