#!/bin/bash
# nsfarm:client
##################################################################################
# Client on WiFi
##################################################################################
set -e

wait4network

# Install wpa_supplicant
apk add wpa_supplicant-openrc
rc-update add wpa_supplicant default
