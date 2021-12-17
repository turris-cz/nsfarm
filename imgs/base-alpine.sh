#!/bin/sh
# images:alpine/3.15
##################################################################################
# Common base for most of the containers with minimal extension.
# This mostly just adds bash as this is suppose to be only script written in plain
# POSIX shell.
##################################################################################
set -e

# Make wait and init scripts executable
for script in wait4boot wait4network wait4tcp; do
	chmod +x "/bin/$script"
done
chmod +x "/etc/init.d/devshm"
rc-update add devshm boot

wait4boot

# Modify configuration for expected network setup of NSFarm
sed -i 's/eth0/internet/g' /etc/network/interfaces
rc-service networking restart

# Now extend system
wait4network
apk update
apk add bash
