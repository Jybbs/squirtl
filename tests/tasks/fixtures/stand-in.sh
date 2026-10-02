#!/bin/sh
call="${0##*/} $*"
echo "$call" >> "$CALLS"
[ -n "$REWRITING" ] && case "$call" in $REWRITING) echo rewritten >> .mise/mise.lock ;; esac
[ -n "$REPORT" ] && [ "$call" = "mise lock" ] && echo "$REPORT" >&2
[ -n "$FAILING" ] && case "$call" in $FAILING) exit 1 ;; esac
exit 0
