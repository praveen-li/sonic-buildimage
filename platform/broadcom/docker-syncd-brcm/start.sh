#!/usr/bin/env bash

HWSKU_DIR=/usr/share/sonic/hwsku

SYNCD_SOCKET_FILE=/var/run/sswsyncd/sswsyncd.socket

# Remove stale files if they exist
rm -f ${SYNCD_SOCKET_FILE}

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

# Function: wait until syncd has created the socket for bcmcmd to connect to
wait_syncd() {
    while true; do
        if [ -e /var/run/sswsyncd/sswsyncd.socket ]; then
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

wait_done=0
# If this platform has an initialization file for the Broadcom LED microprocessor, load it
if [[ -r ${PLATFORM_DIR}/led_proc_init.soc && ! -f /var/warmboot/warm-starting ]]; then
    wait_syncd
    wait_done=1
    supervisorctl start ledinit
fi

if [ -x ${PLATFORM_DIR}/i2c_init.sh ]; then
    if [ $wait_done == 0]; then
        wait_syncd
    fi
    supervisorctl start i2cinit
fi
