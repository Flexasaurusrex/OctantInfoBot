document.addEventListener('DOMContentLoaded', () => {
    const messageInput = document.getElementById('message-input');
    const sendButton = document.getElementById('send-button');
    const messagesContainer = document.getElementById('messages');
    let isWaitingForResponse = false;
    let messageQueue = [];
    const clientId = Math.random().toString(36).substring(7);
    let eventSource;
    
    function setupEventSource() {
        if (eventSource) {
            eventSource.close();
        }
        
        eventSource = new EventSource(`/stream?client_id=${clientId}`);
        
        eventSource.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                appendMessage(data.message, data.is_bot);
                if (isWaitingForResponse) {
                    isWaitingForResponse = false;
                    enableInput();
                }
            } catch (error) {
                console.error('Error processing message:', error);
            }
        };
        
        eventSource.onerror = (error) => {
            console.error('EventSource error:', error);
            updateConnectionStatus('error');
            if (eventSource.readyState === EventSource.CLOSED) {
                setTimeout(setupEventSource, 3000);
            }
        };
        
        eventSource.onopen = () => {
            console.log('EventSource connected');
            updateConnectionStatus('connected');
        };
    }

    function updateConnectionStatus(status) {
        const statusIndicator = document.querySelector('.status-indicator');
        const statusText = document.querySelector('.status-text');
        
        if (!statusIndicator || !statusText) return;
        
        const statusMap = {
            'connected': { text: 'Connected', class: 'connected' },
            'disconnected': { text: 'Disconnected', class: 'disconnected' },
            'reconnecting': { text: 'Reconnecting...', class: 'reconnecting' },
            'error': { text: 'Connection Error', class: 'error' }
        };
        
        const currentStatus = statusMap[status] || statusMap.disconnected;
        statusIndicator.className = 'status-indicator ' + currentStatus.class;
        statusText.textContent = currentStatus.text;
    }

    // Initialize EventSource connection
    setupEventSource();
    
    // Process queued messages periodically
    setInterval(() => {
        if (!isWaitingForResponse && messageQueue.length > 0) {
            const message = messageQueue.shift();
            sendMessage(message, true);
        }
    }, 1000);
    
    // Cleanup on page unload
    window.addEventListener('beforeunload', () => {
        if (eventSource) {
            eventSource.close();
        }
    });

    function handleReconnection() {
        console.error('Connection lost');
        updateConnectionStatus('error');
        appendMessage('Connection lost. Attempting to reconnect...', true);
        
        // Attempt to reconnect EventSource
        setTimeout(() => {
            setupEventSource();
        }, 3000);
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

        const messageContent = document.createElement('div');
        messageContent.className = 'message-content';
        messageContent.innerHTML = message;
        messageDiv.appendChild(messageContent);
        
        messagesContainer.appendChild(messageDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    function disableInput() {
        sendButton.disabled = true;
        messageInput.disabled = true;
        isWaitingForResponse = true;
    }

    function enableInput() {
        sendButton.disabled = false;
        messageInput.disabled = false;
        isWaitingForResponse = false;
        messageInput.focus();
    }

    async function sendMessage(message, fromQueue = false) {
        if (!message) return;
        
        if (isWaitingForResponse && !fromQueue) {
            messageQueue.push(message);
            appendMessage('Processing previous message. Your message has been queued.', true);
            return;
        }
        
        appendMessage(message);
        disableInput();
        
        try {
            const response = await fetch('/send', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message,
                    client_id: clientId
                })
            });
            
            if (!response.ok) {
                throw new Error('Failed to send message');
            }
            
            if (!fromQueue) {
                messageInput.value = '';
            }
            
        } catch (error) {
            console.error('Message send error:', error);
            enableInput();
            appendMessage('Failed to send message. Please try again.', true);
        }
    }

    // UI Event Listeners
    sendButton.addEventListener('click', () => {
        const message = messageInput.value.trim();
        if (message) {
            sendMessage(message);
        }
    });

    messageInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            const message = messageInput.value.trim();
            if (message) {
                sendMessage(message);
            }
        }
    });

    // Periodic connection check
    setInterval(() => {
        if (eventSource && eventSource.readyState === EventSource.CLOSED && !isWaitingForResponse) {
            handleReconnection();
        }
    }, 5000);
});
