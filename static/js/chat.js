document.addEventListener('DOMContentLoaded', () => {
    const messageInput = document.getElementById('message-input');
    const sendButton = document.getElementById('send-button');
    const messagesContainer = document.getElementById('messages');
    let isWaitingForResponse = false;
    let retryCount = 0;
    const MAX_RETRIES = 3;
    
    function appendMessage(message, isBot = false, isLoading = false) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${isBot ? 'bot-message' : 'user-message'} ${isLoading ? 'loading' : ''}`;
        messageDiv.style.opacity = '0';
        
        if (isBot) {
            const botAvatar = document.createElement('img');
            botAvatar.src = '/static/images/2.png';
            botAvatar.className = 'bot-avatar';
            messageDiv.appendChild(botAvatar);
        }

        const messageContent = document.createElement('div');
        messageContent.className = 'message-content';
        
        if (isLoading) {
            messageContent.innerHTML = '<div class="typing-indicator"><span></span><span></span><span></span></div>';
        } else {
            messageContent.textContent = message;
        }
        
        messageDiv.appendChild(messageContent);
        messagesContainer.appendChild(messageDiv);
        
        // Smooth fade in animation
        requestAnimationFrame(() => {
            messageDiv.style.transition = 'opacity 0.3s ease-in-out';
            messageDiv.style.opacity = '1';
        });
        
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
        return messageDiv;
    }

    function updateMessage(messageDiv, newContent, isError = false) {
        const messageContent = messageDiv.querySelector('.message-content');
        messageContent.textContent = newContent;
        if (isError) {
            messageDiv.classList.add('error');
        }
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    function disableInput() {
        sendButton.disabled = true;
        messageInput.disabled = true;
        isWaitingForResponse = true;
        sendButton.classList.add('loading');
    }

    function enableInput() {
        sendButton.disabled = false;
        messageInput.disabled = false;
        isWaitingForResponse = false;
        sendButton.classList.remove('loading');
        messageInput.focus();
    }

    // Debounce function to prevent rapid fire requests
    function debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    async function sendMessage(message, loadingMessage = null) {
        if (!message || isWaitingForResponse) return;
        
        const userMessageDiv = appendMessage(message);
        const loadingMessageDiv = appendMessage('', true, true);
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
                loadingMessageDiv.remove();
                appendMessage(data.response, true);
                retryCount = 0; // Reset retry count on success
            }
            
            messageInput.value = '';
            
        } catch (error) {
            console.error('Message send error:', error);
            if (retryCount < MAX_RETRIES) {
                retryCount++;
                updateMessage(loadingMessageDiv, `Retrying... (${retryCount}/${MAX_RETRIES})`, true);
                setTimeout(() => sendMessage(message, loadingMessageDiv), 1000 * retryCount);
                return;
            } else {
                updateMessage(loadingMessageDiv, 'Failed to send message. Please try again.', true);
                retryCount = 0;
            }
        } finally {
            enableInput();
        }
    }

    // Debounced message sender
    const debouncedSendMessage = debounce((message) => sendMessage(message), 300);

    // UI Event Listeners
    sendButton.addEventListener('click', () => {
        const message = messageInput.value.trim();
        if (message) {
            debouncedSendMessage(message);
        }
    });

    messageInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            const message = messageInput.value.trim();
            if (message) {
                debouncedSendMessage(message);
            }
        }
    });

    // Add input feedback
    messageInput.addEventListener('input', () => {
        if (messageInput.value.trim()) {
            sendButton.classList.add('active');
        } else {
            sendButton.classList.remove('active');
        }
    });

    // Show initial message with animation
    setTimeout(() => {
        appendMessage("👋 Hello! I'm the Octant Information Bot. How can I help you today?", true);
    }, 500);
});