#!/bin/bash
# nsfarm:base-alpine
##################################################################################
# Common image for clients on LAN
##################################################################################
set -e

wait4network

# Add openssh client to access router shell
apk add openssh-client

# Configure LAN1 interface for static local network
cat >> /etc/network/interfaces <<EOF
auto lan
iface lan inet dhcp
EOF
