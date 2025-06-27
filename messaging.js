// Buyer-Farmer Communication System for Agriport
// Handles bidirectional messaging between buyers and farmers

class MessagingSystem {
    constructor() {
        this.conversations = [];
        this.currentConversation = null;
        this.userType = Auth.getUserType(); // 'Farmer' or 'Buyer'
        this.userId = Auth.getUserId();
        this.websocket = null;
        this.messageContainer = null;
        this.isInitialized = false;
        
        this.init();
    }
    
    init() {
        this.createMessagingInterface();
        this.loadConversations();
        this.initializeWebSocket();
        this.setupEventListeners();
        this.isInitialized = true;
        
        console.log('Messaging system initialized for:', this.userType);
    }
    
    createMessagingInterface() {
        // Create messaging modal if it doesn't exist
        if (!document.getElementById('messagingModal')) {
            const modal = document.createElement('div');
            modal.id = 'messagingModal';
            modal.className = 'messaging-modal hidden';
            modal.innerHTML = this.getMessagingModalHTML();
            document.body.appendChild(modal);
        }
        
        this.messageContainer = document.getElementById('messagingModal');
    }
    
    getMessagingModalHTML() {
        return `
            <div class="messaging-overlay">
                <div class="messaging-container">
                    <div class="messaging-header">
                        <h3><i class="fas fa-comments"></i> Messages</h3>
                        <button id="closeMessaging" class="btn-close">
                            <i class="fas fa-times"></i>
                        </button>
                    </div>
                    
                    <div class="messaging-content">
                        <!-- Conversations List -->
                        <div class="conversations-panel">
                            <div class="conversations-header">
                                <h4>Conversations</h4>
                                <button id="newMessageBtn" class="btn-new-message">
                                    <i class="fas fa-plus"></i> New
                                </button>
                            </div>
                            <div class="conversations-search">
                                <input type="text" id="conversationSearch" placeholder="Search conversations...">
                            </div>
                            <div class="conversations-list" id="conversationsList">
                                <div class="loading">Loading conversations...</div>
                            </div>
                        </div>
                        
                        <!-- Chat Panel -->
                        <div class="chat-panel">
                            <div class="chat-header" id="chatHeader">
                                <div class="chat-info">
                                    <div class="chat-avatar">
                                        <i class="fas fa-user"></i>
                                    </div>
                                    <div class="chat-details">
                                        <div class="chat-name">Select a conversation</div>
                                        <div class="chat-status">to start messaging</div>
                                    </div>
                                </div>
                                <div class="chat-actions">
                                    <button id="chatOptionsBtn" class="btn-options">
                                        <i class="fas fa-ellipsis-v"></i>
                                    </button>
                                </div>
                            </div>
                            
                            <div class="messages-container" id="messagesContainer">
                                <div class="no-conversation">
                                    <i class="fas fa-comments"></i>
                                    <p>Select a conversation to start messaging</p>
                                </div>
                            </div>
                            
                            <div class="message-input-container" id="messageInputContainer">
                                <div class="message-input">
                                    <input type="text" id="messageInput" placeholder="Type your message..." disabled>
                                    <button id="sendMessageBtn" class="btn-send" disabled>
                                        <i class="fas fa-paper-plane"></i>
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }
    
    setupEventListeners() {
        // Close modal
        document.addEventListener('click', (e) => {
            if (e.target.id === 'closeMessaging' || e.target.classList.contains('messaging-overlay')) {
                this.hideMessaging();
            }
        });
        
        // New message button
        document.addEventListener('click', (e) => {
            if (e.target.id === 'newMessageBtn') {
                this.showNewMessageDialog();
            }
        });
        
        // Send message
        document.addEventListener('click', (e) => {
            if (e.target.id === 'sendMessageBtn') {
                this.sendMessage();
            }
        });
        
        // Enter key to send message
        document.addEventListener('keypress', (e) => {
            if (e.target.id === 'messageInput' && e.key === 'Enter') {
                this.sendMessage();
            }
        });
        
        // Conversation search
        document.addEventListener('input', (e) => {
            if (e.target.id === 'conversationSearch') {
                this.filterConversations(e.target.value);
            }
        });
        
        // Conversation selection
        document.addEventListener('click', (e) => {
            if (e.target.closest('.conversation-item')) {
                const conversationId = e.target.closest('.conversation-item').dataset.conversationId;
                this.selectConversation(conversationId);
            }
        });
    }
    
    initializeWebSocket() {
        const wsUrl = `ws://localhost:8000/ws/messages/${this.userType.toLowerCase()}/${this.userId}/`;
        
        try {
            this.websocket = new WebSocket(wsUrl);
            
            this.websocket.onopen = () => {
                console.log('Messaging WebSocket connected');
            };
            
            this.websocket.onmessage = (event) => {
                const data = JSON.parse(event.data);
                this.handleNewMessage(data);
            };
            
            this.websocket.onclose = () => {
                console.log('Messaging WebSocket disconnected, attempting to reconnect...');
                setTimeout(() => this.initializeWebSocket(), 5000);
            };
            
            this.websocket.onerror = (error) => {
                console.error('Messaging WebSocket error:', error);
            };
        } catch (error) {
            console.error('Failed to initialize messaging WebSocket:', error);
        }
    }
    
