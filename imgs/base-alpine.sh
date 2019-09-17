#!/bin/sh
# images:alpine/3.10/amd64
##################################################################################
# Common base for most of the containers with minimal extension.
# This mostly just adds bash as this is suppose to be only script written in plain
# POSIX shell.
##################################################################################
set -e

# Make wait scripts executable
for script in wait4boot wait4network; do
	chmod +x "/bin/$script"
done

# Now extend system
wait4network
apk update
apk add bash
