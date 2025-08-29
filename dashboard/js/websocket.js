/**
 * WebSocket Manager - Real-time connection handling for AI Chief of Staff Dashboard
 * 
 * References:
 * - Backend WebSocket endpoint: /Users/david.campos/VibeCode/AICoS-Lab/backend/server.py
 * - Task specification: /Users/david.campos/VibeCode/AICoS-Lab/tasks/frontend_agent_f_dashboard.md
 * - Test requirements: /Users/david.campos/VibeCode/AICoS-Lab/tests/dashboard/test_frontend.html
 * 
 * Features:
 * - Auto-reconnection with exponential backoff
 * - Connection status management and UI updates
 * - Message parsing and error handling
 * - Event-driven architecture for extensibility
 * - Performance optimized for <50ms message handling
 */

class WebSocketManager {
    constructor(url) {
        this.url = url;
        this.ws = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 10;
        this.reconnectDelay = 1000; // Start with 1 second
        this.maxReconnectDelay = 30000; // Maximum 30 seconds
        this.isReconnecting = false;
        this.isManualClose = false;
        
        // Event handlers registry
        this.handlers = {
            open: [],
            message: [],
            close: [],
            error: [],
            reconnect: [],
            reconnectFailed: []
        };
        
        // Performance tracking
        this.stats = {
            connectionsAttempted: 0,
            connectionsSuccessful: 0,
            messagesReceived: 0,
            messageHandlingTimes: [],
            lastConnectedAt: null,
            totalReconnects: 0
        };
        
        // Bind methods to preserve context
        this.connect = this.connect.bind(this);
        this.scheduleReconnect = this.scheduleReconnect.bind(this);
        this.handleOpen = this.handleOpen.bind(this);
        this.handleMessage = this.handleMessage.bind(this);
        this.handleClose = this.handleClose.bind(this);
        this.handleError = this.handleError.bind(this);
    }
    
    /**
     * Establish WebSocket connection with error handling
     */
    connect() {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            console.log('WebSocket already connected');
            return;
        }
        
