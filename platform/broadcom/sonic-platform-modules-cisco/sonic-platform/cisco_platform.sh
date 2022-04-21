#!/bin/bash

### BEGIN INIT INFO
# Provides:          setup-board
# Required-Start:
# Required-Stop:
# Should-Start:
# Should-Stop:
# Default-Start:     S
# Default-Stop:      0 6
# Short-Description: Setup cisco 3232c board - install sonic_plaform APIs.
### END INIT INFO

install_python_api_package() {
    device="/usr/share/sonic/device"
    platform=$(/usr/local/bin/sonic-cfggen -H -v DEVICE_METADATA.localhost.platform)

    rv=$(pip install $device/$platform/sonic_platform-1.0-py2-none-any.whl)
    rv=$(pip3 install $device/$platform/sonic_platform-1.0-py3-none-any.whl)
}

remove_python_api_package() {
    rv=$(pip show sonic-platform > /dev/null 2>/dev/null)
    if [ $? -eq 0 ]; then
        rv=$(pip uninstall -y sonic-platform > /dev/null 2>/dev/null)
    fi

    rv=$(pip3 show sonic-platform > /dev/null 2>/dev/null)
    if [ $? -eq 0 ]; then
        rv=$(pip3 uninstall -y sonic-platform > /dev/null 2>/dev/null)
    fi
}

if [[ "$1" == "init" ]]; then
        install_python_api_package
elif [[ "$1" == "deinit" ]]; then
        remove_python_api_package
else
     echo "cisco_platform : Invalid option !"
fi
