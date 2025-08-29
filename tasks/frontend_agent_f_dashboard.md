# Agent F: Dashboard Frontend Implementation - Phase 4.5 Frontend

**Date Created**: 2025-08-28  
**Owner**: Agent F (Frontend Development Team)  
**Status**: PENDING  
**Estimated Time**: 8 hours (1 day)  
**Dependencies**: Agent E API endpoints (`backend/server.py`)

## Executive Summary

Convert the static cos-paper-dense.html mockup into a dynamic dashboard with WebSocket real-time updates. Focus on preserving the exact paper-dense aesthetic while adding interactivity and live data updates.

**Core Philosophy**: Maintain pixel-perfect fidelity to the mockup design while adding WebSocket connectivity, command input functionality, and real-time DOM updates. No unnecessary UI frameworks - vanilla JavaScript for maximum performance and simplicity.

## Relevant Files for Context

**Read for Context:**
- `/Users/david.campos/VibeCode/AICoS-Lab/cos-paper-dense.html` - Base mockup design
- `backend/server.py` - API endpoints and WebSocket structure (from Agent E)
- `src/search/database.py` - Data structure patterns for state mapping

**Files to Create:**
- `dashboard/index.html` - Enhanced dynamic version of mockup
- `dashboard/js/app.js` - Main application logic
- `dashboard/js/websocket.js` - WebSocket connection handling
- `dashboard/css/paper-dense.css` - Preserved styling from mockup

## Test Acceptance Criteria (Write FIRST)

