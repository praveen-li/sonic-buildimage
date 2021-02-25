# sonic-ssdd (SONiC SSD daemon) Debian package

SONIC_SSDD = python-sonic-ssdd_1.1-1_all.deb
$(SONIC_SSDD)_SRC_PATH = $(SRC_PATH)/sonic-platform-daemons/sonic-ssdd
SONIC_PYTHON_STDEB_DEBS += $(SONIC_SSDD)
