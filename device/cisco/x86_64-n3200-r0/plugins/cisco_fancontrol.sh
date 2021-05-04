#!/bin/bash
#
# Simple script implementing a temperature dependent fan speed control
# Supported Linux kernel versions: 2.6.5 and later
#
# Version 0.71
#
# Usage: fancontrol [CONFIGFILE]
#
# Dependencies:
#   bash, egrep, sed, cut, sleep, readlink, lm_sensors :)
#
# For configuration instructions and warnings please see fancontrol.txt, which
# can be found in the doc/ directory or at the website mentioned above.
#
#
#    Copyright 2003 Marius Reiner <marius.reiner@hdev.de>
#    Copyright (C) 2007-2014 Jean Delvare <jdelvare@suse.de>
#    Copyright (C) 2021 Udayakumar Raghuraman <uraghura@cisco.com>
#    Copyright (C) 2021 Zhenggen Xu <zxu@linkedin.com>
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#    MA 02110-1301 USA.
#
#

#Script specific knobs
PIDFILE="/var/run/fancontrol.pid"
MAX=255
MIN=127

DEBUG=4 #default


#Script specific constants and variables
AFC_EMERG=0
AFC_ALERT=1
AFC_CRIT=2
AFC_ERR=3
AFC_WARN=4
AFC_NOTICE=5
AFC_INFO=6
AFC_DEBUG=7

#Fan control algorithm state constants
AFC_STATE_START=1
AFC_STATE_NORMAL=2      #below the min. temperature threshold
AFC_STATE_INSUFFICIENT_FANS=3
AFC_STATE_FANS_FAULTY=4 #either running at low speed/stopped or higher than expected
AFC_STATE_HOT=5         # min. temp <= current Temp. <= max. temp
AFC_STATE_CRITICAL=6    # current temp. > max. temp
AFC_STATE_FANS_OPP_DIRECTION=7 #Fans are running in opposite directions
AFC_STATE_INLET_HOT=8   # Inlet temperature is > threshold
AFC_STATE_DAEMON_EXIT=9 # Fan control algorithm daemon is about to exit

#Fan control algorithm state variables
AFC_CURRENT_STATE=$AFC_STATE_START
AFC_PREVIOUS_STATE=$AFC_STATE_START
AFC_STATE_STRING=""
AFC_CURRENT_PWM=0
AFC_PREVIOUS_PWM=0

#Platform specific knobs and constants
#Change them at your own risk
MINSPEED=5000
B2F_FAN_MINPWM=153
B2F_FAN_MAXPWM=255
F2B_FAN_MINPWM=204
F2B_FAN_MAXPWM=255
AFC_ENABLE_HOTINLET_PROTECTION=0
AFCHOTINLETMAXTEMP=35

NUMFANTRAYS=4
FANSPERTRAY=1 #inlet and outlet fans
MAXFANLEDS=4 #1 LED per inlet/outlet pair
PSU0_PRESENCE="/sys/class/gpio/gpio116/value"
PSU1_PRESENCE="/sys/class/gpio/gpio117/value"
PSU0_BUS_ADDR=34
PSU0_UC_ADDR=0x5a
PSU1_BUS_ADDR=35
PSU1_UC_ADDR=0x5a


function afc_debug
{
    local lprio=$1
    local lmsg=$2

    if [ "$lprio" -le "$DEBUG" ]
    then
        echo $lmsg >&2
    fi
}

function get_afc_state_string
{
    local state=$1

    case $state in
        $AFC_STATE_START)
            AFC_STATE_STRING="Fan Control algorithm is in START state"
            ;;
        $AFC_STATE_NORMAL)
            AFC_STATE_STRING="Temperatures are below min. threshold and so setting default/min. speed for all fans"
            ;;
        $AFC_STATE_HOT)
            AFC_STATE_STRING="Temperatures are hot. Fan control algorithm is actively adjusting fan speeds"
            ;;
        $AFC_STATE_CRITICAL)
            AFC_STATE_STRING="Temperatures reached critical and so setting FULL speed for all fans"
            ;;
        $AFC_STATE_INSUFFICIENT_FANS)
            AFC_STATE_STRING="Not all fans present and so setting FULL speed for remaining fans"
            ;;
        $AFC_STATE_FANS_FAULTY)
            AFC_STATE_STRING="Some fans are faulty and so setting FULL speed for remaining fans"
            ;;
        $AFC_STATE_FANS_OPP_DIRECTION)
            AFC_STATE_STRING="Some fans are running in opposite directions and so setting FULL speed for all fans"
            ;;
        $AFC_STATE_INLET_HOT)
            AFC_STATE_STRING="Inlet air temperature is too hot and so setting FULL speed for all fans"
            ;;
        $AFC_STATE_DAEMON_EXIT)
            AFC_STATE_STRING="Automatic fan/thermal control daemon is about to exit..."
            ;;
        *)
            AFC_STATE_STRING="Invalid Fan control algorithm state"
            ;;
    esac
}

