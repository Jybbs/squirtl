#!/bin/sh
call="${0##*/} $*"
echo "$call" >> "$CALLS"
case "$call" in $FAILING) exit 1 ;; esac
[ -z "$ANSWER" ] || echo "$ANSWER"