### File: `tests/dashboard/test_frontend.html`
```html
<!DOCTYPE html>
<html>
<head>
    <title>Dashboard Frontend Tests</title>
    <script src="https://unpkg.com/mocha@9/mocha.js"></script>
    <script src="https://unpkg.com/chai@4/chai.js"></script>
    <link rel="stylesheet" href="https://unpkg.com/mocha@9/mocha.css">
</head>
<body>
    <div id="mocha"></div>
    <script>mocha.setup('bdd');</script>
    
    <script>
        describe('Dashboard WebSocket Integration', () => {
            let mockWebSocket;
            
            beforeEach(() => {
                // Mock WebSocket for testing
                mockWebSocket = {
                    readyState: WebSocket.OPEN,
                    send: sinon.stub(),
                    close: sinon.stub(),
                    addEventListener: sinon.stub()
                };
            });
            
            it('connects to WebSocket on page load', () => {
                // Mock successful connection
                const connectionSpy = sinon.spy(window, 'connectWebSocket');
                
                // Trigger page load
                window.onload();
                
                // Verify connection attempt
                expect(connectionSpy.calledOnce).to.be.true;
            });
            
            it('receives and processes initial state', () => {
                const mockState = {
                    system: { status: 'IDLE', progress: 0 },
                    calendar: [
                        { id: 'C1', time: '9:00', title: 'Product Sync' }
                    ],
                    priorities: [
                        { id: 'P1', text: 'Q1 Planning Doc', status: 'done' }
                    ]
                };
                
                // Simulate WebSocket message
                handleWebSocketMessage({ data: JSON.stringify(mockState) });
                
                // Verify DOM updates
                expect(document.querySelector('[data-system-status]').textContent).to.equal('IDLE');
                expect(document.querySelector('[data-calendar-item="C1"]')).to.exist;
                expect(document.querySelector('[data-priority-item="P1"]')).to.exist;
            });
            
            it('updates DOM when state changes', () => {
                const stateUpdate = {
                    system: { status: 'COLLECTING', progress: 45 }
                };
                
                handleWebSocketMessage({ data: JSON.stringify(stateUpdate) });
                
                // Verify system status updated
                expect(document.querySelector('[data-system-status]').textContent).to.equal('COLLECTING');
                
                // Verify progress bar updated
                const progressBar = document.querySelector('.progress-bar');
                expect(progressBar.style.width).to.equal('45%');
            });
        });
        
        describe('Command Input System', () => {
            let commandInput;
            
            beforeEach(() => {
                commandInput = document.querySelector('.command-input');
            });
            
            it('executes commands on Enter key', async () => {
                // Mock API call
                const fetchSpy = sinon.stub(window, 'fetch');
                fetchSpy.returns(Promise.resolve({ ok: true, json: () => ({}) }));
                
                // Simulate command input
                commandInput.value = 'approve P7';
                const enterEvent = new KeyboardEvent('keypress', { key: 'Enter' });
                commandInput.dispatchEvent(enterEvent);
                
                // Verify API call made
                expect(fetchSpy.calledOnce).to.be.true;
                expect(fetchSpy.firstCall.args[0]).to.include('/api/command');
            });
            
            it('shows command history with up/down arrows', () => {
                // Execute several commands
                executeCommand('approve P1');
                executeCommand('brief C2');
                executeCommand('refresh');
                
                // Test up arrow recalls previous commands
                const upEvent = new KeyboardEvent('keydown', { key: 'ArrowUp' });
                commandInput.dispatchEvent(upEvent);
                expect(commandInput.value).to.equal('refresh');
                
                commandInput.dispatchEvent(upEvent);
                expect(commandInput.value).to.equal('brief C2');
            });
            
            it('supports command auto-completion', () => {
                commandInput.value = 'app';
                const tabEvent = new KeyboardEvent('keydown', { key: 'Tab' });
                commandInput.dispatchEvent(tabEvent);
                
                expect(commandInput.value).to.equal('approve ');
            });
        });
        
        describe('Visual State Updates', () => {
            it('preserves paper-dense aesthetic during updates', () => {
                const testState = {
                    calendar: Array.from({length: 10}, (_, i) => ({
                        id: `C${i+1}`,
                        time: `${9+i}:00`,
                        title: `Meeting ${i+1}`
                    }))
                };
                
                updateCalendarSection(testState.calendar);
                
                // Verify styling preserved
                const calendarItems = document.querySelectorAll('.item');
                calendarItems.forEach(item => {
                    const computedStyle = getComputedStyle(item);
                    expect(computedStyle.fontSize).to.equal('12px');
                    expect(computedStyle.lineHeight).to.equal('1.3');
                });
            });
            
            it('shows loading states during API calls', async () => {
                // Mock slow API response
                const slowFetch = () => new Promise(resolve => 
                    setTimeout(() => resolve({ ok: true, json: () => ({}) }), 100));
                sinon.stub(window, 'fetch').returns(slowFetch());
                
                // Execute command
                executeCommand('refresh');
                
                // Verify loading indicator appears
                expect(document.querySelector('.loading')).to.exist;
                
                // Wait for completion
                await new Promise(resolve => setTimeout(resolve, 150));
                
                // Verify loading indicator removed
                expect(document.querySelector('.loading')).to.not.exist;
            });
        });
        
        describe('Error Handling', () => {
            it('handles WebSocket disconnections gracefully', () => {
                // Simulate WebSocket close
                handleWebSocketClose();
                
                // Verify reconnection attempt
                expect(document.querySelector('.connection-status').textContent).to.include('Reconnecting');
                
                // Verify retry mechanism
                setTimeout(() => {
                    expect(connectWebSocket).to.have.been.called;
                }, 1000);
            });
            
            it('displays error messages for failed commands', async () => {
                // Mock API error
                sinon.stub(window, 'fetch').returns(
                    Promise.resolve({ 
                        ok: false, 
                        json: () => ({ error: 'Invalid command' }) 
                    })
                );
                
                await executeCommand('invalid command');
                
                // Verify error displayed
                const errorElement = document.querySelector('.error-message');
                expect(errorElement).to.exist;
                expect(errorElement.textContent).to.include('Invalid command');
            });
        });
    </script>
    
    <script>mocha.run();</script>
</body>
</html>
```

## Implementation Tasks

### Task F1: WebSocket Client Implementation (2 hours)

**Objective**: Implement WebSocket connection with auto-reconnection and state handling