function update_afc_state_and_log_message
{
    afc_debug $AFC_DEBUG "curr. state=$AFC_CURRENT_STATE"
    afc_debug $AFC_DEBUG "prev. state=$AFC_PREVIOUS_STATE"

    if [ "$AFC_CURRENT_STATE" -ne "$AFC_PREVIOUS_STATE" ]
    then
        get_afc_state_string $AFC_CURRENT_STATE
        afc_debug $AFC_ALERT "$AFC_STATE_STRING"
        update_all_fans_leds "$AFC_CURRENT_STATE"
    fi

    AFC_PREVIOUS_STATE=$AFC_CURRENT_STATE
}

function update_afc_pwm
{
    afc_debug $AFC_DEBUG "curr. pwm=$AFC_CURRENT_PWM"
    afc_debug $AFC_DEBUG "prev. pwm=$AFC_PREVIOUS_PWM"

    if [ "$AFC_CURRENT_PWM" -ne "$AFC_PREVIOUS_PWM" ]
    then
       adjustallfanpwms $AFC_CURRENT_PWM
    fi

    AFC_PREVIOUS_PWM=$AFC_CURRENT_PWM
}


function are_all_fans_present
{
    local fcvcount
    local fpres
    local pres
    local n_pres

    let fcvcount=0
    while (( $fcvcount < ${#AFCFANPRESENCE[@]} )) # go through all fan presence inputs
    do
        fpres=${AFCFANPRESENCE[$fcvcount]}
        read pres < $fpres
        if [ $? -ne 0 ]
        then
            afc_debug $AFC_ERR  "Error reading $fpres"
            return 0
        fi

        if [ "$pres" -eq 1 ]
        then
            let n_pres=$n_pres+1
        fi
        let fcvcount=$fcvcount+1
    done

    if [ "$n_pres" -eq "$fcvcount" ]
    then
        return 1
    else
        return 0
    fi

}

function are_all_fans_run_in_same_direction
{
    local fcvcount
    local fdir
    local dir
    local n_dir

    let fcvcount=0
    while (( $fcvcount < ${#AFCFANDIRECTION[@]} )) # go through all fan direction inputs
    do
        fdir=${AFCFANDIRECTION[$fcvcount]}
        read dir < $fdir
        if [ $? -ne 0 ]
        then
            afc_debug $AFC_ERR  "Error reading $fdir"
            return 0
        fi

        if [ "$dir" -eq 1 ]
        then
            let n_dir=$n_dir+1
        fi

        let fcvcount=$fcvcount+1
    done

    if [ "$n_dir" -eq "$fcvcount"  -o "$n_dir" -eq 0 ]
    then
        return 1
    else
        return 0
    fi

}


function LoadConfig
{
        local fcvcount fcv
        local n_vals d_val
        local n_fan_presence n_fan_direction
        local fdir dir

        AFC_CFG_FILE=$1
        afc_debug $AFC_INFO  "Loading configuration from $AFC_CFG_FILE ..."
        if [ ! -r "$1" ]
        then
                afc_debug $AFC_ERR "Error: Can't read configuration file"
                exit 1
        fi

        # grep configuration from file
        INTERVAL=`egrep '^INTERVAL=.*$' $1 | sed -e 's/INTERVAL=//g'`
        MINTEMP=`egrep '^MINTEMP=.*$' $1 | sed -e 's/MINTEMP=//g'`
        MAXTEMP=`egrep '^MAXTEMP=.*$' $1 | sed -e 's/MAXTEMP=//g'`
        MINPWM=`egrep '^MINPWM=.*$' $1 | sed -e 's/MINPWM=//g'`
        MAXPWM=`egrep '^MAXPWM=.*$' $1 | sed -e 's/MAXPWM=//g'`
        ASICTEMP=`egrep '^ASICTEMP=.*$' $1 | sed -e 's/ASICTEMP=//g'`
        FRONTPORTTEMP=`egrep '^FRONTPORTTEMP=.*$' $1 | sed -e 's/FRONTPORTTEMP=//g'`
        FANSIDETEMP=`egrep '^FANSIDETEMP=.*$' $1 | sed -e 's/FANSIDETEMP=//g'`
        FCPWMS=`egrep '^FCPWMS=.*$' $1 | sed -e 's/FCPWMS=//g'`
        FCFANS=`egrep '^FCFANS=.*$' $1 | sed -e 's/FCFANS=//g'`
        FAN_PRESENCE=`egrep '^FAN_PRESENCE=.*$' $1 | sed -e 's/FAN_PRESENCE=//g'`
        FAN_DIRECTION=`egrep '^FAN_DIRECTION=.*$' $1 | sed -e 's/FAN_DIRECTION=//g'`
        FAN_SIMULATION=`egrep '^FAN_SIMULATION=.*$' $1 | sed -e 's/FAN_SIMULATION=//g'`
        DEBUG=`egrep '^DEBUG=.*$' $1 | sed -e 's/DEBUG=//g'`
        ENABLE_HOTINLET_PROTECTION=`egrep '^ENABLE_HOTINLET_PROTECTION=.*$' $1 | sed -e 's/ENABLE_HOTINLET_PROTECTION=//g'`

        # Check whether all mandatory settings are set
        if [[ -z ${INTERVAL} || -z ${ASICTEMP} || -z ${FRONTPORTTEMP} || -z ${FANSIDETEMP} || -z ${FCFANS} || -z ${FCPWMS} || -z ${MINTEMP} || -z ${MAXTEMP} || -z ${MINPWM} || -z ${MAXPWM} || -z ${FAN_PRESENCE} || -z ${FAN_DIRECTION} ]]
        then
                echo "Some mandatory settings missing, please check your config file!"
                exit 1
        fi

        if [ "$INTERVAL" -le 0 ]
        then
                echo "Error in configuration file:"
                echo "INTERVAL must be at least 1" >&2
                exit 1
        fi

        #Assign defaults for optional parameters
        if [ "$FAN_SIMULATION" == "" ]
        then
                FAN_SIMULATION=0
        fi

        if [ "$DEBUG" == "" ]
        then
            DEBUG=4
        fi

        if [ "$ENABLE_HOTINLET_PROTECTION" == "" ]
        then
            AFC_ENABLE_HOTINLET_PROTECTION=0
        else
            AFC_ENABLE_HOTINLET_PROTECTION=$ENABLE_HOTINLET_PROTECTION
        fi

        # write settings to arrays for easier use and print them
        afc_debug $AFC_DEBUG "Common settings:"
        afc_debug $AFC_DEBUG "  INTERVAL=$INTERVAL"

        #Temperature sensors sysfs paths are space separated
        let fcvcount=0
        for fcv in $ASICTEMP
        do
                AFCASICTEMP[$fcvcount]=`echo $fcv |cut -d' ' -f1`
                afc_debug $AFC_DEBUG "ASIC sensor $fcvcount : ${AFCASICTEMP[$fcvcount]}"
                let fcvcount=fcvcount+1
        done

        let fcvcount=0
        for fcv in $FRONTPORTTEMP
        do
                AFCFRONTPORTTEMP[$fcvcount]=`echo $fcv |cut -d' ' -f1`
                afc_debug $AFC_DEBUG "Front port sensor $fcvcount : ${AFCFRONTPORTTEMP[$fcvcount]}"
                let fcvcount=fcvcount+1
        done

        let fcvcount=0
        for fcv in $FANSIDETEMP
        do
                AFCFANSIDETEMP[$fcvcount]=`echo $fcv |cut -d' ' -f1`
                afc_debug $AFC_DEBUG "FAN side sensor $fcvcount : ${AFCFANSIDETEMP[$fcvcount]}"
                let fcvcount=fcvcount+1
        done


        FCTEMPS="$ASICTEMP $FRONTPORTTEMP $FANSIDETEMP"
        let fcvcount=0
        for fcv in $FCTEMPS
        do
                AFCTEMP[$fcvcount]=`echo $fcv |cut -d' ' -f1`
                afc_debug $AFC_DEBUG "Sensor $fcvcount : ${AFCTEMP[$fcvcount]}"
                let fcvcount=fcvcount+1
        done

        #FAN speed sysfs paths are space separated
        let fcvcount=0
        for fcv in $FCFANS
        do
                AFCFAN[$fcvcount]=`echo $fcv |cut -d' ' -f1`
                afc_debug $AFC_DEBUG "Fan speed $fcvcount : ${AFCFAN[$fcvcount]}"
                let fcvcount=fcvcount+1
        done

        #FAN PWM sysfs paths are space separated
        let fcvcount=0
        for fcv in $FCPWMS
        do
                AFCPWM[$fcvcount]=`echo $fcv |cut -d' ' -f1`
                afc_debug $AFC_DEBUG "PWM control $fcvcount : ${AFCPWM[$fcvcount]}"
                let fcvcount=fcvcount+1
        done

        #FAN presence GPIO sysfs paths are space separated
        let fcvcount=0
        for fcv in $FAN_PRESENCE
        do
                AFCFANPRESENCE[$fcvcount]=`echo $fcv |cut -d' ' -f1`
                afc_debug $AFC_DEBUG "FAN $fcvcount presence: ${AFCPWM[$fcvcount]}"
                let fcvcount=fcvcount+1
        done
        let n_fan_presence=$fcvcount

        #FAN direction GPIO sysfs paths are space separated
        let fcvcount=0
        for fcv in $FAN_DIRECTION
        do
                AFCFANDIRECTION[$fcvcount]=`echo $fcv |cut -d' ' -f1`
                afc_debug $AFC_DEBUG "FAN $fcvcount direction : ${AFCPWM[$fcvcount]}"
                let fcvcount=fcvcount+1
        done
        let n_fan_direction=$fcvcount


        AFCMINTEMP=$MINTEMP
        AFCMAXTEMP=$MAXTEMP
        AFCMINPWM=$MINPWM
        AFCMAXPWM=$MAXPWM

        # verify the validity of the settings
        if [ "${AFCMINTEMP}" -ge "${AFCMAXTEMP}" ]
        then
            afc_debug $AFC_ERR "Error in configuration file "
            afc_debug $AFC_ERR "MINTEMP must be less than MAXTEMP"
            exit 1
        fi

        if [ "${AFCMAXPWM}" -gt "$MAX" ]
        then
            afc_debug $AFC_ERR "Error in configuration file"
            afc_debug $AFC_ERR "MAXPWM must be at most $MAX"
            exit 1
        fi

        if [ "${AFCMAXPWM}" -lt "${AFCMINPWM}" ]
        then
            afc_debug $AFC_ERR "Error in configuration file"
            afc_debug $AFC_ERR "MAXPWM must be greater than or equal to MINPWM"
            exit 1
        fi

        if [ "${AFCMINPWM}" -lt "$MIN" ]
        then
            afc_debug $AFC_ERR "Error in configuration file"
            afc_debug $AFC_ERR "MINPWM must be at least $MIN"
            exit 1
        fi

        if [ "$n_fan_presence" -ne "$NUMFANTRAYS" ]
        then
            afc_debug $AFC_ERR "Error in configuration file"
            afc_debug $AFC_ERR "FAN_PRESENCE != $NUMFANTRAYS entries reqd. for this platform"
            exit 1
        fi

        if [ "$n_fan_direction" -ne "$NUMFANTRAYS" ]
        then
            afc_debug $AFC_ERR "Error in configuration file"
            afc_debug $AFC_ERR "FAN_DIRECTION != $NUMFANTRAYS entries reqd. for this platform"
            exit 1
        fi

        if [ $FAN_SIMULATION -eq 1 ]
        then
            afc_debug $AFC_DEBUG "FAN_SIMULATION is enabled"
            DIR=./
            PSU0_PRESENCE="psu0_presence"
            PSU1_PRESENCE="psu1_presence"
        fi

        are_all_fans_run_in_same_direction
        if [[ $? -ne 1 ]]; then
            afc_debug $AFC_WARN "Warning: Some FANs are in opposite directions"
            afc_debug $AFC_WARN "Warning: Setting the fans to FULL speed and exiting."
            restorefans 0
        fi

        fdir=${AFCFANDIRECTION[0]}
        read dir < $fdir
        if [[ $? -ne 0 ]]; then
            afc_debug $AFC_ERR "Error reading $fdir"
            restorefans 0
        fi

        if [[ $dir -eq 0 ]]; then
            #f2b - port side exhaust - Blue fans
            afc_debug $AFC_INFO "FAN Direction: Port side exhaust (F2B / Blue Fans)"
            if [ "${AFCMINPWM}" -lt "$F2B_FAN_MINPWM" ]
            then
                afc_debug $AFC_ERR "Error in configuration file"
                afc_debug $AFC_ERR "MINPWM must be at least $F2B_FAN_MINPWM"
                exit 1
            fi

            if [ "${AFCMAXPWM}" -gt "$F2B_FAN_MAXPWM" ]
            then
                afc_debug $AFC_ERR "Error in configuration file"
                afc_debug $AFC_ERR "MAXPWM cannot be greater than  $F2B_FAN_MAXPWM"
                exit 1
            fi
        else
            #b2f - port side inlet - Red fans
            afc_debug $AFC_INFO "FAN Direction: Port side intake (B2F / Red Fans)"
            if [ "${AFCMINPWM}" -lt "$B2F_FAN_MINPWM" ]
            then
                afc_debug $AFC_ERR "Error in configuration file"
                afc_debug $AFC_ERR "MINPWM must be at least $B2F_FAN_MINPWM"
                exit 1
            fi

            if [ "${AFCMAXPWM}" -gt "$B2F_FAN_MAXPWM" ]
            then
                afc_debug $AFC_ERR "Error in configuration file"
                afc_debug $AFC_ERR "MAXPWM cannot be greater than  $B2F_FAN_MAXPWM"
                exit 1
            fi

        fi

        afc_debug $AFC_DEBUG "  MINTEMP=${AFCMINTEMP}"
        afc_debug $AFC_DEBUG "  MAXTEMP=${AFCMAXTEMP}"
        afc_debug $AFC_DEBUG "  HOTINLETMAXTEMP=${AFCHOTINLETMAXTEMP}"
        afc_debug $AFC_DEBUG "  MINPWM=${AFCMINPWM}"
        afc_debug $AFC_DEBUG "  MAXPWM=${AFCMAXPWM}"
}

function DevicePath()
{
        if [ -h "$1/device" ]
        then
                readlink -f "$1/device" | sed -e 's/^\/sys\///'
        fi
}

function DeviceName()
{
        if [ -r "$1/name" ]
        then
                cat "$1/name" | sed -e 's/[[:space:]=]/_/g'
        elif [ -r "$1/device/name" ]
        then
                cat "$1/device/name" | sed -e 's/[[:space:]=]/_/g'
        fi
}

function ValidateDevices()
{
        local OLD_DEVPATH="$1" OLD_DEVNAME="$2" outdated=0
        local entry device name path

        for entry in $OLD_DEVPATH
        do
                device=`echo "$entry" | sed -e 's/=[^=]*$//'`
                path=`echo "$entry" | sed -e 's/^[^=]*=//'`

                if [ "`DevicePath "$device"`" != "$path" ]
                then
                        afc_debug $AFC_WARN "Device path of $device has changed"
                        outdated=1
                fi
        done

        for entry in $OLD_DEVNAME
        do
                device=`echo "$entry" | sed -e 's/=[^=]*$//'`
                name=`echo "$entry" | sed -e 's/^[^=]*=//'`

                if [ "`DeviceName "$device"`" != "$name" ]
                then
                        afc_debug $AFC_WARN "Device name of $device has changed"
                        outdated=1
                fi
        done

        return $outdated
}

function FixupDeviceFiles
{
        local DEVICE="$1"
        local fcvcount pwmo tsen fan

        let fcvcount=0
        while (( $fcvcount < ${#AFCPWM[@]} )) # go through all pwm outputs
        do
                pwmo=${AFCPWM[$fcvcount]}
                AFCPWM[$fcvcount]=${pwmo//$DEVICE\/device/$DEVICE}
                if [ "${AFCPWM[$fcvcount]}" != "$pwmo" ]
                then
                        afc_debug $AFC_NOTICE "Adjusing $pwmo -> ${AFCPWM[$fcvcount]}"
                fi
                let fcvcount=$fcvcount+1
        done

        let fcvcount=0
        while (( $fcvcount < ${#AFCTEMP[@]} )) # go through all temp inputs
        do
                tsen=${AFCTEMP[$fcvcount]}
                AFCTEMP[$fcvcount]=${tsen//$DEVICE\/device/$DEVICE}
                if [ "${AFCTEMP[$fcvcount]}" != "$tsen" ]
                then
                        afc_debug $AFC_NOTICE "Adjusing $tsen -> ${AFCTEMP[$fcvcount]}"
                fi
                let fcvcount=$fcvcount+1
        done

        let fcvcount=0
        while (( $fcvcount < ${#AFCFAN[@]} )) # go through all fan inputs
        do
                fan=${AFCFAN[$fcvcount]}
                AFCFAN[$fcvcount]=${fan//$DEVICE\/device/$DEVICE}
                if [ "${AFCFAN[$fcvcount]}" != "$fan" ]
                then
                        afc_debug $AFC_NOTICE "Adjusing $fan -> ${AFCFAN[$fcvcount]}"
                fi
                let fcvcount=$fcvcount+1
        done
}

# Some drivers moved their attributes from hard device to class device
function FixupFiles
{
        local DEVPATH="$1"
        local entry device

        for entry in $DEVPATH
        do
                device=`echo "$entry" | sed -e 's/=[^=]*$//'`

                if [ -e "$device/name" ]
                then
                        FixupDeviceFiles "$device"
                fi
        done
}

# Check that all referenced sysfs files exist
function CheckFiles
{
        local outdated=0 fcvcount pwmo tsen fan

        let fcvcount=0
        while (( $fcvcount < ${#AFCPWM[@]} )) # go through all pwm outputs
        do
                pwmo=${AFCPWM[$fcvcount]}
                if [ ! -w $pwmo ]
                then
                        afc_debug $AFC_NOTICE "Error: file $pwmo doesn't exist"
                        outdated=1
                fi
                let fcvcount=$fcvcount+1
        done

        let fcvcount=0
        while (( $fcvcount < ${#AFCTEMP[@]} )) # go through all temp inputs
        do
                tsen=${AFCTEMP[$fcvcount]}
                if [ ! -r $tsen ]
                then
                        afc_debug $AFC_NOTICE "Error: file $tsen doesn't exist"
                        outdated=1
                fi
                let fcvcount=$fcvcount+1
        done

        let fcvcount=0
        while (( $fcvcount < ${#AFCFAN[@]} )) # go through all fan inputs
        do
                # A given PWM output can control several fans
                for fan in $(echo ${AFCFAN[$fcvcount]} | sed -e 's/+/ /')
                do
                        if [ ! -r $fan ]
                        then
                                afc_debug $AFC_NOTICE "Error: file $fan doesn't exist"
                                outdated=1
                        fi
                done
                let fcvcount=$fcvcount+1
        done

        let fcvcount=0
        while (( $fcvcount < ${#AFCFANPRESENCE[@]} )) # go through all fan presence inputs
        do
                fpres=${AFCFANPRESENCE[$fcvcount]}
                if [ ! -r $fpres ]
                then
                        afc_debug $AFC_NOTICE "Error: file $fpres doesn't exist"
                        outdated=1
                fi
                let fcvcount=$fcvcount+1
        done

        let fcvcount=0
        while (( $fcvcount < ${#AFCFANDIRECTION[@]} )) # go through all fan direction inputs
        do
                fdir=${AFCFANPRESENCE[$fcvcount]}
                if [ ! -r $fdir ]
                then
                        afc_debug $AFC_NOTICE "Error: file $fdir doesn't exist"
                        outdated=1
                fi
                let fcvcount=$fcvcount+1
        done

        if [ $outdated -eq 1 ]
        then
                afc_debug $AFC_NOTICE "At least one referenced file is missing. Either some required kernel"
                afc_debug $AFC_NOTICE "modules haven't been loaded, or your configuration file is outdated."
                afc_debug $AFC_NOTICE "In the latter case, you should run pwmconfig again."
        fi

        return $outdated
}

if [ "$1" == "--check" ]
then
        if [ -f "$2" ]
        then
                LoadConfig $2
        else
                LoadConfig /etc/fancontrol
        fi
        exit 0
fi

if [ -f "$1" ]
then
        LoadConfig $1
else
        LoadConfig /etc/fancontrol
fi

# Detect path to sensors
if echo "${AFCPWM[0]}" | egrep -q '^/'
then
        DIR=/
elif echo "${AFCPWM[0]}" | egrep -q '^hwmon[0-9]'
then
        DIR=/sys/class/hwmon
elif echo "${AFCPWM[0]}" | egrep -q '^[1-9]*[0-9]-[0-9abcdef]{4}'
then
        DIR=/sys/bus/i2c/devices
elif [ "$FAN_SIMULATION" -eq 1 ]
then
        DIR=./
else
        afc_debug $AFC_ERR "$0: Invalid path to sensors"
        exit 1
fi

if [ ! -d $DIR ]
then
        afc_debug $AFC_ERR "$0: No sensors found! (did you load the necessary modules?)"
        exit 1
fi

cd $DIR

# Check for configuration change
if [ $FAN_SIMULATION -ne 1 ] && [ "$DIR" != "/" ] && [ -z "$DEVPATH" -o -z "$DEVNAME" ]
then
        afc_debug $AFC_ERR "Configuration is too old, please run pwmconfig again"
        exit 1
fi

if [ "$DIR" = "/" -a -n "$DEVPATH" ]
then
        afc_debug $AFC_ERR "Unneeded DEVPATH with absolute device paths"
        exit 1
fi
if ! ValidateDevices "$DEVPATH" "$DEVNAME"
then
        afc_debug $AFC_ERR "Configuration appears to be outdated, please run pwmconfig again"
        exit 1
fi
if [ "$DIR" = "/sys/class/hwmon" ]
then
        FixupFiles "$DEVPATH"
fi
CheckFiles || exit 1

if [ -f "$PIDFILE" ]
then
        afc_debug $AFC_ERR "File $PIDFILE exists, is fancontrol already running?"
        exit 1
fi
echo $$ > "$PIDFILE"

# $1 = pwm file name
function pwmdisable()
{
        local ENABLE=${1}_enable

        if [  -f $ENABLE ]
        then
            echo 0 > $ENABLE 2> /dev/null
            if [ `cat $ENABLE` -eq 0 ]
            then
                # Success
                return 0
            fi
        fi

        return 1
}

# $1 = pwm file name
function pwmenable()
{
        local ENABLE=${1}_enable

        if [ -f $ENABLE ]
        then
                echo 1 > $ENABLE 2> /dev/null
                if [ $? -ne 0 ]
                then
                        return 1
                fi
                return 0
        fi

        return 1
}

function restorefans()
{
        local status=$1 fcvcount pwmo

        afc_debug $AFC_ALERT 'Aborting, restoring fans...'
        adjustallfanpwms 255
        afc_debug $AFC_ALERT 'Verify fans have returned to full speed'
        AFC_CURRENT_STATE=$AFC_STATE_DAEMON_EXIT
        get_afc_state_string $AFC_CURRENT_STATE
        afc_debug $AFC_ALERT "$AFC_STATE_STRING"
        update_all_fans_leds "$AFC_CURRENT_STATE"
        rm -f "$PIDFILE"
        exit $status
}

trap 'restorefans 0' SIGQUIT SIGTERM
trap 'restorefans 1' SIGHUP SIGINT

function getmaxtemp ()
{
    local array_temp="$@"
    local fcvcount
    local tsensor temp

    tempMax=0
    let fcvcount=0
    let temp=0
    for tsensor in ${array_temp[@]}
    do
        read temp < $tsensor
        if [ $? -ne 0 ]
        then
                afc_debug $AFC_ERR "Error reading sensor value from $tsensor"
                temp=$AFCMAXTEMP
        fi

        if [ $temp -gt $tempMax ]
        then
            tempMax=$temp
        fi

        let fcvcount=$fcvcount+1
    done

}


function getminfanspeed
{

    local fcvcount
    local fanrpm
    local temp

    #use a larger value for comparison
    fanspeedMin=100000
    let fcvcount=0
    let temp=0
    while (( $fcvcount < ${#AFCFAN[@]} )) # go through all fan speed outputs
    do
        fanrpm=${AFCFAN[$fcvcount]}
        read temp < ${fanrpm}
        if [ $? -ne 0 ]
        then
                afc_debug $AFC_ERR "Error reading FAN RPM value from $DIR/$pwmo"
                temp=1
        fi

        if [ $temp -lt $fanspeedMin ]
        then
            fanspeedMin=$temp
        fi

        let fcvcount=$fcvcount+1
    done

}

#adjust fan pwm
function adjustallfanpwms
{
    local fcvcount
    local local_pwm_val
    local l_pwmo

    let local_pwm_val=$1

    if [[ $local_pwm_val -lt $AFCMINPWM ]]
    then
        local_pwm_val=$AFCMINPWM
    fi

    if [[ $local_pwm_val -gt $AFCMAXPWM ]]
    then
        local_pwm_val=$AFCMAXPWM
    fi

    afc_debug $AFC_INFO "Adjusting all fan pwm to $local_pwm_val"

    let fcvcount=0
    while (( $fcvcount < ${#AFCPWM[@]} )) # go through all pwm outputs
    do
        l_pwmo=${AFCPWM[$fcvcount]}
        echo $local_pwm_val > $l_pwmo # write new value to pwm output
        if [ $? -ne 0 ]
        then
                afc_debug $AFC_ERR "Error writing PWM value to $DIR/$l_pwmo"
                restorefans 1
        fi

        let fcvcount=$fcvcount+1
    done
}

#update min. and max. PWMs variables based on FAN direction
function updateFanMinMaxSpeedVars
{
    local d_val
    local fdir dir

    fdir=${AFCFANDIRECTION[0]}
    read dir < $fdir
    if [[ $? -ne 0 ]]; then
        return
    fi

    if [[ $dir -eq 0 ]]; then
        #f2b - port side exhaust - Blue fans
        if [ "${AFCMINPWM}" -lt "$F2B_FAN_MINPWM" ]
        then
            AFCMINPWM=${F2B_FAN_MINPWM}
        fi

        if [ "${AFCMAXPWM}" -gt "$F2B_FAN_MAXPWM" ]
        then
            AFCMAXPWM=${F2B_FAN_MAXPWM}
        fi

    else
        #b2f - port side inlet - Red fans
        if [ "${AFCMINPWM}" -lt "$B2F_FAN_MINPWM" ]
        then
            AFCMINPWM=${B2F_FAN_MINPWM}
        fi

        if [ "${AFCMAXPWM}" -gt "$B2F_FAN_MAXPWM" ]
        then
            AFCMAXPWM=${B2F_FAN_MAXPWM}
        fi
    fi
}

#Updates the FAN LED
#UpdateFanLed <fan index> <green | amber> <on | off>
function UpdateFanLed
{
    local fanidx=$1
    local ledcolor=$2
    local onoff=$3

    local brightness

    if [ "$fanidx" -lt "1"  -o "$fanidx" -gt $MAXFANLEDS ]
    then
        afc_debug $AFC_ERR "Invalid Fan index ; it has to be in the range 1-$MAXFANLEDS"
        return
    fi

    if [ "$ledcolor" != "green" -a "$ledcolor" != "amber" ]
    then
        afc_debug $AFC_ERR "Invalid FAN LED color ; it has to be either green or amber"
        return
    fi

    if [ "$onoff" != "on" -a "$onoff" != "off" ]
    then
        afc_debug $AFC_ERR "Invalid LED argument ; it has to either on or off"
        return
    fi

    afc_debug $AFC_DEBUG "Turning FAN $fanidx $ledcolor LED $onoff"

    #construct the FAN LED path
    FANLEDPATH="/sys/class/leds/fan$fanidx:$ledcolor/brightness"

    if [ "$onoff" == "on" ]
    then
        brightness=255
    else
        brightness=0
    fi

    if [ -f $FANLEDPATH ]
    then
        echo $brightness > $FANLEDPATH
    fi
}


#update all fan LEDs
function update_all_fans_leds
{
    local fcvcount
    local state=$1

    let fcvcount=0
    while (( $fcvcount < ${#AFCPWM[@]} )) # go through all pwm outputs
    do
        let fcvcount=$fcvcount+1
        case $state in
            $AFC_STATE_HOT)
                ;&
            $AFC_STATE_NORMAL)
                UpdateFanLed $fcvcount "green" "on"
                UpdateFanLed $fcvcount "amber" "off"
                ;;
            $AFC_STATE_START)
                ;&
            $AFC_STATE_INSUFFICIENT_FANS)
                ;&
            $AFC_STATE_FANS_FAULTY)
                ;&
            $AFC_STATE_CRITICAL)
                ;&
            $AFC_STATE_FANS_OPP_DIRECTION)
                ;&
            $AFC_STATE_INLET_HOT)
                ;&
            $AFC_STATE_DAEMON_EXIT)
                ;&
            *)
                UpdateFanLed $fcvcount "green" "off"
                UpdateFanLed $fcvcount "amber" "on"
                ;;

        esac
    done
}

# main function
function calc_new_fan_pwm
{
        local fcvcount
        local pwmo mint maxt hotinlett minpwm maxpwm
        local tval min_fanval
        local -i pwmval
        local n_vals d_val
        local fdir dir

        let mint="${AFCMINTEMP}*1000"
        let maxt="${AFCMAXTEMP}*1000"
        let hotinlett="${AFCHOTINLETMAXTEMP}*1000"

        afc_debug $AFC_DEBUG "mint=$mint"
        afc_debug $AFC_DEBUG "maxt=$maxt"
        afc_debug $AFC_DEBUG "hotinlett=$hotinlett"

        updateFanMinMaxSpeedVars
        minpwm=${AFCMINPWM}
        maxpwm=${AFCMAXPWM}
        afc_debug $AFC_DEBUG "minpwm=$minpwm"
        afc_debug $AFC_DEBUG "maxpwm=$maxpwm"


        # Policy #1
        #Check FAN PRESENCE and if some are absent, set full/max speed
        are_all_fans_present
        if [[ $? -ne 1 ]]; then
            AFC_CURRENT_STATE=$AFC_STATE_INSUFFICIENT_FANS
            AFC_CURRENT_PWM=$maxpwm
            return
        fi

        # Policy #2
        #Check whether all the fans are f2b (or) b2f. If not, set full/max speed
        are_all_fans_run_in_same_direction
        if [[ $? -ne 1 ]]; then
            AFC_CURRENT_STATE=$AFC_STATE_FANS_OPP_DIRECTION
            AFC_CURRENT_PWM=$maxpwm
            return
        fi

        # Policy #3
        # Hot inlet protection
        if [ "$AFC_ENABLE_HOTINLET_PROTECTION" -eq 1 ]
        then
            fdir=${AFCFANDIRECTION[0]}
            read dir < $fdir
            if [[ $? -ne 0 ]]; then
                afc_debug $AFC_ERR "Error reading $fdir"
                AFC_CURRENT_STATE=$AFC_STATE_INLET_HOT
                AFC_CURRENT_PWM=$maxpwm
                return
            fi

            if [[ $dir -eq 0 ]]; then
                #f2b - front port exhaust - blue fans
                getmaxtemp "${AFCFANSIDETEMP[@]}"
                tval=$tempMax
                if (( $tval >= $hotinlett ))
                then
                    AFC_CURRENT_STATE=$AFC_STATE_INLET_HOT
                    AFC_CURRENT_PWM=$maxpwm
                    return
                fi
            else
                #b2f - front port inlet - red fans
                getmaxtemp "${AFCFRONTPORTTEMP[@]}"
                tval=$tempMax
                if (( $tval >= $hotinlett ))
                then
                    AFC_CURRENT_STATE=$AFC_STATE_INLET_HOT
                    AFC_CURRENT_PWM=$maxpwm
                    return
                fi
            fi
        fi

        #Policy #4
        #Retrieve the min. fan speed to try to detect and cover faulty/absent fans
        getminfanspeed
        min_fanval=$fanspeedMin
        afc_debug $AFC_DEBUG "min_fanval=$min_fanval"

        if [ $min_fanval -le $MINSPEED ]
            then # if fan was stopped start it using a safe value
            AFC_CURRENT_STATE=$AFC_STATE_FANS_FAULTY
            AFC_CURRENT_PWM=$maxpwm
            return
        fi

        # Policy #5
        # All Fans are present, running ok and so find the max. system temperature, adjust the PWM accordingly

        #Retrieve the max. temperature
        getmaxtemp "${AFCTEMP[@]}"
        tval=$tempMax
        afc_debug $AFC_DEBUG "max tval=$tval"

        #Arrive at the new PWM value
        if (( $tval <= $mint ))
        then
            AFC_CURRENT_STATE=$AFC_STATE_NORMAL
            pwmval=$minpwm # below min temp, use defined min pwm
        elif (( $tval >= $maxt ))
        then
            AFC_CURRENT_STATE=$AFC_STATE_CRITICAL
            pwmval=$maxpwm # over max temp, use defined max pwm
        else
            AFC_CURRENT_STATE=$AFC_STATE_HOT
            # calculate the new value from temperature and settings
            pwmval="(${tval}-${mint})*(${maxpwm}-${minpwm})/(${maxt}-${mint})+${minpwm}"
        fi

        AFC_CURRENT_PWM=$pwmval

}

afc_debug $AFC_INFO 'Enabling PWM on fans...'
let fcvcount=0
get_afc_state_string $AFC_CURRENT_STATE
afc_debug $AFC_ALERT "$AFC_STATE_STRING"
update_all_fans_leds "$AFC_CURRENT_STATE"
afc_debug $AFC_NOTICE 'Starting automatic fan control...'

# main loop calling the main function at specified intervals
while true
do
        calc_new_fan_pwm
        update_afc_pwm
        update_afc_state_and_log_message
        # Sleep while still handling signals
        sleep $INTERVAL &
        wait
done
