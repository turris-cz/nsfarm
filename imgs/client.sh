#!/bin/bash
# nsfarm:base-alpine net:lan
##################################################################################
# Common image for clients on LAN
##################################################################################
set -e

wait4network

# Add openssh client to access router shell
apk add openssh-client
ssh-keygen -f /root/.ssh/id_rsa -N ''

# Additional applications installation
apk add iperf3

# Configure LAN1 interface for static local network
cat >> /etc/network/interfaces <<EOF
auto lan
iface lan inet static
        address 192.168.1.10
        netmask 255.255.255.0
        gateway 192.168.1.1
EOF
