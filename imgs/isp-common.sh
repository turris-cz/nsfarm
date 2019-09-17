#!/bin/bash
# nsfarm:base-alpine
##################################################################################
# This is base for various ISP like containers.
##################################################################################
set -e

wait4boot

echo Common > /desig