**File**: `dashboard/js/websocket.js`
```javascript
class WebSocketManager {
    constructor(url) {
        this.url = url;
        this.ws = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 10;
        this.reconnectDelay = 1000; // Start with 1 second
        this.handlers = {
            open: [],
            message: [],
            close: [],
            error: []
        };
    }
    
    connect() {
        try {
            this.ws = new WebSocket(this.url);
            
            this.ws.onopen = (event) => {
                console.log('WebSocket connected');
                this.reconnectAttempts = 0;
                this.reconnectDelay = 1000;
                this.updateConnectionStatus('connected');
                this.handlers.open.forEach(handler => handler(event));
            };
            
            this.ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    this.handlers.message.forEach(handler => handler(data));
                } catch (error) {
                    console.error('Error parsing WebSocket message:', error);
                }
            };
            
            this.ws.onclose = (event) => {
                console.log('WebSocket disconnected');
                this.updateConnectionStatus('disconnected');
                this.handlers.close.forEach(handler => handler(event));
                this.scheduleReconnect();
            };
            
            this.ws.onerror = (event) => {
                console.error('WebSocket error:', event);
                this.updateConnectionStatus('error');
                this.handlers.error.forEach(handler => handler(event));
            };
            
        } catch (error) {
            console.error('WebSocket connection failed:', error);
            this.scheduleReconnect();
        }
    }
    
    scheduleReconnect() {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.error('Max reconnection attempts reached');
            this.updateConnectionStatus('failed');
            return;
        }
        
        this.reconnectAttempts++;
        this.updateConnectionStatus('reconnecting', this.reconnectAttempts);
        
        setTimeout(() => {
            this.connect();
        }, this.reconnectDelay);
        
        // Exponential backoff
        this.reconnectDelay = Math.min(this.reconnectDelay * 2, 30000);
    }
    
    updateConnectionStatus(status, attempts = 0) {
        const statusElement = document.querySelector('.connection-status');
        if (statusElement) {
            switch (status) {
                case 'connected':
                    statusElement.textContent = 'Connected';
                    statusElement.className = 'connection-status connected';
                    break;
                case 'disconnected':
                    statusElement.textContent = 'Disconnected';
                    statusElement.className = 'connection-status disconnected';
                    break;
                case 'reconnecting':
                    statusElement.textContent = `Reconnecting... (${attempts}/${this.maxReconnectAttempts})`;
                    statusElement.className = 'connection-status reconnecting';
                    break;
                case 'error':
                    statusElement.textContent = 'Connection Error';
                    statusElement.className = 'connection-status error';
                    break;
                case 'failed':
                    statusElement.textContent = 'Connection Failed';
                    statusElement.className = 'connection-status failed';
                    break;
            }
        }
    }
    
    on(event, handler) {
        if (this.handlers[event]) {
            this.handlers[event].push(handler);
        }
    }
    
    send(data) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(data));
        } else {
            console.warn('WebSocket not connected, message not sent:', data);
        }
    }
}
```

**Acceptance Criteria**:
- WebSocket connects on page load
- Auto-reconnection with exponential backoff
- Connection status displayed to user
- Message parsing and error handling

### Task F2: DOM Update System (3 hours)

**Objective**: Implement efficient DOM updates preserving paper-dense styling