    async loadConversations() {
        try {
            const response = await fetch(`/api/messages/conversations`, {
                headers: {
                    'Authorization': `Bearer ${Auth.getToken()}`
                }
            });
            
            if (response.ok) {
                const data = await response.json();
                this.conversations = data.conversations || [];
                this.renderConversations();
            }
        } catch (error) {
            console.error('Error loading conversations:', error);
        }
    }
    
    renderConversations() {
        const listContainer = document.getElementById('conversationsList');
        if (!listContainer) return;
        
        if (this.conversations.length === 0) {
            listContainer.innerHTML = `
                <div class="no-conversations">
                    <i class="fas fa-comment-slash"></i>
                    <p>No conversations yet</p>
                    <small>Start a conversation with a ${this.userType === 'Farmer' ? 'buyer' : 'farmer'}</small>
                </div>
            `;
            return;
        }
        
        listContainer.innerHTML = this.conversations.map(conversation => 
            this.getConversationItemHTML(conversation)
        ).join('');
    }
    
    getConversationItemHTML(conversation) {
        const otherUser = conversation.participants.find(p => p.id !== this.userId);
        const lastMessage = conversation.lastMessage;
        const timeAgo = this.getTimeAgo(lastMessage?.timestamp);
        const unreadCount = conversation.unreadCount || 0;
        
        return `
            <div class="conversation-item ${conversation.id === this.currentConversation?.id ? 'active' : ''}" 
                 data-conversation-id="${conversation.id}">
                <div class="conversation-avatar">
                    <img src="${otherUser.avatar || '../assets/default-profile.jpg'}" alt="${otherUser.name}">
                    <div class="status-indicator ${otherUser.isOnline ? 'online' : 'offline'}"></div>
                </div>
                <div class="conversation-info">
                    <div class="conversation-header">
                        <div class="conversation-name">${otherUser.name}</div>
                        <div class="conversation-time">${timeAgo}</div>
                    </div>
                    <div class="conversation-preview">
                        <div class="last-message">
                            ${lastMessage ? (lastMessage.senderId === this.userId ? 'You: ' : '') + lastMessage.content : 'No messages yet'}
                        </div>
                        ${unreadCount > 0 ? `<div class="unread-badge">${unreadCount}</div>` : ''}
                    </div>
                </div>
            </div>
        `;
    }
    
