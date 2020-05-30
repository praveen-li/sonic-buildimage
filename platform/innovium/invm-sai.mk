# INVM SAI

#INVM_SAI_ONLINE = https://github.com/Innovium/SONiC/raw/master/debian/201811
#INVM_SAI_ONLINE = https://github.com/Innovium/SONiC/raw/master/debian/201811/0.10.6

INVM_LIBSAI = isai.deb
INVM_HSAI   = saihdr.deb
INVM_DRV    = ipd.deb
INVM_ISHELL = ishell.deb
INVM_CIS_DRV = csaipd_1.0-1_amd64.deb


$(INVM_LIBSAI)_PATH = $(PLATFORM_PATH)/sonic-platform-modules-cisco
$(INVM_HSAI)_PATH = $(PLATFORM_PATH)/sonic-platform-modules-cisco
$(INVM_DRV)_PATH = $(PLATFORM_PATH)/sonic-platform-modules-cisco
$(INVM_ISHELL)_PATH = $(PLATFORM_PATH)/sonic-platform-modules-cisco
$(INVM_CIS_DRV)_PATH = $(PLATFORM_PATH)/sonic-platform-modules-cisco


#$(INVM_LIBSAI)_URL = $(INVM_SAI_ONLINE)/$(INVM_LIBSAI)
#$(INVM_HSAI)_URL   =  $(INVM_SAI_ONLINE)/$(INVM_HSAI)
#$(INVM_DRV)_URL    =  $(INVM_SAI_ONLINE)/$(INVM_DRV)

#SONIC_ONLINE_DEBS  += $(INVM_LIBSAI) $(INVM_HSAI) $(INVM_DRV)
SONIC_COPY_DEBS  += $(INVM_LIBSAI) $(INVM_HSAI) $(INVM_DRV) $(INVM_CIS_DRV) $(INVM_ISHELL)
#SONIC_COPY_DEBS  += $(INVM_CIS_DRV) $(INVM_ISHELL)
SONIC_STRETCH_DEBS += $(INVM_DRV)
