BRCM_SAI = libsaibcm_3.7.4.1-LI2-test_amd64.deb
$(BRCM_SAI)_URL = "http://172.21.47.11/lnos/sonic/Xu/SAI/libsaibcm_3.7.4.1-LI2-test_amd64.deb"

BRCM_SAI_DEV = libsaibcm-dev_3.7.4.1-LI2-test_amd64.deb
$(eval $(call add_derived_package,$(BRCM_SAI),$(BRCM_SAI_DEV)))
$(BRCM_SAI_DEV)_URL = "http://172.21.47.11/lnos/sonic/Xu/SAI/libsaibcm-dev_3.7.4.1-LI2-test_amd64.deb"

SONIC_ONLINE_DEBS += $(BRCM_SAI)
$(BRCM_SAI_DEV)_DEPENDS += $(BRCM_SAI)

