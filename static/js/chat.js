document.addEventListener('DOMContentLoaded', () => {
    const messageInput = document.getElementById('message-input');
    const sendButton = document.getElementById('send-button');
    const messagesContainer = document.getElementById('messages');
    let isWaitingForResponse = false;
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

    const socket = io({
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
        console.log('Received message:', data);
        try {
            if (!data) {
                throw new Error('No data received from server');
            }

            if (typeof data !== 'object') {
                throw new Error('Invalid message format received');
            }

            if (data.error) {
                console.error('Error from server:', data.error);
                appendMessage('Sorry, I encountered an error. Please try again.', true);
                return;
            }

            if (!data.message) {
                throw new Error('Message content is missing');
            }

            appendMessage(data.message, data.is_bot || false);
        } catch (error) {
            console.error('Error processing received message:', error);
            appendMessage('Error: ' + error.message, true);
        } finally {
            isWaitingForResponse = false;
            sendButton.disabled = false;
            messageInput.disabled = false;
            messageInput.focus();
        }
    });

    // Enhanced error handling for socket events
    socket.on('error', (error) => {
        console.error('Socket error:', error);
        appendMessage('Connection error occurred. Please try again.', true);
        updateConnectionStatus('disconnected');
    });

    socket.on('connect_error', (error) => {
        console.error('Connection error:', error);
        appendMessage('Failed to connect to server. Please refresh the page.', true);
        updateConnectionStatus('disconnected');
    });

    // Add handler for connection status
    socket.on('bot_status', (data) => {
        console.log('Bot status:', data);
        updateConnectionStatus(data.status);
    });

    function handleReconnection() {
        if (reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) {
            console.error('Max reconnection attempts reached');
            updateConnectionStatus('disconnected');
            appendMessage('Connection lost. Please refresh the page to reconnect.', true);
            return;
        }

        reconnectAttempts++;
        updateConnectionStatus('reconnecting');
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
        if (isWaitingForResponse || !socket.connected) {
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
                console.error('Message send error:', error);
                isWaitingForResponse = false;
                sendButton.disabled = false;
                messageInput.disabled = false;
                appendMessage('Failed to send message. Please try again.', true);
            } else {
                console.log('Message sent successfully');
            }
        });
    }

    // UI Event Listeners
    sendButton.addEventListener('click', sendMessage);

    messageInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
});