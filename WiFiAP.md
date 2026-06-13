Raspberry Pi as Wi-Fi Access Point
==================================

**Important:** Do this *last*, because installing stuff via reverse proxy can be a bit of a pain!

The following instructions were based on the [official RPi documentation on the topic][link1] (as
of Dec 2023) and tested to be working (as of June 2026) on the Trixie-based Raspberry Pi OS Lite.

[link1]: https://www.raspberrypi.com/documentation/computers/configuration.html#host-a-wireless-network-on-your-raspberry-pi

- Assuming you're using `ufw`:

      sudo ufw allow DNS
      sudo ufw allow from any port 68 to any port 67 proto udp comment DHCP

- To set up and enable the WiFi AP, do the following. **Note:** If you're currently connected to
  the RPi via WiFi, the first command will immediately try to start up the AP and kill your
  connection, so you'll probably want to do the following via a console.

      sudo nmcli device wifi hotspot con-name Hotspot ssid <SSID> password <Password>
      sudo nmcli connection modify Hotspot ipv4.method shared ipv4.may-fail no \
        ipv4.addresses 192.168.42.1/24 ipv6.method disabled \
        autoconnect TRUE connection.autoconnect-priority 1
      sudo systemctl restart NetworkManager

- On the Raspberry Pi Zero W, I've had issues with the network connection not activating; the
  following fixed it:

      sudo nmcli connection modify Hotspot \
        802-11-wireless-security.pmf 1 \
        802-11-wireless-security.proto "" \
        802-11-wireless-security.pairwise "" \
        802-11-wireless-security.group ""
      sudo nmcli c down Hotspot
      sudo systemctl restart NetworkManager

- If you keep the WiFi client connection you had previously, and you want to switch back to that:

      sudo nmcli connection modify Hotspot autoconnect FALSE connection.autoconnect-priority 0
      sudo nmcli connection down Hotspot

  If you don't want to keep the client connection, then you can simply delete it,
  and the above `autoconnect-priority` setting on the hotspot is not needed.

- If there are files in `/etc/netplan` that cause connections to be reconfigured on every reboot,
  read them first to check, but it is usually safe to delete them. See also the notes in
  [my base install notes](./BaseInstall.md) on removing `cloud-init`.

- I've noticed that sometimes, some of the commands to modify the network connection reset the PSK.
  To check and fix:

      sudo nmcli c show --show-secrets Hotspot | grep psk
      # And in case the password has been reset:
      sudo nmcli c modify Hotspot 802-11-wireless-security.psk '<Password>'

- Tips:
  - Short device and connection list: `nmcli device` and `nmcli connection`
    (can also be abbreviated `nmcli d` and `nmcli c`); details via `nmcli c show <con-name>`
  - Documentation on NetworkManager settings: `man nm-settings`
    and <https://networkmanager.dev/docs/man-pages/>
  - `sudo nmtui` is a curses-based NetworkManager configuration tool that can do (almost) all of
    the above (it apparently doesn't support changing the `autoconnect` settings).
  - In some cases, depending on the router, it may help to add `ipv6.disable=1` to `cmdline.txt`
    if IPv6 isn't needed.


Making the RPi a NAT Access Point for its Ethernet
--------------------------------------------------

Assuming you're *not* using UFW! Otherwise, please see [my USB LTE Modem notes](./USB-LTE-Modem.md).

1. Checks
   - Ensure `net.ipv4.ip_forward=1` is on: `cat /proc/sys/net/ipv4/ip_forward`.
     If not, add a file in `/etc/sysctl.d` with that line.
   - `sudo nmcli c show Hotspot | grep ip4v.method` should show `shared`.
2. Configure NAT with nftables
   - `sudo nft add table ip nat`
   - `sudo nft 'add chain ip nat postrouting { type nat hook postrouting priority 100 ; }'`
   - `sudo nft add rule ip nat postrouting oifname eth0 masquerade`
3. Configure Forwarding Rules
   - `sudo nft add table ip filter`
   - `sudo nft 'add chain ip filter forward { type filter hook forward priority 0; policy accept; }'`
   - `sudo nft add rule ip filter forward ct state established,related accept`
   - `sudo nft add rule ip filter forward iifname wlan0 oifname eth0 accept`
4. Persist Changes
   - `sudo nft list ruleset | sudo tee -a /etc/nftables.conf`
   - `cat /etc/nftables.conf` and read it to make sure it makes sense
   - `sudo systemctl enable nftables`


Previous Manual Instructions
----------------------------

**Unmaintained:** Assuming the above `nmcli` method continues to work well for me, I will eventually delete this section.

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


<!-- spell: ignore wlan CCMP Hotspot TKIP Trixie YOURHOSTNAME algs cmdline dhcpcd dnsmasq hostapd
spell: ignore iifname macaddr mgmt netplan nftables nmcli nmtui nohook oifname postrouting -->

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
