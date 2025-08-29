# AI Chief of Staff Dashboard - Agent F Frontend

Dynamic real-time dashboard for the AI Chief of Staff system, built with vanilla JavaScript and WebSocket connectivity.

## Overview

This dashboard provides a live, interactive interface for executive intelligence, featuring:

- **Real-time Updates**: WebSocket connection with auto-reconnection
- **Command Interface**: Interactive command system with history and autocomplete
- **Paper-Dense Design**: High information density optimized for executive use
- **Performance Optimized**: <100ms DOM updates, <50ms WebSocket handling
- **Accessibility**: Full screen reader and keyboard navigation support

## Architecture

### Core Components

```
dashboard/
├── index.html              # Main dashboard HTML
├── css/
│   ├── paper-dense.css     # Core styling from mockup
│   └── enhancements.css    # Interactive features styling
├── js/
│   ├── websocket.js        # WebSocket connection management
│   ├── app.js              # Main application logic
│   └── commands.js         # Command input system
└── assets/
    └── favicon.svg         # Dashboard icon
```

### Integration Points

- **WebSocket**: `ws://localhost:8000/ws` (Agent E backend)
- **API**: `http://localhost:8000/api/*` (RESTful commands)
- **State Format**: Compatible with Agent E state manager

## Quick Start

### Prerequisites

1. Agent E backend running on `localhost:8000`
2. Modern web browser (Chrome 90+, Firefox 88+, Safari 14+)

### Running the Dashboard

1. **Start Backend** (Agent E must be running):
   ```bash
   cd /Users/david.campos/VibeCode/AICoS-Lab
   python -m uvicorn backend.server:app --host 0.0.0.0 --port 8000
   ```

2. **Open Dashboard**:
   ```bash
   # Simple HTTP server for local development
   cd dashboard
   python -m http.server 3000
   
   # Then open: http://localhost:3000
   ```

3. **Alternative - Direct File Access**:
   ```bash
   open /Users/david.campos/VibeCode/AICoS-Lab/dashboard/index.html
   ```

### Verification Steps

1. **Connection Status**: Green "Connected" indicator in top-right
2. **System Status**: Shows current backend status in sidebar
3. **Command Input**: Try `refresh`, `status`, or `approve P1`
4. **Real-time Updates**: Progress bars and counters update automatically

## Testing

### Browser Tests

Open the test suite in your browser:
```bash
open /Users/david.campos/VibeCode/AICoS-Lab/tests/dashboard/test_frontend.html
```

**Test Categories:**
- WebSocket Integration (connection, messages, reconnection)
- Command Input System (history, autocomplete, execution)
- Visual State Updates (DOM performance, styling preservation)
- Performance Validation (timing requirements)
- Cross-browser Compatibility

### Manual Testing Checklist

#### ✅ Core Functionality
- [ ] Dashboard loads within 3 seconds
- [ ] WebSocket connects automatically
- [ ] System status updates in real-time
- [ ] Command input accepts text and executes on Enter
- [ ] Command history navigates with arrow keys
- [ ] Auto-completion works with Tab key
- [ ] Connection status indicator shows current state

