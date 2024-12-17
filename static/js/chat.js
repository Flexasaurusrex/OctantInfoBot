document.addEventListener('DOMContentLoaded', () => {
    // UI Elements
    const messageInput = document.getElementById('message-input');
    const sendButton = document.getElementById('send-button');
    const messagesContainer = document.getElementById('messages');
    
    // Connection constants
    const MAX_RECONNECT_ATTEMPTS = 5;
    const INITIAL_RETRY_DELAY = 1000;
    
    // Socket and state management
    let socket = null;
    let isWaitingForResponse = false;
    
    function updateConnectionStatus(status) {
        const statusIndicator = document.querySelector('.status-indicator');
        const statusText = document.querySelector('.status-text');
        
        if (!statusIndicator || !statusText) return;
        
        const statusMap = {
            'connected': { text: 'Connected', class: 'connected' },
            'disconnected': { text: 'Disconnected', class: '' },
            'reconnecting': { text: 'Reconnecting...', class: '' }
        };
        
        const currentStatus = statusMap[status] || statusMap.disconnected;
        statusIndicator.className = 'status-indicator ' + currentStatus.class;
        statusText.textContent = currentStatus.text;
    }

    async function cleanupSocket(socket) {
        if (!socket) return;
        
        console.log('Cleaning up socket connection...');
        try {
            if (socket.connectionState?.monitors) {
                socket.connectionState.monitors.forEach(clearInterval);
                socket.connectionState.monitors.clear();
            }
            
            socket.removeAllListeners();
            
            if (socket.connected) {
                await new Promise((resolve) => {
                    const timeout = setTimeout(() => {
                        console.warn('Socket disconnect timeout');
                        resolve();
                    }, 5000);
                    
                    socket.once('disconnect', () => {
                        clearTimeout(timeout);
                        resolve();
                    });
                    socket.disconnect();
                });
            }
            
            socket.close();
        } catch (error) {
            console.error('Error during socket cleanup:', error);
        }
    }

    async function createSocket() {
        try {
            if (socket) {
                await cleanupSocket(socket);
            }
            
            socket = io({
                reconnection: false, // We'll handle reconnection manually
                timeout: 20000,
                transports: ['websocket', 'polling']
            });
            
            socket.connectionState = {
                attemptCount: 0,
                lastAttempt: Date.now(),
                isReconnecting: false,
                monitors: new Set()
            };
            
            const connectionMonitor = setInterval(() => {
                if (!socket?.connected && !socket?.connecting && 
                    !socket.connectionState.isReconnecting &&
                    Date.now() - socket.connectionState.lastAttempt > 5000) {
                    handleReconnection();
                }
            }, 5000);
            
            socket.connectionState.monitors.add(connectionMonitor);
            
            await initializeSocketEvents();
            return true;
        } catch (error) {
            console.error('Error creating socket:', error);
            updateConnectionStatus('disconnected');
            return false;
        }
    }

    async function handleReconnection() {
        if (!socket?.connectionState || socket.connectionState.isReconnecting) return;
        
        socket.connectionState.attemptCount++;
        socket.connectionState.isReconnecting = true;
        socket.connectionState.lastAttempt = Date.now();
        
        updateConnectionStatus('reconnecting');
        
        if (socket.connectionState.attemptCount > MAX_RECONNECT_ATTEMPTS) {
            console.error('Max reconnection attempts reached');
            updateConnectionStatus('disconnected');
            appendMessage('📡 Connection lost. Please refresh the page.', true);
            return;
        }
        
        const attempt = socket.connectionState.attemptCount;
        const baseDelay = INITIAL_RETRY_DELAY * Math.pow(2, attempt - 1);
        const jitter = Math.random() * Math.min(baseDelay * 0.1, 1000);
        const delay = baseDelay + jitter;
        
        appendMessage(`🔄 Attempting to reconnect... (${attempt}/${MAX_RECONNECT_ATTEMPTS})`, true);
        
        await new Promise(resolve => setTimeout(resolve, delay));
        
        try {
            if (await createSocket()) {
                socket.connectionState.isReconnecting = false;
                updateConnectionStatus('connected');
                appendMessage('✅ Connection restored!', true);
            }
        } catch (error) {
            console.error('Reconnection failed:', error);
            socket.connectionState.isReconnecting = false;
            handleReconnection();
        }
    }

    async function initializeSocketEvents() {
        if (!socket) return;
        
        socket.removeAllListeners();
        
        socket.on('connect', () => {
            console.log('Connected to server');
            socket.connectionState.attemptCount = 0;
            socket.connectionState.isReconnecting = false;
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
            if (reason === 'io server disconnect') {
                socket.connect();
            } else {
                handleReconnection();
            }
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
                sendButton.disabled = false;
                messageInput.disabled = false;
                messageInput.focus();
            }
        });
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
        if (isWaitingForResponse || !socket?.connected) {
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
        
        const messageTimeout = setTimeout(() => {
            if (isWaitingForResponse) {
                isWaitingForResponse = false;
                sendButton.disabled = false;
                messageInput.disabled = false;
                appendMessage('Message timed out. Please try again.', true);
            }
        }, 30000);

        socket.emit('send_message', { message }, (error) => {
            if (error) {
                clearTimeout(messageTimeout);
                isWaitingForResponse = false;
                sendButton.disabled = false;
                messageInput.disabled = false;
                appendMessage('Failed to send message. Please try again.', true);
            }
        });
    }

    // Initialize connection and UI handlers
    if (!createSocket()) {
        appendMessage('Failed to establish connection. Please refresh the page.', true);
    }

    // UI Event Listeners
    sendButton.addEventListener('click', sendMessage);

    messageInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    // Handle unhandled promise rejections
    window.addEventListener('unhandledrejection', (event) => {
        console.warn('Unhandled promise rejection:', event.reason);
        event.preventDefault();
        if (socket && !socket.connected) {
            handleReconnection();
        }
    });
});