**File**: `dashboard/js/app.js`
```javascript
class DashboardApp {
    constructor() {
        this.state = {
            system: { status: 'IDLE', progress: 0 },
            calendar: [],
            priorities: [],
            commitments: { owe: [], owed: [] },
            active_brief: null
        };
        this.commandHistory = [];
        this.historyIndex = 0;
        
        this.initializeWebSocket();
        this.initializeCommands();
    }
    
    initializeWebSocket() {
        this.ws = new WebSocketManager('ws://localhost:8000/ws');
        
        this.ws.on('message', (data) => {
            this.updateState(data);
        });
        
        this.ws.connect();
    }
    
    updateState(newState) {
        // Merge new state with existing state
        this.state = { ...this.state, ...newState };
        
        // Update each section
        this.updateSystemSection();
        this.updateCalendarSection();
        this.updatePrioritiesSection();
        this.updateCommitmentsSection();
        this.updateBriefSection();
    }
    
    updateSystemSection() {
        const { status, progress, last_sync } = this.state.system;
        
        // Update status
        const statusElement = document.querySelector('[data-system-status]');
        if (statusElement) {
            statusElement.textContent = status;
            statusElement.className = `status ${status.toLowerCase()}`;
        }
        
        // Update progress bar
        const progressBar = document.querySelector('.progress-bar');
        const progressText = document.querySelector('.progress-text');
        if (progressBar && progressText) {
            progressBar.style.width = `${progress}%`;
            progressText.textContent = `${progress}%`;
        }
        
        // Update last sync time
        const lastSyncElement = document.querySelector('[data-last-sync]');
        if (lastSyncElement && last_sync) {
            const syncTime = new Date(last_sync).toLocaleTimeString();
            lastSyncElement.textContent = syncTime;
        }
    }
    
    updateCalendarSection() {
        const calendarContainer = document.querySelector('.calendar-items');
        if (!calendarContainer) return;
        
        // Clear existing items
        calendarContainer.innerHTML = '';
        
        // Add calendar items
        this.state.calendar.forEach(item => {
            const itemElement = document.createElement('div');
            itemElement.className = 'item';
            itemElement.setAttribute('data-calendar-item', item.id);
            
            const isAlert = item.alert || false;
            const alertClass = isAlert ? 'alert' : '';
            
            itemElement.innerHTML = `
                <span class="item-code">${item.id}:</span>
                <span class="time">${item.time}</span>
                <span class="${alertClass}">${item.title}</span>
                ${item.new ? '<span class="new">[new]</span>' : ''}
            `;
            
            calendarContainer.appendChild(itemElement);
        });
    }
    
    updatePrioritiesSection() {
        const prioritiesContainer = document.querySelector('.priorities-items');
        if (!prioritiesContainer) return;
        
        prioritiesContainer.innerHTML = '';
        
        this.state.priorities.forEach(item => {
            const itemElement = document.createElement('div');
            itemElement.className = 'item';
            itemElement.setAttribute('data-priority-item', item.id);
            
            let checkboxSymbol;
            let checkboxClass;
            
            switch (item.status) {
                case 'done':
                    checkboxSymbol = '[✓]';
                    checkboxClass = 'checkbox done';
                    break;
                case 'partial':
                    checkboxSymbol = '[◐]';
                    checkboxClass = 'checkbox partial';
                    break;
                default:
                    checkboxSymbol = '[ ]';
                    checkboxClass = 'checkbox';
            }
            
            const alertClass = item.alert ? 'alert' : '';
            
            itemElement.innerHTML = `
                <span class="item-code">${item.id}:</span>
                <span class="${checkboxClass}">${checkboxSymbol}</span>
                <span class="${alertClass}">${item.text}</span>
                ${item.new ? '<span class="new">[new]</span>' : ''}
            `;
            
            prioritiesContainer.appendChild(itemElement);
        });
    }
    
    updateCommitmentsSection() {
        // Update "I OWE" section
        const oweContainer = document.querySelector('.commitments-owe');
        if (oweContainer) {
            oweContainer.innerHTML = '';
            this.state.commitments.owe.forEach(item => {
                const itemElement = this.createCommitmentItem(item);
                oweContainer.appendChild(itemElement);
            });
        }
        
        // Update "OWED TO ME" section  
        const owedContainer = document.querySelector('.commitments-owed');
        if (owedContainer) {
            owedContainer.innerHTML = '';
            this.state.commitments.owed.forEach(item => {
                const itemElement = this.createCommitmentItem(item);
                owedContainer.appendChild(itemElement);
            });
        }
        
        // Update summary numbers
        this.updateCommitmentSummary();
    }
    
    createCommitmentItem(item) {
        const itemElement = document.createElement('div');
        itemElement.className = 'item';
        itemElement.setAttribute('data-commitment-item', item.id);
        
        const alertClass = item.alert ? 'alert' : '';
        const completedClass = item.status === 'done' ? 'checkbox done' : '';
        
        itemElement.innerHTML = `
            <span class="item-code">${item.id}:</span>
            ${item.status === 'done' ? '<span class="checkbox done">[✓]</span>' : ''}
            <span class="${alertClass}">${item.text}</span>
        `;
        
        return itemElement;
    }
    
    updateCommitmentSummary() {
        const dueToday = this.state.commitments.owe.filter(item => 
            item.due_date && this.isToday(item.due_date) && item.status !== 'done'
        ).length;
        
        const totalOwed = this.state.commitments.owed.filter(item => 
            item.status !== 'done'
        ).length;
        
        // Update summary boxes
        const dueTodayElement = document.querySelector('.commit-num.urgent');
        const totalOwedElement = document.querySelector('.commit-num:not(.urgent)');
        
        if (dueTodayElement) {
            dueTodayElement.textContent = dueToday;
        }
        
        if (totalOwedElement) {
            totalOwedElement.textContent = totalOwed;
        }
    }
    
    isToday(dateString) {
        const date = new Date(dateString);
        const today = new Date();
        return date.toDateString() === today.toDateString();
    }
    
    updateBriefSection() {
        if (this.state.active_brief) {
            // Show brief in main content area
            this.displayBrief(this.state.active_brief);
        }
    }
    
    displayBrief(brief) {
        const contentArea = document.querySelector('.content');
        if (contentArea) {
            contentArea.innerHTML = brief.html_content || brief.text_content || '';
        }
    }
}
```

