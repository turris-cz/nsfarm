#!/bin/bash
# nsfarm:isp-common char:/dev/ppp
##################################################################################
# This is simulating ISP with PPPoE setup.
##################################################################################
set -e

wait4network

# DHCP server
apk add busybox-extras busybox-initscripts
# rp-pppoe PPPoE server
apk add rp-pppoe ppp
rc-update add rp-pppoe default

awall enable isp-pppoe
awall activate --force
