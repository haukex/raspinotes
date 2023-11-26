#!/bin/bash
# Check for Overlay Filesystem on Raspberry Pi (and writable data partition)
# The following function can for example be placed in .bashrc (or .bash_aliases),
# then used in PS1, for example: PS1='\u@\h:\w$(overlaycheck)\$ '
# also works in combination with __git_ps1, e.g.: PROMPT_COMMAND='__git_ps1 "..." "$(overlaycheck)\\\$ " "[%s]"'
function overlaycheck {
	[[ "$( findmnt --all --first --noheadings --list --output FSTYPE --notruncate --target . )" =~ ^overlay ]] \
		&& echo -en '[\033[01;31mOV\033[00m]'
}
