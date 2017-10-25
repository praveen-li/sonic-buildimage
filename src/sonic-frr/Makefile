.ONESHELL:
SHELL = /bin/bash
.SHELLFLAGS += -e

MAIN_TARGET = frr_$(FRR_VERSION)_amd64.deb

$(addprefix $(DEST)/, $(MAIN_TARGET)): $(DEST)/% :

        # UID/GID env-vars must be explicitly passed to installation scripts to
        # allow subsequent 'dpkg -i' process to make use of this variable.
	if ! grep -q "^SONIC_USER_UID=" sonic_frr.preinst; then
		sed -e"/^set -u/a SONIC_USER_GID=${SONIC_USER_GID}" \
		    -e"/^set -u/a SONIC_USER_UID=${SONIC_USER_UID}" \
		    sonic_frr.preinst > tmp_file && \
		mv tmp_file sonic_frr.preinst
	fi

	pushd ./frr

        # Replacing frr's rules/install/service files with SONiC's own versions
        # to activate specific knobs and adjust install process to SONiC needs.
	cp ../sonic_frr.rules debian/rules
	cp ../sonic_frr.install debian/frr.install
	cp ../sonic_frr.preinst debian/frr.preinst
	cp ../sonic_frr.postinst debian/frr.postinst
	cp ../sonic_frr.init.d.frr tools/frr

        # Build the package
	rm -f debian/*.debhelper.log
	dpkg-buildpackage -rfakeroot -b -us -uc
	popd

	mv $* $(DEST)/
