#!/bin/bash
# nsfarm:isp-common
##################################################################################
# This is simulating ISP with simple DHCP setup.
##################################################################################
set -e

wait4network

# DHCP server
apk add busybox-extras busybox-initscripts
rc-update add udhcpd default

awall enable isp-dhcp
awall activate --force
