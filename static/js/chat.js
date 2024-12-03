document.addEventListener('DOMContentLoaded', () => {
    const socket = io();
    const messagesContainer = document.getElementById('messages');
    const messageInput = document.getElementById('message-input');
    const sendButton = document.getElementById('send-button');
    let isWaitingForResponse = false;

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
        messageContent.textContent = message;
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

    function sendMessage() {
        if (isWaitingForResponse || !messageInput.value.trim()) return;

        const message = messageInput.value.trim();
        const messageElement = createMessageElement(message, false);
        messagesContainer.appendChild(messageElement);
        
        const loadingIndicator = addLoadingIndicator();
        isWaitingForResponse = true;
        
        socket.emit('send_message', { message: message });
        messageInput.value = '';
        
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
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
