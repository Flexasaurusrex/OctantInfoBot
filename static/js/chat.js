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

    // Add restart functionality
    socket.on('restart_status', (data) => {
        const restartBtn = document.querySelector('.restart-button');
        if (data.status === 'restarting') {
            restartBtn.classList.add('restarting');
            restartBtn.disabled = true;
            appendMessage('Restarting services... The page will refresh in 5 seconds.', true);
            setTimeout(() => {
                window.location.reload();
            }, 5000);
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

function restartServices() {
    const restartBtn = document.querySelector('.restart-button');
    const messagesContainer = document.getElementById('messages');
    
    if (restartBtn.classList.contains('restarting')) return;

    if (confirm('Are you sure you want to restart all services? This will briefly interrupt the chat.')) {
        restartBtn.classList.add('restarting');
        restartBtn.disabled = true;
        
        let countdown = 5;
        const messages = [];
        
        function updateCountdown() {
            if (countdown > 0) {
                const msg = `Services will restart in ${countdown} seconds...`;
                appendMessage(msg, true);
                messages.push(msg);
                countdown--;
                setTimeout(updateCountdown, 1500); // Longer delay between countdown messages
            } else {
                const initMsg = '🔄 Initiating restart process...';
                appendMessage(initMsg, true);
                messages.push(initMsg);
                
                fetch('/restart', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    }
                }).then(response => {
                    if (!response.ok) throw new Error('Restart request failed');
                    
                    const steps = [
                        '📡 Cleaning up connections...',
                        '🔄 Preparing services for restart...',
                        '⚡ Restarting services...',
                        '🔄 Page will refresh in 5 seconds...'
                    ];
                    
                    let stepIndex = 0;
                    function showStep() {
                        if (stepIndex < steps.length) {
                            appendMessage(steps[stepIndex], true);
                            messages.push(steps[stepIndex]);
                            stepIndex++;
                            setTimeout(showStep, 2000); // 2 seconds between status messages
                        } else {
                            setTimeout(() => {
                                window.location.reload();
                            }, 5000);
                        }
                    }
                    showStep();
                    
                }).catch(error => {
                    console.error('Error initiating restart:', error);
                    restartBtn.classList.remove('restarting');
                    restartBtn.disabled = false;
                    const errorMsg = '❌ Failed to restart services: ' + error.message;
                    appendMessage(errorMsg, true);
                    // Keep error message visible for longer
                    setTimeout(() => {
                        messages.forEach(msg => {
                            const messageDiv = document.createElement('div');
                            messageDiv.className = 'message bot-message error-message';
                            messageDiv.innerHTML = msg;
                            messagesContainer.appendChild(messageDiv);
                        });
                    }, 1000);
                });
            }
        }
        
        updateCountdown();
    }
}

// Socket events for restart status
document.addEventListener('DOMContentLoaded', () => {
    const socket = io();
    
    socket.on('restart_status', (data) => {
        console.log('Received restart status:', data);
        const restartBtn = document.querySelector('.restart-button');
        
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