    async selectConversation(conversationId) {
        try {
            const conversation = this.conversations.find(c => c.id === conversationId);
            if (!conversation) return;
            
            this.currentConversation = conversation;
            
            // Update UI
            this.updateChatHeader(conversation);
            this.enableMessageInput();
            
            // Load messages
            await this.loadMessages(conversationId);
            
            // Mark as read
            await this.markConversationAsRead(conversationId);
            
            // Update conversation list
            this.renderConversations();
            
        } catch (error) {
            console.error('Error selecting conversation:', error);
        }
    }
    
    updateChatHeader(conversation) {
        const otherUser = conversation.participants.find(p => p.id !== this.userId);
        const chatHeader = document.getElementById('chatHeader');
        
        chatHeader.querySelector('.chat-name').textContent = otherUser.name;
        chatHeader.querySelector('.chat-status').textContent = otherUser.isOnline ? 'Online' : 'Last seen recently';
        chatHeader.querySelector('.chat-avatar img')?.setAttribute('src', otherUser.avatar || '../assets/default-profile.jpg');
    }
    
    enableMessageInput() {
        const messageInput = document.getElementById('messageInput');
        const sendBtn = document.getElementById('sendMessageBtn');
        
        messageInput.disabled = false;
        messageInput.placeholder = 'Type your message...';
        sendBtn.disabled = false;
    }
    
    async loadMessages(conversationId) {
        try {
            const response = await fetch(`/api/messages/conversations/${conversationId}/messages`, {
                headers: {
                    'Authorization': `Bearer ${Auth.getToken()}`
                }
            });
            
            if (response.ok) {
                const data = await response.json();
                this.renderMessages(data.messages || []);
            }
        } catch (error) {
            console.error('Error loading messages:', error);
        }
    }
    
    renderMessages(messages) {
        const container = document.getElementById('messagesContainer');
        
        container.innerHTML = messages.map(message => 
            this.getMessageHTML(message)
        ).join('');
        
        // Scroll to bottom
        container.scrollTop = container.scrollHeight;
    }
    
    getMessageHTML(message) {
        const isOwn = message.senderId === this.userId;
        const time = new Date(message.timestamp).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
        
        return `
            <div class="message ${isOwn ? 'own' : 'other'}">
                <div class="message-content">
                    <div class="message-text">${message.content}</div>
                    <div class="message-time">${time}</div>
                </div>
                ${isOwn ? `<div class="message-status ${message.status}">
                    <i class="fas fa-${message.status === 'sent' ? 'check' : message.status === 'delivered' ? 'check-double' : 'check-double'}"></i>
                </div>` : ''}
            </div>
        `;
    }
    
