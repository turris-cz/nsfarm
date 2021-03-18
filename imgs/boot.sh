#!/bin/bash
# nsfarm:base-alpine internet net:wan
##################################################################################
# This is image used to boot medkit. It provides TFTP server with prepared image
# for u-boot.
##################################################################################
set -e

# Make prepare script executable so we can later run it
chmod +x "/bin/prepare_turris_image"

# Configure WAN interface for static local network
cat >> /etc/network/interfaces <<EOF
auto wan
iface wan inet static
        address 192.168.1.1
        netmask 255.255.255.0
EOF

# Install utilities we need to repack image
apk add uboot-tools

# Install and enable TFTP server
apk add tftp-hpa
rc-update add "in.tftpd" default
