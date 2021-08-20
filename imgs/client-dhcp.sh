#!/bin/bash
# nsfarm:client net:lan
##################################################################################
# DHCP image for clients on LAN
##################################################################################
set -e

wait4network

# Add openssh client to access router shell
apk add openssh-client

# Additional applications installation
apk add iperf3

# First remove config of static ip
sed -i '/auto lan.*/,$d' /etc/network/interfaces
# Configure LAN1 interface for static local network
cat >> /etc/network/interfaces <<EOF
auto lan
iface lan inet dhcp
EOF
