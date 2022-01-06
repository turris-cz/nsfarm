#!/bin/bash
# nsfarm:client net:lan
##################################################################################
# Image with static IP assigned to it.
# Note that there should be always only one instance of such image on one
# network as otherwise they will collide.
##################################################################################
set -e

wait4network

# Add openssh client to access router shell
apk add openssh-client

# Additional applications installation
apk add iperf3
apk add netcat-openbsd

# First remove config for DHCP
sed -i '/auto lan.*/,$d' /etc/network/interfaces
# Configure LAN1 interface for static local network
cat >> /etc/network/interfaces <<EOF
auto lan
iface lan inet static
        address 192.168.1.10
        netmask 255.255.255.0
        gateway 192.168.1.1
EOF