**Acceptance Criteria**:
- All sections update correctly from WebSocket data
- Paper-dense styling preserved during updates
- Efficient DOM manipulation (no full re-renders)
- Visual feedback for different item states

### Task F3: Command Input System (2 hours)

**Objective**: Implement command input with history and auto-completion

**File**: `dashboard/js/commands.js`
```javascript
class CommandManager {
    constructor(apiBaseUrl = 'http://localhost:8000') {
        this.apiBaseUrl = apiBaseUrl;
        this.history = this.loadCommandHistory();
        this.historyIndex = this.history.length;
        this.suggestions = [
            'approve P1', 'approve P2', 'approve P3', 'approve P4', 'approve P5',
            'brief C1', 'brief C2', 'brief C3', 'brief C4',
            'refresh', 'quick', 'full'
        ];
        
        this.initializeInput();
    }
    
    initializeInput() {
        const input = document.querySelector('.command-input');
        if (!input) return;
        
        input.addEventListener('keypress', this.handleKeyPress.bind(this));
        input.addEventListener('keydown', this.handleKeyDown.bind(this));
        input.addEventListener('input', this.handleInput.bind(this));
    }
    
    async handleKeyPress(event) {
        if (event.key === 'Enter') {
            event.preventDefault();
            const command = event.target.value.trim();
            
            if (command) {
                await this.executeCommand(command);
                this.addToHistory(command);
                event.target.value = '';
                this.historyIndex = this.history.length;
            }
        }
    }
    
    handleKeyDown(event) {
        const input = event.target;
        
        switch (event.key) {
            case 'ArrowUp':
                event.preventDefault();
                this.showPreviousCommand(input);
                break;
                
            case 'ArrowDown':
                event.preventDefault();
                this.showNextCommand(input);
                break;
                
            case 'Tab':
                event.preventDefault();
                this.autoCompleteCommand(input);
                break;
                
            case 'Escape':
                input.value = '';
                this.historyIndex = this.history.length;
                break;
        }
    }
    
    handleInput(event) {
        const input = event.target;
        this.showSuggestions(input);
    }
    
    showPreviousCommand(input) {
        if (this.historyIndex > 0) {
            this.historyIndex--;
            input.value = this.history[this.historyIndex];
            input.setSelectionRange(input.value.length, input.value.length);
        }
    }
    
    showNextCommand(input) {
        if (this.historyIndex < this.history.length - 1) {
            this.historyIndex++;
            input.value = this.history[this.historyIndex];
        } else if (this.historyIndex === this.history.length - 1) {
            this.historyIndex++;
            input.value = '';
        }
    }
    
    autoCompleteCommand(input) {
        const partial = input.value.toLowerCase();
        const matches = this.suggestions.filter(cmd => 
            cmd.toLowerCase().startsWith(partial)
        );
        
        if (matches.length === 1) {
            input.value = matches[0];
            input.setSelectionRange(partial.length, matches[0].length);
        } else if (matches.length > 1) {
            // Show suggestions dropdown
            this.showSuggestionsDropdown(input, matches);
        }
    }
    
    showSuggestions(input) {
        const value = input.value.toLowerCase();
        if (value.length < 2) {
            this.hideSuggestions();
            return;
        }
        
        const matches = this.suggestions.filter(cmd =>
            cmd.toLowerCase().includes(value)
        ).slice(0, 5);
        
        if (matches.length > 0) {
            this.showSuggestionsDropdown(input, matches);
        } else {
            this.hideSuggestions();
        }
    }
    
    showSuggestionsDropdown(input, suggestions) {
        let dropdown = document.querySelector('.command-suggestions');
        
        if (!dropdown) {
            dropdown = document.createElement('div');
            dropdown.className = 'command-suggestions';
            input.parentNode.appendChild(dropdown);
        }
        
        dropdown.innerHTML = suggestions.map((suggestion, index) => 
            `<div class="suggestion-item" data-index="${index}">${suggestion}</div>`
        ).join('');
        
        // Handle suggestion clicks
        dropdown.addEventListener('click', (e) => {
            if (e.target.classList.contains('suggestion-item')) {
                input.value = e.target.textContent;
                this.hideSuggestions();
                input.focus();
            }
        });
    }
    
    hideSuggestions() {
        const dropdown = document.querySelector('.command-suggestions');
        if (dropdown) {
            dropdown.remove();
        }
    }
    
    async executeCommand(command) {
        this.showLoading(true);
        
        try {
            const response = await fetch(`${this.apiBaseUrl}/api/command`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ command })
            });
            
            if (response.ok) {
                const result = await response.json();
                this.showCommandResult(command, result, 'success');
            } else {
                const error = await response.json();
                this.showCommandResult(command, error, 'error');
            }
        } catch (error) {
            console.error('Command execution failed:', error);
            this.showCommandResult(command, { error: error.message }, 'error');
        }
        
        this.showLoading(false);
    }
    
    showCommandResult(command, result, type) {
        const resultArea = document.querySelector('.command-result') || this.createResultArea();
        
        resultArea.className = `command-result ${type}`;
        resultArea.innerHTML = `
            <div class="result-command">&gt; ${command}</div>
            <div class="result-message">${this.formatResult(result)}</div>
        `;
        
        // Auto-hide after 3 seconds for success, keep errors visible
        if (type === 'success') {
            setTimeout(() => {
                resultArea.style.display = 'none';
            }, 3000);
        }
    }
    
    formatResult(result) {
        if (result.error) {
            return `Error: ${result.error}`;
        } else if (result.action) {
            return `Executed: ${result.action} ${result.target || ''}`;
        } else {
            return 'Command executed successfully';
        }
    }
    
    createResultArea() {
        const resultArea = document.createElement('div');
        resultArea.className = 'command-result';
        
        const commandArea = document.querySelector('.command');
        commandArea.appendChild(resultArea);
        
        return resultArea;
    }
    
    showLoading(show) {
        const input = document.querySelector('.command-input');
        if (show) {
            input.disabled = true;
            input.placeholder = 'Executing...';
        } else {
            input.disabled = false;
            input.placeholder = '> approve P7 | refresh | brief C3';
        }
    }
    
    addToHistory(command) {
        if (this.history[this.history.length - 1] !== command) {
            this.history.push(command);
            
            // Keep history size reasonable
            if (this.history.length > 100) {
                this.history = this.history.slice(-50);
            }
            
            this.saveCommandHistory();
        }
    }
    
    loadCommandHistory() {
        try {
            const stored = localStorage.getItem('commandHistory');
            return stored ? JSON.parse(stored) : [];
        } catch (error) {
            console.warn('Failed to load command history:', error);
            return [];
        }
    }
    
    saveCommandHistory() {
        try {
            localStorage.setItem('commandHistory', JSON.stringify(this.history));
        } catch (error) {
            console.warn('Failed to save command history:', error);
        }
    }
}
```

