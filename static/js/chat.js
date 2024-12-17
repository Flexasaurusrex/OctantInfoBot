document.addEventListener('DOMContentLoaded', () => {
    const messageInput = document.getElementById('message-input');
    const sendButton = document.getElementById('send-button');
    const messagesContainer = document.getElementById('messages');
    let isWaitingForResponse = false;
    
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
        messageContent.textContent = message;
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

    async function sendMessage(message) {
        if (!message || isWaitingForResponse) return;
        
        appendMessage(message);
        disableInput();
        
        try {
            const response = await fetch('/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ message })
            });
            
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || 'Failed to send message');
            }
            
            if (data.response) {
                appendMessage(data.response, true);
            }
            
            messageInput.value = '';
            
        } catch (error) {
            console.error('Message send error:', error);
            appendMessage('Failed to send message. Please try again.', true);
        } finally {
            enableInput();
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

    // Show initial message
    appendMessage("👋 Hello! I'm the Octant Information Bot. How can I help you today?", true);
});