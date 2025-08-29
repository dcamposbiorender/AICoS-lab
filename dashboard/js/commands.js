/**
 * Command Manager - Interactive command system for AI Chief of Staff Dashboard
 * 
 * References:
 * - Backend command API: /Users/david.campos/VibeCode/AICoS-Lab/backend/api_routes.py
 * - Command parsing logic: _parse_command function in api_routes.py
 * - Test requirements: /Users/david.campos/VibeCode/AICoS-Lab/tests/dashboard/test_frontend.html
 * 
 * Features:
 * - Command input with Enter key execution
 * - Command history navigation with up/down arrows
 * - Auto-completion with Tab key
 * - Real-time suggestions dropdown
 * - Command result display with visual feedback
 * - Local storage for command history persistence
 * - Performance optimized API calls
 */

class CommandManager {
    constructor(apiBaseUrl = 'http://localhost:8000') {
        this.apiBaseUrl = apiBaseUrl;
        this.history = this.loadCommandHistory();
        this.historyIndex = this.history.length;
        this.currentSuggestionIndex = -1;
        this.isExecuting = false;
        
        // Command suggestions - matches backend command parser
        this.suggestions = [
            // Approve commands
            'approve P1', 'approve P2', 'approve P3', 'approve P4', 'approve P5',
            'approve P6', 'approve P7', 'approve P8', 'approve P9', 'approve P10',
            
            // Brief commands  
            'brief daily', 'brief weekly', 'brief C1', 'brief C2', 'brief C3', 'brief C4',
            
            // System commands
            'refresh', 'status', 'status details',
            
            // Quick actions
            'quick', 'full',
            
            // Search commands
            'search keyword', 'search person:name', 'search date:today'
        ];
        
        // Performance tracking
        this.stats = {
            commandsExecuted: 0,
            averageResponseTime: 0,
            responseTimes: [],
            lastExecutionTime: null
        };
        
        // Initialize the command system
        this.init();
    }
    
    /**
     * Initialize command input system
     */
    init() {
        this.input = document.querySelector('.command-input');
        
        if (!this.input) {
            console.error('Command input element not found');
            return;
        }
        
        // Set up event listeners
        this.initializeEventListeners();
        
        // Set initial placeholder with examples
        this.updatePlaceholder();
        
        console.log('Command Manager initialized');
    }
    
    /**
     * Initialize all event listeners
     */
    initializeEventListeners() {
        // Enter key for command execution
        this.input.addEventListener('keypress', this.handleKeyPress.bind(this));
        
        // Arrow keys and Tab for navigation and completion
        this.input.addEventListener('keydown', this.handleKeyDown.bind(this));
        
        // Input changes for suggestions
        this.input.addEventListener('input', this.handleInput.bind(this));
        
        // Focus and blur events
        this.input.addEventListener('focus', this.handleFocus.bind(this));
        this.input.addEventListener('blur', this.handleBlur.bind(this));
        
        // Click outside to hide suggestions
        document.addEventListener('click', (event) => {
            if (!this.input.contains(event.target)) {
                this.hideSuggestions();
            }
        });
    }
    
    /**
     * Handle key press events (primarily Enter)
     */
    async handleKeyPress(event) {
        if (event.key === 'Enter' && !this.isExecuting) {
            event.preventDefault();
            const command = this.input.value.trim();
            
            if (command) {
                await this.executeCommand(command);
                this.addToHistory(command);
                this.input.value = '';
                this.historyIndex = this.history.length;
                this.hideSuggestions();
            }
        }
    }
    
    /**
     * Handle key down events (arrows, Tab, Escape)
     */
    handleKeyDown(event) {
        switch (event.key) {
            case 'ArrowUp':
                event.preventDefault();
                this.navigateHistory('up');
                break;
                
            case 'ArrowDown':
                event.preventDefault();
                this.navigateHistory('down');
                break;
                
            case 'Tab':
                event.preventDefault();
                this.handleTabCompletion();
                break;
                
            case 'Escape':
                this.input.value = '';
                this.historyIndex = this.history.length;
                this.hideSuggestions();
                break;
                
            case 'Enter':
                // Handle suggestion selection
                if (this.currentSuggestionIndex >= 0) {
                    event.preventDefault();
                    this.selectSuggestion(this.currentSuggestionIndex);
                }
                break;
        }
    }
    
