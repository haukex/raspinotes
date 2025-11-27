#!/bin/bash
set -euo pipefail

if [[ "$(id -u)" -ne 0 ]]; then
    echo "You need to be root."
    exit 1
fi

usage() { echo "Usage: $0 ROOT_FS_PATH" 1>&2; exit 1; }
[[ $# -eq 1 ]] || usage
root_fs_path="$(realpath -s "$1")"

target="$(findmnt --all --first --noheadings --list --output TARGET --notruncate --target "$root_fs_path")"
if [[ $target =~ ^/[^/]+ ]]; then
    source="$(findmnt --all --first --noheadings --list --output SOURCE --notruncate --target "$root_fs_path")"
    if [ ! -d "$root_fs_path/var" ]; then
        echo "Not a directory: $root_fs_path/var"
        exit 1
    fi
else
    echo "Refusing to operate on target: $target"
    exit 1
fi

# note the wildcard expansion in /var/lib/bluetooth needs root permissions
to_delete_files=(
    "$root_fs_path"/var/lib/bluetooth/[0-9A-Fa-f]*
    "$root_fs_path"/var/log/*
    "$root_fs_path"/var/cache/*
    "$root_fs_path"/var/lib/systemd/random-seed
)

echo -e "\nv WARNING v WARNING v WARNING v WARNING v WARNING v WARNING v WARNING v\n"
echo "You are about to delete the following files"
echo -n "from $source"
echo -e " WITH ROOT PERMISSIONS.\n\nTo be deleted:"
for elem in "${to_delete_files[@]}"; do echo "$elem"; done
echo -e "\n^ WARNING ^ WARNING ^ WARNING ^ WARNING ^ WARNING ^ WARNING ^ WARNING ^\n"

read -n 1 -r -p "ARE YOU SURE? [yN] " REPLY
echo -e "\n"
if [[ $REPLY =~ ^[Yy]$ ]]
then
    for elem in "${to_delete_files[@]}"; do rm -rvf "$elem"; done
fi

# spell: ignore noheadings notruncate
