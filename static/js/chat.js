document.addEventListener('DOMContentLoaded', () => {
    const messageInput = document.getElementById('message-input');
    const sendButton = document.getElementById('send-button');
    const messagesContainer = document.getElementById('messages');
    let isWaitingForResponse = false;
    let socket = null;
    let reconnectAttempts = 0;
    const MAX_RECONNECT_ATTEMPTS = 5;
    const INITIAL_RETRY_DELAY = 1000;

    // Initialize with welcome message
    appendMessage("👋 Hello! I'm the Octant Information Bot. I'm here to help you learn about Octant, GLM tokens, and everything related to the platform. Feel free to ask me anything!", true);

    function updateConnectionStatus(status) {
        const statusIndicator = document.querySelector('.status-indicator');
        const statusText = document.querySelector('.status-text');
        
        if (!statusIndicator || !statusText) return;
        
        const statusMap = {
            'connected': { text: 'Connected', class: 'connected' },
            'disconnected': { text: 'Disconnected', class: 'disconnected' },
            'reconnecting': { text: 'Reconnecting...', class: 'reconnecting' }
        };
        
        const currentStatus = statusMap[status] || statusMap.disconnected;
        statusIndicator.className = 'status-indicator ' + currentStatus.class;
        statusText.textContent = currentStatus.text;
    }

    function createSocket() {
        if (socket) {
            socket.disconnect();
        }

        socket = io({
            reconnection: true,
            reconnectionAttempts: MAX_RECONNECT_ATTEMPTS,
            reconnectionDelay: INITIAL_RETRY_DELAY,
            reconnectionDelayMax: 5000,
            timeout: 20000,
            transports: ['websocket', 'polling']
        });

        socket.on('connect', () => {
            console.log('Connected to server');
            reconnectAttempts = 0;
            updateConnectionStatus('connected');
            const errorDiv = document.querySelector('.connection-error');
            if (errorDiv) {
                errorDiv.remove();
            }
        });

        socket.on('connect_error', (error) => {
            console.warn('Connection error:', error);
            handleReconnection();
        });

        socket.on('disconnect', (reason) => {
            console.warn('Disconnected:', reason);
            updateConnectionStatus('disconnected');
            handleReconnection();
        });

        socket.on('error', (error) => {
            console.error('Socket error:', error);
            handleReconnection();
        });

        socket.on('receive_message', (data) => {
            try {
                appendMessage(data.message, data.is_bot);
            } catch (error) {
                console.error('Error processing received message:', error);
                appendMessage('Error displaying message', true);
            } finally {
                isWaitingForResponse = false;
                sendButton.disabled = false;
                messageInput.disabled = false;
                messageInput.focus();
            }
        });
    }

    function handleReconnection() {
        if (reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) {
            console.error('Max reconnection attempts reached');
            updateConnectionStatus('disconnected');
            appendMessage('Connection lost. Please refresh the page to reconnect.', true);
            return;
        }

        reconnectAttempts++;
        updateConnectionStatus('reconnecting');
        
        setTimeout(() => {
            createSocket();
        }, INITIAL_RETRY_DELAY * Math.pow(2, reconnectAttempts - 1));
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

    function sendMessage() {
        if (isWaitingForResponse || !socket || !socket.connected) {
            console.warn('Cannot send message: Socket not ready or waiting for response');
            return;
        }
        
        const message = messageInput.value.trim();
        if (!message) return;
        
        appendMessage(message);
        messageInput.value = '';
        
        isWaitingForResponse = true;
        sendButton.disabled = true;
        messageInput.disabled = true;
        
        socket.emit('send_message', { message }, (error) => {
            if (error) {
                isWaitingForResponse = false;
                sendButton.disabled = false;
                messageInput.disabled = false;
                appendMessage('Failed to send message. Please try again.', true);
            }
        });
    }

    // Initialize socket
    createSocket();

    // UI Event Listeners
    sendButton.addEventListener('click', sendMessage);

    messageInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
});
