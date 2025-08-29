#!/usr/bin/env bash
# AI CoS — Paper-Dense Dashboard - Check Status
#
# Shows status of service, logs, and data files

set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
LOG_DIR="$ROOT/logs"
DATA_DIR="$ROOT/data"

GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

echo "============================================================"
echo -e "${BLUE}📊 AI Chief of Staff Paper-Dense Dashboard - Status${NC}"
echo "============================================================"
echo ""

# Check service status
echo -e "${BLUE}🔧 Service:${NC}"
if launchctl list | grep -q "com.aicos.paperdense.dashboard"; then
    log_success "Paper-dense dashboard service is running"
else
    log_error "Dashboard service is not running"
fi

echo ""

# Check dashboard accessibility
echo -e "${BLUE}🌐 Dashboard Accessibility:${NC}"
if curl -s -f http://127.0.0.1:8501/_stcore/health > /dev/null 2>&1; then
    log_success "Dashboard is accessible at http://127.0.0.1:8501"
else
    log_error "Dashboard is not accessible"
fi

echo ""

# Check data files
echo -e "${BLUE}📁 Data Files:${NC}"
for file in "calendar_events.json" "priorities.json" "commitments.json"; do
    filepath="$DATA_DIR/$file"
    if [ -f "$filepath" ]; then
        size=$(stat -f%z "$filepath" 2>/dev/null || echo "unknown")
        modified=$(date -r "$filepath" "+%Y-%m-%d %H:%M:%S" 2>/dev/null || echo "unknown")
        log_success "$file ($size bytes, modified: $modified)"
    else
        log_error "$file not found"
    fi
done

echo ""

# Check recent log entries
echo -e "${BLUE}📝 Recent Logs:${NC}"
if [ -f "$LOG_DIR/streamlit.out.log" ]; then
    echo -e "${YELLOW}Streamlit Output (last 3 lines):${NC}"
    tail -n 3 "$LOG_DIR/streamlit.out.log" 2>/dev/null || echo "No recent output"
    echo ""
fi

if [ -f "$LOG_DIR/streamlit.err.log" ]; then
    echo -e "${YELLOW}Streamlit Errors (last 3 lines):${NC}"
    tail -n 3 "$LOG_DIR/streamlit.err.log" 2>/dev/null || echo "No recent errors"
    echo ""
fi

# System info
echo -e "${BLUE}💻 System Info:${NC}"
echo "Project Directory: $ROOT"
echo "Python Version: $(python3 --version 2>/dev/null || echo 'Not found')"
echo "Streamlit Version: $($ROOT/venv/bin/python -c 'import streamlit; print(streamlit.__version__)' 2>/dev/null || echo 'Not installed')"
echo ""

# Usage instructions
echo -e "${BLUE}🛠️  Management:${NC}"
echo "• View dashboard: open http://127.0.0.1:8501"
echo "• Start service: ./start.sh"
echo "• Stop service: ./stop.sh"
echo "• View full logs: tail -f logs/streamlit.out.log"
if [ -f "$ROOT/tools/load_dashboard_data.py" ]; then
    echo "• Refresh data: $ROOT/venv/bin/python tools/load_dashboard_data.py"
fi
echo ""
echo "============================================================"