#!/usr/bin/env bash

mkdir -p /var/sonic
echo "# Config files managed by sonic-config-engine" > /var/sonic/config_status

rm -f /var/run/rsyslogd.pid

supervisorctl start rsyslogd

# If this platform has an lm-sensors config file, copy it to it's proper place
# and start lm-sensors
if [ -e /usr/share/sonic/platform/sensors.conf ]; then
    mkdir -p /etc/sensors.d
    /bin/cp -f /usr/share/sonic/platform/sensors.conf /etc/sensors.d/
    supervisorctl start lm-sensors
fi

# If this platform has a fancontrol config file, copy it to it's proper place
# and start fancontrol
if [ -e /usr/share/sonic/platform/fancontrol ]; then
    # Remove stale pid file if it exists
    rm -f /var/run/fancontrol.pid

    /bin/cp -f /usr/share/sonic/platform/fancontrol /etc/

    #
    # Verify if the i2c-busid utilized by the hw-monitor driver matches the one
    # defined in fancontrol configuration file. If a mismatch is detected, proceed
    # to adjust fancontrol config accordingly. Note that if no explicit hwmon
    # device is provided in configuration, we will skip this configuration-adjustment
    # process.
    #
    CONF_DEVNAME=`egrep "^DEVNAME=$*" /etc/fancontrol | cut -d'=' -f2`

    CONF_I2C_BUSID=`egrep "^DEVPATH=" /etc/fancontrol | sed 's/^.*\(i2c-[0-9]\/i2c-\).*$/\1/' | cut -d'/' -f1`

    REAL_I2C_BUSID=`readlink -f "/sys/class/hwmon/$CONF_DEVNAME" | sed 's/^.*\(i2c-[0-9]\)\/i2c-.*$/\1/'`

    if [ ! -z "$CONF_I2C_BUSID" ] && [ "$CONF_I2C_BUSID" != "$REAL_I2C_BUSID" ]
    then
        echo -e "I2C bus-id mismatch detected between /etc/fancontrol config-file"\
                "($CONF_I2C_BUSID) and actual i2c-driver ($REAL_I2C_BUSID)."\
                "Adjusting fancontrol configuration..."

        sed -i "s/$CONF_I2C_BUSID\/i2c-/$REAL_I2C_BUSID\/i2c-/g" /etc/fancontrol
    fi

    supervisorctl start fancontrol
fi


# If the sonic-platform package is not installed, try to install it
pip show sonic-platform > /dev/null 2>&1
if [ $? -ne 0 ]; then
    SONIC_PLATFORM_WHEEL="/usr/share/sonic/platform/sonic_platform-1.0-py2-none-any.whl"
    echo "sonic-platform package not installed, attempting to install..."
    if [ -e ${SONIC_PLATFORM_WHEEL} ]; then
       pip install ${SONIC_PLATFORM_WHEEL}
       if [ $? -eq 0 ]; then
          echo "Successfully installed ${SONIC_PLATFORM_WHEEL}"
       else
          echo "Error: Failed to install ${SONIC_PLATFORM_WHEEL}"
       fi
    else
       echo "Error: Unable to locate ${SONIC_PLATFORM_WHEEL}"
    fi
fi

supervisorctl start ledd

supervisorctl start xcvrd

supervisorctl start ssdd
