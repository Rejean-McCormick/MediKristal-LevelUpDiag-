#!/usr/bin/env sh
set -eu
HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
TARGET=${1:-}
CAMPAIGN=${2:-release}
if [ -z "$TARGET" ]; then
  echo "usage: $0 /path/to/MediKristal [baseline|software|delivery|release|deep]" >&2
  exit 64
fi
exec python "$HERE/levelupdiag.py" --target "$TARGET" run "$CAMPAIGN"
