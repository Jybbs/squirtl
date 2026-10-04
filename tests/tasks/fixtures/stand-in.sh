#!/bin/sh
call="${MISE_LOCKED_SCOPES:+MISE_LOCKED_SCOPES=$MISE_LOCKED_SCOPES }${0##*/} $*"
echo "$call" >> "$CALLS"
[ -n "$REWRITING" ] && case "$call" in $REWRITING) echo rewritten >> .mise/mise.lock ;; esac
if [ -n "$REPORT" ] && [ "$call" = "mise lock" ]; then
  [ "$MISE_QUIET" = 1 ] || [ "$MISE_LOG_LEVEL" = error ] || echo "$REPORT" >&2
fi
[ -n "$FAILING" ] && case "$call" in $FAILING) exit 1 ;; esac
exit 0