    async sendMessage() {
        const messageInput = document.getElementById('messageInput');
        const content = messageInput.value.trim();
        
        if (!content || !this.currentConversation) return;
        
        try {
            const response = await fetch('/api/messages/send', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${Auth.getToken()}`
                },
                body: JSON.stringify({
                    conversationId: this.currentConversation.id,
                    content: content
                })
            });
            
            if (response.ok) {
                const data = await response.json();
                
                // Add message to UI immediately
                this.addMessageToUI(data.message);
                
                // Clear input
                messageInput.value = '';
                
                // Update conversation list
                this.updateConversationLastMessage(data.message);
                
            } else {
                throw new Error('Failed to send message');
            }
        } catch (error) {
            console.error('Error sending message:', error);
            showNotification('Failed to send message', 'error');
        }
    }
    
    addMessageToUI(message) {
        const container = document.getElementById('messagesContainer');
        const messageHTML = this.getMessageHTML(message);
        
        container.insertAdjacentHTML('beforeend', messageHTML);
        container.scrollTop = container.scrollHeight;
    }
    
    updateConversationLastMessage(message) {
        const conversation = this.conversations.find(c => c.id === message.conversationId);
        if (conversation) {
            conversation.lastMessage = message;
            this.renderConversations();
        }
    }
    
    handleNewMessage(data) {
        // Add to current conversation if it's the active one
        if (this.currentConversation && data.conversationId === this.currentConversation.id) {
            this.addMessageToUI(data.message);
            
            // Mark as read immediately if conversation is active
            this.markConversationAsRead(data.conversationId);
        } else {
            // Update conversation list with new message
            this.updateConversationLastMessage(data.message);
            
            // Show notification
            this.showMessageNotification(data.message, data.sender);
        }
    }
    
    showMessageNotification(message, sender) {
        if (window.notificationSystem) {
            window.notificationSystem.handleRealTimeNotification({
                id: `msg_${message.id}`,
                type: 'message',
                title: `New message from ${sender.name}`,
                message: message.content,
                senderId: sender.id,
                createdAt: message.timestamp
            });
        }
    }
    
    async markConversationAsRead(conversationId) {
        try {
            await fetch(`/api/messages/conversations/${conversationId}/read`, {
                method: 'PUT',
                headers: {
                    'Authorization': `Bearer ${Auth.getToken()}`
                }
            });
        } catch (error) {
            console.error('Error marking conversation as read:', error);
        }
    }
    
    async showNewMessageDialog() {
        // This would show a dialog to select a user to message
        // For now, we'll implement a simple prompt
        const recipientType = this.userType === 'Farmer' ? 'buyer' : 'farmer';
        const recipientId = prompt(`Enter ${recipientType} ID to start a conversation:`);
        
        if (recipientId) {
            await this.startNewConversation(recipientId);
        }
    }
    
    async startNewConversation(recipientId) {
        try {
            const response = await fetch('/api/messages/conversations/start', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${Auth.getToken()}`
                },
                body: JSON.stringify({
                    recipientId: recipientId
                })
            });
            
            if (response.ok) {
                const data = await response.json();
                
                // Add to conversations list
                this.conversations.unshift(data.conversation);
                this.renderConversations();
                
                // Select the new conversation
                this.selectConversation(data.conversation.id);
                
            } else {
                throw new Error('Failed to start conversation');
            }
        } catch (error) {
            console.error('Error starting conversation:', error);
            showNotification('Failed to start conversation', 'error');
        }
    }
    
    filterConversations(searchTerm) {
        const items = document.querySelectorAll('.conversation-item');
        
        items.forEach(item => {
            const name = item.querySelector('.conversation-name').textContent.toLowerCase();
            const lastMessage = item.querySelector('.last-message').textContent.toLowerCase();
            
            if (name.includes(searchTerm.toLowerCase()) || lastMessage.includes(searchTerm.toLowerCase())) {
                item.style.display = 'flex';
            } else {
                item.style.display = 'none';
            }
        });
    }
    
    showMessaging() {
        this.messageContainer.classList.remove('hidden');
        this.loadConversations(); // Refresh when opened
    }
    
    hideMessaging() {
        this.messageContainer.classList.add('hidden');
    }
    
    getTimeAgo(timestamp) {
        if (!timestamp) return '';
        
        const now = new Date();
        const time = new Date(timestamp);
        const diffInSeconds = Math.floor((now - time) / 1000);
        
        if (diffInSeconds < 60) return 'now';
        if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)}m`;
        if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)}h`;
        if (diffInSeconds < 604800) return `${Math.floor(diffInSeconds / 86400)}d`;
        return time.toLocaleDateString();
    }
    
    // Static method to open messaging with specific user
    static openConversationWith(userId, userName) {
        if (window.messagingSystem) {
            window.messagingSystem.showMessaging();
            
            // Find existing conversation or start new one
            const existingConversation = window.messagingSystem.conversations.find(c => 
                c.participants.some(p => p.id === userId)
            );
            
            if (existingConversation) {
                window.messagingSystem.selectConversation(existingConversation.id);
            } else {
                window.messagingSystem.startNewConversation(userId);
            }
        }
    }
}

// Initialize messaging system when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Initialize messaging system if user is authenticated
    if (Auth.isAuthenticated()) {
        window.messagingSystem = new MessagingSystem();
    }
});

// Export for use in other modules
window.MessagingSystem = MessagingSystem;
