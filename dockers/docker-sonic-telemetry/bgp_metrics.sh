#!/usr/bin/env bash

# Start with default config

exec /usr/sbin/bgp_metrics -poll_interval 10s -logtostderr  -v 2
