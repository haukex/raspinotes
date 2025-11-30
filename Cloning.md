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

- If you have the overlay filesystem enabled, I suggest disabling it before pulling the images,
  just to make later configuration easier.

- Remove `cloud-init` as per my [BaseInstall notes](./BaseInstall.md).

In the following, replace `/dev/sdX` with the source SD card's device name.

- Partition table:
  - Dump the table via: `sudo sfdisk -d /dev/sdX | tee part_table`
  - To prevent conflicts, remove unique identifiers via:
    `perl -wM5.014 -i.orig -ne 's/,\h*uuid=[-0-9a-fA-F]*\b//g;/^label-id/||print' part_table`

- RPi FAT `/boot` Partition:
  - `sudo partclone.fat32 --clone --source /dev/sdX1 --output sdX1.pc.img`
  - **Note** this is a "special" format used by partclone, not an actual image!

- ext4 Partition(s):
  - The `e2image` tool can create sparse images. **Note** that with `ls`, the file sizes will look
    like they have their original size, but `du` shows they are actually taking up much less space.
    **Warning:** If you use tools that can't handle sparse files, they may balloon to the listed
    size, so be careful!
  - `sudo e2image -pra /dev/sdX2 sdX2.sparse.img`
  - `sudo e2image -pra /dev/sdX3 sdX3.sparse.img` (optional if you have a `data` partition)

- Adjust permissions on image files:
  - `sudo chown -c $USER:$USER *.img`
  - `chmod -c 440 *.img part_table`

- If you want to back up these files into one:
  `tar --create --file rpi-images.sparse.tgz -I 'gzip -9' --verbose --sparse -- part_table *.img`


Writing Images to an SD Card
----------------------------

**⚠️ DANGER ZONE:** Make sure you're writing to the correct device!

Remove the original source SD card from your system, at least until new UUIDs are generated (below).
In the following, replace `/dev/sdY` with the clone SD card's device name.

- Partition table:
  - `sudo sfdisk /dev/sdY < part_table`

- FAT Partition:
  - `sudo partclone.fat32 --restore --source sdX1.pc.img --output /dev/sdY1`

- ext4 Partitions:
  - `sudo e2image -pra sdX2.sparse.img /dev/sdY2`
  - `sudo e2image -pra sdX3.sparse.img /dev/sdY3` (optional)

- Just to play it safe, check the filesystems:
  - `sudo fsck.fat -v /dev/sdY1`
  - `sudo fsck.ext4 -f /dev/sdY2`
  - `sudo fsck.ext4 -f /dev/sdY3`


Post-Clone Updates
------------------

**⚠️ DANGER ZONE:** Make sure you're writing to the correct device and directories!

In the following, replace `/dev/sdY` with the clone SD card's device name.

- Check the partition IDs via `sudo lsblk -o+PARTUUID,UUID,LABEL /dev/sdY`,
  then generate new UUIDs as follows:
  - `sudo fatlabel -ir /dev/sdY1`
  - `sudo tune2fs -U random /dev/sdY2`
  - `sudo tune2fs -U random /dev/sdY3`
- Note: In case you need to adjust partition labels later, see `e2label` and `fatlabel`.
  The usual partition labels are `bootfs` and `rootfs` (and the optional `data`).

Mount the clone's FAT `bootfs` and ext4 `rootfs`. In the following, I will assume that
they are mounted at `/media/$USER/bootfs` and `/media/$USER/rootfs`.

- `sudo lsblk -o+PARTUUID /dev/sdY`, then:
  - `sudo vi /media/$USER/bootfs/cmdline.txt` and edit `root=PARTUUID=...` to match the new `PARTUUID`
  - `sudo vi /media/$USER/rootfs/etc/fstab` and edit all of the `PARTUUID=` fields to match the new `PARTUUID`s

- `sudo ./clone-delete.sh /media/$USER/rootfs` to delete various files that will be re-generated

- machine-id and Hostname
  - `sudo systemd-firstboot --root=/media/$USER/rootfs --hostname=HOSTNAME --setup-machine-id --force`
  - `sudo vi /media/$USER/rootfs/etc/hosts` and replace all instances of the old hostname there too

- If you have this file, `sudo vi /media/$USER/rootfs/etc/machine-info` and edit `PRETTY_HOSTNAME` etc.

- Do any other customization steps that you might need and can do before first boot here.


Post-Boot Updates on Clone
--------------------------

- Regenerate SSH Host keys:
  - `sudo rm -v /etc/ssh/ssh_host_*` (Note: The ssh service doesn't re-generate these files on boot, and will
    refuse to start if they're missing, which is why we don't do this until after the first boot of the clone.)
  - `sudo dpkg-reconfigure openssh-server && sudo systemctl restart ssh`

- SSL Certs - only if you had/have the package `ssl-cert` installed:
  - `sudo make-ssl-cert generate-default-snakeoil --force-overwrite`

- Do any other customization steps needed for your system here.

- If you had the overlay filesystem enabled, reenable it now
  (`sudo raspi-config nonint do_overlayfs 0`).


More Information
----------------

- <https://gparted.org/livecd.php>
- <https://wiki.archlinux.org/title/Disk_cloning#Versatile_cloning_solutions>


<!-- spell: ignore PARTUUID blkid cmdline dhcpcd dpkg firstboot sfdisk zcat snakeoil fatlabel bootfs
spell: ignore rootfs Imager autoremove partclone nonint overlayfs raspi -->

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
