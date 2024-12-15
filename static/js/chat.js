document.addEventListener('DOMContentLoaded', () => {
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
            // Cleanup existing socket
            if (socket) {
                try {
                    socket.removeAllListeners();
                    socket.close();
                    socket.disconnect();
                } catch (e) {
                    console.warn('Error cleaning up existing socket:', e);
                }
            }
            
            socket = io({
                reconnection: true,
                reconnectionAttempts: MAX_RECONNECT_ATTEMPTS,
                reconnectionDelay: INITIAL_RETRY_DELAY,
                reconnectionDelayMax: 5000,
                timeout: 20000,
                transports: ['websocket', 'polling']
            });

            // Add connection state monitoring
            let connectionMonitor = setInterval(() => {
                if (socket && !socket.connected && !socket.connecting) {
                    console.log('Connection monitor: detected disconnection');
                    handleReconnection();
                }
            }, 10000);

            // Track connection state
            socket.connectionState = {
                lastAttempt: Date.now(),
                attemptCount: 0,
                lastError: null,
                isReconnecting: false
            };

            initializeSocketEvents();
            
            // Monitor socket health
            const healthCheck = setInterval(() => {
                if (socket && !socket.connected && !socket.connectionState.isReconnecting) {
                    console.warn('Socket health check failed - initiating reconnection');
                    handleReconnection();
                }
            }, 30000);

            socket.on('close', () => {
                clearInterval(healthCheck);
            });

            return true;
        } catch (error) {
            console.error('Error creating socket:', error);
            updateConnectionStatus('disconnected');
            return false;
        }
    }

    async function handleReconnection() {
        if (socket && socket.connectionState.isReconnecting) {
            console.warn('Reconnection already in progress');
            return;
        }

        socket.connectionState.attemptCount++;
        socket.connectionState.isReconnecting = true;
        socket.connectionState.lastAttempt = Date.now();
        
        updateConnectionStatus('reconnecting');
        
        if (socket.connectionState.attemptCount > MAX_RECONNECT_ATTEMPTS) {
            console.error('Max reconnection attempts reached');
            updateConnectionStatus('disconnected');
            appendMessage('🔄 Connection lost. Maximum retry attempts reached.', true);
            appendMessage('⚡ Attempting emergency recovery...', true);
            
            try {
                // Enhanced recovery process
                await cleanupConnection();
                const response = await fetch('/restart', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    signal: AbortSignal.timeout(10000) // 10s timeout
                });
                
                if (response.ok) {
                    const data = await response.json();
                    appendMessage(`✨ ${data.message || 'Recovery initiated'}. Page will refresh in 5 seconds...`, true);
                    await new Promise(resolve => setTimeout(resolve, 5000));
                    window.location.reload();
                } else {
                    throw new Error(`Recovery failed: ${response.statusText}`);
                }
            } catch (error) {
                console.error('Recovery error:', error);
                appendMessage('❌ Recovery failed. Please refresh the page manually.', true);
                appendMessage(`Error details: ${error.message}`, true);
                
                // Attempt one final reconnect after a longer delay
                await new Promise(resolve => setTimeout(resolve, 10000));
                createSocket();
            } finally {
                socket.connectionState.isReconnecting = false;
            }
            return;
        }

        console.log(`Attempting to reconnect (${reconnectAttempts}/${MAX_RECONNECT_ATTEMPTS})...`);
        
        // Enhanced exponential backoff with jitter
        const baseDelay = INITIAL_RETRY_DELAY * Math.pow(2, reconnectAttempts - 1);
        const maxJitter = Math.min(baseDelay * 0.25, 2000);
        const jitter = Math.random() * maxJitter;
        const delay = Math.min(baseDelay + jitter, 15000);
        
        updateConnectionStatus('reconnecting');
        appendMessage(`📡 Reconnecting in ${(delay/1000).toFixed(1)} seconds... (Attempt ${reconnectAttempts}/${MAX_RECONNECT_ATTEMPTS})`, true);
        
        // Cleanup existing connection
        if (socket) {
            try {
                socket.removeAllListeners();
                await new Promise(resolve => {
                    socket.once('disconnect', resolve);
                    socket.close();
                });
            } catch (e) {
                console.warn('Error during socket cleanup:', e);
            }
        }
        
        // Wait for the backoff delay
        await new Promise(resolve => setTimeout(resolve, delay));
        
        try {
            if (createSocket()) {
                // Wait for connection or timeout
                await Promise.race([
                    new Promise((resolve, reject) => {
                        socket.once('connect', () => {
                            reconnectAttempts = 0;
                            console.log('Connection restored');
                            updateConnectionStatus('connected');
                            appendMessage('✅ Connection restored! You can continue chatting.', true);
                            resolve();
                        });
                        socket.once('connect_error', reject);
                    }),
                    new Promise((_, reject) => setTimeout(() => reject(new Error('Connection timeout')), 5000))
                ]);
            } else {
                throw new Error('Failed to recreate socket');
            }
        } catch (error) {
            console.error('Error during reconnection:', error);
            updateConnectionStatus('disconnected');
            handleReconnection();
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

    // Enhanced restart functionality with better state management
    socket.on('restart_status', (data) => {
        const restartBtn = document.querySelector('#restartButton');
        if (!restartBtn) return;

        if (data.status === 'restarting') {
            restartBtn.classList.add('restarting');
            restartBtn.disabled = true;
            appendMessage('🔄 Restarting services... Please wait.', true);
            setTimeout(() => {
                appendMessage('⚡ Services restarting, page will refresh in 5 seconds...', true);
                setTimeout(() => {
                    window.location.reload();
                }, 5000);
            }, 1000);
        } else if (data.status === 'error') {
            restartBtn.classList.remove('restarting');
            restartBtn.disabled = false;
            appendMessage('❌ Restart failed: ' + (data.message || 'Unknown error'), true);
        }
    });
});

