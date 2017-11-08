BRCM_SAI = libsaibcm_3.0.3.2-10-vlan-memleak_amd64.deb
$(BRCM_SAI)_URL = "http://172.25.11.11/lnos/sonic/SAI-package/master/libsaibcm_3.0.3.2-10-vlan-memleak_amd64.deb"

BRCM_SAI_DEV = libsaibcm-dev_3.0.3.2-10-vlan-memleak_amd64.deb
$(eval $(call add_derived_package,$(BRCM_SAI),$(BRCM_SAI_DEV)))
$(BRCM_SAI_DEV)_URL = "http://172.25.11.11/lnos/sonic/SAI-package/master/libsaibcm-dev_3.0.3.2-10-vlan-memleak_amd64.deb"

SONIC_ONLINE_DEBS += $(BRCM_SAI) $(BRCM_SAI_DEV)
$(BRCM_SAI_DEV)_DEPENDS += $(BRCM_SAI)
