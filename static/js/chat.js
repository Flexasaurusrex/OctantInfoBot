document.addEventListener('DOMContentLoaded', () => {
    // UI Elements
    const messageInput = document.getElementById('message-input');
    const sendButton = document.getElementById('send-button');
    const messagesContainer = document.getElementById('messages');
    
    // Connection constants
    const MAX_RECONNECT_ATTEMPTS = 5;
    const INITIAL_RETRY_DELAY = 1000;
    
    // Global state
    let socket = null;
    let isWaitingForResponse = false;
    let reconnectAttempts = 0;
    let connectionTimeout = null;
    
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

    async function cleanupSocket() {
        if (!socket) return;
        
        console.log('Cleaning up socket connection...');
        try {
            clearTimeout(connectionTimeout);
            
            if (socket.connected) {
                socket.disconnect();
            }
            
            socket.removeAllListeners();
            socket.close();
            socket = null;
        } catch (error) {
            console.error('Error during socket cleanup:', error);
        }
    }

    async function initializeSocket() {
        try {
            await cleanupSocket();
            
            socket = io({
                reconnection: false,
                timeout: 20000,
                transports: ['websocket']
            });
            
            socket.on('connect', () => {
                console.log('Connected to server');
                reconnectAttempts = 0;
                updateConnectionStatus('connected');
                appendMessage('✅ Connected to server', true);
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
                    console.error('Error processing message:', error);
                    appendMessage('Error displaying message', true);
                } finally {
                    isWaitingForResponse = false;
                    enableMessageInput();
                }
            });
            
            return true;
        } catch (error) {
            console.error('Error initializing socket:', error);
            updateConnectionStatus('disconnected');
            return false;
        }
    }

    async function handleReconnection() {
        if (!socket || reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) {
            console.error('Max reconnection attempts reached');
            updateConnectionStatus('disconnected');
            appendMessage('📡 Connection lost. Please refresh the page.', true);
            return;
        }
        
        reconnectAttempts++;
        updateConnectionStatus('reconnecting');
        
        const baseDelay = INITIAL_RETRY_DELAY * Math.pow(2, reconnectAttempts - 1);
        const jitter = Math.random() * Math.min(baseDelay * 0.1, 1000);
        const delay = baseDelay + jitter;
        
        appendMessage(`🔄 Attempting to reconnect... (${reconnectAttempts}/${MAX_RECONNECT_ATTEMPTS})`, true);
        
        await new Promise(resolve => setTimeout(resolve, delay));
        
        if (await initializeSocket()) {
            updateConnectionStatus('connected');
            appendMessage('✅ Connection restored!', true);
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

    function disableMessageInput() {
        sendButton.disabled = true;
        messageInput.disabled = true;
    }

    function enableMessageInput() {
        sendButton.disabled = false;
        messageInput.disabled = false;
        messageInput.focus();
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
        
        connectionTimeout = setTimeout(() => {
            if (isWaitingForResponse) {
                isWaitingForResponse = false;
                enableMessageInput();
                appendMessage('Message timed out. Please try again.', true);
            }
        }, 30000);

        socket.emit('send_message', { message }, (error) => {
            if (error) {
                clearTimeout(connectionTimeout);
                isWaitingForResponse = false;
                enableMessageInput();
                appendMessage('Failed to send message. Please try again.', true);
            }
        });
    }

    // Initialize connection
    if (!initializeSocket()) {
        appendMessage('Failed to establish connection. Please refresh the page.', true);
    }

    // Event Listeners
    sendButton.addEventListener('click', sendMessage);

    messageInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    // Handle unhandled promise rejections
    window.addEventListener('unhandledrejection', (event) => {
        console.error('Unhandled promise rejection:', event.reason);
        if (!socket?.connected) {
            handleReconnection();
        }
    });
});