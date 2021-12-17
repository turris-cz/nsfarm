#!/bin/bash
# nsfarm:client
##################################################################################
# Selenium client for testing web interface
##################################################################################
set -eu
GECKODRIVER_VERSION="0.29.1"
GECKODRIVER_URL="https://github.com/mozilla/geckodriver/releases/download/v${GECKODRIVER_VERSION}/geckodriver-v${GECKODRIVER_VERSION}-linux64.tar.gz"

# Create user we run web drivers under
addgroup -S webdriver
adduser -D -h /home/webdriver -G webdriver webdriver

# Make our init scripts executable
for init in xvfb x11vnc geckodriver chromedriver webkitdriver; do
	chmod +x "/etc/init.d/$init"
done

wait4network

# Selenium
apk add xvfb xorgproto x11vnc
rc-update add xvfb
rc-update add x11vnc

# Firefox
apk add firefox gcompat tar
wget "$GECKODRIVER_URL" -O - | tar -xzf - -C /usr/bin geckodriver
rc-update add geckodriver

# Chromium
apk add chromium-chromedriver chromium dbus
rc-update add dbus
rc-update add chromedriver

# WebKit
apk add webkit2gtk adwaita-icon-theme
rc-update add webkitdriver
