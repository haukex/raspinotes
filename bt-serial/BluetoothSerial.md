Serial-to-Bluetooth Bridge
==========================

**WARNING: BETA** I've only done basic testing on this.

- Tested on Raspberry Pi Zero W with Raspberry Pi OS Lite 32-bit 2025-10-01 (trixie)
- Base Installation: <https://github.com/haukex/raspinotes/blob/e6d82750/BaseInstall.md>
  - With overlay filesystem, ufw
  - Without fail2ban, crontab, mail, unattended upgrades

Setup:

    # From local machine:
    scp bt_serial_bridge.py bt-serial-bridge.service pi@192.168.x.x:
    # Then ssh into the RPi

    sudo apt install -y python3-serial python3-bluez python3-inotify

    sudo mv -v ~/bt_serial_bridge.py /usr/local/bin/
    sudo chown -c root:root /usr/local/bin/bt_serial_bridge.py
    sudo chmod -c 755 /usr/local/bin/bt_serial_bridge.py

    sudo mv -v ~/bt-serial-bridge.service /etc/systemd/system/
    sudo chown -c root:root /etc/systemd/system/bt-serial-bridge.service
    sudo chmod -c 644 /etc/systemd/system/bt-serial-bridge.service
    # Adjust settings (port name, baud rate etc.) in that file as needed

    sudo rfkill unblock bluetooth

    sudo vi /etc/bluetooth/main.conf
      DiscoverableTimeout = 0
      AlwaysPairable = true
      JustWorksRepairing = always

    echo PRETTY_HOSTNAME="Ser-BT-1" | sudo tee /etc/machine-info

    sudo perl -wMstrict -i -pe 's#^ExecStart=.*bluetoothd\K\s*$# --compat\n#' /lib/systemd/system/bluetooth.service

    sudo systemctl daemon-reload
    sudo systemctl restart bluetooth

    sudo systemctl enable bt-serial-bridge
    sudo systemctl start bt-serial-bridge

    # For testing:
    sudo socat pty,rawer,link=/tmp/fakepty -,icanon=0,min=1
    sudo vi /etc/systemd/system/bt-serial-bridge.service
      ExecStart=... --debug /tmp/fakepty

    # Optional (conserve power on deployed systems):
    sudo rfkill block wlan

<!-- spell: ignore Mstrict Pairable bluetoothd bluez fakepty icanon rfkill socat wlan trixie inotify -->


Author, Copyright, and License
------------------------------

Copyright (c) 2025 Hauke Dämpfling <haukex@zero-g.net>
at the Leibniz Institute of Freshwater Ecology and Inland Fisheries (IGB),
Berlin, Germany, <https://www.igb-berlin.de/>

This project is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This project is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this project. If not, see <https://www.gnu.org/licenses/>.
