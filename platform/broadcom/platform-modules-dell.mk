# Dell S6000, Z9100, S6100, Z9264F Platform modules

DELL_S6000_PLATFORM_MODULE_VERSION = 1.1
DELL_Z9100_PLATFORM_MODULE_VERSION = 1.1
DELL_S6100_PLATFORM_MODULE_VERSION = 1.1
DELL_Z9264F_PLATFORM_MODULE_VERSION = 1.1

export DELL_S6000_PLATFORM_MODULE_VERSION
export DELL_Z9100_PLATFORM_MODULE_VERSION
export DELL_S6100_PLATFORM_MODULE_VERSION
export DELL_Z9264F_PLATFORM_MODULE_VERSION


# Dell Z9100 Platform modules
DELL_Z9100_PLATFORM_MODULE = platform-modules-z9100_$(DELL_Z9100_PLATFORM_MODULE_VERSION)_amd64.deb
$(DELL_Z9100_PLATFORM_MODULE)_SRC_PATH = $(PLATFORM_PATH)/sonic-platform-modules-dell
$(DELL_Z9100_PLATFORM_MODULE)_DEPENDS += $(LINUX_HEADERS) $(LINUX_HEADERS_COMMON)
$(DELL_Z9100_PLATFORM_MODULE)_PLATFORM = x86_64-dell_z9100_c2538-r0
SONIC_DPKG_DEBS += $(DELL_Z9100_PLATFORM_MODULE)

# Dell S6100 Platform modules
DELL_S6100_PLATFORM_MODULE = platform-modules-s6100_$(DELL_S6100_PLATFORM_MODULE_VERSION)_amd64.deb
$(DELL_S6100_PLATFORM_MODULE)_PLATFORM = x86_64-dell_s6100_c2538-r0
$(eval $(call add_extra_package,$(DELL_Z9100_PLATFORM_MODULE),$(DELL_S6100_PLATFORM_MODULE)))

# Dell Z9264F Platform modules
DELL_Z9264F_PLATFORM_MODULE = platform-modules-z9264f_$(DELL_Z9264F_PLATFORM_MODULE_VERSION)_amd64.deb
$(DELL_Z9264F_PLATFORM_MODULE)_PLATFORM = x86_64-dellemc_z9264f_c3538-r0
$(eval $(call add_extra_package,$(DELL_Z9100_PLATFORM_MODULE),$(DELL_Z9264F_PLATFORM_MODULE)))

# Dell S6000 Platform modules
DELL_S6000_PLATFORM_MODULE = platform-modules-s6000_$(DELL_S6000_PLATFORM_MODULE_VERSION)_amd64.deb
$(DELL_S6000_PLATFORM_MODULE)_PLATFORM = x86_64-dell_s6000_s1220-r0
$(eval $(call add_extra_package,$(DELL_Z9100_PLATFORM_MODULE),$(DELL_S6000_PLATFORM_MODULE)))

SONIC_STRETCH_DEBS += $(DELL_Z9100_PLATFORM_MODULE)

#flashrom tool
$(shell ./$(PLATFORM_PATH)/sonic-platform-modules-dell/tools/flashrom.sh  > /dev/null 2>&1)
