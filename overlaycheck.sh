#!/bin/bash
# Check for Overlay Filesystem on Raspberry Pi (and writable data partition)
# The following function can for example be placed in .bashrc, then for example:
# PS1='\u@\h:\w[$(overlaycheck)]\$ '
function overlaycheck {
    mount | egrep -q '^overlay(root)? on / type overlay'; OVERFS=$?
    [[ $(pwd -P)/ = /data/* ]]; DATAFS=$?
    if (( OVERFS==0 )) && (( DATAFS!=0 )); then
        echo -en '\033[01;31mOV\033[00m'
    else
        echo -en '\033[01;32mRW\033[00m'
    fi
}
