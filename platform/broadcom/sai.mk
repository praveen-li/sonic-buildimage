BRCM_SAI = libsaibcm_4.3.5.4-LI1_amd64.deb
$(BRCM_SAI)_URL = "http://172.21.47.11/lnos/sonic/SAI-package/libsaibcm_4.3.5.4-LI1_amd64.deb"
BRCM_SAI_DEV = libsaibcm-dev_4.3.5.4-LI1_amd64.deb
$(eval $(call add_derived_package,$(BRCM_SAI),$(BRCM_SAI_DEV)))
$(BRCM_SAI_DEV)_URL = "http://172.21.47.11/lnos/sonic/SAI-package/libsaibcm-dev_4.3.5.4-LI1_amd64.deb"

SONIC_ONLINE_DEBS += $(BRCM_SAI)
$(BRCM_SAI_DEV)_DEPENDS += $(BRCM_SAI)
$(eval $(call add_conflict_package,$(BRCM_SAI_DEV),$(LIBSAIVS_DEV)))
