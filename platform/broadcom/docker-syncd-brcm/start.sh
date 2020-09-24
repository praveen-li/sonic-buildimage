#!/usr/bin/env bash

PLATFORM_DIR=/usr/share/sonic/platform
HWSKU_DIR=/usr/share/sonic/hwsku

SYNCD_SOCKET_FILE=/var/run/sswsyncd/sswsyncd.socket

# Function: wait until syncd has created the socket and bcmshell is ready
wait_syncd() {
    while true; do
        if [ -e ${SYNCD_SOCKET_FILE} ]; then
            # wait until bcm shell is ready to process requests
            if bcmcmd -t 1 "a"; then
                echo "bcmcmd is ready to process requests"
                break
            else
                echo "bcmcmd is not ready to process requests, wait again"
            fi
        fi
        sleep 1
    done
}

# Remove stale files if they exist
rm -f /var/run/rsyslogd.pid
rm -f ${SYNCD_SOCKET_FILE}

supervisorctl start rsyslogd

mkdir -p /etc/sai.d/

# Create/Copy the sai.profile to /etc/sai.d/sai.profile
if [ -f $HWSKU_DIR/sai.profile.j2 ]; then
    sonic-cfggen -d -t $HWSKU_DIR/sai.profile.j2 > /etc/sai.d/sai.profile
else
    if [ -f $HWSKU_DIR/sai.profile ]; then
        cp $HWSKU_DIR/sai.profile /etc/sai.d/sai.profile
    fi
fi

rm -f /var/run/sswsyncd/sswsyncd.socket
supervisorctl start syncd

# always wait for syncd to be ready
wait_syncd

# If this platform has an initialization file for the Broadcom LED microprocessor, load it
if [[ -r ${PLATFORM_DIR}/led_proc_init.soc && ! -f /var/warmboot/warm-starting ]]; then
    supervisorctl start ledinit
fi

if [[ -r ${HWSKU_DIR}/pre_emphasis_PAM4_optics.soc && ! -f /var/warmboot/warm-starting ]]; then
    bcmcmd "rcload ${HWSKU_DIR}/pre_emphasis_PAM4_optics.soc"
fi

if [ -x ${PLATFORM_DIR}/i2c_init.sh ]; then
    supervisorctl start i2cinit
fi
