/**
 * Chat interface JavaScript for RAG System
 */

class ChatInterface {
    constructor() {
        this.websocket = null;
        this.sessionId = null;
        this.isConnected = false;
        this.messageHistory = [];
        
        this.initializeElements();
        this.attachEventListeners();
        this.connect();
        this.loadAnalytics();
    }
    
    initializeElements() {
        this.messagesContainer = document.getElementById('messages-container');
        this.messageInput = document.getElementById('message-input');
        this.sendButton = document.getElementById('send-button');
        this.statusIndicator = document.getElementById('status-indicator');
        this.statusText = document.getElementById('status-text');
        this.typingIndicator = document.getElementById('typing-indicator');
        this.analyticsContainer = document.getElementById('analytics-summary');
        this.clearButton = document.getElementById('clear-chat');
    }
    
    attachEventListeners() {
        // Send message on button click
        this.sendButton.addEventListener('click', () => this.sendMessage());
        
        // Send message on Enter (Shift+Enter for new line)
        this.messageInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });
        
        // Auto-resize textarea
        this.messageInput.addEventListener('input', () => {
            this.messageInput.style.height = 'auto';
            this.messageInput.style.height = this.messageInput.scrollHeight + 'px';
        });
        
        // Quick action buttons
        document.querySelectorAll('.quick-action').forEach(button => {
            button.addEventListener('click', () => {
                const query = button.getAttribute('data-query');
                this.messageInput.value = query;
                this.sendMessage();
            });
        });
        
        // Example query buttons
        document.querySelectorAll('.example-query').forEach(button => {
            button.addEventListener('click', () => {
                const query = button.getAttribute('data-query');
                this.messageInput.value = query;
                this.sendMessage();
            });
        });
        
        // Clear chat
        this.clearButton.addEventListener('click', () => this.clearChat());
    }
    
    connect() {
        try {
            // Connect to the WebSocket endpoint on the main server
            const wsUrl = 'ws://localhost:8001/ws/chat';
            
            this.websocket = new WebSocket(wsUrl);
            
            this.websocket.onopen = () => {
                this.isConnected = true;
                this.updateConnectionStatus('Connected', 'green');
                console.log('WebSocket connected');
            };
            
            this.websocket.onmessage = (event) => {
                const data = JSON.parse(event.data);
                this.handleMessage(data);
            };
            
            this.websocket.onclose = () => {
                this.isConnected = false;
                this.updateConnectionStatus('Disconnected', 'red');
                console.log('WebSocket disconnected');
                
                // Attempt to reconnect after 3 seconds
                setTimeout(() => this.connect(), 3000);
            };
            
            this.websocket.onerror = (error) => {
                console.error('WebSocket error:', error);
                this.updateConnectionStatus('Error', 'red');
            };
            
        } catch (error) {
            console.error('Connection error:', error);
            this.updateConnectionStatus('Error', 'red');
        }
    }
    
    updateConnectionStatus(text, color) {
        this.statusText.textContent = text;
        this.statusIndicator.className = `w-2 h-2 bg-${color}-500 rounded-full`;
    }
    
    sendMessage() {
        const message = this.messageInput.value.trim();
        if (!message || !this.isConnected) return;
        
        // Add user message to chat
        this.addMessage('user', message);
        
        // Send to WebSocket
        this.websocket.send(JSON.stringify({
            type: 'query',
            query: message
        }));
        
        // Clear input
        this.messageInput.value = '';
        this.messageInput.style.height = 'auto';
        
        // Disable send button temporarily
        this.sendButton.disabled = true;
    }
    
    handleMessage(data) {
        switch (data.type) {
            case 'welcome':
                this.sessionId = data.session_id;
                if (data.suggestions) {
                    this.addSuggestions(data.suggestions);
                }
                break;
                
            case 'response':
                this.hideTyping();
                this.addMessage('assistant', data.answer);
                if (data.suggestions) {
                    this.addSuggestions(data.suggestions);
                }
                this.sendButton.disabled = false;
                break;
                
            case 'typing':
                if (data.is_typing) {
                    this.showTyping();
                } else {
                    this.hideTyping();
                }
                break;
                
            case 'analytics':
                this.updateAnalytics(data.summary);
                break;
                
            case 'analytics_update':
                this.updateAnalyticsCounter(data);
                break;
                
            case 'error':
                this.hideTyping();
                this.addMessage('error', data.error);
                this.sendButton.disabled = false;
                break;
        }
    }
    
    addMessage(type, content) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'flex items-start space-x-3';
        
        if (type === 'user') {
            messageDiv.innerHTML = `
                <div class="w-8 h-8 bg-gray-600 rounded-full flex items-center justify-center ml-auto">
                    <i class="fas fa-user text-white text-sm"></i>
                </div>
                <div class="bg-blue-600 text-white rounded-lg p-4 shadow-sm max-w-md ml-auto">
                    <p>${this.escapeHtml(content)}</p>
                </div>
            `;
            messageDiv.className += ' flex-row-reverse';
        } else if (type === 'assistant') {
            messageDiv.innerHTML = `
                <div class="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center">
                    <i class="fas fa-robot text-white text-sm"></i>
                </div>
                <div class="bg-white rounded-lg p-4 shadow-sm max-w-md">
                    <p class="text-gray-800">${this.formatResponse(content)}</p>
                </div>
            `;
        } else if (type === 'error') {
            messageDiv.innerHTML = `
                <div class="w-8 h-8 bg-red-600 rounded-full flex items-center justify-center">
                    <i class="fas fa-exclamation-triangle text-white text-sm"></i>
                </div>
                <div class="bg-red-50 border border-red-200 rounded-lg p-4 shadow-sm max-w-md">
                    <p class="text-red-800">${this.escapeHtml(content)}</p>
                </div>
            `;
        }
        
        this.messagesContainer.appendChild(messageDiv);
        this.scrollToBottom();
        
        // Store in history
        this.messageHistory.push({ type, content, timestamp: new Date() });
    }
    
    addSuggestions(suggestions) {
        const suggestionsDiv = document.createElement('div');
        suggestionsDiv.className = 'flex items-start space-x-3 mt-2';
        
        const suggestionsContent = suggestions.map(suggestion => 
            `<button class="suggestion-btn bg-gray-100 hover:bg-gray-200 text-gray-700 px-3 py-1 rounded-full text-sm transition-colors" 
                     data-query="${this.escapeHtml(suggestion)}">
                ${this.escapeHtml(suggestion)}
             </button>`
        ).join(' ');
        
        suggestionsDiv.innerHTML = `
            <div class="w-8 h-8"></div>
            <div class="flex flex-wrap gap-2">
                ${suggestionsContent}
            </div>
        `;
        
        this.messagesContainer.appendChild(suggestionsDiv);
        
        // Add click handlers to suggestion buttons
        suggestionsDiv.querySelectorAll('.suggestion-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const query = btn.getAttribute('data-query');
                this.messageInput.value = query;
                this.sendMessage();
            });
        });
        
        this.scrollToBottom();
    }
    
    showTyping() {
        this.typingIndicator.classList.remove('hidden');
    }
    
    hideTyping() {
        this.typingIndicator.classList.add('hidden');
    }
    
    scrollToBottom() {
        this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
    }
    
    clearChat() {
        // Keep only the welcome message
        const welcomeMessage = this.messagesContainer.firstElementChild;
        this.messagesContainer.innerHTML = '';
        this.messagesContainer.appendChild(welcomeMessage);
        
        this.messageHistory = [];
    }
    
    async loadAnalytics() {
        try {
            const response = await fetch('/api/rag/analytics/summary');
            const data = await response.json();
            this.updateAnalytics(data);
        } catch (error) {
            console.error('Failed to load analytics:', error);
        }
    }
    
    updateAnalytics(summary) {
        this.analyticsContainer.innerHTML = `
            <div class="bg-blue-50 p-3 rounded-lg">
                <div class="text-sm font-medium text-blue-800">Anomalies</div>
                <div class="text-lg font-bold text-blue-900">${summary.anomalies || 0}</div>
                <div class="text-xs text-blue-600">${summary.high_severity_anomalies || 0} high severity</div>
            </div>
            <div class="bg-green-50 p-3 rounded-lg">
                <div class="text-sm font-medium text-green-800">Active Vendors</div>
                <div class="text-lg font-bold text-green-900">${summary.vendor_count || 0}</div>
                <div class="text-xs text-green-600">This month</div>
            </div>
            <div class="bg-purple-50 p-3 rounded-lg">
                <div class="text-sm font-medium text-purple-800">Price Changes</div>
                <div class="text-lg font-bold text-purple-900">${summary.price_changes || 0}</div>
                <div class="text-xs text-purple-600">Last 30 days</div>
            </div>
        `;
    }
    
    updateAnalyticsCounter(data) {
        // Update real-time counters
        const anomaliesElement = this.analyticsContainer.querySelector('.text-blue-900');
        if (anomaliesElement) {
            anomaliesElement.textContent = data.anomalies_count || 0;
        }
    }
    
    formatResponse(text) {
        // Basic formatting for responses
        return text
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/₹(\d+(?:,\d{3})*(?:\.\d{2})?)/g, '<span class="font-semibold text-green-600">₹$1</span>')
            .replace(/\n/g, '<br>');
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Initialize chat interface when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new ChatInterface();
});
