/**
 * Dashboard Application - Main application logic for AI Chief of Staff Dashboard
 * 
 * References:
 * - Mockup design: /Users/david.campos/VibeCode/AICoS-Lab/cos-paper-dense.html
 * - Backend state structure: /Users/david.campos/VibeCode/AICoS-Lab/backend/state_manager.py
 * - WebSocket manager: /Users/david.campos/VibeCode/AICoS-Lab/dashboard/js/websocket.js
 * - Test requirements: /Users/david.campos/VibeCode/AICoS-Lab/tests/dashboard/test_frontend.html
 * 
 * Features:
 * - Real-time state management with WebSocket updates
 * - Efficient DOM updates preserving paper-dense aesthetic
 * - Performance optimized for <100ms DOM operations
 * - Comprehensive error handling and user feedback
 * - Responsive design with accessibility support
 */

class DashboardApp {
    constructor() {
        // Application state
        this.state = {
            system: { 
                status: 'IDLE', 
                progress: 0,
                last_sync: null 
            },
            calendar: [],
            priorities: [],
            commitments: { owe: [], owed: [] },
            active_brief: null
        };
        
        // Performance tracking
        this.performanceMetrics = {
            domUpdateTimes: [],
            stateUpdateTimes: [],
            renderingStartTime: performance.now()
        };
        
        // DOM element cache for performance
        this.elements = {};
        
        // Component update flags
        this.pendingUpdates = new Set();
        
        // Initialize application
        this.init();
    }
    
    /**
     * Initialize the dashboard application
     */
    init() {
        console.log('Initializing Dashboard Application...');
        
        // Cache DOM elements
        this.cacheElements();
        
        // Initialize WebSocket connection
        this.initializeWebSocket();
        
        // Initialize time display
        this.initializeTimeDisplay();
        
        // Initialize button handlers
        this.initializeButtons();
        
        // Initialize responsive behavior
        this.initializeResponsiveHandlers();
        
        // Mark as initialized
        this.initialized = true;
        
        console.log('Dashboard Application initialized successfully');
    }
    
    /**
     * Cache frequently accessed DOM elements for performance
     */
    cacheElements() {
        this.elements = {
            // System status elements
            systemStatus: document.querySelector('[data-system-status]'),
            progressBar: document.querySelector('.progress-bar'),
            progressText: document.querySelector('.progress-text'),
            lastSync: document.querySelector('[data-last-sync]'),
            
            // Content sections
            calendarItems: document.querySelector('.calendar-items'),
            prioritiesItems: document.querySelector('.priorities-items'),
            commitmentsOwe: document.querySelector('.commitments-owe'),
            commitmentsOwed: document.querySelector('.commitments-owed'),
            
            // Commitment summary boxes
            commitDueToday: document.querySelector('.commit-num.urgent'),
            commitTotalOwed: document.querySelector('.commit-num:not(.urgent)'),
            
            // Main content
            content: document.querySelector('.content'),
            headerTime: document.querySelector('.header-time'),
            
            // Connection status
            connectionStatus: document.querySelector('.connection-status'),
            
            // Quick action buttons
            quickBtn: document.querySelector('button[data-action="quick"]'),
            fullBtn: document.querySelector('button[data-action="full"]'),
            refreshBtn: document.querySelector('button[data-action="refresh"]')
        };
        
        // Log missing elements for debugging
        Object.keys(this.elements).forEach(key => {
            if (!this.elements[key]) {
                console.warn(`Element not found: ${key}`);
            }
        });
    }
    
