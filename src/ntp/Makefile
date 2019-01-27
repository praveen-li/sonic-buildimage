SHELL = /bin/bash
.ONESHELL:
.SHELLFLAGS += -e

MAIN_TARGET = ntp_$(NTP_VERSION_FULL)_amd64.deb

NTP_URL = http://cdn-fastly.deb.debian.org/debian/pool/main/n/ntp

DSC_FILE = ntp_$(NTP_VERSION_FULL).dsc
DSC_FILE_URL = $(NTP_URL)/$(DSC_FILE)

$(addprefix $(DEST)/, $(MAIN_TARGET)): $(DEST)/% :
	rm -rf ntp-$(NTP_VERSION)
	dget -u $(DSC_FILE_URL)

	pushd ntp-$(NTP_VERSION)

	git init
	git add -f *
	git commit -m "original source files"

	stg init
	stg import -s ../patch/series

	dpkg-buildpackage -us -uc -b -j$(SONIC_CONFIG_MAKE_JOBS)
	popd

	mv $* $(DEST)/
