#############################################################################
# Cisco 
#
# implementation of new platform api
#############################################################################


try:
    import os
    import io
    import re
    import sys
    import glob
    import tempfile
    import subprocess
    from sonic_platform_base.component_base import ComponentBase
except ImportError as e:
    raise ImportError(str(e) + "- required module not found")

class ComponentIOFPGA(ComponentBase):
    
    def get_name(self):
        return "IOFPGA"
    
    def get_description(self):
        return "FPGA component that manages platform components"

    def get_firmware_version(self):
        version_file = "/host/version.conf"
        if not os.path.exists(version_file):
            return ""
        with open(version_file) as f:
            lines = f.readlines()
            for line in lines:
                if "IOFPGA" in line:
                    line = line.split(':')[1]
                    return (line.strip())
            return ""

class ComponentMIFPGA(ComponentBase):

    def __init__(self, index):
        #Make sure that MIFPGA instances are 0-based
        self.index = index

    def get_name(self):
        return "MIFPGA-{}".format(self.index + 1)
    
    def get_description(self):
        return "FPGA component that manages front panel media interfaces"

    def get_firmware_version(self):
        version_file = "/host/version.conf"
        if not os.path.exists(version_file):
            return ""
        with open(version_file) as f:
            lines = f.readlines()
            for line in lines:
                name = "MIFPGA-{}".format(self.index+1)
                if name in line:
                    line = line.split(':')[1]
                    return (line.strip())
            return ""
       

class ComponentBIOS(ComponentBase):

    def __init__(self, index):
        self.index = index

    def _get_name(self):
        if self.index == 0:
            return "Golden"
        elif self.index == 1:
            return "Primary"
        else:
            return "Invalid"

    def get_name(self):
        return "{} BIOS".format(self._get_name())

    def get_description(self):
        return "Basic I/O system that manages system boot"


    def get_firmware_version(self):
        version_file = "/host/version.conf"
        if not os.path.exists(version_file):
            return ""
        with open(version_file) as f:
            lines = f.readlines()
            for line in lines:
                if self.index == 0 :
                    if "Golden BIOS" in line:
                        line = line.split(':')[1]
                        return (line.strip())
                elif self.index == 1:
                    if "Primary BIOS" in line:
                        line = line.split(':')[1]
                        return (line.strip())
            return ""