    /**
     * Initialize WebSocket connection and event handlers
     */
    initializeWebSocket() {
        this.ws = getWebSocketManager();
        
        // Handle successful connection
        this.ws.on('open', () => {
            console.log('Dashboard connected to backend WebSocket');
        });
        
        // Handle incoming state updates
        this.ws.on('message', (data) => {
            this.handleStateUpdate(data);
        });
        
        // Handle connection issues
        this.ws.on('close', () => {
            console.log('Dashboard WebSocket connection closed');
        });
        
        this.ws.on('error', (error) => {
            console.error('Dashboard WebSocket error:', error);
            this.showError('Connection error occurred');
        });
        
        this.ws.on('reconnectFailed', () => {
            this.showError('Unable to connect to server. Please refresh the page.');
        });
    }
    
    /**
     * Initialize time display updates
     */
    initializeTimeDisplay() {
        this.updateCurrentTime();
        
        // Update time every minute
        setInterval(() => {
            this.updateCurrentTime();
        }, 60000);
    }
    
    /**
     * Initialize button event handlers
     */
    initializeButtons() {
        // Quick collect button
        if (this.elements.quickBtn) {
            console.log('Setting up QUICK button event handler');
            this.elements.quickBtn.addEventListener('click', () => {
                console.log('QUICK button clicked');
                this.triggerCollection('quick');
            });
        } else {
            console.warn('QUICK button not found - check selector');
        }
        
        // Full collect button  
        if (this.elements.fullBtn) {
            console.log('Setting up FULL button event handler');
            this.elements.fullBtn.addEventListener('click', () => {
                console.log('FULL button clicked');
                this.triggerCollection('full');
            });
        } else {
            console.warn('FULL button not found - check selector');
        }
        
        // Refresh button
        if (this.elements.refreshBtn) {
            console.log('Setting up REFRESH button event handler');
            this.elements.refreshBtn.addEventListener('click', () => {
                console.log('REFRESH button clicked');
                this.triggerRefresh();
            });
        } else {
            console.warn('REFRESH button not found - check selector');
        }
    }
    
    /**
     * Initialize responsive behavior handlers
     */
    initializeResponsiveHandlers() {
        // Handle window resize
        window.addEventListener('resize', () => {
            this.handleResize();
        });
        
        // Handle visibility changes
        document.addEventListener('visibilitychange', () => {
            this.handleVisibilityChange();
        });
    }
    
    /**
     * Handle incoming state updates from WebSocket
     */
    handleStateUpdate(newState) {
        const startTime = performance.now();
        
        try {
            // Merge new state with existing state
            this.state = this.mergeState(this.state, newState);
            
            // Queue DOM updates efficiently
            this.queueUpdates(newState);
            
            // Process queued updates
            this.processQueuedUpdates();
            
            // Track performance
            const updateTime = performance.now() - startTime;
            this.performanceMetrics.stateUpdateTimes.push(updateTime);
            
            if (updateTime > 100) {
                console.warn(`Slow state update: ${updateTime.toFixed(2)}ms`);
            }
            
        } catch (error) {
            console.error('Error handling state update:', error);
            this.showError('Failed to update dashboard data');
        }
    }
    
    /**
     * Merge new state with existing state intelligently
     */
    mergeState(currentState, newState) {
        const merged = { ...currentState };
        
        Object.keys(newState).forEach(key => {
            if (typeof newState[key] === 'object' && newState[key] !== null && !Array.isArray(newState[key])) {
                // Deep merge objects
                merged[key] = { ...merged[key], ...newState[key] };
            } else {
                // Replace arrays and primitives
                merged[key] = newState[key];
            }
        });
        
        return merged;
    }
    
    /**
     * Queue DOM updates based on what changed in state
     */
    queueUpdates(newState) {
        if (newState.system) {
            this.pendingUpdates.add('system');
        }
        if (newState.calendar) {
            this.pendingUpdates.add('calendar');
        }
        if (newState.priorities) {
            this.pendingUpdates.add('priorities');
        }
        if (newState.commitments) {
            this.pendingUpdates.add('commitments');
        }
        if (newState.active_brief) {
            this.pendingUpdates.add('brief');
        }
    }
    
