// Agriport Chat System - Buyer Side
const API_BASE_URL = 'http://localhost:8000/api';

// Global variables
let currentConversationId = null;
let conversations = [];
let currentUser = null;
let messagePollingInterval = null;
let isTyping = false;
let typingTimeout = null;

// DOM elements
let elements = {};

document.addEventListener('DOMContentLoaded', function() {
    // Check authentication
    if (!window.BuyerAuth || !window.BuyerAuth.isAuthenticated()) {
        window.location.href = 'loginbuyer.html';
        return;
    }
    
    // Initialize chat system
    initializeChatSystem();
});

async function initializeChatSystem() {
    try {
        // Get DOM elements
        initializeElements();
        
        // Setup event listeners
        setupEventListeners();
        
        // Get current user info
        currentUser = window.BuyerAuth.getCurrentUser();
        updateUserInfo();
        
        // Load conversations
        await loadConversations();

        // Check for session storage instructions
        await handleSessionStorageInstructions();

        // Hide loading screen and show chat app
        document.getElementById('loading-screen').style.display = 'none';
        document.getElementById('chat-app').style.display = 'flex';

        console.log('Chat system initialized successfully');
    } catch (error) {
        console.error('Failed to initialize chat system:', error);
        showError('Failed to load chat system. Please refresh the page.');
    }
}

function initializeElements() {
    elements = {
        // Sidebar elements
        btnNewChat: document.getElementById('btn-new-chat'),
        btnSearch: document.getElementById('btn-search'),
        searchContainer: document.getElementById('search-container'),
        searchInput: document.getElementById('search-input'),
        btnCloseSearch: document.getElementById('btn-close-search'),
        conversationsList: document.getElementById('conversations-list'),
        
        // Main chat elements
        chatWelcome: document.getElementById('chat-welcome'),
        chatActive: document.getElementById('chat-active'),
        btnStartFirstChat: document.getElementById('btn-start-first-chat'),
        
        // Active chat elements
        participantName: document.getElementById('participant-name'),
        participantStatus: document.getElementById('participant-status'),
        messagesList: document.getElementById('messages-list'),
        messagesContainer: document.getElementById('messages-container'),
        messageInput: document.getElementById('message-input'),
        btnSend: document.getElementById('btn-send'),
        btnAttach: document.getElementById('btn-attach'),
        charCount: document.getElementById('char-count'),
        btnCloseChat: document.getElementById('btn-close-chat'),
        
        // Modal elements
        newChatModal: document.getElementById('new-chat-modal'),
        btnCloseNewChat: document.getElementById('btn-close-new-chat'),
        userSearchInput: document.getElementById('user-search-input'),
        usersList: document.getElementById('users-list')
    };
}

function setupEventListeners() {
    // Sidebar events
    elements.btnNewChat.addEventListener('click', openNewChatModal);
    elements.btnSearch.addEventListener('click', toggleSearch);
    elements.btnCloseSearch.addEventListener('click', closeSearch);
    elements.searchInput.addEventListener('input', handleConversationSearch);
    elements.btnStartFirstChat.addEventListener('click', openNewChatModal);
    
    // Chat events
    elements.btnCloseChat.addEventListener('click', closeActiveChat);
    elements.messageInput.addEventListener('input', handleMessageInput);
    elements.messageInput.addEventListener('keypress', handleMessageKeyPress);
    elements.btnSend.addEventListener('click', sendMessage);
    
    // Modal events
    elements.btnCloseNewChat.addEventListener('click', closeNewChatModal);
    elements.newChatModal.addEventListener('click', handleModalClick);
    elements.userSearchInput.addEventListener('input', handleUserSearch);
    
    // Auto-resize textarea
    elements.messageInput.addEventListener('input', autoResizeTextarea);
}

function updateUserInfo() {
    if (currentUser) {
        const userNameElement = document.querySelector('.user-name');
        if (userNameElement) {
            userNameElement.textContent = currentUser.first_name || 'Buyer';
        }
    }
}

async function loadConversations() {
    try {
        showConversationsLoading(true);
        
        const response = await window.BuyerAuth.apiRequest('/messages/conversations/', {
            method: 'GET'
        });
        
        if (response && response.ok) {
            const data = await response.json();
            if (data.success) {
                conversations = data.conversations || [];
                renderConversations(conversations);
            } else {
                throw new Error(data.error || 'Failed to load conversations');
            }
        } else {
            throw new Error('Failed to fetch conversations');
        }
    } catch (error) {
        console.error('Error loading conversations:', error);
        showError('Failed to load conversations: ' + error.message);
        renderEmptyConversations();
    } finally {
        showConversationsLoading(false);
    }
}

