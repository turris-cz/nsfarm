#!/bin/sh
PYTHONPATH="$(readlink -f "${0%/*}")"
export PYTHONPATH
exec /usr/bin/env python3 -m nsfarm "$@"
