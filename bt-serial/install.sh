#!/bin/bash
set -euxo pipefail
cd -- "$( dirname -- "${BASH_SOURCE[0]}" )"

sudo apt-get install -y python3-serial python3-bluez python3-inotify python3-types-pyserial
sudo install -o root -g root -m 755 bt_serial_bridge.py /usr/local/bin/
sudo install -o root -g root -m 644 bt-serial-bridge.service /etc/systemd/system/
