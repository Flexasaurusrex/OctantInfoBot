document.addEventListener('DOMContentLoaded', () => {
    // UI Elements
    const messageInput = document.getElementById('message-input');
    const sendButton = document.getElementById('send-button');
    const messagesContainer = document.getElementById('messages');
    const statusIndicator = document.querySelector('.status-indicator');
    const statusText = document.querySelector('.status-text');
    
    // Initialize socket with basic configuration
    const socket = io({
        transports: ['websocket'],
        reconnection: true,
        reconnectionAttempts: 3
    });

    function updateConnectionStatus(connected) {
        if (!statusIndicator || !statusText) return;
        
        if (connected) {
            statusIndicator.className = 'status-indicator connected';
            statusText.textContent = 'Connected to server';
        } else {
            statusIndicator.className = 'status-indicator disconnected';
            statusText.textContent = 'Disconnected';
        }
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

    // Socket event handlers
    socket.on('connect', () => {
        console.log('Connected to server');
        updateConnectionStatus(true);
        messageInput.disabled = false;
        sendButton.disabled = false;
    });

    socket.on('disconnect', () => {
        console.log('Disconnected from server');
        updateConnectionStatus(false);
        messageInput.disabled = true;
        sendButton.disabled = true;
    });

    socket.on('receive_message', (data) => {
        try {
            appendMessage(data.message, data.is_bot);
            messageInput.disabled = false;
            sendButton.disabled = false;
        } catch (error) {
            console.error('Error displaying message:', error);
        }
    });

    // Send message function
    function sendMessage() {
        const message = messageInput.value.trim();
        if (!message || !socket.connected) return;
        
        appendMessage(message);
        messageInput.value = '';
        messageInput.disabled = true;
        sendButton.disabled = true;
        
        socket.emit('send_message', { message });
    }

    // Event listeners
    sendButton.addEventListener('click', sendMessage);
    messageInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
});