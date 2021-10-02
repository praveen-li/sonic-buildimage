#!/usr/bin/env python
  
#############################################################################
# Cisco
#
# Module contains an implementation of SONiC Platform Base API and
# provides the FANs status which are available in the platform
#
#############################################################################
try:
    from sonic_platform_base.fan_drawer_base import FanDrawerBase
    from sonic_platform_base.fan_base import FanBase
    from sonic_platform.fan import Fan
except ImportError as e:
    raise ImportError(str(e) + "- required module not found")


class FanDrawer(FanDrawerBase):

    def __init__(self, platform_data, index, fan_drawer_data):
        FanDrawerBase.__init__(self)

        self._fan_drawer_data = fan_drawer_data
        self._index = index + 1
        self._fan_num_per_drawer = fan_drawer_data['fan_num']

        for fan_index in range(self._fan_num_per_drawer):
            fan_data = fan_drawer_data['fan'][fan_index]
            fan_obj = Fan(fan_index, index, platform_data, fan_data)
            self._fan_list.append(fan_obj)

    def get_name(self):
        return 'Fantray-' + str(self._index)

    def set_status_led(self, color):
        for fan in self._fan_list:
            fan.set_status_led(color)

    def get_status_led(self):
        if len(self._fan_list) != 0:
            return self._fan_list[0].get_status_led()  #There is only 1 LED per drawer
        else:
            return 'red'

    def get_presence(self):
        #Fan drawer/tray is field replaceable and can have multiple fans
        if len(self._fan_list) != 0:
            return self._fan_list[0].get_presence()
        else:
            return False

    def get_model(self):
        #For TORs, fan drawer/tray doesn't contain any IDPROM data
        return 'N/A'

    def get_serial(self):
        #For TORs, fan drawer/tray doesn't contain any IDPROM data
        return 'N/A'

    def is_replaceable(self):
        #Fan drawer/tray is field replaceable 
        return True

    def get_position_in_parent(self) :
        #Fan_drawer position
        return self._index

    def get_status(self):
        status = True 
        #Need to return failure even if any of the fans is failed
        for fan in self._fan_list:
            status = status and fan.get_status()

        return status
