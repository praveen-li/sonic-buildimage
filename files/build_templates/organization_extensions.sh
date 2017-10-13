#!/bin/bash
#########################################################################
## This script is to automate Orignaization specific extensions 	#
## such as Configuration & Scripts for features like AAA, ZTP, etc.	#
## to include in ONIE installer image					#
##									#
## USAGE:								#
##   ./organization_extensions.sh -f<filesystem_root> -n<hostname> 	#
##   ./organization_extensions.sh 	\				#
##			--fsroot <filesystem_root> 	\		#
##			--hostname <hostname>				#
## PARAMETERS:								#
##   -f FILESYSTEM_ROOT							#
##          The location of the root file system			#
##   -h HOSTNAME							#
##          The hostname of the target system				#
#########################################################################

## Initialize the arguments to default values.
## The values get updated to user provided value, if supplied
FILESYSTEM_ROOT=./fsroot
HOSTNAME=sonic

# read the options
TEMP=`getopt -o f:h: --long fsroot:,hostname: -- "$@"`
eval set -- "$TEMP"

# extract options and their arguments into variables.
while true ; do
    case "$1" in
        -f|--fsroot)
            case "$2" in
                "") shift 2 ;;
                *) FILESYSTEM_ROOT=$2 ; shift 2 ;;
            esac ;;
        -h|--hostname)
            case "$2" in
                "") shift 2 ;;
                *) HOSTNAME=$2 ; shift 2 ;;
            esac ;;
        --) shift ; break ;;
        *) echo "Internal error!" ; exit 1 ;;
    esac
done

echo "Executing SONIC Organization Extensions"

## LNOS Extensions to AAA
if [ -f files/lnos-internal/aaa/lnos_aaa.sh ]; then
   sudo chmod 755 files/lnos-internal/aaa/lnos_aaa.sh
   ./files/lnos-internal/aaa/lnos_aaa.sh $FILESYSTEM_ROOT $HOSTNAME
fi

## LNOS Extensions to CLI
if [ -f files/lnos-internal/scripts/lnos_cli_extensions.sh ]; then
   sudo chmod 755 files/lnos-internal/scripts/lnos_cli_extensions.sh
   ./files/lnos-internal/scripts/lnos_cli_extensions.sh $FILESYSTEM_ROOT
fi

## LNOS Extensions to ZTP
if [ -f files/lnos-internal/ztp/lnos_ztp.sh ]; then
   sudo chmod 755 files/lnos-internal/ztp/lnos_ztp.sh
   ./files/lnos-internal/ztp/lnos_ztp.sh $FILESYSTEM_ROOT
fi

echo "SONIC Organization Extensions - Done"

