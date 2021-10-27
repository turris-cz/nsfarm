#!/bin/sh
# images:openwrt/19.07
##################################################################################
# OpenWrt container we can use to test nsfarm as well as cooperation with Turris.
##################################################################################
set -e

# Make wait scripts executable
for script in wait4boot wait4network; do
	chmod +x "/bin/$script"
done

wait4boot

# Configure the Internet access
uci set network.wan.ifname=internet
uci commit network
/etc/init.d/network reload

# Now extend system
wait4network
opkg update
opkg install bash coreutils-base64
