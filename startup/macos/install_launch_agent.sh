#!/usr/bin/env bash
# FYERS Auth Utility — macOS LaunchAgent installer helper
#
# Does NOT load the agent automatically without your confirmation.
# Usage:
#   ./startup/macos/install_launch_agent.sh /path/to/project

set -euo pipefail

PROJECT_ROOT="${1:-$(cd "$(dirname "$0")/../.." && pwd)}"
PLIST_TEMPLATE="$(cd "$(dirname "$0")" && pwd)/com.fyers.auth.renewal.plist"
PLIST_DEST="$HOME/Library/LaunchAgents/com.fyers.auth.renewal.plist"

if [[ ! -f "$PLIST_TEMPLATE" ]]; then
  echo "Template not found: $PLIST_TEMPLATE" >&2
  exit 1
fi

mkdir -p "$PROJECT_ROOT/logs"
sed "s|FYERS_PROJECT_ROOT|$PROJECT_ROOT|g" "$PLIST_TEMPLATE" > "$PLIST_DEST"

echo "LaunchAgent plist written to:"
echo "  $PLIST_DEST"
echo ""
echo "To activate:"
echo "  launchctl load $PLIST_DEST"
echo ""
echo "Prerequisites:"
echo "  pip install -r $PROJECT_ROOT/auth_helper/requirements.txt"
echo "  playwright install msedge"
