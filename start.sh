#!/usr/bin/env bash
# AI CoS — Paper-Dense Dashboard - Start Service
#
# Loads and starts the paper-dense dashboard service

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

echo "🚀 Starting AI Chief of Staff Paper-Dense Dashboard..."

# Load dashboard service
if launchctl load "$LAUNCH_DIR/com.aicos.paperdense.dashboard.plist" 2>/dev/null; then
    log_success "Paper-dense dashboard service started"
else
    if launchctl list | grep -q "com.aicos.paperdense.dashboard"; then
        log_info "Dashboard service already running"
    else
        log_error "Failed to start dashboard service"
        exit 1
    fi
fi

echo ""
log_success "Dashboard service started!"
echo "📍 Dashboard: http://127.0.0.1:8501"
echo "📊 Check status with: ./status.sh"