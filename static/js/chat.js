document.addEventListener('DOMContentLoaded', () => {
    let socket = null;
    
    // Close any existing connections
    if (socket) {
        socket.close();
    }
    
    socket = io({
        reconnection: true,
        reconnectionAttempts: Infinity,
        reconnectionDelay: 1000,
        reconnectionDelayMax: 5000,
        timeout: 20000,
        transports: ['websocket'],
        upgrade: false,
        autoConnect: true,
        reconnectionDelayMax: 10000
    });

    // Handle initial connection error
    socket.on('connect_failed', (error) => {
        console.log('Initial connection failed:', error);
        appendMessage('Failed to establish connection. Please refresh the page.', true);
    });

    // Handle disconnect
    socket.on('disconnect', (reason) => {
        console.log('Disconnected:', reason);
        appendMessage('Connection lost. Attempting to reconnect...', true);
    });

    // Handle reconnect failed
    socket.on('reconnect_failed', () => {
        console.log('Reconnection failed');
        appendMessage('Failed to reconnect. Please refresh the page.', true);
    });

    // Handle reconnect attempt
    socket.on('reconnect_attempt', (attemptNumber) => {
        console.log('Attempting to reconnect:', attemptNumber);
    });
    const messageInput = document.getElementById('message-input');
    const sendButton = document.getElementById('send-button');
    const messagesContainer = document.getElementById('messages');
    let isWaitingForResponse = false;

    socket.on('connect_error', (error) => {
        console.log('Connection error:', error);
        const messages = document.getElementById('messages');
        if (!document.querySelector('.connection-error')) {
            const errorDiv = document.createElement('div');
            errorDiv.className = 'message bot-message connection-error';
            errorDiv.innerHTML = 'Connection lost. Attempting to reconnect...';
            messages.appendChild(errorDiv);
            messages.scrollTop = messages.scrollHeight;
        }
    });

    socket.on('reconnect', (attemptNumber) => {
        console.log('Reconnected after', attemptNumber, 'attempts');
        const errorDiv = document.querySelector('.connection-error');
        if (errorDiv) {
            errorDiv.remove();
        }
        appendMessage('Connection restored!', true);
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
            botAvatar.src = '/static/images/2.png';
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
