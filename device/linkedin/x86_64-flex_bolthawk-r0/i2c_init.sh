#!/bin/bash

readonly QSFP_STATE_MUX_ADDR='0x74'
readonly QSFP_RESET_LPMODE_CH='0x02'
readonly QSFP_RESET_LPMODE_ADDR='0x21'
readonly QSFP_RESET_ADDR='2'
readonly QSFP_LPMODE_ADDR='3'
readonly QSFP_IO0_CTL='6'
readonly QSFP_IO1_CTL='7'

# prob i2c devices
/usr/bin/bcmcmd "i2c prob"

# Enable the I2C mux to access RESET_N and LPMODE IOs
cmd="i2c write $QSFP_STATE_MUX_ADDR $QSFP_RESET_LPMODE_CH"
cmd="/usr/bin/bcmcmd \"$cmd\""
echo $cmd
eval $cmd

# Set IO expander of RESET_N and LPMODE IOs to output
cmd="i2c write $QSFP_RESET_LPMODE_ADDR $QSFP_IO0_CTL 0x00"
cmd="/usr/bin/bcmcmd \"$cmd\""
echo $cmd
eval $cmd

cmd="i2c write $QSFP_RESET_LPMODE_ADDR $QSFP_IO1_CTL 0x00"
cmd="/usr/bin/bcmcmd \"$cmd\""
echo $cmd
eval $cmd

#Clear RESET
cmd="i2c write $QSFP_RESET_LPMODE_ADDR $QSFP_RESET_ADDR 0xff"
cmd="/usr/bin/bcmcmd \"$cmd\""
echo $cmd
eval $cmd

# Turn off lpmode
cmd="i2c write $QSFP_RESET_LPMODE_ADDR $QSFP_LPMODE_ADDR 0x00"
cmd="/usr/bin/bcmcmd \"$cmd\""
echo $cmd
eval $cmd
