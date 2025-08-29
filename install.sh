#!/usr/bin/env bash
# AI CoS — Paper-Dense Dashboard - Single Process Install
# 
# This script creates a self-managing paper-dense dashboard system that:
# - Uses Streamlit as a pure HTML container (preserves exact aesthetic)
# - Runs continuously on port 8501 (auto-restart if crashes)
# - Reads JSON data files directly (no API complexity)
# - Starts automatically on login
# - Keeps everything local and private
#
# Usage: ./install.sh

set -euo pipefail

# Configuration
APP_NAME="AI CoS — Paper Dense"
ROOT="$(cd "$(dirname "$0")" && pwd)"
PYTHON_BIN="$ROOT/venv/bin/python"
PIP_BIN="$ROOT/venv/bin/pip"
LAUNCH_DIR="$HOME/Library/LaunchAgents"
LOG_DIR="$ROOT/logs"
DATA_DIR="$ROOT/data"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
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

# Check if we're on macOS
check_macos() {
    if [[ "$OSTYPE" != "darwin"* ]]; then
        log_error "This script is designed for macOS only (uses launchd)"
        exit 1
    fi
}

# Create virtual environment and install dependencies
setup_python_environment() {
    log_info "Setting up Python environment..."
    
    # Create virtual environment if it doesn't exist
    if [ ! -d "$ROOT/venv" ]; then
        log_info "Creating virtual environment..."
        python3 -m venv "$ROOT/venv"
    fi
    
    # Upgrade pip and install dependencies
    log_info "Installing Python packages..."
    "$PIP_BIN" install --upgrade pip --quiet
    
    # Install Streamlit only (no other dependencies needed)
    "$PIP_BIN" install --quiet streamlit==1.28.1
    
    log_success "Python environment ready"
}

# Create necessary directories
create_directories() {
    log_info "Creating directories..."
    
    mkdir -p "$DATA_DIR" "$LOG_DIR" "$LAUNCH_DIR"
    
    # Create .gitignore for data directory
    if [ ! -f "$DATA_DIR/.gitignore" ]; then
        cat > "$DATA_DIR/.gitignore" <<'EOF'
# Ignore all JSON data files but keep directory structure
*.json
!.gitignore
EOF
    fi
    
    log_success "Directories created"
}

# Configure Streamlit
configure_streamlit() {
    log_info "Configuring Streamlit..."
    
    mkdir -p "$HOME/.streamlit"
    
    cat > "$HOME/.streamlit/config.toml" <<'EOF'
[server]
address = "127.0.0.1"
headless = true
port = 8501
runOnSave = true
enableCORS = false
enableXsrfProtection = false

[browser]
serverAddress = "localhost"
serverPort = 8501

[theme]
primaryColor = "#005f87"
backgroundColor = "#fafaf8"
secondaryBackgroundColor = "#ffffff"
textColor = "#2c2c2c"

[logger]
level = "warning"
EOF
    
    log_success "Streamlit configured"
}

# Create launchd service for paper-dense dashboard
create_dashboard_service() {
    log_info "Creating paper-dense dashboard service..."
    
    local plist_file="$LAUNCH_DIR/com.aicos.paperdense.dashboard.plist"
    
    cat > "$plist_file" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
 "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.aicos.paperdense.dashboard</string>
    
    <key>ProgramArguments</key>
    <array>
        <string>$PYTHON_BIN</string>
        <string>-m</string>
        <string>streamlit</string>
        <string>run</string>
        <string>$ROOT/app.py</string>
    </array>
    
    <key>WorkingDirectory</key>
    <string>$ROOT</string>
    
    <key>EnvironmentVariables</key>
    <dict>
        <key>PYTHONPATH</key>
        <string>$ROOT</string>
        <key>PATH</key>
        <string>$ROOT/venv/bin:/usr/local/bin:/usr/bin:/bin</string>
    </dict>
    
    <key>RunAtLoad</key>
    <true/>
    
    <key>KeepAlive</key>
    <true/>
    
    <key>StandardOutPath</key>
    <string>$LOG_DIR/streamlit.out.log</string>
    
    <key>StandardErrorPath</key>
    <string>$LOG_DIR/streamlit.err.log</string>
    
    <key>ProcessType</key>
    <string>Interactive</string>
</dict>
</plist>
EOF
    
    log_success "Dashboard service created"
}

# Start the service
start_service() {
    log_info "Starting dashboard service..."
    
    # Unload existing service (ignore errors)
    launchctl unload "$LAUNCH_DIR/com.aicos.paperdense.dashboard.plist" 2>/dev/null || true
    
    # Load new service
    launchctl load "$LAUNCH_DIR/com.aicos.paperdense.dashboard.plist"
    
    log_success "Service started"
}

