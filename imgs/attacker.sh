#!/bin/bash
# nsfarm:base-alpine net:wan
##################################################################################
# This is container to perform attacks to router from WAN side.
##################################################################################
set -e

wait4network

## Software to perform various types of connections
apk add busybox-extras ncftp nmap openssh


## Configure WAN interface of router
cat >> /etc/network/interfaces <<EOF
auto wan
iface wan inet static
        address 172.16.42.42
        netmask 255.240.0.0
EOF
