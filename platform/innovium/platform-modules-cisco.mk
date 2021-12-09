# Cisco platform modules

CISCO_PLATFORM_MODULE_VERSION = 1.0

export CISCO_PLATFORM_MODULE_VERSION

CISCO_PLATFORM_MODULE = platform-modules-n9200_$(CISCO_PLATFORM_MODULE_VERSION)_amd64.deb
$(CISCO_PLATFORM_MODULE)_PATH = $(PLATFORM_PATH)/sonic-platform-modules-cisco/debians

CISCO_NBI_PACKAGE = cisco-nbi-package_1.0_amd64.deb
$(CISCO_NBI_PACKAGE)_PATH = $(PLATFORM_PATH)/sonic-platform-modules-cisco/debians

SONIC_COPY_DEBS += $(CISCO_PLATFORM_MODULE) $(CISCO_NBI_PACKAGE)
SONIC_STRETCH_DEBS += $(CISCO_PLATFORM_MODULE) $(CISCO_NBI_PACKAGE)

SONIC_CISCO_PLATFORM_API_PY2 = python-sonic-platform-cisco_1.0_all.deb
$(SONIC_CISCO_PLATFORM_API_PY2)_SRC_PATH = $(PLATFORM_PATH)/sonic-platform-modules-cisco/sonic-platform
SONIC_DPKG_DEBS += $(SONIC_CISCO_PLATFORM_API_PY2)
export SONIC_CISCO_PLATFORM_API_PY2

SONIC_CISCO_PLATFORM_API_PY3 = python3-sonic-platform-cisco_1.0_all.deb
$(SONIC_CISCO_PLATFORM_API_PY3)_SRC_PATH = $(PLATFORM_PATH)/sonic-platform-modules-cisco/sonic-platform
$(eval $(call add_extra_package,$(SONIC_CISCO_PLATFORM_API_PY2),$(SONIC_CISCO_PLATFORM_API_PY3)))
export SONIC_CISCO_PLATFORM_API_PY3
