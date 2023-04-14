Raspberry Pi as Wi-Fi Access Point
==================================

**Important:** Do this *last*, because installing stuff via reverse proxy
can be a bit of a pain!

- Initial steps
  
      sudo apt-get install hostapd dnsmasq
      sudo systemctl stop dnsmasq
      sudo systemctl stop hostapd
      sudo cp /etc/dnsmasq.conf /etc/dnsmasq.conf.orig
      sudo ufw allow DNS
      sudo ufw allow from any port 68 to any port 67 proto udp comment DHCP
  
- `sudo vi /etc/dhcpcd.conf` and add the lines:
  
      interface wlan0
      static ip_address=192.168.42.1/24
      static domain_name_servers=192.168.42.1
      nohook wpa_supplicant
  
- `sudo vi /etc/dnsmasq.conf` and add the lines:
  
      interface=wlan0
      domain-needed
      bogus-priv
      dhcp-range=192.168.42.100,192.168.42.150
      domain=internal
      address=/YOURHOSTNAME.internal/192.168.42.1
  
- `sudo vi /etc/hostapd/hostapd.conf` and create or replace contents with:
  
      interface=wlan0
      driver=nl80211
      ssid=YOUR_SSID_HERE
      hw_mode=g
      country_code=DE
      channel=5
      wmm_enabled=0
      macaddr_acl=0
      auth_algs=1
      ignore_broadcast_ssid=0
      wpa=2
      wpa_passphrase=YOUR_PASSPHRASE_HERE
      wpa_key_mgmt=WPA-PSK
      wpa_pairwise=TKIP
      rsn_pairwise=CCMP
  
- `sudo vi /etc/default/hostapd` and set
  `DAEMON_CONF="/etc/hostapd/hostapd.conf"`
  
- Start things up:
  
      sudo systemctl unmask hostapd
      sudo reboot
  
- To disable temporarily:
  - `sudo systemctl disable hostapd`
  - `sudo vi /etc/dhcpcd.conf` and comment out the lines added above
  - `sudo reboot`

Access Point + Client
---------------------

**TODO** I tried the following, but this caused connection instability.
I need to investigate further.

First do:

        echo 'KERNEL=="wlan0", ACTION=="add", RUN+="/usr/sbin/iw dev %k interface add uap0 type __ap"' | sudo tee /etc/udev/rules.d/90-wlan.rules

And then use `uap0` instead of `wlan0` in the instructions above.


Author, Copyright, and License
------------------------------

Copyright (c) 2018-2023 Hauke Dämpfling <haukex@zero-g.net>
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
