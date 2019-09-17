#!/bin/bash
# nsfarm:isp-common
##################################################################################
# This is simulating ISP with simple DHCP setup.
##################################################################################
# 2
set -e

wait4boot

echo DHCP > /desig