        try {
            console.log(`Attempting WebSocket connection to ${this.url}`);
            this.stats.connectionsAttempted++;
            
            this.ws = new WebSocket(this.url);
            
            // Set up event handlers
            this.ws.onopen = this.handleOpen;
            this.ws.onmessage = this.handleMessage;
            this.ws.onclose = this.handleClose;
            this.ws.onerror = this.handleError;
            
        } catch (error) {
            console.error('WebSocket connection failed:', error);
            this.updateConnectionStatus('error');
            this.scheduleReconnect();
        }
    }
    
    /**
     * Handle successful WebSocket connection
     */
    handleOpen(event) {
        console.log('WebSocket connected successfully');
        
        // Reset reconnection state
        this.reconnectAttempts = 0;
        this.reconnectDelay = 1000;
        this.isReconnecting = false;
        
        // Update statistics
        this.stats.connectionsSuccessful++;
        this.stats.lastConnectedAt = new Date().toISOString();
        
        // Update UI
        this.updateConnectionStatus('connected');
        
        // Notify handlers
        this.handlers.open.forEach(handler => {
            try {
                handler(event);
            } catch (error) {
                console.error('Error in open handler:', error);
            }
        });
    }
    
    /**
     * Handle incoming WebSocket messages with performance tracking
     */
    handleMessage(event) {
        const startTime = performance.now();
        
        try {
            // Parse message data
            const data = JSON.parse(event.data);
            
            // Track statistics
            this.stats.messagesReceived++;
            
            // Notify handlers
            this.handlers.message.forEach(handler => {
                try {
                    handler(data, event);
                } catch (error) {
                    console.error('Error in message handler:', error);
                }
            });
            
            // Track performance
            const endTime = performance.now();
            const handlingTime = endTime - startTime;
            this.stats.messageHandlingTimes.push(handlingTime);
            
            // Keep only last 100 measurements
            if (this.stats.messageHandlingTimes.length > 100) {
                this.stats.messageHandlingTimes = this.stats.messageHandlingTimes.slice(-100);
            }
            
            // Log slow message handling
            if (handlingTime > 50) {
                console.warn(`Slow WebSocket message handling: ${handlingTime.toFixed(2)}ms`);
            }
            
        } catch (error) {
            console.error('Error parsing WebSocket message:', error, event.data);
        }
    }
    
    /**
     * Handle WebSocket connection close
     */
    handleClose(event) {
        const { code, reason, wasClean } = event;
        
        console.log(`WebSocket disconnected: code=${code}, reason="${reason}", wasClean=${wasClean}`);
        
        // Update UI
        this.updateConnectionStatus('disconnected');
        
        // Notify handlers
        this.handlers.close.forEach(handler => {
            try {
                handler(event);
            } catch (error) {
                console.error('Error in close handler:', error);
            }
        });
        
        // Schedule reconnection unless it was a manual close
        if (!this.isManualClose && !wasClean) {
            this.scheduleReconnect();
        }
    }
    
    /**
     * Handle WebSocket errors
     */
    handleError(event) {
        console.error('WebSocket error occurred:', event);
        this.updateConnectionStatus('error');
        
        // Notify handlers
        this.handlers.error.forEach(handler => {
            try {
                handler(event);
            } catch (error) {
                console.error('Error in error handler:', error);
            }
        });
    }
    
    /**
     * Schedule automatic reconnection with exponential backoff
     */
    scheduleReconnect() {
        if (this.isReconnecting || this.isManualClose) {
            return;
        }
        
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.error('Max reconnection attempts reached');
            this.updateConnectionStatus('failed');
            
            // Notify handlers of failed reconnection
            this.handlers.reconnectFailed.forEach(handler => {
                try {
                    handler();
                } catch (error) {
                    console.error('Error in reconnectFailed handler:', error);
                }
            });
            return;
        }
        
        this.isReconnecting = true;
        this.reconnectAttempts++;
        this.stats.totalReconnects++;
        
        console.log(`Scheduling reconnection attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts} in ${this.reconnectDelay}ms`);
        
        this.updateConnectionStatus('reconnecting', this.reconnectAttempts);
        
        // Notify handlers of reconnection attempt
        this.handlers.reconnect.forEach(handler => {
            try {
                handler(this.reconnectAttempts, this.reconnectDelay);
            } catch (error) {
                console.error('Error in reconnect handler:', error);
            }
        });
        
        setTimeout(() => {
            this.connect();
        }, this.reconnectDelay);
        
        // Exponential backoff with jitter
        this.reconnectDelay = Math.min(
            this.reconnectDelay * 2 + Math.random() * 1000,
            this.maxReconnectDelay
        );
    }
    
    /**
     * Update connection status in UI
     */
    updateConnectionStatus(status, attempts = 0) {
        const statusElement = document.querySelector('.connection-status');
        
        if (statusElement) {
            statusElement.className = `connection-status ${status}`;
            
            switch (status) {
                case 'connected':
                    statusElement.textContent = 'Connected';
                    break;
                case 'disconnected':
                    statusElement.textContent = 'Disconnected';
                    break;
                case 'reconnecting':
                    statusElement.textContent = `Reconnecting... (${attempts}/${this.maxReconnectAttempts})`;
                    break;
                case 'error':
                    statusElement.textContent = 'Connection Error';
                    break;
                case 'failed':
                    statusElement.textContent = 'Connection Failed';
                    break;
                default:
                    statusElement.textContent = 'Unknown';
            }
        }
    }
    
    /**
     * Add event handler for specific event type
     */
    on(event, handler) {
        if (this.handlers[event]) {
            this.handlers[event].push(handler);
        } else {
            console.warn(`Unknown event type: ${event}`);
        }
        return this; // Allow chaining
    }
    
    /**
     * Remove event handler
     */
    off(event, handler) {
        if (this.handlers[event]) {
            const index = this.handlers[event].indexOf(handler);
            if (index > -1) {
                this.handlers[event].splice(index, 1);
            }
        }
        return this;
    }
    
    /**
     * Send message through WebSocket if connected
     */
    send(data) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            try {
                const message = typeof data === 'string' ? data : JSON.stringify(data);
                this.ws.send(message);
                return true;
            } catch (error) {
                console.error('Failed to send WebSocket message:', error);
                return false;
            }
        } else {
            console.warn('WebSocket not connected, message not sent:', data);
            return false;
        }
    }
    
    /**
     * Manually close WebSocket connection
     */
    close() {
        this.isManualClose = true;
        this.isReconnecting = false;
        
        if (this.ws) {
            this.ws.close(1000, 'Manual close');
        }
        
        this.updateConnectionStatus('disconnected');
    }
    
    /**
     * Get connection status
     */
    isConnected() {
        return this.ws && this.ws.readyState === WebSocket.OPEN;
    }
    
    /**
     * Get connection statistics
     */
    getStats() {
        const avgHandlingTime = this.stats.messageHandlingTimes.length > 0 ?
            this.stats.messageHandlingTimes.reduce((a, b) => a + b, 0) / this.stats.messageHandlingTimes.length : 0;
            
        const maxHandlingTime = this.stats.messageHandlingTimes.length > 0 ?
            Math.max(...this.stats.messageHandlingTimes) : 0;
        
        return {
            url: this.url,
            connected: this.isConnected(),
            reconnectAttempts: this.reconnectAttempts,
            totalReconnects: this.stats.totalReconnects,
            connectionsAttempted: this.stats.connectionsAttempted,
            connectionsSuccessful: this.stats.connectionsSuccessful,
            messagesReceived: this.stats.messagesReceived,
            averageHandlingTime: parseFloat(avgHandlingTime.toFixed(2)),
            maxHandlingTime: parseFloat(maxHandlingTime.toFixed(2)),
            lastConnectedAt: this.stats.lastConnectedAt,
            currentDelay: this.reconnectDelay
        };
    }
    
    /**
     * Reset connection with fresh state
     */
    reset() {
        this.close();
        this.reconnectAttempts = 0;
        this.reconnectDelay = 1000;
        this.isManualClose = false;
        this.isReconnecting = false;
        
        // Reset stats
        this.stats.messagesReceived = 0;
        this.stats.messageHandlingTimes = [];
        this.stats.totalReconnects = 0;
        
        console.log('WebSocket connection reset');
    }
}