function renderConversations(conversationsList) {
    if (!conversationsList || conversationsList.length === 0) {
        renderEmptyConversations();
        return;
    }
    
    const html = conversationsList.map(conversation => {
        const isActive = conversation.conversation_id === currentConversationId;
        const unreadCount = conversation.unread_count || 0;
        const lastMessage = conversation.last_message || {};
        const otherParticipant = conversation.other_participant || {};
        
        // Format time
        const timeStr = conversation.last_message_time ? 
            formatMessageTime(conversation.last_message_time) : '';
        
        // Get participant initials
        const initials = getInitials(otherParticipant.name || otherParticipant.username || 'U');
        
        return `
            <div class="conversation-item ${isActive ? 'active' : ''}" 
                 data-conversation-id="${conversation.conversation_id}"
                 onclick="openConversation(${conversation.conversation_id})">
                <div class="conversation-avatar">
                    ${initials}
                </div>
                <div class="conversation-info">
                    <div class="conversation-name">
                        ${otherParticipant.name || otherParticipant.username || 'Unknown User'}
                    </div>
                    <div class="conversation-preview">
                        ${lastMessage.content ? truncateText(lastMessage.content, 50) : 'No messages yet'}
                    </div>
                </div>
                <div class="conversation-meta">
                    ${timeStr ? `<div class="conversation-time">${timeStr}</div>` : ''}
                    ${unreadCount > 0 ? `<div class="unread-badge">${unreadCount}</div>` : ''}
                </div>
            </div>
        `;
    }).join('');
    
    elements.conversationsList.innerHTML = html;
}

function renderEmptyConversations() {
    elements.conversationsList.innerHTML = `
        <div class="conversations-empty">
            <i class="fas fa-comments"></i>
            <h3>No Conversations Yet</h3>
            <p>Start chatting with farmers to discuss products and make arrangements.</p>
            <button class="btn-start-chat" onclick="openNewChatModal()">
                <i class="fas fa-plus"></i>
                Start New Chat
            </button>
        </div>
    `;
}

async function openConversation(conversationId) {
    try {
        currentConversationId = conversationId;
        
        // Update active conversation in sidebar
        updateActiveConversation();
        
        // Load conversation messages
        await loadConversationMessages(conversationId);
        
        // Show active chat
        elements.chatWelcome.style.display = 'none';
        elements.chatActive.style.display = 'flex';
        
        // Start message polling
        startMessagePolling();
        
        // Focus message input
        elements.messageInput.focus();
        
    } catch (error) {
        console.error('Error opening conversation:', error);
        showError('Failed to open conversation: ' + error.message);
    }
}

function updateActiveConversation() {
    // Remove active class from all conversations
    document.querySelectorAll('.conversation-item').forEach(item => {
        item.classList.remove('active');
    });
    
    // Add active class to current conversation
    const activeItem = document.querySelector(`[data-conversation-id="${currentConversationId}"]`);
    if (activeItem) {
        activeItem.classList.add('active');
    }
}

async function loadConversationMessages(conversationId) {
    try {
        showMessagesLoading(true);
        
        const response = await window.BuyerAuth.apiRequest(`/messages/conversation/${conversationId}/`, {
            method: 'GET'
        });
        
        if (response && response.ok) {
            const data = await response.json();
            if (data.success) {
                renderMessages(data.messages || []);
                updateChatHeader(conversationId);
            } else {
                throw new Error(data.error || 'Failed to load messages');
            }
        } else {
            throw new Error('Failed to fetch messages');
        }
    } catch (error) {
        console.error('Error loading messages:', error);
        showError('Failed to load messages: ' + error.message);
    } finally {
        showMessagesLoading(false);
    }
}

function renderMessages(messages) {
    if (!messages || messages.length === 0) {
        elements.messagesList.innerHTML = `
            <div class="messages-empty">
                <p>No messages yet. Start the conversation!</p>
            </div>
        `;
        return;
    }
    
    const html = messages.map(message => {
        const isSent = message.sender_id === currentUser.id;
        const messageClass = isSent ? 'sent' : 'received';
        const timeStr = formatMessageTime(message.created_at);
        
        return `
            <div class="message ${messageClass}">
                <div class="message-content">${escapeHtml(message.content)}</div>
                <div class="message-time">${timeStr}</div>
            </div>
        `;
    }).join('');
    
    elements.messagesList.innerHTML = html;
    scrollToBottom();
}

function updateChatHeader(conversationId) {
    const conversation = conversations.find(c => c.conversation_id === conversationId);
    if (conversation && conversation.other_participant) {
        const participant = conversation.other_participant;
        elements.participantName.textContent = participant.name || participant.username || 'Unknown User';
        elements.participantStatus.textContent = 'Online'; // TODO: Implement real status
    }
}