**Acceptance Criteria**:
- Enter key executes commands
- Up/down arrows navigate command history
- Tab key auto-completes commands
- Suggestions dropdown appears while typing
- Command results display with appropriate styling

### Task F4: Visual Polish & Error States (1 hour)

**Objective**: Add loading states, error displays, and connection status

**File**: `dashboard/css/enhancements.css`
```css
/* Connection status indicator */
.connection-status {
    position: fixed;
    top: 10px;
    right: 10px;
    padding: 4px 8px;
    font-size: 10px;
    border-radius: 3px;
    z-index: 1000;
}

.connection-status.connected {
    background: #2e7d32;
    color: white;
}

.connection-status.disconnected {
    background: #d32f2f;
    color: white;
}

.connection-status.reconnecting {
    background: #f57c00;
    color: white;
    animation: pulse 1s infinite;
}

.connection-status.error,
.connection-status.failed {
    background: #c62828;
    color: white;
}

/* Loading states */
.loading::after {
    content: '';
    display: inline-block;
    width: 10px;
    height: 10px;
    border: 1px solid #005f87;
    border-radius: 50%;
    border-top-color: transparent;
    animation: spin 0.8s linear infinite;
    margin-left: 5px;
}

/* Command result display */
.command-result {
    margin-top: 4px;
    padding: 4px;
    font-size: 10px;
    border-left: 2px solid #005f87;
}

.command-result.error {
    border-left-color: #c62828;
    background: #ffebee;
}

.command-result.success {
    border-left-color: #2e7d32;
    background: #e8f5e8;
}

.result-command {
    font-weight: bold;
    color: #005f87;
}

.result-message {
    margin-top: 2px;
}

/* Command suggestions dropdown */
.command-suggestions {
    position: absolute;
    top: 100%;
    left: 0;
    right: 0;
    background: white;
    border: 1px solid #d0d0d0;
    border-top: none;
    max-height: 120px;
    overflow-y: auto;
    z-index: 1000;
}

.suggestion-item {
    padding: 4px 8px;
    cursor: pointer;
    font-size: 10px;
    border-bottom: 1px solid #f0f0f0;
}

.suggestion-item:hover {
    background: #f0f0f0;
}

/* Animations */
@keyframes pulse {
    0% { opacity: 1; }
    50% { opacity: 0.5; }
    100% { opacity: 1; }
}

@keyframes spin {
    to { transform: rotate(360deg); }
}

/* Error states */
.error-message {
    color: #c62828;
    font-weight: bold;
    background: #ffebee;
    padding: 2px 4px;
    margin: 2px 0;
}

/* Progress bar enhancements */
.progress-bar {
    transition: width 0.3s ease-in-out;
}

/* Status color coding */
.status.idle { color: #666; }
.status.collecting { color: #d75f00; }
.status.processing { color: #005f87; }
.status.error { color: #c62828; }
```

