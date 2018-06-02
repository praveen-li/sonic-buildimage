#!/usr/bin/env bash

mkdir -p /var/sonic
echo "# Config files managed by sonic-config-engine" > /var/sonic/config_status

rm -f /var/run/rsyslogd.pid

supervisorctl start rsyslogd

# don't start telemetry daemons by default
echo "telemetry daemons are not started"
exit 0

supervisorctl start telemetry
supervisorctl start dialout
