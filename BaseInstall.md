
My Notes on Setting up Raspberry Pi OS
======================================

*by Hauke Dämpfling <haukex@zero-g.net>
at the Leibniz Institute of Freshwater Ecology and Inland Fisheries (IGB),
Berlin, Germany, <http://www.igb-berlin.de/>
(legal information below)*

Introduction
------------

These instructions assume you have knowledge of using a Raspberry Pi and Debian Linux.

**Last tested:**

- December 2023 with
	- Raspberry Pi OS Lite 64-bit 2023-12-11 (bookworm)
	- Raspberry Pi Imager v1.8.1
	- Raspberry Pi 3B+

Basic Setup
-----------

1. **Pre-Boot Setup**
	
	1. Use the Raspberry Pi Imager to flash the OS onto the SD card as per its instructions,
	   with the following notes:
	
		1. You may need to select "No filtering" for the device so the OS selection isn't filtered.
		   I (almost) always use the "lite" edition.
		
		2. Use OS customization and edit and enable all of the settings:
		
			- Hostname
			- Username (I usually stick to `pi` for consistency) and password
			- WiFi
			- Locale settings
			- Enable SSH and set up key ("Allow public-key authentication only")
			- Disable telemetry
		
		3. The following steps in this section assume you've got the resulting SD card mounted on a Linux system.
	
	2. *Optional:* If you need to set up `cron` jobs before the first boot, like those
	   described in the corresponding section below, that is possible as follows.
	   *Note* that the format of the crontab file *must* be valid, so double-check it for mistakes;
	   after booting the RPi, always use `crontab -e` to edit the crontab.
	
			cd /path/to/rootfs
			sudo vi var/spool/cron/crontabs/pi
			# edit the file as necessary
			sudo chmod -v 600 var/spool/cron/crontabs/pi
			sudo chown -v `stat -c %u home/pi`:`stat -c %g var/spool/cron/crontabs` var/spool/cron/crontabs/pi
	
	3. *Optional Procedure:* Protecting the SD card against wear and sudden power-offs
	   by making root FS read-only ("overlay filesystem") with a writable data partition.
		
		1. **Note** there is no point in setting up the "unattended upgrades" below,
		   you'll have to do updates manually. Also, while `fail2ban` (below) will
		   still generally work if the system isn't rebooted too often, note its
		   data will *not* be persisted across reboots unless all of it (including
		   the logs it uses) is placed on the `/data` partition - this is not (yet)
		   covered in these instructions.
		
		2. Using e.g. `gparted`, resize the root filesystem on the SD card to the
		   desired size, e.g. 16GB, and then create a new ext4 primary partition covering
		   the rest of the space on the SD card, label it e.g. `data`
		   (at least that's what the rest of these instructions assume).
		
		3. The rest of this prodecure after booting is covered below.

2. **At First Boot Procedures**

	1. Boot the Pi and log in with ssh user `pi`; you can make the login with this username
	   automatic by putting the following in `~/.ssh/config` on your local machine:
		
			Host yourpihostname
				User pi
				IdentityFile ~/.ssh/id_rsa_yourprivkeyfile
	
	2. `sudo raspi-config`
	
		1. Locales: Add needed locales (for me, `en_US.UTF-8` and `de_DE.UTF-8`),
		   don't delete existing locales, set `C.UTF-8` as default
		
		2. I prefer turning off predictable network interface names
		   (this gives `eth0` instead of `enxMACADDR`; the WiFi adapter is apparently always called `wlan0`)
		
		3. Optional: Any other options as appropriate
		
		4. Since I usually configure my RPi remotely with no keyboard connected,
		   the keyboard configuration in `raspi-config` usually fails, so if that happens,
		   edit `/etc/default/keyboard` and set e.g. `XKBLAYOUT="de"` and `XKBVARIANT="nodeadkeys"`
	
	3. `sudo apt update && sudo apt full-upgrade -y && sudo apt autoremove -y && echo Done`
	   (reboot afterward is usually necessary)
	
	4. `sudo apt-get install --no-install-recommends aptitude ufw vim git screen moreutils minicom ntpdate socat lsof tshark dnsutils elinks lftp jq zip tofrodos proxychains4 build-essential cpanminus liblocal-lib-perl perl-doc python3-pip python3-dev`
	   (these are my preferred tools on top of the Lite edition, you may modify this as you like)
	
	5. Misc.
	
		- Edit `/etc/ssh/sshd_config` and set `PermitRootLogin no`
		- `sudo adduser pi wireshark`
		- `perl -Mlocal::lib >>~/.profile`
		- Set up any files like `.bash_aliases`, `.vimrc`, etc.

3. **UFW**: `sudo ufw allow OpenSSH && sudo ufw enable`

	- `sudo ufw logging off`, if logging messages fill up the syslog too much

4. **fail2ban**

	1. `sudo apt-get install --no-install-recommends fail2ban python3-systemd`

	2. `sudo cp -v /etc/fail2ban/jail.conf /etc/fail2ban/jail.local`
	
	3. `ls -l /etc/fail2ban/action.d/ufw.conf` - file should exist
	
	4. `cat /etc/fail2ban/jail.d/defaults-debian.conf`:
	
		- Should contain `enabled = true` in section `[sshd]`
		- Add additional enables here if needed, for example,
		  create a section `[pure-ftpd]` and add `enabled = true`
	
	5. Edit `/etc/fail2ban/jail.local` to set the following values:
	
		- **Note:** search from the top of the file to set the global values in the `[DEFAULT]` section
		- `bantime   = 1day`
		- `findtime  = 6hours`
		- `maxretry  = 3`
		- `backend   = systemd`  (<https://github.com/fail2ban/fail2ban/issues/3292#issuecomment-1678844644>)
		- `banaction = ufw`
		- In section `[sshd]`, set `mode = aggressive`
	
	6. In `/etc/fail2ban/fail2ban.conf`, set `dbpurgeage = 7d`
	
	7. `sudo systemctl restart fail2ban`, then check status:
	
		- `sudo fail2ban-client status`
		- `sudo fail2ban-client status sshd`
		- `sudo zgrep 'Ban' /var/log/fail2ban.log*`
	
	8. Note: Manual banning of repeat offenders:
	
		- `sudo zgrep Ban /var/log/fail2ban.log* | perl -wMstrict -Mvars=%x -nale '$x{$F[7]}++}{print "$_\t$x{$_}" for grep {$x{$_}>1} sort { $x{$b}<=>$x{$a} } keys %x'`
		- `sudo ufw deny from ADDRESS comment 'too many failed login attempts'`

5. **Crontab** to broadcast RPi's address and name

	1. `crontab -e`
		
			@reboot    hostname | socat -s - UDP-DATAGRAM:255.255.255.255:12340,broadcast 2>/dev/null
			* * * * *  hostname | socat -s - UDP-DATAGRAM:255.255.255.255:12340,broadcast 2>/dev/null
	
	2. In `/etc/rsyslog.conf`, apply this patch:
		
			-*.*;auth,authpriv.none          -/var/log/syslog
			+*.*;cron,auth,authpriv.none     -/var/log/syslog
	
	3. `sudo systemctl restart rsyslog`
	
	4. Can use `udplisten.py` from this repository to listen for the broadcasts.
	
	5. Alternative: You can use `postip.pl` from this repository in the `crontab` to send an
	   HTTP request instead of a UDP packet; remember to use the full pathname to the script
	   and adjust the variables at the top of the script as necessary.
	   TODO: The HMAC-SHA256 signature provided by the script can be used by the server to verify the authenticity.

6. **Mail**: Configure Postfix either as "Local only" or "Internet Site" as appropriate in the following steps:
	
		sudo apt-get install alpine postfix bsd-mailx
		echo "root: pi" | sudo tee -a /etc/aliases && echo "===>" && cat /etc/aliases
		sudo vi /etc/postfix/main.cf
		#=> correct "myhostname" if necessary
		#=> may need to remove duplicates in "mydestination"
		#=> if it doesn't exist, add the line "smtp_tls_security_level = may"
		#=> if this option or the option "smtp_tls_CApath" doesn't exist,
		#   add the line "smtp_tls_CAfile = /etc/ssl/certs/ca-certificates.crt"
		sudo dpkg-reconfigure postfix  # and configure as appropriate
		sudo systemctl restart postfix
		echo "This is a mailx test" | mailx -s "mailx test" root
		alpine
		# Configure "User Domain" and anything else as needed

7. **Unattended Upgrades**

	1. `sudo apt-get install unattended-upgrades`
	
	2. `sudo vi /etc/apt/apt.conf.d/50unattended-upgrades`
		- Set `Unattended-Upgrade::Mail` to `pi@localhost`
	
	3. `sudo vi /etc/apt/apt.conf.d/20auto-upgrades`
		
			APT::Periodic::Update-Package-Lists "1";
			APT::Periodic::Unattended-Upgrade "1";
			APT::Periodic::Download-Upgradeable-Packages "1";
			//APT::Periodic::Verbose "1";
			APT::Periodic::AutocleanInterval "7";
	
	4. Test with `sudo unattended-upgrade -d -v --dry-run`
	
	5. Enable with `sudo dpkg-reconfigure --priority=low unattended-upgrades`

8. **Overlay Filesystem** (*optional*, continued from above!)

	1. Create an `/etc/fstab` entry for the `data` partition:
	
			sudo mkdir -v /data
			echo "PARTUUID=$(lsblk -no PARTUUID /dev/disk/by-label/data)  /data  ext4  defaults,noatime  0  2" | sudo tee -a /etc/fstab
			cat /etc/fstab  # double-check to make sure it looks right
			sudo reboot
	
		*Note:* Depending on the data being written, you may also want to add
		`sync` to the mount options for a little bit more protection against
		sudden power offs (make sure you understand the implications of this
		depending on the type of flash memory you're using).
	
	2. `sudo mkdir -v /data/pi`, `sudo chown pi:pi /data/pi`, and `ln -svnf /data/pi /home/pi/data`
	
	3. If you set up `postfix` and `alpine` above, do this:
		
			ls -l /var/spool/mail  # => should normally be a symlink to ../mail !
			sudo systemctl stop postfix
			sudo mkdir -v /data/spool
			sudo mv -v /var/mail /data/spool/mail
			sudo mv -v /var/spool/postfix /data/spool/postfix
			sudo ln -svf /data/spool/mail /var/
			sudo ln -svf /data/spool/mail /var/spool/
			sudo ln -svf /data/spool/postfix /var/spool/
			mv -v ~/mail /data/pi
			ln -svf /data/pi/mail ~
			sudo systemctl start postfix
	
	4. Currently, `overlayroot` defaults to `recurse=1`, meaning that the `/data` partition
	   also gets overlayed, and `raspi-config` does not support corresponding options
	   (see also <https://github.com/RPi-Distro/raspi-config/pull/225>).
	   For now, as a workaround, apply `raspi-config_overlayroot.patch` from this repository.
	   For example, over a remote connection, `sudo patch -d/ -r- -p0` and then paste the patch into the terminal (Ctrl-D after).
	   Note the patch needs to be reapplied when `raspi-config` gets updated!
	
	5. Later, after completing the installation, you can enable the "Overlay File System"
	   in the "Performance Options" of `raspi-config`. Remember that if making changes
	   that need to persist across reboots, you'll need to disable and re-enable this
	   option, rebooting each time.
	   
	   Note this can also be done on the commandline:
	   To turn on the overlay filesystem, `sudo raspi-config nonint do_overlayfs 0`,
	   to turn it off, `sudo raspi-config nonint do_overlayfs 1`
	   (yes, on=0 and off=1 is correct).
	
	6. To integrate information on whether the overlay filesystem is enabled or not into
	   your prompt, see `overlaycheck.sh` in this repository.

9. **Miscellaneous**

	- For network time, `sudo apt-get install --no-install-recommends ntp` and edit `/etc/ntpsec/ntp.conf` as appropriate.
	  *However,* newer OSes have `systemd-timesyncd` preinstalled!
	
	- If the Raspberry Pi doesn't have direct internet access after installation:
		
		1. In `/etc/proxychains4.conf`, replace the default `socks4` line in the `[ProxyList]` section
		   with `socks5	127.0.0.1	12333`
		
		2. When you connect to the RPi via SSH, use `ssh -R12333 pi@...`
		
		3. Then, with commands that support it, you can use e.g. `ALL_PROXY=socks5h://localhost:12333 curl http://example.com`,
		   for other commands use e.g. `sudo proxychains4 -q apt-get update` or `proxychains4 -q cpanm ...`
		
		4. If you have a Git repository on the RPi that you would like to push to, you can push to a non-bare
		   repository by doing this in the target repository: `git config receive.denyCurrentBranch updateInstead`
	
	- Sometimes, on some Wi-Fi nets, Wi-Fi will stop working unless I reboot the Pi once in a while.
	  This can be done via e.g. `sudo -i crontab -e`: `0 8 * * * /sbin/shutdown --reboot +5 2>/dev/null`
	
	- Serial port: `sudo adduser pi dialout`, `stty -F /dev/ttyS0 19200 cs8 -parenb raw -crtscts -echo`, `cat /dev/ttyS0`
	  (Also: `minicom -D/dev/ttyS0` and `screen /dev/ttyS0 19200`)
	
	- Making a backup of an SD card from another system (where `/dev/sdb` is the SD card):
	  `sudo dd if=/dev/sdb | gzip -9 >backup.img.gz`


Author, Copyright, and License
------------------------------

Copyright (c) 2016-2023 Hauke Dämpfling <haukex@zero-g.net>
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
