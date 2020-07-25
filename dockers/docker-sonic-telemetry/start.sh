#!/usr/bin/env bash

mkdir -p /var/sonic
echo "# Config files managed by sonic-config-engine" > /var/sonic/config_status

rm -f /var/run/rsyslogd.pid

supervisorctl start rsyslogd

supervisorctl start telemetry
supervisorctl start dialout
supervisorctl start node_exporter
supervisorctl start bgp_metrics
