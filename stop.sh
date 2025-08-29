#!/usr/bin/env bash
# AI CoS — Paper-Dense Dashboard - Stop Service
#
# Unloads and stops the paper-dense dashboard service

set -euo pipefail

LAUNCH_DIR="$HOME/Library/LaunchAgents"
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

echo "🛑 Stopping AI Chief of Staff Paper-Dense Dashboard..."

# Unload dashboard service
if launchctl unload "$LAUNCH_DIR/com.aicos.paperdense.dashboard.plist" 2>/dev/null; then
    log_success "Paper-dense dashboard service stopped"
else
    log_info "Dashboard service was not running"
fi

echo ""
log_success "Dashboard service stopped!"
echo "🚀 Start again with: ./start.sh"