// Global WebSocket instance management
let globalWebSocketManager = null;

/**
 * Initialize global WebSocket connection
 */
function initializeWebSocket(url = 'ws://localhost:8000/ws') {
    if (globalWebSocketManager) {
        globalWebSocketManager.close();
    }
    
    globalWebSocketManager = new WebSocketManager(url);
    
    // Auto-connect
    globalWebSocketManager.connect();
    
    return globalWebSocketManager;
}

/**
 * Get or create global WebSocket manager
 */
function getWebSocketManager() {
    if (!globalWebSocketManager) {
        globalWebSocketManager = initializeWebSocket();
    }
    return globalWebSocketManager;
}

/**
 * Convenience functions for backward compatibility
 */
function connectWebSocket() {
    const manager = getWebSocketManager();
    manager.connect();
    return manager;
}

function handleWebSocketMessage(event) {
    // Legacy handler support for tests
    const manager = getWebSocketManager();
    if (event.data) {
        const data = JSON.parse(event.data);
        manager.handlers.message.forEach(handler => handler(data, event));
    }
}

function handleWebSocketClose() {
    const manager = getWebSocketManager();
    manager.updateConnectionStatus('disconnected');
    manager.scheduleReconnect();
}

// Export for module systems and global access
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        WebSocketManager,
        initializeWebSocket,
        getWebSocketManager,
        connectWebSocket,
        handleWebSocketMessage,
        handleWebSocketClose
    };
}

// Global access for browser
window.WebSocketManager = WebSocketManager;
window.initializeWebSocket = initializeWebSocket;
window.getWebSocketManager = getWebSocketManager;
window.connectWebSocket = connectWebSocket;
window.handleWebSocketMessage = handleWebSocketMessage;
window.handleWebSocketClose = handleWebSocketClose;