#!/bin/sh
# Read-only readiness check; never creates certificates or changes trust settings.
set -eu
cd "$(dirname "$0")/.."
printf 'Configured identity: %s\n' "${SECOND_BRAIN_SIGNING_IDENTITY:-not configured (ad-hoc builds)}"
security find-identity -v -p codesigning
if [ -z "${SECOND_BRAIN_SIGNING_IDENTITY:-}" ]; then
  printf '\nStable signing is not configured. Supply a valid local identity before rebuilding.\n'
  printf 'See docs/signing.md. No certificates or permissions were changed.\n'
  exit 2
fi