    /**
     * Handle input changes for real-time suggestions
     */
    handleInput(event) {
        const value = this.input.value;
        this.currentSuggestionIndex = -1;
        
        if (value.length >= 2) {
            this.showSuggestions(value);
        } else {
            this.hideSuggestions();
        }
    }
    
    /**
     * Handle input focus
     */
    handleFocus() {
        this.input.placeholder = 'Type command and press Enter...';
    }
    
    /**
     * Handle input blur
     */
    handleBlur() {
        // Delay hiding suggestions to allow for clicks
        setTimeout(() => {
            if (document.activeElement !== this.input) {
                this.hideSuggestions();
                this.updatePlaceholder();
            }
        }, 150);
    }
    
    /**
     * Navigate command history
     */
    navigateHistory(direction) {
        if (direction === 'up' && this.historyIndex > 0) {
            this.historyIndex--;
            this.input.value = this.history[this.historyIndex];
            this.setCursorToEnd();
            
        } else if (direction === 'down') {
            if (this.historyIndex < this.history.length - 1) {
                this.historyIndex++;
                this.input.value = this.history[this.historyIndex];
            } else if (this.historyIndex === this.history.length - 1) {
                this.historyIndex++;
                this.input.value = '';
            }
            this.setCursorToEnd();
        }
        
        this.hideSuggestions();
    }
    
    /**
     * Handle Tab completion
     */
    handleTabCompletion() {
        const partial = this.input.value.toLowerCase();
        const matches = this.suggestions.filter(cmd => 
            cmd.toLowerCase().startsWith(partial)
        );
        
        if (matches.length === 1) {
            // Single match - complete it
            this.input.value = matches[0];
            this.setCursorToEnd();
            this.hideSuggestions();
            
        } else if (matches.length > 1) {
            // Multiple matches - show dropdown and complete common prefix
            const commonPrefix = this.findCommonPrefix(matches);
            if (commonPrefix.length > partial.length) {
                this.input.value = commonPrefix;
                this.setCursorToEnd();
            }
            this.showSuggestionsDropdown(matches);
        }
    }
    
    /**
     * Find common prefix among suggestions
     */
    findCommonPrefix(suggestions) {
        if (suggestions.length === 0) return '';
        
        let prefix = suggestions[0];
        
        for (let i = 1; i < suggestions.length; i++) {
            while (suggestions[i].indexOf(prefix) !== 0 && prefix.length > 0) {
                prefix = prefix.substring(0, prefix.length - 1);
            }
        }
        
        return prefix;
    }
    
    /**
     * Show suggestions based on input value
     */
    showSuggestions(value) {
        const lowerValue = value.toLowerCase();
        const matches = this.suggestions.filter(cmd =>
            cmd.toLowerCase().includes(lowerValue)
        ).slice(0, 8); // Limit to 8 suggestions for performance
        
        if (matches.length > 0) {
            this.showSuggestionsDropdown(matches);
        } else {
            this.hideSuggestions();
        }
    }
    
    /**
     * Show suggestions dropdown
     */
    showSuggestionsDropdown(suggestions) {
        let dropdown = document.querySelector('.command-suggestions');
        
        if (!dropdown) {
            dropdown = document.createElement('div');
            dropdown.className = 'command-suggestions';
            this.input.parentElement.style.position = 'relative';
            this.input.parentElement.appendChild(dropdown);
        }
        
        dropdown.innerHTML = suggestions.map((suggestion, index) => 
            `<div class="suggestion-item ${index === this.currentSuggestionIndex ? 'selected' : ''}" 
                 data-index="${index}">${this.highlightMatch(suggestion)}</div>`
        ).join('');
        
        // Add click handlers
        dropdown.querySelectorAll('.suggestion-item').forEach((item, index) => {
            item.addEventListener('click', () => {
                this.selectSuggestion(index);
            });
        });
        
        dropdown.style.display = 'block';
    }
    
    /**
     * Highlight matching text in suggestions
     */
    highlightMatch(suggestion) {
        const value = this.input.value.toLowerCase();
        const index = suggestion.toLowerCase().indexOf(value);
        
        if (index >= 0) {
            return suggestion.substring(0, index) + 
                   '<strong>' + suggestion.substring(index, index + value.length) + '</strong>' +
                   suggestion.substring(index + value.length);
        }
        
        return suggestion;
    }
    