# Verify that required files exist
verify_files() {
    log_info "Verifying required files..."
    
    if [ ! -f "$ROOT/app.py" ]; then
        log_error "app.py not found - this is required for the dashboard"
        exit 1
    fi
    
    if [ ! -f "$ROOT/cos-paper-dense.html" ]; then
        log_error "cos-paper-dense.html not found - this is required for the aesthetic"
        exit 1
    fi
    
    # Check if data loader exists (optional but recommended)
    if [ -f "$ROOT/tools/load_dashboard_data.py" ]; then
        log_info "Data loader found - you can populate data with: python tools/load_dashboard_data.py"
    else
        log_warning "Data loader not found - you'll need to populate JSON files manually"
    fi
    
    log_success "Required files verified"
}

# Generate initial data if loader exists
generate_initial_data() {
    if [ -f "$ROOT/tools/load_dashboard_data.py" ]; then
        log_info "Generating initial dashboard data..."
        
        if "$PYTHON_BIN" "$ROOT/tools/load_dashboard_data.py" --output-dir "$DATA_DIR" 2>/dev/null; then
            log_success "Initial data generated"
        else
            log_warning "Could not generate initial data (dashboard will show empty until data is available)"
        fi
    else
        log_warning "No data loader - dashboard will be empty until JSON files are populated"
    fi
}

# Verify installation
verify_installation() {
    log_info "Verifying installation..."
    
    # Check if service is loaded
    if launchctl list | grep -q "com.aicos.paperdense.dashboard"; then
        log_success "Dashboard service is loaded"
    else
        log_error "Dashboard service failed to load"
        return 1
    fi
    
    # Wait a moment for service to start
    log_info "Waiting for dashboard to start..."
    sleep 8
    
    # Check if dashboard is accessible
    if curl -s -f http://127.0.0.1:8501/_stcore/health > /dev/null 2>&1; then
        log_success "Dashboard is accessible at http://127.0.0.1:8501"
    else
        log_warning "Dashboard may still be starting up. Check logs if it doesn't appear soon."
        log_info "View logs with: tail -f $LOG_DIR/streamlit.out.log"
    fi
    
    # Check if data files exist
    local data_files=("calendar_events.json" "priorities.json" "commitments.json")
    local files_exist=0
    
    for file in "${data_files[@]}"; do
        if [ -f "$DATA_DIR/$file" ]; then
            files_exist=$((files_exist + 1))
        fi
    done
    
    if [ $files_exist -gt 0 ]; then
        log_success "$files_exist/3 data files present"
    else
        log_warning "No data files found - dashboard will show empty sections"
    fi
}

# Print completion message
print_completion_message() {
    echo ""
    echo "============================================================"
    echo -e "${GREEN}🎉 $APP_NAME INSTALLED SUCCESSFULLY!${NC}"
    echo "============================================================"
    echo -e "${BLUE}📍 Dashboard URL:${NC} http://127.0.0.1:8501"
    echo -e "${BLUE}📁 Project Directory:${NC} $ROOT"
    echo -e "${BLUE}📊 Data Directory:${NC} $DATA_DIR"
    echo -e "${BLUE}📝 Logs Directory:${NC} $LOG_DIR"
    echo ""
    echo -e "${YELLOW}🎨 Visual Design:${NC}"
    echo "   • Paper-dense terminal aesthetic preserved exactly"
    echo "   • Monospace fonts with 2px spacing"
    echo "   • C1-C7 calendar codes, P1-P7 priority codes, M1-M8 commitment codes"
    echo "   • Command input with keyboard shortcuts"
    echo ""
    echo -e "${YELLOW}🔄 How It Works:${NC}"
    echo "   • Streamlit serves as HTML container only"
    echo "   • JavaScript reads JSON files and populates interface"
    echo "   • Auto-refreshes every 60 seconds"
    echo "   • Auto-restarts on crash, auto-starts on login"
    echo ""
    echo -e "${YELLOW}📊 Data Management:${NC}"
    if [ -f "$ROOT/tools/load_dashboard_data.py" ]; then
        echo "   • Refresh data: python tools/load_dashboard_data.py"
    fi
    echo "   • Data files: $DATA_DIR/*.json"
    echo "   • Manual data: Edit JSON files directly"
    echo ""
    echo -e "${YELLOW}🛠️  Management Commands:${NC}"
    echo "   • Check status: ./status.sh"
    echo "   • Stop service: ./stop.sh"  
    echo "   • Start service: ./start.sh"
    echo "   • View logs: tail -f logs/streamlit.out.log"
    echo ""
    echo -e "${GREEN}🚀 Visit http://127.0.0.1:8501 to see your paper-dense dashboard!${NC}"
    echo "============================================================"
}

# Main installation flow
main() {
    echo ""
    echo "============================================================"
    echo -e "${BLUE}🚀 Installing $APP_NAME${NC}"
    echo "============================================================"
    
    check_macos
    verify_files
    setup_python_environment
    create_directories
    configure_streamlit
    create_dashboard_service
    generate_initial_data
    start_service
    verify_installation
    print_completion_message
}

# Run main function
main "$@"