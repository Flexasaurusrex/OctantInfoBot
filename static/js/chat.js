document.addEventListener('DOMContentLoaded', () => {
    const socket = io({
        reconnection: true,
        reconnectionAttempts: 5,
        reconnectionDelay: 1000,
        reconnectionDelayMax: 5000,
        timeout: 20000,
    });
    
    const messageInput = document.getElementById('message-input');
    const sendButton = document.getElementById('send-button');
    const messagesContainer = document.getElementById('messages');
    let isWaitingForResponse = false;

    // Connection event handlers
    socket.on('connect', () => {
        console.log('Connected to server');
        if (messagesContainer) {
            const statusDiv = document.createElement('div');
            statusDiv.className = 'message bot-message';
            statusDiv.innerHTML = '<span>Connected to server ✓</span>';
            messagesContainer.appendChild(statusDiv);
        }
    });

    socket.on('connect_error', (error) => {
        console.error('Connection error:', error);
        if (messagesContainer) {
            const statusDiv = document.createElement('div');
            statusDiv.className = 'message bot-message';
            statusDiv.innerHTML = '<span>Connection error. Attempting to reconnect...</span>';
            messagesContainer.appendChild(statusDiv);
        }
    });

    socket.on('disconnect', () => {
        console.log('Disconnected from server');
        if (messagesContainer) {
            const statusDiv = document.createElement('div');
            statusDiv.className = 'message bot-message';
            statusDiv.innerHTML = '<span>Disconnected from server. Reconnecting...</span>';
            messagesContainer.appendChild(statusDiv);
        }
    });

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
            botAvatar.src = '/static/images/octant-logo.svg';
            botAvatar.className = 'bot-avatar';
            messageDiv.appendChild(botAvatar);
        }

        const messageContent = document.createElement('span');
        messageContent.innerHTML = message;
        messageDiv.appendChild(messageContent);
        
        messagesContainer.appendChild(messageDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;

        // Check for correct answer and trigger confetti
        if (isBot && message.includes('✅ Correct! Well done!')) {
            triggerConfetti();
        }
    }

    function sendMessage() {
        if (isWaitingForResponse) return;
        
        const message = messageInput.value.trim();
        if (!message) return;
        
        appendMessage(message);
        messageInput.value = '';
        
        isWaitingForResponse = true;
        sendButton.disabled = true;
        messageInput.disabled = true;
        
        socket.emit('send_message', { message });
    }

    socket.on('receive_message', (data) => {
        appendMessage(data.message, data.is_bot);
        isWaitingForResponse = false;
        sendButton.disabled = false;
        messageInput.disabled = false;
        messageInput.focus();
    });

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
});
