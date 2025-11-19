Serial-to-Bluetooth Bridge
==========================

- Tested on Raspberry Pi Zero W with Raspberry Pi OS Lite 32-bit 2025-10-01 (trixie)
  - A fairly large electrolytic capacitor (e.g. 470-1000uF) on the 5V pins is useful
    to handle current spikes and prevent reboots when plugging in OTG cable.
- Base Installation: <https://github.com/haukex/raspinotes/blob/e6d82750/BaseInstall.md>
  - With overlay filesystem, ufw, proxychains
  - Without fail2ban, crontab, mail, unattended upgrades
  - In raspi-config, enable WLAN power saving

Setup on RPi:

    git clone https://github.com/haukex/raspinotes.git ~/code/raspinotes

    ~/code/raspinotes/bt-serial/install.sh

    sudo vi /etc/systemd/system/bt-serial-bridge.service
      # Adjust settings (UUID, ports, baud rate etc.) in that file as needed
      # BT UUID should be random, *except* xxxxxxxx-0000-1000-8000-00805f9b34fb
    # Just for example, this replaces the UUID by a random one:
    sudo perl -wMstrict -i -pe 's/--bt-uuid=\K[-0-9a-fA-F]{36}\b/chomp(my $u=lc qx#uuid -v4#);say STDERR $u;$u/e' /etc/systemd/system/bt-serial-bridge.service

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

    # Optional (conserve power on deployed systems):
    sudo rfkill block wlan

Debugging notes:

    # For testing:
    sudo socat pty,rawer,link=/tmp/fakepty -,icanon=0,min=1
    sudo vi /etc/systemd/system/bt-serial-bridge.service
      ExecStart=... --debug /tmp/fakepty

    # Simulating re-connect
    ls -l /sys/bus/usb-serial/devices  #=> e.g. ".../usb1/1-1/1-1:..."
    echo '1-1' | sudo tee /sys/bus/usb/drivers/usb/unbind
    echo '1-1' | sudo tee /sys/bus/usb/drivers/usb/bind


<!-- spell: ignore Mstrict Pairable bluetoothd fakepty icanon rfkill socat wlan trixie proxychains raspi raspinotes -->

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
