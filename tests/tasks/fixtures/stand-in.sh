#!/bin/sh
call="${0##*/} $*"
echo "$call" >> "$CALLS"
case "$call" in $FAILING) exit 1 ;; esac
[ -z "$ANSWER" ] || echo "$ANSWER"
[ -z "$ERROR_ANSWER" ] || echo "$ERROR_ANSWER" >&2
