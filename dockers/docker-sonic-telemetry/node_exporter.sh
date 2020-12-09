#!/usr/bin/env bash

# node_exporter testfile_collector dir
NODE_EXPORTER_TEXT_COLL_DIR="/var/lib/node_exporter/textfile_collector"

# create node-exporter text_collector directory
mkdir -p $NODE_EXPORTER_TEXT_COLL_DIR

# Start with default config
NODE_EXPORTER_OPTS="--collector.textfile.directory $NODE_EXPORTER_TEXT_COLL_DIR"
exec /usr/sbin/node_exporter $NODE_EXPORTER_OPTS
