# ntp_4.2.6.p5+dfsg-7+deb8u2.deb

NTP_VERSION_MAJOR = 4.2.6
NTP_VERSION_SUFFIX = .p5+dfsg
NTP_VERSION_SUFFIX_NUM = 7+deb8u2
NTP_VERSION_FULL = $(NTP_VERSION_MAJOR)$(NTP_VERSION_SUFFIX)-$(NTP_VERSION_SUFFIX_NUM)
NTP_VERSION = $(NTP_VERSION_MAJOR)$(NTP_VERSION_SUFFIX)

export NTP_VERSION NTP_VERSION_FULL

NTP = ntp_$(NTP_VERSION_FULL)_amd64.deb
$(NTP)_SRC_PATH = $(SRC_PATH)/ntp
SONIC_MAKE_DEBS += $(NTP)