**Acceptance Criteria**:
- Connection status visible and updates correctly
- Loading indicators show during API calls
- Error messages display appropriately
- Smooth transitions for progress bars
- Command suggestions styled consistently

## Integration Requirements

### API Integration
- Connect to Agent E backend API endpoints
- Handle WebSocket messages from `/ws` endpoint
- Execute commands via `/api/command` endpoint
- Display system status from `/api/system/status`

### Styling Preservation
- Maintain exact paper-dense aesthetic from mockup
- Preserve all original color scheme and typography
- Keep responsive behavior for different screen sizes
- Ensure accessibility for keyboard navigation

### Performance Requirements
- Page load time <3 seconds
- DOM updates complete in <100ms
- WebSocket message handling <50ms
- Smooth animations and transitions

## Files to Create/Modify

### Core Dashboard Files
```
dashboard/
├── index.html             # Enhanced from cos-paper-dense.html
├── js/
│   ├── app.js             # Main application logic
│   ├── websocket.js       # WebSocket connection management
│   └── commands.js        # Command input system
├── css/
│   ├── paper-dense.css    # Preserved original styling
│   └── enhancements.css   # New functionality styling
└── assets/
    └── favicon.ico        # Dashboard icon
```

### Test Files
```
tests/dashboard/
├── test_frontend.html     # Browser-based test suite
├── test_websocket.js      # WebSocket functionality tests
└── test_commands.js       # Command system tests
```

## Success Criteria

### Visual Validation ✅
- [ ] Dashboard looks identical to cos-paper-dense.html mockup
- [ ] All sections update correctly from WebSocket data
- [ ] Paper-dense aesthetic preserved during all updates
- [ ] Responsive design works on different screen sizes

### Functional Validation ✅
- [ ] WebSocket connects and receives initial state
- [ ] Real-time updates appear within 100ms
- [ ] Command input works with all specified features
- [ ] Command history and auto-completion functional
- [ ] Error states display appropriately

### Performance Validation ✅
- [ ] Page loads in <3 seconds
- [ ] DOM updates complete in <100ms  
- [ ] No memory leaks during extended use
- [ ] Smooth reconnection after WebSocket drops

### Integration Validation ✅
- [ ] Compatible with Agent E backend API
- [ ] Prepares integration points for Agent G coding system
- [ ] No conflicts with existing project structure

## Delivery Checklist

Before marking Agent F complete:
- [ ] All test suites written and passing in browser
- [ ] Dashboard functional with mockup aesthetic preserved  
- [ ] WebSocket client operational with auto-reconnection
- [ ] Command input system fully featured
- [ ] Error handling covers edge cases
- [ ] Performance benchmarks documented
- [ ] Integration points clearly defined for Agent G/H

---

**Contact Agent F Team Lead for questions or Agent G/H integration points**  
**Dependencies**: Requires Agent E backend API to be functional