    /**
     * Select suggestion by index
     */
    selectSuggestion(index) {
        const dropdown = document.querySelector('.command-suggestions');
        if (dropdown) {
            const items = dropdown.querySelectorAll('.suggestion-item');
            if (items[index]) {
                this.input.value = items[index].textContent;
                this.setCursorToEnd();
                this.hideSuggestions();
                this.input.focus();
            }
        }
    }
    
    /**
     * Hide suggestions dropdown
     */
    hideSuggestions() {
        const dropdown = document.querySelector('.command-suggestions');
        if (dropdown) {
            dropdown.style.display = 'none';
        }
        this.currentSuggestionIndex = -1;
    }
    
    /**
     * Execute command via API
     */
    async executeCommand(command) {
        this.isExecuting = true;
        this.showLoading(true);
        
        const startTime = performance.now();
        
        try {
            const response = await fetch(`${this.apiBaseUrl}/api/command`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ command })
            });
            
            const endTime = performance.now();
            const responseTime = endTime - startTime;
            
            // Track performance
            this.trackPerformance(responseTime);
            
            if (response.ok) {
                const result = await response.json();
                this.showCommandResult(command, result, 'success');
                
                // Log successful execution
                console.log(`Command executed: ${command} -> ${JSON.stringify(result)}`);
                
            } else {
                const error = await response.json();
                this.showCommandResult(command, error, 'error');
                
                console.warn(`Command failed: ${command} -> ${JSON.stringify(error)}`);
            }
            
        } catch (error) {
            console.error('Command execution failed:', error);
            this.showCommandResult(command, { error: error.message }, 'error');
        } finally {
            this.isExecuting = false;
            this.showLoading(false);
        }
    }
    
    /**
     * Track command execution performance
     */
    trackPerformance(responseTime) {
        this.stats.commandsExecuted++;
        this.stats.responseTimes.push(responseTime);
        this.stats.lastExecutionTime = new Date().toISOString();
        
        // Keep only last 100 response times
        if (this.stats.responseTimes.length > 100) {
            this.stats.responseTimes = this.stats.responseTimes.slice(-100);
        }
        
        // Calculate average
        this.stats.averageResponseTime = 
            this.stats.responseTimes.reduce((a, b) => a + b, 0) / this.stats.responseTimes.length;
        
        // Log slow responses
        if (responseTime > 1000) {
            console.warn(`Slow command response: ${responseTime.toFixed(2)}ms`);
        }
    }
    
    /**
     * Show command execution result
     */
    showCommandResult(command, result, type) {
        let resultArea = document.querySelector('.command-result');
        
        if (!resultArea) {
            resultArea = this.createResultArea();
        }
        
        resultArea.className = `command-result ${type}`;
        resultArea.innerHTML = `
            <div class="result-command">&gt; ${command}</div>
            <div class="result-message">${this.formatResult(result)}</div>
        `;
        
        // Show result with animation
        resultArea.style.display = 'block';
        
        // Auto-hide success messages after 3 seconds
        if (type === 'success') {
            setTimeout(() => {
                if (resultArea && resultArea.style.display !== 'none') {
                    resultArea.style.opacity = '0';
                    setTimeout(() => {
                        resultArea.style.display = 'none';
                        resultArea.style.opacity = '1';
                    }, 300);
                }
            }, 3000);
        }
    }
    
    /**
     * Format command result for display
     */
    formatResult(result) {
        if (result.error) {
            return `Error: ${result.error}`;
        } else if (result.action) {
            const target = result.target ? ` ${result.target}` : '';
            return `Executed: ${result.action}${target}`;
        } else if (result.success) {
            return result.message || 'Command executed successfully';
        } else {
            return 'Command completed';
        }
    }
    
    /**
     * Create command result display area
     */
    createResultArea() {
        const resultArea = document.createElement('div');
        resultArea.className = 'command-result';
        resultArea.style.display = 'none';
        
        const commandContainer = this.input.parentElement;
        commandContainer.appendChild(resultArea);
        
        return resultArea;
    }
    
    /**
     * Show loading state
     */
    showLoading(show) {
        if (show) {
            this.input.disabled = true;
            this.input.classList.add('loading');
            this.previousPlaceholder = this.input.placeholder;
            this.input.placeholder = 'Executing command...';
            
        } else {
            this.input.disabled = false;
            this.input.classList.remove('loading');
            if (this.previousPlaceholder) {
                this.input.placeholder = this.previousPlaceholder;
                this.previousPlaceholder = null;
            } else {
                this.updatePlaceholder();
            }
        }
    }
    
    /**
     * Update input placeholder with examples
     */
    updatePlaceholder() {
        const examples = ['approve P7', 'refresh', 'brief daily'];
        const randomExample = examples[Math.floor(Math.random() * examples.length)];
        this.input.placeholder = `> ${randomExample} | Type command here...`;
    }
    
    /**
     * Set cursor to end of input
     */
    setCursorToEnd() {
        setTimeout(() => {
            this.input.setSelectionRange(this.input.value.length, this.input.value.length);
        }, 0);
    }
    
    /**
     * Add command to history
     */
    addToHistory(command) {
        // Don't add duplicates of the last command
        if (this.history.length === 0 || this.history[this.history.length - 1] !== command) {
            this.history.push(command);
            
            // Keep history size reasonable
            if (this.history.length > 100) {
                this.history = this.history.slice(-50);
            }
            
            this.saveCommandHistory();
        }
    }
    
    /**
     * Load command history from localStorage
     */
    loadCommandHistory() {
        try {
            const stored = localStorage.getItem('aicos_command_history');
            return stored ? JSON.parse(stored) : [];
        } catch (error) {
            console.warn('Failed to load command history:', error);
            return [];
        }
    }
    
    /**
     * Save command history to localStorage
     */
    saveCommandHistory() {
        try {
            localStorage.setItem('aicos_command_history', JSON.stringify(this.history));
        } catch (error) {
            console.warn('Failed to save command history:', error);
        }
    }
    
    /**
     * Get command execution statistics
     */
    getStats() {
        return {
            commandsExecuted: this.stats.commandsExecuted,
            averageResponseTime: parseFloat(this.stats.averageResponseTime.toFixed(2)),
            historySize: this.history.length,
            lastExecutionTime: this.stats.lastExecutionTime,
            suggestionsAvailable: this.suggestions.length
        };
    }
    
    /**
     * Clear command history
     */
    clearHistory() {
        this.history = [];
        this.historyIndex = 0;
        this.saveCommandHistory();
        console.log('Command history cleared');
    }
    
    /**
     * Add custom suggestion
     */
    addSuggestion(suggestion) {
        if (!this.suggestions.includes(suggestion)) {
            this.suggestions.push(suggestion);
            this.suggestions.sort();
        }
    }
    
    /**
     * Destroy command manager
     */
    destroy() {
        if (this.input) {
            this.input.removeEventListener('keypress', this.handleKeyPress);
            this.input.removeEventListener('keydown', this.handleKeyDown);
            this.input.removeEventListener('input', this.handleInput);
            this.input.removeEventListener('focus', this.handleFocus);
            this.input.removeEventListener('blur', this.handleBlur);
        }
        
        this.hideSuggestions();
        
        console.log('Command Manager destroyed');
    }
}