    /**
     * Process all queued DOM updates in a single batch
     */
    processQueuedUpdates() {
        if (this.pendingUpdates.size === 0) return;
        
        const startTime = performance.now();
        
        // Use requestAnimationFrame for smooth updates
        requestAnimationFrame(() => {
            try {
                // Process updates in dependency order
                const updateOrder = ['system', 'calendar', 'priorities', 'commitments', 'brief'];
                
                updateOrder.forEach(section => {
                    if (this.pendingUpdates.has(section)) {
                        this.updateSection(section);
                        this.pendingUpdates.delete(section);
                    }
                });
                
                // Track DOM update performance
                const domUpdateTime = performance.now() - startTime;
                this.performanceMetrics.domUpdateTimes.push(domUpdateTime);
                
                if (domUpdateTime > 100) {
                    console.warn(`Slow DOM update: ${domUpdateTime.toFixed(2)}ms`);
                }
                
            } catch (error) {
                console.error('Error processing DOM updates:', error);
            }
        });
    }
    
    /**
     * Update specific section of the dashboard
     */
    updateSection(section) {
        switch (section) {
            case 'system':
                this.updateSystemSection();
                break;
            case 'calendar':
                this.updateCalendarSection();
                break;
            case 'priorities':
                this.updatePrioritiesSection();
                break;
            case 'commitments':
                this.updateCommitmentsSection();
                break;
            case 'brief':
                this.updateBriefSection();
                break;
        }
    }
    
    /**
     * Update system status section
     */
    updateSystemSection() {
        const { status, progress, last_sync } = this.state.system;
        
        // Update status display
        if (this.elements.systemStatus) {
            this.elements.systemStatus.textContent = status;
            this.elements.systemStatus.className = `status ${status.toLowerCase()}`;
        }
        
        // Update progress bar with animation
        if (this.elements.progressBar && this.elements.progressText) {
            // Animate progress changes
            const currentProgress = parseInt(this.elements.progressBar.style.width) || 0;
            
            if (currentProgress !== progress) {
                this.animateProgress(currentProgress, progress);
            }
            
            this.elements.progressText.textContent = `${progress}%`;
        }
        
        // Update last sync time
        if (this.elements.lastSync && last_sync) {
            const syncTime = new Date(last_sync);
            this.elements.lastSync.textContent = syncTime.toLocaleTimeString([], {
                hour: '2-digit',
                minute: '2-digit'
            });
        }
    }
    
    /**
     * Animate progress bar changes smoothly
     */
    animateProgress(from, to) {
        const duration = 300; // ms
        const startTime = performance.now();
        const diff = to - from;
        
        const animate = (currentTime) => {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);
            
            // Easing function for smooth animation
            const eased = 1 - Math.pow(1 - progress, 3);
            const currentValue = from + (diff * eased);
            
            this.elements.progressBar.style.width = `${currentValue}%`;
            
            if (progress < 1) {
                requestAnimationFrame(animate);
            }
        };
        