#### ✅ Visual Fidelity
- [ ] Layout matches cos-paper-dense.html mockup exactly
- [ ] Typography is monospace (SF Mono/Monaco/Cascadia)
- [ ] Color scheme preserved (#005f87, #d75f00, #c62828, etc.)
- [ ] Responsive sidebar maintains proportions
- [ ] Progress bars animate smoothly
- [ ] Status indicators use correct colors

#### ✅ Performance Requirements
- [ ] Page load < 3 seconds
- [ ] DOM updates complete < 100ms
- [ ] WebSocket message handling < 50ms
- [ ] No memory leaks during extended use
- [ ] Smooth reconnection after network drops

#### ✅ Accessibility
- [ ] Screen reader announces status changes
- [ ] Keyboard navigation works throughout
- [ ] Focus indicators visible
- [ ] ARIA labels provide context
- [ ] High contrast mode support

### Backend Integration Tests

```bash
# Test WebSocket connection
curl -v -N -H "Connection: Upgrade" -H "Upgrade: websocket" -H "Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==" -H "Sec-WebSocket-Version: 13" http://localhost:8000/ws

# Test command API
curl -X POST http://localhost:8000/api/command -H "Content-Type: application/json" -d '{"command": "status"}'

# Test system status
curl http://localhost:8000/api/system/status

# Test collection trigger
curl http://localhost:8000/api/trigger_collection
```

## Command Reference

### System Commands
- `refresh` - Refresh dashboard and reconnect WebSocket
- `status` - Show detailed system status
- `status details` - Show extended system information

### Collection Commands  
- `quick` - Trigger quick data collection
- `full` - Trigger full data collection

### Approval Commands
- `approve P1` - Approve priority item P1
- `approve P2` - Approve priority item P2
- (Supports P1-P10, C1-C10, M1-M10)

### Brief Commands
- `brief daily` - Generate daily intelligence brief
- `brief weekly` - Generate weekly summary
- `brief C1` - Brief on specific calendar item

### Search Commands
- `search keyword` - Search for keyword across data
- `search person:name` - Search by person
- `search date:today` - Search by date

## Keyboard Shortcuts

- `Ctrl+K` / `Cmd+K` - Focus command input
- `Ctrl+R` / `Cmd+R` - Refresh dashboard  
- `Escape` - Focus command input from anywhere
- `↑` / `↓` - Navigate command history
- `Tab` - Auto-complete commands
- `Enter` - Execute command

## Troubleshooting

### Connection Issues

**WebSocket won't connect:**
1. Verify Agent E backend is running on port 8000
2. Check browser console for connection errors
3. Ensure firewall allows WebSocket connections
4. Try refreshing the page

**Commands failing:**
1. Check API endpoint availability: `curl http://localhost:8000/api/health`
2. Verify command syntax matches supported commands
3. Check browser network tab for 4xx/5xx responses

### Performance Issues

**Slow page load:**
1. Check browser console for JavaScript errors
2. Verify CSS and JS files load correctly
3. Clear browser cache and reload

**Slow DOM updates:**
1. Open browser DevTools Performance tab
2. Record interaction to identify bottlenecks
3. Check `getDashboardApp().getPerformanceStats()` in console

### Browser Compatibility

**Minimum Requirements:**
- Chrome 90+ (2021)
- Firefox 88+ (2021)  
- Safari 14+ (2020)
- Edge 90+ (2021)

**Not Supported:**
- Internet Explorer (any version)
- Chrome < 90
- Safari < 14

## Development

### Code Structure

**WebSocket Manager** (`js/websocket.js`):
- Connection management with exponential backoff
- Event-driven message handling
- Performance monitoring and statistics
- Auto-reconnection with status indicators

**Dashboard App** (`js/app.js`):
- State management and DOM updates
- Section-based rendering system  
- Performance-optimized batch updates
- Real-time data synchronization

**Command Manager** (`js/commands.js`):
- Command parsing and execution
- History and auto-completion
- API integration with error handling
- Local storage persistence

### Performance Monitoring

Access performance metrics in browser console:
```javascript
// Get WebSocket statistics
getWebSocketManager().getStats()

// Get DOM update performance
getDashboardApp().getPerformanceStats()

// Get command execution stats
getCommandManager().getStats()
```

### Adding New Commands

1. **Update suggestions** in `commands.js`:
   ```javascript
   this.suggestions = [
       'your-new-command',
       // ... existing commands
   ];
   ```

2. **Backend support**: Ensure command is supported in `backend/api_routes.py`

3. **Documentation**: Update this README with command description

### Styling Modifications

- **Core styles**: Modify `css/paper-dense.css` (preserve original aesthetics)
- **New features**: Add to `css/enhancements.css`
- **Critical CSS**: Update `<style>` block in `index.html` for above-fold content

## API Contract

### WebSocket Messages

**Incoming State Updates:**
```json
{
  "system": {
    "status": "COLLECTING|PROCESSING|IDLE|ERROR",
    "progress": 0-100,
    "last_sync": "2025-08-28T14:30:00Z"
  },
  "calendar": [
    {
      "id": "C1",
      "time": "9:00",
      "title": "Product Sync",
      "alert": false,
      "new": false
    }
  ],
  "priorities": [
    {
      "id": "P1", 
      "text": "Q1 Planning Doc",
      "status": "done|partial|pending",
      "alert": false,
      "new": false
    }
  ],
  "commitments": {
    "owe": [...],
    "owed": [...]
  },
  "active_brief": {
    "type": "daily",
    "html_content": "<div>...",
    "generated_at": "2025-08-28T14:30:00Z"
  }
}
```

**Outgoing Client Messages:**
```json
{
  "type": "ping|ack|client_status",
  "data": "optional_data"
}
```

### REST API Endpoints

**POST /api/command**
```json
{
  "command": "approve P1"
}
```

**Response:**
```json
{
  "action": "approve",
  "target": "P1",
  "success": true
}
```

**GET /api/system/status**
```json
{
  "status": "IDLE",
  "progress": 0,
  "last_sync": "2025-08-28T14:30:00Z"
}
```

## Deployment

### Production Build

1. **Minify assets**:
   ```bash
   # CSS minification
   npx clean-css-cli css/paper-dense.css css/enhancements.css -o dist/styles.min.css
   
   # JS minification  
   npx terser js/*.js -o dist/app.min.js --source-map
   ```

2. **Update HTML** to reference minified assets

3. **Configure web server**:
   - Serve static files with caching headers
   - Enable gzip compression
   - Configure WebSocket proxy to backend
   - Set up SSL termination

### Docker Deployment

```dockerfile
FROM nginx:alpine
COPY dashboard/ /usr/share/nginx/html/
COPY nginx.conf /etc/nginx/nginx.conf
EXPOSE 80
```

### Environment Configuration

Update backend URLs for different environments:
```javascript
const API_BASE_URL = process.env.NODE_ENV === 'production' 
  ? 'https://api.your-domain.com'
  : 'http://localhost:8000';
  
const WS_URL = process.env.NODE_ENV === 'production'
  ? 'wss://api.your-domain.com/ws' 
  : 'ws://localhost:8000/ws';
```

## Security Considerations

- **CSP Headers**: Implement Content Security Policy
- **WebSocket Origin**: Validate WebSocket connection origins
- **API Authentication**: Add authentication for production use
- **Input Sanitization**: Commands are validated server-side
- **XSS Protection**: All user input is escaped

## Support

For issues or questions:

1. **Check browser console** for JavaScript errors
2. **Review test output** in `/tests/dashboard/test_frontend.html`
3. **Verify backend connectivity** with curl commands above
4. **Check performance metrics** with developer console commands

**Agent F Team Lead**: Frontend development questions
**Agent E Team Lead**: Backend integration issues
**Agent G/H Teams**: Full system integration

---

**Status**: ✅ Complete - Ready for Agent E backend integration
**Version**: 1.0.0  
**Last Updated**: 2025-08-28
**Agent**: F (Frontend Development Team)