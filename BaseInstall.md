
My Notes on Setting up Raspbian
===============================

*by Hauke Dämpfling <haukex@zero-g.net>
at the Leibniz Institute of Freshwater Ecology and Inland Fisheries (IGB),
Berlin, Germany, <http://www.igb-berlin.de/>
(legal information below)*

Introduction
------------

These instructions assume you have some basic knowledge of using
a Raspberry Pi and Raspbian / Debian.

Last tested:

- May 2020 on a Raspberry Pi Zero W with Raspbian Buster Lite 2020-02-13
- December 2020 on a Raspberry Pi Zero W with Raspberry Pi OS (32-bit) Lite 2020-12-02
- January 2021 on a Raspberry Pi 3B with Raspberry Pi OS (32-bit) Lite 2020-12-02
- May 2021 on a Raspberry Pi 3B+ with Raspberry Pi OS (32-bit) Lite 2021-03-04
- September 2021 on a Raspberry Pi 3B+ with Rasperry Pi OS (32-bit) Lite 2021-05-07
- May 2022 on a Raspberry Pi 3B+ with Raspberry Pi OS Lite (32-bit) 2022-04-04 (bullseye)


Basic Setup
-----------

1. Flash the Raspbian image onto an SD card. See also:
<https://www.raspberrypi.org/documentation/installation/installing-images/>
	
	1. On the `boot` partition:
	
		1. Touch a file `ssh`
		   (<https://www.raspberrypi.org/documentation/remote-access/ssh/>)
		
		2. In the file `config.txt`, uncomment the `hdmi_force_hotplug=1` line.
		
		3. Edit `wpa_supplicant.conf` to the following (make sure file has LF line endings;
		   <https://www.raspberrypi.org/documentation/configuration/wireless/headless.md>)
			
				ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
				update_config=1
				country=<Insert 2 letter ISO 3166-1 country code here, e.g. DE>
				
				network={
					ssid="ssid"
					psk="pass"
				}
	
	2. On the `rootfs` partition:
	
		1. Edit `/etc/hostname` and set the desired hostname
		
		2. Edit `/etc/hosts` to rename the `raspberrypi` entry as well
		
		3. **Security:** Set up SSH key-only auth before first boot:
		   Create `/home/pi/.ssh` and `chown` it to the same UID & GID as `/home/pi`,
		   and (optionally generating a new SSH key for this) copy your public SSH key
		   to `authorized_keys` in that directory, for example:
			
				sudo mkdir -vp home/pi/.ssh
				sudo cp -v ~/.ssh/id_rsa.pub home/pi/.ssh/authorized_keys
				sudo chmod -v 700 home/pi/.ssh
				sudo chmod -v 600 home/pi/.ssh/authorized_keys
				sudo chown -Rv `stat -c %u:%g home/pi` home/pi/.ssh
			
			Also edit `/etc/ssh/sshd_config` and set:
			
				PermitRootLogin no
				PasswordAuthentication no
	
	3. *Optional Procedure:* Protecting the SD card against wear and sudden power-offs
	   by making root FS read-only ("overlay filesystem") with a writable data partition
	
		1. Prevent automatic resize of the root filesystem
		   as per <https://raspberrypi.stackexchange.com/a/56623>:
		
			1. In `/boot/cmdline.txt`, remove `init=/usr/lib/raspi-config/init_resize.sh`
			
			2. In the RPi's root filesystem, delete
			   `/etc/init.d/resize2fs_once` and `/etc/rc3.d/S01resize2fs_once`
		
		2. Using e.g. `gparted`, resize the root filesystem on the SD card to the
		   desired size, e.g. 16GB, and then create a new ext4 partition covering
		   the rest of the space on the SD card, label it e.g. `data`
		
		3. After booting, create an `/etc/fstab` entry, you can get the ID via
		   `lsblk -o PARTUUID /dev/disk/by-label/data`. The entry might look like:
		   `PARTUUID=9730496b-03  /data  ext4  defaults,noatime  0  2`
		   where you should also do `sudo mkdir -v /data`. Then reboot.
		
		4. `sudo mkdir -v /data/pi`, `sudo chown pi:pi /data/pi`, and `ln -svnf /data/pi /home/pi/data`
		
		5. Note there is no point in setting up the "unattended upgrades" below,
		   you'll have to do updates manually. Also, while `fail2ban` (below) will
		   still generally work if the system isn't rebooted too often, note its
		   data will *not* be persisted across reboots unless all of it (including
		   the logs it uses) is placed on the `/data` partition.
		
		6. If setting up `postfix` and `alpine`, do this afterwards:
			
				sudo mkdir -v /data/spool
				sudo systemctl stop postfix
				ls -l /var/spool/mail  # => should normally be a symlink to ../mail !
				sudo mv -v /var/mail /data/spool/mail
				sudo mv -v /var/spool/postfix /data/spool/postfix
				sudo ln -svf /data/spool/mail /var/
				sudo ln -svf /data/spool/mail /var/spool/
				sudo ln -svf /data/spool/postfix /var/spool/
				sudo systemctl start postfix
				mv -v ~/mail /data/pi
				ln -svf /data/pi/mail ~
		
		7. Later, after completing the install, you can enable the "Overlay File System"
		   in the "Performance Options" of `raspi-config`. Remember that if making changes
		   that need to persist across reboots, you'll need to disable and re-enable this
		   option, rebooting each time.
	
	3. Boot the Pi and log in with ssh user `pi`; you can make the login with this username
	   automatic by putting the following in `~/.ssh/config` on your local machine:
		
			Host yourpihostname
				User pi
				IdentityFile ~/.ssh/id_rsa_yourprivkeyfile
	
	4. `sudo raspi-config`
	
		1. **Set a password**, and if not done above, the hostname
		
		2. Locales: Add needed locales (for me, `en_US.UTF-8` and `de_DE.UTF-8`),
		   don't delete existing locales, set `C.UTF-8` as default
		
		3. If setting the keyboard layout setting fails (e.g. if no keyboard connected),
		   edit `/etc/default/keyboard` and e.g. set `XKBLAYOUT="de"` and `XKBVARIANT="nodeadkeys"`
		
		4. All other options as appropriate
	
	5. `sudo apt-get update && sudo apt-get upgrade -y && sudo apt-get dist-upgrade -y && sudo apt-get autoremove -y && echo Done` (reboot afterwards is usually necessary)
	
	6. `sudo apt-get install --no-install-recommends ufw fail2ban vim git screen moreutils minicom ntpdate socat lsof tshark dnsutils elinks lftp proxychains4 build-essential cpanminus liblocal-lib-perl perl-doc jq zip`
	   (these is my preferred toolset on top of the Lite edition, you may modify this as you like)
	
	7. Misc.
	
		- `rm -vf /boot/wpa_supplicant.conf`
		- `sudo adduser pi wireshark`
		- `perl -Mlocal::lib >>~/.profile`
		- Set up any files like `.bash_aliases`, `.vimrc`, etc.

2. **UFW**: `sudo ufw allow OpenSSH && sudo ufw enable`

	- `sudo ufw logging off`, if logging messages fill up the syslog too much

3. **fail2ban**

	1. `sudo cp -v /etc/fail2ban/jail.conf /etc/fail2ban/jail.local`
	
	2. `ls -l /etc/fail2ban/action.d/ufw.conf` - file should exist
	
	3. `cat /etc/fail2ban/jail.d/defaults-debian.conf`:
	
		- Should contain `enabled = true` in section `[sshd]`
		- Add additional enables here if needed, for example,
		  create a section `[pure-ftpd]` and add `enabled = true`
	
	4. Edit `/etc/fail2ban/jail.local` to set the following values:
	
		- **Note:** search from the top of the file to set the global values in the `[DEFAULT]` section
		- `bantime   = 1day`
		- `findtime  = 6hours`
		- `maxretry  = 3`
		- `banaction = ufw`
		- In section `[sshd]`, set `mode = aggressive`
	
	5. In `/etc/fail2ban/fail2ban.conf`, set `dbpurgeage = 7d`
	
	6. `sudo systemctl restart fail2ban`, then check status:
	
		- `sudo fail2ban-client status`
		- `sudo fail2ban-client status sshd`
		- `sudo zgrep 'Ban' /var/log/fail2ban.log*`
	
	7. Note: Manual banning of repeat offenders:
	
		- `sudo zgrep Ban /var/log/fail2ban.log* | perl -wMstrict -Mvars=%x -nale '$x{$F[7]}++}{print "$_\t$x{$_}" for grep {$x{$_}>1} sort { $x{$b}<=>$x{$a} } keys %x'`
		- `sudo ufw deny from ADDRESS comment 'too many failed login attempts'`

4. **Crontab** to broadcast RPi's address and name

	1. `crontab -e`
		
			@reboot    hostname | socat -s - UDP-DATAGRAM:255.255.255.255:12340,broadcast 2>/dev/null
			* * * * *  hostname | socat -s - UDP-DATAGRAM:255.255.255.255:12340,broadcast 2>/dev/null
	
	2. In `/etc/rsyslog.conf`, apply this patch:
		
			-*.*;auth,authpriv.none          -/var/log/syslog
			+*.*;cron,auth,authpriv.none     -/var/log/syslog
	
	3. `sudo systemctl restart rsyslog`
	
	4. Can use `udplisten.py` from this repository to listen for the broadcasts.

5. **Mail**: Configure Postfix either as "Local only" or "Internet Site" as appropriate in the following steps:
	
		sudo apt-get install alpine postfix bsd-mailx
		sudo vi /etc/postfix/main.cf
		#=> correct "myhostname" if necessary
		#=> if it doesn't exist, add the line "smtp_tls_security_level = may"
		#=> if this option or the option "smtp_tls_CApath" doesn't exist,
		#   add the line "smtp_tls_CAfile = /etc/ssl/certs/ca-certificates.crt"
		sudo dpkg-reconfigure postfix  # and configure as appropriate
		echo "root: pi" | sudo tee -a /etc/aliases && echo "---" && cat /etc/aliases
		sudo newaliases && sudo systemctl restart postfix
		echo "This is a mailx test" | mailx -s "mailx test" root
		alpine
		# Configure "User Domain" and anything else as needed

6. **Unattended Upgrades**

	1. `sudo apt-get install unattended-upgrades`
	
	2. `sudo vi /etc/apt/apt.conf.d/50unattended-upgrades`
		- Change the two `origin=Debian` to `origin=${distro_id}`
		  and change `label=Debian` to `label=Raspbian`
		- Set `Unattended-Upgrade::Mail` to `pi@localhost`
	
	3. `sudo vi /etc/apt/apt.conf.d/20auto-upgrades`
		
			APT::Periodic::Update-Package-Lists "1";
			APT::Periodic::Unattended-Upgrade "1";
			APT::Periodic::Download-Upgradeable-Packages "1";
			//APT::Periodic::Verbose "1";
			APT::Periodic::AutocleanInterval "7";
	
	4. Test with `sudo unattended-upgrade -d -v --dry-run`
	
	5. Enable with `sudo dpkg-reconfigure --priority=low unattended-upgrades`

7. **Miscellaneous**

	- For network time, `sudo apt-get install --no-install-recommends ntp` and edit `/etc/ntp.conf` as appropriate.
	
	- If the Raspberry Pi doesn't have direct internet access after installation:
		
		1. In `/etc/proxychains4.conf`, replace the default `socks4` line in the `[ProxyList]` section
		   with `socks5	127.0.0.1	12333`
		
		2. When you connect to the RPi via SSH, use `ssh -R12333 pi@...`
		
		3. Then, commands that support it, you can use e.g. `ALL_PROXY=socks5h://localhost:12333 curl http://example.com`,
		   for other commands use e.g. `sudo proxychains4 -q apt-get update` or `proxychains4 -q cpanm ...`
	
	- Sometimes, on some WiFi nets, WiFi will stop working unless I reboot the Pi once in a while.
	  This can be done via e.g. `sudo -i crontab -e`: `0 8 * * * /sbin/shutdown --reboot +5 2>/dev/null`
	
	- Serial port: `sudo adduser pi dialout`, `stty -F /dev/ttyS0 19200 cs8 -parenb raw -crtscts -echo`, `cat /dev/ttyS0`
	  (Also: `minicom -D/dev/ttyS0` and `screen /dev/ttyS0 19200`)


Author, Copyright, and License
------------------------------

Copyright (c) 2016-2022 Hauke Dämpfling <haukex@zero-g.net>
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