// Utility functions
function getInitials(name) {
    return name.split(' ').map(word => word.charAt(0).toUpperCase()).join('').substring(0, 2);
}

function formatMessageTime(timestamp) {
    const date = new Date(timestamp);
    const now = new Date();
    const diffInHours = (now - date) / (1000 * 60 * 60);
    
    if (diffInHours < 24) {
        return date.toLocaleTimeString('en-US', { 
            hour: '2-digit', 
            minute: '2-digit',
            hour12: false 
        });
    } else if (diffInHours < 168) { // 7 days
        return date.toLocaleDateString('en-US', { weekday: 'short' });
    } else {
        return date.toLocaleDateString('en-US', { 
            month: 'short', 
            day: 'numeric' 
        });
    }
}

function truncateText(text, maxLength) {
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function scrollToBottom() {
    elements.messagesContainer.scrollTop = elements.messagesContainer.scrollHeight;
}

function showConversationsLoading(show) {
    if (show) {
        elements.conversationsList.innerHTML = `
            <div class="loading-messages">
                <i class="fas fa-spinner fa-spin"></i>
                Loading conversations...
            </div>
        `;
    }
}

function showMessagesLoading(show) {
    if (show) {
        elements.messagesList.innerHTML = `
            <div class="loading-messages">
                <i class="fas fa-spinner fa-spin"></i>
                Loading messages...
            </div>
        `;
    }
}

function showError(message) {
    // Create or update error notification
    console.error('Chat Error:', message);
    // TODO: Implement proper error notification system
    alert('Error: ' + message);
}

// Message sending functionality
async function sendMessage() {
    const messageText = elements.messageInput.value.trim();

    if (!messageText || !currentConversationId) {
        return;
    }

    try {
        // Disable send button
        elements.btnSend.disabled = true;

        const response = await window.BuyerAuth.apiRequest('/messages/send/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                conversation_id: currentConversationId,
                message_text: messageText
            })
        });

        if (response && response.ok) {
            const data = await response.json();
            if (data.success) {
                // Clear input
                elements.messageInput.value = '';
                updateCharCount();
                autoResizeTextarea();

                // Add message to UI immediately
                addMessageToUI(data.message);

                // Update conversation in sidebar
                await loadConversations();
            } else {
                throw new Error(data.error || 'Failed to send message');
            }
        } else {
            throw new Error('Failed to send message');
        }
    } catch (error) {
        console.error('Error sending message:', error);
        showError('Failed to send message: ' + error.message);
    } finally {
        elements.btnSend.disabled = false;
    }
}

function addMessageToUI(message) {
    const isSent = message.sender_id === currentUser.id;
    const messageClass = isSent ? 'sent' : 'received';
    const timeStr = formatMessageTime(message.created_at);

    const messageElement = document.createElement('div');
    messageElement.className = `message ${messageClass}`;
    messageElement.innerHTML = `
        <div class="message-content">${escapeHtml(message.content)}</div>
        <div class="message-time">${timeStr}</div>
    `;

    elements.messagesList.appendChild(messageElement);
    scrollToBottom();
}

function handleMessageInput() {
    updateCharCount();

    // Handle send button state
    const hasText = elements.messageInput.value.trim().length > 0;
    elements.btnSend.disabled = !hasText;
}

function handleMessageKeyPress(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
    }
}

function updateCharCount() {
    const currentLength = elements.messageInput.value.length;
    elements.charCount.textContent = `${currentLength}/1000`;

    if (currentLength > 900) {
        elements.charCount.style.color = '#e74c3c';
    } else {
        elements.charCount.style.color = '#95a5a6';
    }
}

function autoResizeTextarea() {
    const textarea = elements.messageInput;
    textarea.style.height = 'auto';
    textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
}

// Search functionality
function toggleSearch() {
    const isVisible = elements.searchContainer.style.display !== 'none';
    elements.searchContainer.style.display = isVisible ? 'none' : 'block';

    if (!isVisible) {
        elements.searchInput.focus();
    } else {
        elements.searchInput.value = '';
        loadConversations(); // Reset conversations
    }
}

function closeSearch() {
    elements.searchContainer.style.display = 'none';
    elements.searchInput.value = '';
    loadConversations(); // Reset conversations
}

function handleConversationSearch() {
    const query = elements.searchInput.value.toLowerCase().trim();

    if (!query) {
        renderConversations(conversations);
        return;
    }

    const filteredConversations = conversations.filter(conversation => {
        const participant = conversation.other_participant || {};
        const name = (participant.name || participant.username || '').toLowerCase();
        const lastMessage = (conversation.last_message?.content || '').toLowerCase();

        return name.includes(query) || lastMessage.includes(query);
    });

    renderConversations(filteredConversations);
}

