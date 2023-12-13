Raspberry Pi with USB LTE Stick as Modem
========================================

The following instructions were updated Dec 2023 and
tested on the new Bookworm-based Raspberry Pi OS Lite.

- Raspberry Pi 3B+ with microSD Card (e.g. 64GB SanDisk Extreme) and heatsink(s)
  - Other RPi models should work too, but that's what these notes were tested on
- LTE/UMTS Stick with SIM Card and optional external GSM antenna (with adapter cable if needed)
- Enclosure, optionally with 5V fan
- 5V >=3A regulator wired to RPi 5V supply pins, with 1000uF electrolytic capacitor

### Installation

1. Plug the LTE stick into a desktop PC (Linux is usually easiest; Windows may require drivers)
   and go to its web interface to set it up and make sure it works (PIN etc.)
   - Turn on automatic firmware updates
   - I also turned on UPnP although I'm not sure at the moment I will need it
     (testing in the past showed the stick I used didn't respond to UPnP port forwarding commands)
   - I also haven't yet tested using the LTE stick's DMZ mode
   - Note: The USB stick I used has the 192.168.8.X subnet and MAC enx001e101f0000

2. https://github.com/haukex/raspinotes/blob/7c42cf33/BaseInstall.md
   - But turn **on** predictable network interface names (`enxMACADDRESS`)
   - Overlay filesystem, no unattended upgrades, IP broadcast optional, fail2ban optional
   - Scheduled daily reboots (just to play it safe)

3. https://github.com/haukex/raspinotes/blob/7c42cf33/WiFiAP.md

4. Use `sudo nmtui` and rename the connections to nicer/shorter names;
   in particular, name the Ethernet connection `Ethernet`
   - `sudo nmcli connection modify LTEStick connection.metered TRUE`

5. Enable IP forwarding (assuming `ufw` is in use)

       sudo vi /etc/ufw/sysctl.conf  # and uncomment net/ipv4/ip_forward=1
       sudo vi /etc/sysctl.conf      # and uncomment net.ipv4.ip_forward=1
       sudo vi /etc/default/ufw      # and set DEFAULT_FORWARD_POLICY="ACCEPT"

6. Configure Ethernet+WiFi in a Bridge (based on the [RPi documentation][link1])
   **Important:** Pick a different IP address range than for WiFi, so as to
   not cause a conflict.

       sudo nmcli connection add type bridge con-name Bridge ifname bridge0 \
           ipv4.addresses 192.168.1.1/24 ipv4.method shared
       sudo nmcli connection modify Ethernet master bridge0
       sudo nmcli connection modify Hotspot master bridge0
       sudo nmtui  # and re-configure the WiFi connection password if necessary
       sudo systemctl restart NetworkManager

[link1]: https://www.raspberrypi.com/documentation/computers/configuration.html#use-your-raspberry-pi-as-a-network-bridge


Author, Copyright, and License
------------------------------

Copyright (c) 2023 Hauke Dämpfling <haukex@zero-g.net>
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
