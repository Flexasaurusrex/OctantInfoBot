document.addEventListener('DOMContentLoaded', () => {
    let socket = null;
    let reconnectAttempts = 0;
    const MAX_RECONNECT_ATTEMPTS = 5;
    const INITIAL_RETRY_DELAY = 1000;
    const messageInput = document.getElementById('message-input');
    const sendButton = document.getElementById('send-button');
    const messagesContainer = document.getElementById('messages');
    let isWaitingForResponse = false;

    function createSocket() {
        try {
            // Close any existing connections
            if (socket) {
                socket.close();
            }
            
            socket = io({
                reconnection: true,
                reconnectionAttempts: MAX_RECONNECT_ATTEMPTS,
                reconnectionDelay: INITIAL_RETRY_DELAY,
                reconnectionDelayMax: 5000,
                timeout: 20000,
                transports: ['websocket', 'polling'],  // Fallback to polling if websocket fails
                upgrade: true,  // Allow transport upgrade
                autoConnect: true,
                forceNew: true,
                reconnectionDelayMax: 10000,  // Increased max delay
                randomizationFactor: 0.5,  // Add randomization to prevent thundering herd
                pingTimeout: 30000,  // Increased ping timeout
                pingInterval: 10000  // More frequent ping checks
            });

            initializeSocketEvents();
            return true;
        } catch (error) {
            console.error('Error creating socket:', error);
            return false;
        }
    }

    function handleReconnection() {
        reconnectAttempts++;
        if (reconnectAttempts <= MAX_RECONNECT_ATTEMPTS) {
            console.log(`Attempting to reconnect (${reconnectAttempts}/${MAX_RECONNECT_ATTEMPTS})...`);
            
            // Enhanced exponential backoff with jitter
            const baseDelay = INITIAL_RETRY_DELAY * Math.pow(2, reconnectAttempts - 1);
            const maxJitter = Math.min(baseDelay * 0.25, 2000); // Up to 25% jitter, max 2s
            const jitter = Math.random() * maxJitter;
            const delay = Math.min(baseDelay + jitter, 15000); // Cap at 15 seconds
            
            updateConnectionStatus('reconnecting');
            appendMessage(`Attempting to reconnect in ${(delay/1000).toFixed(1)} seconds...`, true);
            
            // Graceful cleanup of existing connection
            if (socket) {
                try {
                    socket.removeAllListeners();
                    socket.close();
                } catch (e) {
                    console.warn('Error during socket cleanup:', e);
                }
            }
            
            setTimeout(() => {
                try {
                    if (createSocket()) {
                        console.log('Socket recreated successfully');
                        socket.on('connect', () => {
                            reconnectAttempts = 0;
                            console.log('Connection restored');
                            updateConnectionStatus('connected');
                            appendMessage('Connection restored! You can continue chatting.', true);
                        });
                    } else {
                        console.error('Failed to recreate socket');
                        updateConnectionStatus('disconnected');
                        handleReconnection();
                    }
                } catch (error) {
                    console.error('Error during socket recreation:', error);
                    updateConnectionStatus('disconnected');
                    handleReconnection();
                }
            }, delay);
        } else {
            console.error('Max reconnection attempts reached');
            updateConnectionStatus('disconnected');
            appendMessage('Unable to restore connection after multiple attempts. The page will refresh in 5 seconds...', true);
            setTimeout(() => {
                window.location.reload();
            }, 5000);
        }
    }

    function initializeSocketEvents() {
        if (!socket) {
            console.error('Cannot initialize events: Socket is null');
            return;
        }

        socket.on('connect', () => {
            console.log('Connected to server');
            reconnectAttempts = 0;
            updateConnectionStatus('connected');
            const errorDiv = document.querySelector('.connection-error');
            if (errorDiv) {
                errorDiv.remove();
            }
        });

        function updateConnectionStatus(status) {
            let statusDiv = document.getElementById('connection-status');
            if (!statusDiv) {
                statusDiv = document.createElement('div');
                statusDiv.id = 'connection-status';
                document.body.insertBefore(statusDiv, document.body.firstChild);
            }
            
            const statusMap = {
                'connected': { text: '🟢 Connected', color: '#4CAF50' },
                'disconnected': { text: '🔴 Disconnected', color: '#f44336' },
                'reconnecting': { text: '🟡 Reconnecting...', color: '#ff9800' }
            };
            
            const currentStatus = statusMap[status] || statusMap.disconnected;
            statusDiv.textContent = currentStatus.text;
            statusDiv.style.cssText = `
                position: fixed;
                top: 60px;
                right: 10px;
                padding: 8px 16px;
                background-color: ${currentStatus.color};
                color: white;
                border-radius: 20px;
                font-weight: bold;
                z-index: 1000;
                transition: all 0.3s ease;
                box-shadow: 0 2px 4px rgba(0,0,0,0.2);
                font-size: 14px;
            `;
        }

        socket.on('connect_error', (error) => {
            console.warn('Connection error:', error);
            if (!document.querySelector('.connection-error')) {
                const errorDiv = document.createElement('div');
                errorDiv.className = 'message bot-message connection-error';
                errorDiv.innerHTML = 'Connection lost. Attempting to reconnect...';
                messagesContainer.appendChild(errorDiv);
                messagesContainer.scrollTop = messagesContainer.scrollHeight;
            }
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

        socket.on('reconnect_attempt', (attemptNumber) => {
            console.log(`Reconnection attempt ${attemptNumber}/${MAX_RECONNECT_ATTEMPTS}`);
            updateConnectionStatus('reconnecting');
            appendMessage(`Attempting to reconnect (${attemptNumber}/${MAX_RECONNECT_ATTEMPTS})...`, true);
        });

        socket.on('reconnect', (attemptNumber) => {
            console.log('Reconnected after', attemptNumber, 'attempts');
            reconnectAttempts = 0;
            const errorDiv = document.querySelector('.connection-error');
            if (errorDiv) {
                errorDiv.remove();
            }
            appendMessage('Connection restored!', true);
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

    function triggerConfetti() {
        confetti({
            particleCount: 100,
            spread: 70,
            origin: { y: 0.6 },
            colors: ['#ff0000', '#00ff00', '#0000ff'],
            disableForReducedMotion: true
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

        if (isBot && message.includes('✅ Correct! Well done!')) {
            triggerConfetti();
        }
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

    // Initialize socket and UI event listeners
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

    // Trivia click handlers
    messagesContainer.addEventListener('click', (e) => {
        const triviaOption = e.target.closest('.trivia-option');
        if (triviaOption && !isWaitingForResponse) {
            const option = triviaOption.dataset.option;
            if (option) {
                messageInput.value = option;
                sendMessage();
            }
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