// New chat modal functionality
function openNewChatModal() {
    elements.newChatModal.style.display = 'flex';
    elements.userSearchInput.focus();
}

function closeNewChatModal() {
    elements.newChatModal.style.display = 'none';
    elements.userSearchInput.value = '';
    elements.usersList.innerHTML = '';
}

function handleModalClick(event) {
    if (event.target === elements.newChatModal) {
        closeNewChatModal();
    }
}

let userSearchTimeout;
function handleUserSearch() {
    const query = elements.userSearchInput.value.trim();

    clearTimeout(userSearchTimeout);

    if (!query) {
        elements.usersList.innerHTML = '';
        return;
    }

    userSearchTimeout = setTimeout(async () => {
        await searchUsers(query);
    }, 300);
}

async function searchUsers(query) {
    try {
        const response = await window.BuyerAuth.apiRequest(`/messages/search-users/?q=${encodeURIComponent(query)}&type=Farmer`, {
            method: 'GET'
        });

        if (response && response.ok) {
            const data = await response.json();
            if (data.success) {
                renderUserSearchResults(data.users || []);
            } else {
                throw new Error(data.error || 'Failed to search users');
            }
        } else {
            throw new Error('Failed to search users');
        }
    } catch (error) {
        console.error('Error searching users:', error);
        elements.usersList.innerHTML = `
            <div style="padding: 1rem; text-align: center; color: #e74c3c;">
                Failed to search users: ${error.message}
            </div>
        `;
    }
}

function renderUserSearchResults(users) {
    if (users.length === 0) {
        elements.usersList.innerHTML = `
            <div style="padding: 1rem; text-align: center; color: #7f8c8d;">
                No farmers found matching your search.
            </div>
        `;
        return;
    }

    const html = users.map(user => {
        const initials = getInitials(user.name || user.username);

        return `
            <div class="user-item" onclick="startConversationWithUser(${user.user_id})">
                <div class="user-item-avatar">
                    ${initials}
                </div>
                <div class="user-item-info">
                    <div class="user-item-name">${user.name || user.username}</div>
                    <div class="user-item-username">@${user.username}</div>
                </div>
                <div class="user-item-type">${user.user_type}</div>
            </div>
        `;
    }).join('');

    elements.usersList.innerHTML = html;
}

async function startConversationWithUser(userId) {
    try {
        const response = await window.BuyerAuth.apiRequest('/messages/conversations/start/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                recipient_id: userId,
                conversation_type: 'direct',
                initial_message: 'Hello! I\'m interested in your products.'
            })
        });

        if (response && response.ok) {
            const data = await response.json();
            if (data.success) {
                closeNewChatModal();
                await loadConversations();
                await openConversation(data.conversation_id);
            } else {
                throw new Error(data.error || 'Failed to start conversation');
            }
        } else {
            throw new Error('Failed to start conversation');
        }
    } catch (error) {
        console.error('Error starting conversation:', error);
        showError('Failed to start conversation: ' + error.message);
    }
}

// Chat management
function closeActiveChat() {
    currentConversationId = null;
    stopMessagePolling();

    elements.chatActive.style.display = 'none';
    elements.chatWelcome.style.display = 'flex';

    // Remove active class from conversations
    document.querySelectorAll('.conversation-item').forEach(item => {
        item.classList.remove('active');
    });
}

// Message polling for real-time updates
function startMessagePolling() {
    stopMessagePolling();

    messagePollingInterval = setInterval(async () => {
        if (currentConversationId) {
            await loadConversationMessages(currentConversationId);
        }
    }, 5000); // Poll every 5 seconds
}

function stopMessagePolling() {
    if (messagePollingInterval) {
        clearInterval(messagePollingInterval);
        messagePollingInterval = null;
    }
}

// Handle session storage instructions from dashboard
async function handleSessionStorageInstructions() {
    try {
        // Check if we should open a specific conversation
        const openConversationId = sessionStorage.getItem('openConversationId');
        if (openConversationId) {
            sessionStorage.removeItem('openConversationId');
            await openConversation(parseInt(openConversationId));
            return;
        }

        // Check if we should start a chat with a specific farmer
        const startChatWithFarmerId = sessionStorage.getItem('startChatWithFarmerId');
        if (startChatWithFarmerId) {
            sessionStorage.removeItem('startChatWithFarmerId');
            await startConversationWithUser(parseInt(startChatWithFarmerId));
            return;
        }
    } catch (error) {
        console.error('Error handling session storage instructions:', error);
    }
}

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    stopMessagePolling();
});

// Export functions for global access
window.openConversation = openConversation;
window.openNewChatModal = openNewChatModal;
window.closeNewChatModal = closeNewChatModal;
window.startConversationWithUser = startConversationWithUser;
window.handleSessionStorageInstructions = handleSessionStorageInstructions;
