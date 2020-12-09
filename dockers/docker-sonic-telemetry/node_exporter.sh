#!/usr/bin/env bash

# create node-exporter text_collector directory
mkdir -p /var/lib/node_exporter/textfile_collector

# Start with default config
NODE_EXPORTER_OPTS="--collector.textfile.directory /var/lib/node_exporter/textfile_collector"
exec /usr/sbin/node_exporter $NODE_EXPORTER_OPTS