// Global command manager instance
let globalCommandManager = null;

/**
 * Initialize global command manager
 */
function initializeCommandManager(apiBaseUrl) {
    if (globalCommandManager) {
        globalCommandManager.destroy();
    }
    
    globalCommandManager = new CommandManager(apiBaseUrl);
    return globalCommandManager;
}

/**
 * Get global command manager instance
 */
function getCommandManager() {
    if (!globalCommandManager) {
        globalCommandManager = new CommandManager();
    }
    return globalCommandManager;
}

// Legacy function support for tests
function executeCommand(command) {
    const manager = getCommandManager();
    return manager.executeCommand(command);
}

function handleCommandHistory(event, input) {
    const manager = getCommandManager();
    if (event.key === 'ArrowUp') {
        manager.navigateHistory('up');
    } else if (event.key === 'ArrowDown') {
        manager.navigateHistory('down');
    }
}

function autoCompleteCommand(input) {
    const manager = getCommandManager();
    manager.handleTabCompletion();
}

function showLoading(show) {
    const manager = getCommandManager();
    manager.showLoading(show);
}

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        CommandManager,
        initializeCommandManager,
        getCommandManager,
        executeCommand,
        handleCommandHistory,
        autoCompleteCommand,
        showLoading
    };
}

// Global access for browser
window.CommandManager = CommandManager;
window.initializeCommandManager = initializeCommandManager;
window.getCommandManager = getCommandManager;
window.executeCommand = executeCommand;
window.handleCommandHistory = handleCommandHistory;
window.autoCompleteCommand = autoCompleteCommand;
window.showLoading = showLoading;