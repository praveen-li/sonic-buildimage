# docker image for fpm-quagga

DOCKER_FPM_QUAGGA_STEM = docker-fpm-quagga
DOCKER_FPM_QUAGGA = $(DOCKER_FPM_QUAGGA_STEM).gz
DOCKER_FPM_QUAGGA_DBG = $(DOCKER_FPM_QUAGGA_STEM)-$(DBG_IMAGE_MARK).gz

$(DOCKER_FPM_QUAGGA)_PATH = $(DOCKERS_PATH)/docker-fpm-quagga
$(DOCKER_FPM_QUAGGA)_DEPENDS += $(QUAGGA) $(SWSS)

$(DOCKER_FPM_QUAGGA)_DBG_DEPENDS = $($(DOCKER_CONFIG_ENGINE)_DBG_DEPENDS)
$(DOCKER_FPM_QUAGGA)_DBG_DEPENDS += $(QUAGGA_DBG)

$(DOCKER_FPM_QUAGGA)_DBG_IMAGE_PACKAGES = $($(DOCKER_CONFIG_ENGINE)_DBG_IMAGE_PACKAGES)

$(DOCKER_FPM_QUAGGA)_LOAD_DOCKERS += $(DOCKER_CONFIG_ENGINE)
SONIC_DOCKER_IMAGES += $(DOCKER_FPM_QUAGGA)

SONIC_DOCKER_DBG_IMAGES += $(DOCKER_FPM_QUAGGA_DBG)

$(DOCKER_FPM_QUAGGA)_CONTAINER_NAME = bgp
$(DOCKER_FPM_QUAGGA)_RUN_OPT += --privileged -t
$(DOCKER_FPM_QUAGGA)_RUN_OPT += -v /etc/sonic:/etc/sonic:ro

$(DOCKER_FPM_QUAGGA)_FILES += $(SUPERVISOR_PROC_EXIT_LISTENER_SCRIPT)

$(DOCKER_FPM_QUAGGA)_BASE_IMAGE_FILES += vtysh:/usr/bin/vtysh
