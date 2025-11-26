Cloning Raspberry Pi SD Cards
=============================

**⚠️ WARNING ‼️**
-----------------

Several commands shown here can lead to **data loss** if used incorrectly, for example if you mix
up source/destination arguments. Always make backups and be sure you know what you're doing!


Making Images from an SD Card
-----------------------------

It's of course possible to simply pull an image of the entire SD card and write it back using `dd`
(there is also an "SD Card Copier" built into Raspberry Pi OS), however, this also copies tons of
NUL bytes, uses a lot of disk space, and can take a while. So instead, in this document, I'm
focusing on how to do these things more efficiently, copying only those parts of the partitions
holding the data.

- Partition table:
  - Dump the table via: `sudo sfdisk -d /dev/sdX | tee part_table`
  - To prevent conflicts, remove unique identifiers via:
    `perl -wM5.014 -i -ne 's/,\h*uuid=[-0-9a-fA-F]*\b//g;/^label-id/||print' part_table`

- RPi FAT `/boot` Partition:
  - This partition is usually not very big (~100 of 512MB used), so I won't be doing a sparse copy
    here, just a compressed one.
  - `sudo dd if=/dev/sdX1 status=progress | gzip -9 >sdX1.img.gz`
  - Alternatively, uncompressed, for example if you want to create a compressed backup anyway (as
    shown below): `sudo dd if=/dev/sdX1 of=sdX1.img status=progress` (or just `gunzip` the `.gz`)

- ext4 Partition(s):
  - The `e2image` tool can create sparse images. **Note** that with `ls`, the file sizes will look
    like they have their original size, but `du` shows they are actually taking up much less space.
    **Warning:** If you use tools that can't handle sparse files, they may balloon to the listed
    size, so be careful!
  - `sudo e2image -pra /dev/sdX2 sdX2.img`
  - `sudo e2image -pra /dev/sdX3 sdX3.img` (optional if you have a `data` partition)

- `sudo chown -c $USER:$USER *.img`
- `chmod -c a-w *.img*`

- If you want to back up these files into one:
  - `tar --create --file rpi-images.tar --verbose --sparse -- part_table sdX?.img*`
  - Alternatively, compressed, which can save a lot of space (in one test I ran, 50%):
    `tar --create --file rpi-images.tgz -I 'gzip -9' --verbose --sparse -- part_table sdX?.img`
    (in this case it's more efficient if you didn't compress the FAT backup above)


⚠️ Untested Stuff Follows
--------------------------

This document is a work in progress and I have not tested the following yet.


Writing Images to an SD Card
----------------------------

**⚠️ DANGER ZONE:** Make sure you're writing to the correct device!

- Partition table:
  - `sudo sfdisk /dev/sdX < part_table`
  - TODO: I don't see the "data" label in the sfdisk output, do I need to do that manually?

- FAT Partition:
  - `zcat sdX1.img.gz | sudo dd of=/dev/sdX1 status=progress`

- ext4 Partitions:
  - `sudo e2image -pra sdX2.img /dev/sdX2`
  - `sudo e2image -pra sdX3.img /dev/sdX3` (optional)


Post-Clone Updates
------------------

Mount the system ext4 partition on a Linux system.

- TODO: `sudo lsblk -o+PARTUUID,UUID /dev/sdX` and `sudo tune2fs -U random /dev/sdX1` for `.../etc/fstab` update?
  - **and** adjust `root=PARTUUID=...` in `/boot/firmware/cmdline.txt` !

- machine-id, Hostname
  - TODO: Test `sudo systemd-firstboot --root=/media/... --hostname=... --setup-machine-id --force`
  - TODO: Check that `/etc/hostname` *and* `/etc/hosts` were modified

- SSH Host Keys
  - `sudo rm .../etc/ssh/ssh_host_*`

- Bluetooth pairings
  - `sudo bash -c 'rm -rf .../var/lib/bluetooth/[0-9A-Fa-f]*'`
    (wildcard expansion needs to happen with root permissions)

- `sudo vi .../etc/machine-info` for `PRETTY_HOSTNAME` etc.
- `sudo rm -rf .../var/log/journal/* .../var/log/* .../var/cache/* .../var/lib/systemd/random-seed`

- TODO: Test: if the processor architectures are the same,
  `sudo chroot /media/... /usr/sbin/make-ssl-cert generate-default-snakeoil --force-overwrite`


Post-Boot Updates on Clone
--------------------------

- SSL Certs (if the processor architectures are different)
  - `sudo make-ssl-cert generate-default-snakeoil --force-overwrite`
- SSH Keys should have been regenerated, but if you want to play it safe:
  - `sudo dpkg-reconfigure openssh-server`


More Information
----------------

- <https://gparted.org/livecd.php>
- <https://wiki.archlinux.org/title/Disk_cloning#Versatile_cloning_solutions>


<!-- spell: ignore PARTUUID blkid cmdline dhcpcd dpkg firstboot sfdisk zcat snakeoil -->

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
