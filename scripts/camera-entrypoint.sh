#!/bin/sh
set -eu

if [ "${1:-}" = "serve" ]; then
  if [ ! -s /config/go2rtc.yaml ]; then
    printf '%s\n' "No /config/go2rtc.yaml found. Run the authentication and render steps first." >&2
    exit 78
  fi
  exec go2rtc -config /config/go2rtc.yaml
fi

exec "$@"

