# Linkedin Open19 Platform modules

LNKD_BOLT_FLEX_PLATFORM_MODULE_VERSION = 0.1
LNKD_BOLT_CEL_PLATFORM_MODULE_VERSION = 0.1
LNKD_BOLT_FLEX_OLD_PLATFORM_MODULE_VERSION = 0.1

export LNKD_BOLT_FLEX_PLATFORM_MODULE_VERSION
export LNKD_BOLT_CEL_PLATFORM_MODULE_VERSION
export LNKD_BOLT_FLEX_OLD_PLATFORM_MODULE_VERSION

LNKD_BOLT_FLEX_PLATFORM_MODULE = platform-modules-bolt-flex_$(LNKD_BOLT_FLEX_PLATFORM_MODULE_VERSION)_amd64.deb

$(LNKD_BOLT_FLEX_PLATFORM_MODULE)_SRC_PATH = $(PLATFORM_PATH)/sonic-platform-modules-linkedin
$(LNKD_BOLT_FLEX_PLATFORM_MODULE)_PLATFORM = x86_64-flex_bolthawk-r0
SONIC_DPKG_DEBS += $(LNKD_BOLT_FLEX_PLATFORM_MODULE)

LNKD_BOLT_CEL_PLATFORM_MODULE = platform-modules-bolt-cel_$(LNKD_BOLT_CEL_PLATFORM_MODULE_VERSION)_amd64.deb
$(LNKD_BOLT_CEL_PLATFORM_MODULE)_PLATFORM = x86_64-open19_bolt-r0
$(eval $(call add_extra_package,$(LNKD_BOLT_FLEX_PLATFORM_MODULE),$(LNKD_BOLT_CEL_PLATFORM_MODULE)))

LNKD_BOLT_FLEX_OLD_PLATFORM_MODULE = platform-modules-bolt-flex-old_$(LNKD_BOLT_FLEX_OLD_PLATFORM_MODULE_VERSION)_amd64.deb
$(LNKD_BOLT_FLEX_OLD_PLATFORM_MODULE)_PLATFORM = x86_64-qwave_bolt_uefi-r0
$(eval $(call add_extra_package,$(LNKD_BOLT_FLEX_PLATFORM_MODULE),$(LNKD_BOLT_FLEX_OLD_PLATFORM_MODULE)))
