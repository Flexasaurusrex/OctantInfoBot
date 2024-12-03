document.addEventListener('DOMContentLoaded', () => {
    const socket = io({
        reconnectionAttempts: 10,
        timeout: 20000,
        reconnectionDelay: 2000,
        reconnectionDelayMax: 10000,
        transports: ['polling', 'websocket']
    });
    
    const messagesContainer = document.getElementById('messages');
    const messageInput = document.getElementById('message-input');
    const sendButton = document.getElementById('send-button');
    let isWaitingForResponse = false;
    let reconnectAttempts = 0;
    const maxMessageLength = 500;
    
    socket.on('connect', () => {
        reconnectAttempts = 0;
        if (messagesContainer.querySelector('.connection-error')) {
            messagesContainer.querySelector('.connection-error').remove();
        }
    });

    socket.on('connect_error', (error) => {
        console.error('Connection error:', error);
        reconnectAttempts++;
        
        const loadingIndicator = messagesContainer.querySelector('.loading');
        if (loadingIndicator) {
            loadingIndicator.remove();
        }
        
        isWaitingForResponse = false;
        
        const reconnectMessage = `Connection issues detected. Attempting to reconnect... (Attempt ${reconnectAttempts}/10)`;
        
        if (!messagesContainer.querySelector('.connection-error')) {
            const errorMessage = document.createElement('div');
            errorMessage.className = 'message system-message connection-error';
            errorMessage.textContent = reconnectMessage;
            messagesContainer.appendChild(errorMessage);
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        } else {
            const errorMessage = messagesContainer.querySelector('.connection-error');
            errorMessage.textContent = reconnectMessage;
        }
        
        // If max reconnection attempts reached, show permanent error
        if (reconnectAttempts >= 10) {
            const finalError = document.createElement('div');
            finalError.className = 'message system-message connection-error';
            finalError.textContent = 'Unable to establish connection. Please refresh the page to try again.';
            messagesContainer.appendChild(finalError);
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }

        return Promise.resolve();
    });
    
    socket.on('error', (error) => {
        console.error('Socket error:', error);
        if (!isWaitingForResponse) {
            showError('An error occurred. Please try again.');
        }
    });

    function createMessageElement(message, isBot) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${isBot ? 'bot-message' : 'user-message'}`;
        
        if (isBot) {
            const avatarImg = document.createElement('img');
            avatarImg.src = '/static/images/octant-logo.svg';
            avatarImg.className = 'bot-avatar';
            messageDiv.appendChild(avatarImg);
        }
        
        const messageContent = document.createElement('span');
        messageContent.innerHTML = message;
        messageDiv.appendChild(messageContent);
        
        return messageDiv;
    }

    function addLoadingIndicator() {
        const loadingDiv = document.createElement('div');
        loadingDiv.className = 'message bot-message loading';
        loadingDiv.innerHTML = `
            <img src="/static/images/octant-logo.svg" class="bot-avatar">
            <span></span>
            <span></span>
            <span></span>
        `;
        messagesContainer.appendChild(loadingDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
        return loadingDiv;
    }

    function validateMessage(message) {
        if (!message.trim()) {
            throw new Error("Please enter a message");
        }
        if (message.length > maxMessageLength) {
            throw new Error(`Message is too long (maximum ${maxMessageLength} characters)`);
        }
        return message.trim();
    }

    function showError(message) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'message system-message error';
        errorDiv.textContent = message;
        messagesContainer.appendChild(errorDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
        
        // Auto-remove error message after 5 seconds
        setTimeout(() => {
            errorDiv.remove();
        }, 5000);
    }

    function sendMessage() {
        if (isWaitingForResponse) {
            showError("Please wait for the previous response");
            return;
        }

        try {
            const message = validateMessage(messageInput.value);
            const messageElement = createMessageElement(message, false);
            messagesContainer.appendChild(messageElement);
            
            const loadingIndicator = addLoadingIndicator();
            isWaitingForResponse = true;
            
            socket.emit('send_message', { message: message });
            messageInput.value = '';
            
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        } catch (error) {
            showError(error.message);
        }
    }

    socket.on('receive_message', (data) => {
        const loadingIndicator = messagesContainer.querySelector('.loading');
        if (loadingIndicator) {
            loadingIndicator.remove();
        }
        
        const messageElement = createMessageElement(data.message, true);
        messagesContainer.appendChild(messageElement);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
        isWaitingForResponse = false;
    });

    sendButton.addEventListener('click', sendMessage);
    messageInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });
});