        requestAnimationFrame(animate);
    }
    
    /**
     * Update calendar section with new items
     */
    updateCalendarSection() {
        if (!this.elements.calendarItems) return;
        
        // Clear existing items efficiently
        this.elements.calendarItems.innerHTML = '';
        
        // Create document fragment for batch DOM manipulation
        const fragment = document.createDocumentFragment();
        
        this.state.calendar.forEach(item => {
            const itemElement = this.createCalendarItem(item);
            fragment.appendChild(itemElement);
        });
        
        // Single DOM update
        this.elements.calendarItems.appendChild(fragment);
    }
    
    /**
     * Create calendar item element
     */
    createCalendarItem(item) {
        const itemElement = document.createElement('div');
        itemElement.className = 'item';
        itemElement.setAttribute('data-calendar-item', item.id);
        
        // Handle different item states
        const isAlert = item.alert || false;
        const isNew = item.new || false;
        
        itemElement.innerHTML = `
            <span class="item-code">${item.id}:</span>
            <span class="time">${item.time}</span>
            <span class="${isAlert ? 'alert' : ''}">${item.title}</span>
            ${isNew ? '<span class="new">[new]</span>' : ''}
        `;
        
        // Add visual effects for new items
        if (isNew) {
            itemElement.classList.add('new-item');
        }
        
        return itemElement;
    }
    
    /**
     * Update priorities section
     */
    updatePrioritiesSection() {
        if (!this.elements.prioritiesItems) return;
        
        this.elements.prioritiesItems.innerHTML = '';
        const fragment = document.createDocumentFragment();
        
        this.state.priorities.forEach(item => {
            const itemElement = this.createPriorityItem(item);
            fragment.appendChild(itemElement);
        });
        
        this.elements.prioritiesItems.appendChild(fragment);
    }
    
    /**
     * Create priority item element
     */
    createPriorityItem(item) {
        const itemElement = document.createElement('div');
        itemElement.className = 'item';
        itemElement.setAttribute('data-priority-item', item.id);
        
        // Determine checkbox state
        let checkboxSymbol, checkboxClass;
        
        switch (item.status) {
            case 'done':
                checkboxSymbol = '[✓]';
                checkboxClass = 'checkbox done';
                itemElement.classList.add('completed');
                break;
            case 'partial':
                checkboxSymbol = '[◐]';
                checkboxClass = 'checkbox partial';
                break;
            default:
                checkboxSymbol = '[ ]';
                checkboxClass = 'checkbox';
        }
        
        const isAlert = item.alert || false;
        const isNew = item.new || false;
        
        itemElement.innerHTML = `
            <span class="item-code">${item.id}:</span>
            <span class="${checkboxClass}">${checkboxSymbol}</span>
            <span class="${isAlert ? 'alert' : ''}">${item.title}</span>
            ${isNew ? '<span class="new">[new]</span>' : ''}
        `;
        
        if (isNew) {
            itemElement.classList.add('new-item');
        }
        
        return itemElement;
    }
    
    /**
     * Update commitments section
     */
    updateCommitmentsSection() {
        // Update "I OWE" section
        if (this.elements.commitmentsOwe) {
            this.elements.commitmentsOwe.innerHTML = '';
            const oweFragment = document.createDocumentFragment();
            
            this.state.commitments.owe.forEach(item => {
                const itemElement = this.createCommitmentItem(item);
                oweFragment.appendChild(itemElement);
            });
            
            this.elements.commitmentsOwe.appendChild(oweFragment);
        }
        
        // Update "OWED TO ME" section
        if (this.elements.commitmentsOwed) {
            this.elements.commitmentsOwed.innerHTML = '';
            const owedFragment = document.createDocumentFragment();
            
            this.state.commitments.owed.forEach(item => {
                const itemElement = this.createCommitmentItem(item);
                owedFragment.appendChild(itemElement);
            });
            
            this.elements.commitmentsOwed.appendChild(owedFragment);
        }
        
        // Update summary counts
        this.updateCommitmentSummary();
    }
    
    /**
     * Create commitment item element
     */
    createCommitmentItem(item) {
        const itemElement = document.createElement('div');
        itemElement.className = 'item';
        itemElement.setAttribute('data-commitment-item', item.id);
        
        const isAlert = item.alert || false;
        const isDone = item.status === 'done';
        const isUrgent = item.urgent || false;
        
        if (isUrgent) {
            itemElement.classList.add('urgent');
        }
        
        itemElement.innerHTML = `
            <span class="item-code">${item.id}:</span>
            ${isDone ? '<span class="checkbox done">[✓]</span>' : ''}
            <span class="${isAlert ? 'alert' : ''}">${item.description}</span>
        `;
        
        return itemElement;
    }
    
    /**
     * Update commitment summary numbers
     */
    updateCommitmentSummary() {
        const dueToday = this.state.commitments.owe.filter(item => 
            item.due_date && this.isToday(item.due_date) && item.status !== 'done'
        ).length;
        
        const totalOwed = this.state.commitments.owed.filter(item => 
            item.status !== 'done'
        ).length;
        
        if (this.elements.commitDueToday) {
            this.elements.commitDueToday.textContent = dueToday;
        }
        
        if (this.elements.commitTotalOwed) {
            this.elements.commitTotalOwed.textContent = totalOwed;
        }
    }
    
    /**
     * Check if date is today
     */
    isToday(dateString) {
        const date = new Date(dateString);
        const today = new Date();
        return date.toDateString() === today.toDateString();
    }
    
    /**
     * Update active brief in main content area
     */
    updateBriefSection() {
        if (!this.elements.content) return;
        
        if (this.state.active_brief) {
            this.displayBrief(this.state.active_brief);
        }
    }
    
    /**
     * Display brief content
     */
    displayBrief(brief) {
        if (brief.html_content) {
            this.elements.content.innerHTML = brief.html_content;
        } else if (brief.text_content) {
            this.elements.content.textContent = brief.text_content;
        } else {
            // Display brief metadata if no content
            this.elements.content.innerHTML = `
                <div class="brief-title">Brief Loading...</div>
                <div class="brief-date">${brief.generated_at ? new Date(brief.generated_at).toLocaleString() : ''}</div>
                <p>Brief type: ${brief.type || 'daily'}</p>
            `;
        }
    }
    
    /**
     * Update current time display
     */
    updateCurrentTime() {
        if (!this.elements.headerTime) return;
        
        const now = new Date();
        const timeStr = now.toLocaleString('en-US', {
            weekday: 'short',
            month: 'short', 
            day: 'numeric',
            year: 'numeric',
            hour: 'numeric',
            minute: '2-digit',
            hour12: true,
            timeZoneName: 'short'
        }).toUpperCase();
        
        this.elements.headerTime.textContent = timeStr;
    }
    
    /**
     * Trigger data collection
     */
    async triggerCollection(type = 'quick') {
        try {
            console.log(`Triggering ${type} collection...`);
            this.showLoading(`Triggering ${type} collection...`);
            
            // Pass collection type as query parameter
            const response = await fetch(`http://localhost:8000/api/trigger_collection?type=${type}`, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                }
            });
            
            if (response.ok) {
                const result = await response.json();
                console.log('Collection triggered successfully:', result);
                this.showSuccess(`${type.charAt(0).toUpperCase() + type.slice(1)} collection started`);
            } else {
                const errorText = await response.text();
                console.error('Collection trigger failed:', response.status, errorText);
                throw new Error(`Collection trigger failed: ${response.status}`);
            }
            
        } catch (error) {
            console.error('Failed to trigger collection:', error);
            this.showError(`Failed to start ${type} collection: ${error.message}`);
        } finally {
            this.hideLoading();
        }
    }
    
    /**
     * Trigger dashboard refresh
     */
    async triggerRefresh() {
        try {
            this.showLoading('Refreshing dashboard...');
            
            // Reset WebSocket connection
            this.ws.reset();
            this.ws.connect();
            
            this.showSuccess('Dashboard refreshed');
            
        } catch (error) {
            console.error('Failed to refresh dashboard:', error);
            this.showError('Failed to refresh dashboard');
        } finally {
            this.hideLoading();
        }
    }
    
    /**
     * Show loading state
     */
    showLoading(message) {
        // Add loading class to appropriate elements
        if (this.elements.systemStatus) {
            this.elements.systemStatus.classList.add('loading');
        }
    }
    
    /**
     * Hide loading state
     */
    hideLoading() {
        // Remove loading class from elements
        document.querySelectorAll('.loading').forEach(element => {
            element.classList.remove('loading');
        });
    }
    
    /**
     * Show success message
     */
    showSuccess(message) {
        this.showMessage(message, 'success');
    }
    
    /**
     * Show error message
     */
    showError(message) {
        this.showMessage(message, 'error');
    }
    
    /**
     * Show message to user
     */
    showMessage(message, type) {
        // Create or update message element
        let messageElement = document.querySelector('.dashboard-message');
        
        if (!messageElement) {
            messageElement = document.createElement('div');
            messageElement.className = 'dashboard-message';
            document.body.appendChild(messageElement);
        }
        
        messageElement.textContent = message;
        messageElement.className = `dashboard-message ${type}`;
        
        // Auto-hide after delay
        setTimeout(() => {
            if (messageElement && messageElement.parentNode) {
                messageElement.parentNode.removeChild(messageElement);
            }
        }, type === 'error' ? 5000 : 3000);
    }
    
    /**
     * Handle window resize
     */
    handleResize() {
        // Could implement responsive adjustments here
        console.log('Window resized');
    }
    
    /**
     * Handle visibility changes
     */
    handleVisibilityChange() {
        if (document.hidden) {
            // Page hidden - could pause updates
            console.log('Dashboard hidden');
        } else {
            // Page visible - resume updates
            console.log('Dashboard visible');
            this.updateCurrentTime();
        }
    }
    
    /**
     * Get performance statistics
     */
    getPerformanceStats() {
        const domTimes = this.performanceMetrics.domUpdateTimes;
        const stateTimes = this.performanceMetrics.stateUpdateTimes;
        
        return {
            totalRenderTime: performance.now() - this.performanceMetrics.renderingStartTime,
            domUpdates: domTimes.length,
            averageDomUpdate: domTimes.length > 0 ? 
                domTimes.reduce((a, b) => a + b, 0) / domTimes.length : 0,
            maxDomUpdate: domTimes.length > 0 ? Math.max(...domTimes) : 0,
            stateUpdates: stateTimes.length,
            averageStateUpdate: stateTimes.length > 0 ?
                stateTimes.reduce((a, b) => a + b, 0) / stateTimes.length : 0,
            wsStats: this.ws ? this.ws.getStats() : null
        };
    }
    
    /**
     * Clean up resources
     */
    destroy() {
        if (this.ws) {
            this.ws.close();
        }
        
        // Remove event listeners
        window.removeEventListener('resize', this.handleResize);
        document.removeEventListener('visibilitychange', this.handleVisibilityChange);
        
        console.log('Dashboard application destroyed');
    }
}

