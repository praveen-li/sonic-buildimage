.ONESHELL:
SHELL = /bin/bash
.SHELLFLAGS += -e

MAIN_TARGET = frr_$(FRR_VERSION)_amd64.deb

$(addprefix $(DEST)/, $(MAIN_TARGET)): $(DEST)/% :
        # Cloning FRR repo if not already done
	if [ ! -d "frr" ]; then \
		git clone -b stable/$(FRR_VERSION) https://github.com/FRRouting/frr.git; \
	fi

	pushd ./frr

        # Stepping back in time to the last commit-id that sonic-frr built with.
	git reset --hard 5424c62d

        # Replacing frr's rules/install files with SONiC's own versions to activate
        # specific knobs and adjust install process to address SONiC's needs.
	cp ../sonic_frr.rules debian/rules
	cp ../sonic_frr.install debian/frr.install

        # Build the package
	rm -f debian/*.debhelper.log
	dpkg-buildpackage -rfakeroot -b -us -uc
	popd

	mv $* $(DEST)/
