#!/bin/sh
# images:alpine/3.13/amd64
##################################################################################
# Common base for most of the containers with minimal extension.
# This mostly just adds bash as this is suppose to be only script written in plain
# POSIX shell.
##################################################################################
set -e

# Modify configuration for expected network setup of NSFarm
sed -i 's/eth0/internet/g' /etc/network/interfaces

# Make wait scripts executable
for script in wait4boot wait4network; do
	chmod +x "/bin/$script"
done

# Now extend system
wait4network
apk update
apk add bash
