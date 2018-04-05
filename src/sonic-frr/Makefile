.ONESHELL:
SHELL = /bin/bash
.SHELLFLAGS += -e

MAIN_TARGET = frr_$(FRR_VERSION)-1~sonic.debian8+1_amd64.deb

DEBIAN8_DIR = debianpkg/backports/sonic.debian8/debian

sed_gid_param = s/SONIC_USER_GID=.*/SONIC_USER_GID=${SONIC_USER_GID}/
sed_uid_param = s/SONIC_USER_UID=.*/SONIC_USER_UID=${SONIC_USER_UID}/

$(addprefix $(DEST)/, $(MAIN_TARGET)): $(DEST)/% :

	pushd ./frr

	if [ ${SONIC_USER_GID}"unset" = "unset" ] || [ ${SONIC_USER_UID}"unset" = "unset" ]; then
		sed -i "/SONIC_USER_GID=/d" $(DEBIAN8_DIR)/frr.preinst
		sed -i "/SONIC_USER_UID=/d" $(DEBIAN8_DIR)/frr.preinst
		if patch -Rsfp1 --dry-run < ../tools.frr.patch; then
			patch -Rsfp1 < ../tools.frr.patch
		fi
	else
		if ! grep -q "^SONIC_USER_GID=" $(DEBIAN8_DIR)/frr.preinst; then
			sed -i "/^set -u/a SONIC_USER_GID=${SONIC_USER_GID}" $(DEBIAN8_DIR)/frr.preinst
		else
			sed -i "$(sed_gid_param)" $(DEBIAN8_DIR)/frr.preinst
		fi

		if ! grep -q "^SONIC_USER_UID=" $(DEBIAN8_DIR)/frr.preinst; then
			sed -i "/^set -u/a SONIC_USER_UID=${SONIC_USER_UID}" $(DEBIAN8_DIR)/frr.preinst
		else
			sed -i "$(sed_uid_param)" $(DEBIAN8_DIR)/frr.preinst
		fi

		if patch -sfp1 --dry-run < ../tools.frr.patch; then
			patch -sfp1 < ../tools.frr.patch
		else
			if ! patch -Rsfp1 --dry-run < ../tools.frr.patch; then
				echo "Error: Patch for tools/frr failed"
				exit 1
			fi
		fi
	fi

        # Build the package
	rm -rf debian
	./bootstrap.sh
	./configure
	make dist
	cp -a debianpkg debian
	make -f debian/rules backports
	rm -rf frrpkg
	mkdir frrpkg
	tar xf frr_*.orig.tar.gz
	cd frr*
	tar xf ../frr_*sonic.debian8*.debian.tar.xz
	dpkg-buildpackage -rfakeroot -b -us -uc
	cd ..
	mv $* $(DEST)/

	popd
