BRCM_SAI = libsaibcm_3.5.3.6-LI1_amd64.deb
$(BRCM_SAI)_URL = "http://172.21.47.11/lnos/sonic/SAI-package/libsaibcm_3.5.3.6-LI1_amd64.deb"

BRCM_SAI_DEV = libsaibcm-dev_3.5.3.6-LI1_amd64.deb
$(eval $(call add_derived_package,$(BRCM_SAI),$(BRCM_SAI_DEV)))
$(BRCM_SAI_DEV)_URL = "http://172.21.47.11/lnos/sonic/SAI-package/libsaibcm-dev_3.5.3.6-LI1_amd64.deb"

SONIC_ONLINE_DEBS += $(BRCM_SAI)
$(BRCM_SAI_DEV)_DEPENDS += $(BRCM_SAI)
