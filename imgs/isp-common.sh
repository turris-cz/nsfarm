#!/bin/bash
# nsfarm:base-alpine internet net:wan
##################################################################################
# This is base for various ISP like containers.
##################################################################################
set -e

wait4network

## Firewall
# Install requirements
apk add iptables ip6tables lua5.2-lyaml awall
# Activate firewall services
rc-update add iptables
rc-update add ip6tables
# Activate policies (provided to container by files)
awall enable isp isp-iperf3
# Activate firewall itself
awall activate --force

## DNS service
# Install and activate bind
apk add bind
rc-update add named
# Changing premissions to folders copied to container
# - the permissions are not managed when copying by nsfarm (see README.md)
chown :named /etc/bind
chmod a+r /etc/bind/named.conf

## Additonal service
# iperf3 for benchmarking tests
apk add iperf3 iperf3-openrc
rc-update add iperf3 default

## Configure WAN interface of router
cat >> /etc/network/interfaces <<EOF
auto wan
iface wan inet static
        address 172.16.1.1
        netmask 255.240.0.0
EOF