// Global appendMessage function for restart functionality
function appendMessage(message, isBot = false) {
    const messagesContainer = document.getElementById('messages');
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

document.addEventListener('DOMContentLoaded', () => {
    // Initialize restart button functionality
    const restartButton = document.getElementById('restartButton');
    if (restartButton) {
        restartButton.addEventListener('click', async () => {
            if (!confirm('Are you sure you want to restart all services? This will briefly interrupt the connection.')) {
                return;
            }

            try {
                console.log('Initiating restart process...');
                restartButton.classList.add('restarting');
                restartButton.disabled = true;
                appendMessage('🔄 Initiating service restart...', true);

                // Send restart request
                const response = await fetch('/restart', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' }
                });

                if (!response.ok) {
                    throw new Error(`Restart failed: ${response.statusText}`);
                }

                // Show restart progress
                appendMessage('📡 Disconnecting services...', true);
                if (socket) {
                    socket.disconnect();
                }

                // Sequential restart process with visual feedback
                await new Promise(resolve => setTimeout(resolve, 1000));
                appendMessage('⚡ Restarting services...', true);
                
                await new Promise(resolve => setTimeout(resolve, 2000));
                appendMessage('🔄 Page will refresh in 5 seconds...', true);
                
                await new Promise(resolve => setTimeout(resolve, 5000));
                window.location.reload();

            } catch (error) {
                console.error('Restart error:', error);
                restartButton.classList.remove('restarting');
                restartButton.disabled = false;
                appendMessage(`❌ Restart failed: ${error.message}`, true);
            }
        });
    }

    // Listen for restart status updates using the main socket
    socket.on('restart_status', (data) => {
        console.log('Received restart status:', data);
        const restartBtn = document.querySelector('.sidebar-button');
        
        if (data.status === 'restarting') {
            restartBtn.classList.add('restarting');
            restartBtn.disabled = true;
            appendMessage(data.message || 'Restarting services...', true);
        } else if (data.status === 'error') {
            restartBtn.classList.remove('restarting');
            restartBtn.disabled = false;
            appendMessage(data.message || 'Restart failed. Please try again.', true);
        }
    });
});

async function restartServices(socket) {
    const restartBtn = document.querySelector('.sidebar-button');
    if (!restartBtn || restartBtn.classList.contains('restarting')) return;

    try {
        if (!confirm('Are you sure you want to restart all services? This will briefly interrupt the chat.')) {
            return;
        }

        // Disable button and show restarting state
        restartBtn.classList.add('restarting');
        restartBtn.disabled = true;

        // Update connection status
        updateConnectionStatus('reconnecting');
        
        // Disconnect existing socket connections
        if (socket) {
            socket.disconnect();
        }

        // Show countdown
        for (let i = 5; i > 0; i--) {
            appendMessage(`🔄 Restarting services in ${i} seconds...`, true);
            await new Promise(resolve => setTimeout(resolve, 1000));
        }

        // Send restart request
        const response = await fetch('/restart', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        if (!response.ok) {
            throw new Error(`Restart request failed: ${response.statusText}`);
        }

        // Show progress messages
        const steps = [
            '📡 Disconnecting active connections...',
            '🔄 Preparing services for restart...',
            '⚡ Restarting all services...',
            '🔁 Initializing new connections...',
            '✅ Services restarted successfully!'
        ];

        for (const step of steps) {
            appendMessage(step, true);
            await new Promise(resolve => setTimeout(resolve, 1000));
        }

        appendMessage('🔄 Refreshing page to complete restart...', true);
        
        // Wait briefly before refresh
        await new Promise(resolve => setTimeout(resolve, 3000));
        
        // Reload the page
        window.location.reload();

    } catch (error) {
        console.error('Restart error:', error);
        
        // Reset button state
        restartBtn.classList.remove('restarting');
        restartBtn.disabled = false;
        
        // Show error message
        appendMessage('❌ Failed to restart services. Please try again.', true);
        appendMessage(`Error details: ${error.message}`, true);
        
        // Attempt to restore connection
        updateConnectionStatus('disconnected');
        handleReconnection();
    }
}