// Global dashboard instance
let globalDashboardApp = null;

/**
 * Initialize global dashboard application
 */
function initializeDashboard() {
    if (globalDashboardApp) {
        globalDashboardApp.destroy();
    }
    
    globalDashboardApp = new DashboardApp();
    return globalDashboardApp;
}

/**
 * Get global dashboard instance
 */
function getDashboardApp() {
    if (!globalDashboardApp) {
        globalDashboardApp = initializeDashboard();
    }
    return globalDashboardApp;
}

// Legacy function support for tests
function updateCalendarSection(calendar) {
    const app = getDashboardApp();
    app.state.calendar = calendar;
    app.updateCalendarSection();
}

function updatePrioritiesSection(priorities) {
    const app = getDashboardApp();
    app.state.priorities = priorities;
    app.updatePrioritiesSection();
}

function updateCommitmentsSection(commitments) {
    const app = getDashboardApp();
    app.state.commitments = commitments;
    app.updateCommitmentsSection();
}

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        DashboardApp,
        initializeDashboard,
        getDashboardApp,
        updateCalendarSection,
        updatePrioritiesSection,
        updateCommitmentsSection
    };
}

// Global access for browser
window.DashboardApp = DashboardApp;
window.initializeDashboard = initializeDashboard;
window.getDashboardApp = getDashboardApp;
window.updateCalendarSection = updateCalendarSection;
window.updatePrioritiesSection = updatePrioritiesSection;
window.updateCommitmentsSection = updateCommitmentsSection;