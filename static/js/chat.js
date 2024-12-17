document.addEventListener('DOMContentLoaded', () => {
    // UI Elements
    const messageInput = document.getElementById('message-input');
    const sendButton = document.getElementById('send-button');
    const messagesContainer = document.getElementById('messages');
    const statusIndicator = document.querySelector('.status-indicator');
    const statusText = document.querySelector('.status-text');
    
    // Global state
    let socket = null;
    let isWaitingForResponse = false;
    
    function updateConnectionStatus(status) {
        if (!statusIndicator || !statusText) return;
        
        const statusMap = {
            'connected': { text: 'Connected', class: 'connected' },
            'disconnected': { text: 'Disconnected', class: 'disconnected' },
            'connecting': { text: 'Connecting...', class: 'connecting' }
        };
        
        const currentStatus = statusMap[status] || statusMap.disconnected;
        statusIndicator.className = 'status-indicator ' + currentStatus.class;
        statusText.textContent = currentStatus.text;
    }

    function appendMessage(message, isBot = false) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${isBot ? 'bot-message' : 'user-message'}`;
        
        if (isBot) {
            const botAvatar = document.createElement('img');
            botAvatar.src = '/static/images/2.png';
            botAvatar.className = 'bot-avatar';
            messageDiv.appendChild(botAvatar);
        }

        const messageContent = document.createElement('span');
        messageContent.innerHTML = message;
        messageDiv.appendChild(messageContent);
        
        messagesContainer.appendChild(messageDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    function enableMessageInput() {
        messageInput.disabled = false;
        sendButton.disabled = false;
        messageInput.focus();
    }

    function disableMessageInput() {
        messageInput.disabled = true;
        sendButton.disabled = true;
    }

    function initializeSocket() {
        if (socket) {
            socket.disconnect();
            socket.removeAllListeners();
        }

        socket = io({
            transports: ['websocket'],
            reconnection: true,
            reconnectionAttempts: 5,
            reconnectionDelay: 1000
        });

        socket.on('connect', () => {
            console.log('Connected to server');
            updateConnectionStatus('connected');
            enableMessageInput();
            appendMessage('✅ Connected to server', true);
        });

        socket.on('disconnect', () => {
            console.log('Disconnected from server');
            updateConnectionStatus('disconnected');
            disableMessageInput();
            appendMessage('❌ Disconnected from server', true);
        });

        socket.on('connect_error', (error) => {
            console.error('Connection error:', error);
            updateConnectionStatus('disconnected');
        });

        socket.on('receive_message', (data) => {
            try {
                appendMessage(data.message, data.is_bot);
            } catch (error) {
                console.error('Error processing message:', error);
                appendMessage('Error displaying message', true);
            } finally {
                isWaitingForResponse = false;
                enableMessageInput();
            }
        });
    }

    function sendMessage() {
        if (isWaitingForResponse || !socket?.connected) {
            console.warn('Cannot send message: Socket not ready or waiting for response');
            return;
        }
        
        const message = messageInput.value.trim();
        if (!message) return;
        
        appendMessage(message);
        messageInput.value = '';
        
        isWaitingForResponse = true;
        disableMessageInput();
        
        socket.emit('send_message', { message }, (error) => {
            if (error) {
                console.error('Error sending message:', error);
                isWaitingForResponse = false;
                enableMessageInput();
                appendMessage('Failed to send message. Please try again.', true);
            }
        });

        // Add timeout for message response
        setTimeout(() => {
            if (isWaitingForResponse) {
                isWaitingForResponse = false;
                enableMessageInput();
                appendMessage('Message timed out. Please try again.', true);
            }
        }, 30000);
    }

    // Initialize connection
    initializeSocket();

    // Event Listeners
    sendButton.addEventListener('click', sendMessage);

    messageInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
});