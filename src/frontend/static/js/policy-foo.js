// Constants
const MAX_MESSAGES = 10;  // Maximum number of messages to keep
let conversationHistory = [];

// Function to extract answer from response
function extractAnswer(response) {
    try {
        const answerMatch = response.match(/<answer>([\s\S]*?)<\/answer>/);
        return answerMatch ? answerMatch[1].trim() : response;
    } catch (e) {
        console.error('Error extracting answer:', e);
        return response;
    }
}

// Function to extract citations from response
function extractCitations(response) {
    try {
        const citationsMatch = response.match(/<citations>([\s\S]*?)<\/citations>/);
        if (!citationsMatch) return "";
        return citationsMatch[1].trim();
    } catch (e) {
        console.error('Error extracting citations:', e);
        return "";
    }
}

// Function to extract follow-up questions
function extractFollowUp(response) {
    try {
        const followUpMatch = response.match(/<follow_up>([\s\S]*?)<\/follow_up>/);
        if (!followUpMatch) return [];
        
        return followUpMatch[1].trim()
            .split(/\n/)
            .map(q => q.replace(/^-\s*/, '').trim())
            .filter(q => q);
    } catch (e) {
        console.error('Error extracting follow-up:', e);
        return [];
    }
}

// Function to create follow-up buttons
function createFollowUpSection(questions, messageDiv) {
    if (!questions.length) return;
    
    const followUpDiv = document.createElement('div');
    followUpDiv.className = 'mt-4 space-y-2';
    
    const heading = document.createElement('div');
    heading.className = 'text-sm font-medium text-gray-700';
    heading.textContent = 'Follow-up Questions:';
    followUpDiv.appendChild(heading);
    
    const buttonsDiv = document.createElement('div');
    buttonsDiv.className = 'flex flex-wrap gap-2';
    
    questions.forEach(question => {
        const button = document.createElement('button');
        button.className = 'px-3 py-1 text-sm bg-blue-100 text-blue-700 rounded-full hover:bg-blue-200 transition-colors';
        button.textContent = question;
        button.onclick = () => {
            const textarea = document.getElementById('questionInput');
            textarea.value = question;
            textarea.dispatchEvent(new Event('input')); // Trigger auto-resize
            submitQuestion(question);
        };
        buttonsDiv.appendChild(button);
    });
    
    followUpDiv.appendChild(buttonsDiv);
    messageDiv.appendChild(followUpDiv);
}

// Function to handle message editing
function setupMessageActions(messageElement, originalText) {
    const editButton = messageElement.querySelector('.edit-button');
    const resubmitButton = messageElement.querySelector('.resubmit-button');
    const editContainer = messageElement.querySelector('.edit-container');
    const editTextarea = messageElement.querySelector('.edit-textarea');
    const saveButton = messageElement.querySelector('.save-button');
    const cancelButton = messageElement.querySelector('.cancel-button');
    const messageText = messageElement.querySelector('.message-text');

    editTextarea.value = originalText;

    editButton.addEventListener('click', () => {
        messageText.style.display = 'none';
        editContainer.style.display = 'block';
        editTextarea.style.height = 'auto';
        editTextarea.style.height = editTextarea.scrollHeight + 'px';
        editTextarea.focus();
    });

    cancelButton.addEventListener('click', () => {
        messageText.style.display = 'block';
        editContainer.style.display = 'none';
        editTextarea.value = originalText;
    });

    saveButton.addEventListener('click', () => {
        const newText = editTextarea.value.trim();
        if (!newText) return;

        messageText.textContent = newText;
        messageText.style.display = 'block';
        editContainer.style.display = 'none';

        const messageIndex = Array.from(messageElement.parentElement.children).indexOf(messageElement);
        if (messageIndex >= 0 && messageIndex < conversationHistory.length) {
            conversationHistory[messageIndex].content = newText;
        }
    });

    resubmitButton.addEventListener('click', async () => {
        const messagesContainer = document.getElementById('messagesContainer');
        const allMessages = Array.from(messagesContainer.children);
        const messageIndex = allMessages.indexOf(messageElement.closest('.message'));
        
        if (messageIndex >= 0) {
            while (messagesContainer.children.length > messageIndex + 1) {
                messagesContainer.lastChild.remove();
            }
            
            const historyIndex = Math.floor(messageIndex / 2);
            conversationHistory = conversationHistory.slice(0, historyIndex);
        }
        
        await submitQuestion(messageText.textContent.trim(), true);
    });

    editTextarea.addEventListener('input', function() {
        this.style.height = 'auto';
        this.style.height = this.scrollHeight + 'px';
    });
}

// Function to add message to history
function addToHistory(role, content) {
    conversationHistory.push({
        role: role,
        content: content
    });
    console.log('Updated conversation history:', conversationHistory);
    if (conversationHistory.length > MAX_MESSAGES) {
        conversationHistory = conversationHistory.slice(-MAX_MESSAGES);
    }
}

// Function to create a message element
function createMessageElement(role, content) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `flex items-start space-x-4 p-4 ${role === 'user' ? 'bg-gray-50' : 'bg-white'}`;

    // Avatar
    const avatarDiv = document.createElement('div');
    avatarDiv.className = 'flex-shrink-0';
    const avatarIcon = document.createElement('i');
    avatarIcon.className = `fas ${role === 'user' ? 'fa-user' : 'fa-robot'} text-gray-400`;
    avatarDiv.appendChild(avatarIcon);

    // Message content
    const contentDiv = document.createElement('div');
    contentDiv.className = 'flex-grow space-y-2';

    if (role === 'user') {
        // User message with edit controls
        const messageHeader = document.createElement('div');
        messageHeader.className = 'flex justify-between items-start';

        const messageText = document.createElement('p');
        messageText.className = 'message-text text-gray-900';
        messageText.textContent = content;

        const actionsDiv = document.createElement('div');
        actionsDiv.className = 'flex space-x-2 opacity-0 group-hover:opacity-100 transition-opacity';

        const editButton = document.createElement('button');
        editButton.className = 'edit-button text-gray-400 hover:text-blue-500';
        editButton.innerHTML = '<i class="fas fa-edit"></i>';

        const resubmitButton = document.createElement('button');
        resubmitButton.className = 'resubmit-button text-gray-400 hover:text-blue-500';
        resubmitButton.innerHTML = '<i class="fas fa-redo-alt"></i>';

        actionsDiv.appendChild(editButton);
        actionsDiv.appendChild(resubmitButton);

        messageHeader.appendChild(messageText);
        messageHeader.appendChild(actionsDiv);
        contentDiv.appendChild(messageHeader);

        // Edit container
        const editContainer = document.createElement('div');
        editContainer.className = 'edit-container hidden mt-2';
        editContainer.innerHTML = `
            <textarea class="edit-textarea w-full p-2 border rounded-md"></textarea>
            <div class="flex justify-end space-x-2 mt-2">
                <button class="save-button text-green-500 hover:text-green-600">
                    <i class="fas fa-check"></i>
                </button>
                <button class="cancel-button text-red-500 hover:text-red-600">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `;
        contentDiv.appendChild(editContainer);

        setupMessageActions(contentDiv, content);
    } else {
        // Assistant message
        const messageText = document.createElement('div');
        messageText.className = 'prose max-w-none';
        
        const answer = extractAnswer(content);
        const citations = extractCitations(content);
        
        messageText.innerHTML = `
            <p class="text-gray-900">${answer}</p>
            ${citations ? `<div class="text-sm text-gray-600 mt-2"><strong>References:</strong><br>${citations}</div>` : ''}
        `;
        
        contentDiv.appendChild(messageText);
        
        // Add follow-up questions if any
        const followUpQuestions = extractFollowUp(content);
        if (followUpQuestions.length > 0) {
            createFollowUpSection(followUpQuestions, contentDiv);
        }
    }

    messageDiv.appendChild(avatarDiv);
    messageDiv.appendChild(contentDiv);
    return messageDiv;
}

// Function to submit a question
async function submitQuestion(question, isResubmission = false) {
    const textarea = document.getElementById('questionInput');
    const messagesContainer = document.getElementById('messagesContainer');
    const submitButton = document.querySelector('button[type="submit"]');
    
    // Disable input during processing
    textarea.disabled = true;
    submitButton.disabled = true;
    
    try {
        if (!isResubmission) {
            // Add user message to UI and history
            addToHistory('user', question);
            messagesContainer.appendChild(createMessageElement('user', question));
        }

        // Make API request
        const response = await fetch('/llm/policyfoo/generate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                content: question,
                conversation_history: conversationHistory
            })
        });

        const data = await response.json();
        
        if (data.content) {
            // Add assistant message to UI and history
            addToHistory('assistant', data.content);
            messagesContainer.appendChild(createMessageElement('assistant', data.content));
        } else {
            throw new Error(data.error || 'Failed to get response');
        }

    } catch (error) {
        console.error('Error:', error);
        const errorDiv = document.createElement('div');
        errorDiv.className = 'text-red-500 p-4';
        errorDiv.textContent = `Error: ${error.message}`;
        messagesContainer.appendChild(errorDiv);
    } finally {
        // Re-enable input
        textarea.disabled = false;
        submitButton.disabled = false;
        textarea.value = '';
        textarea.style.height = 'auto';
        textarea.focus();
        
        // Scroll to bottom
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
}

// Initialize when document is ready
document.addEventListener('DOMContentLoaded', () => {
    // Set up form submission
    const form = document.getElementById('chatForm');
    const textarea = document.getElementById('questionInput');

    form.addEventListener('submit', (e) => {
        e.preventDefault();
        const question = textarea.value.trim();
        if (question) {
            submitQuestion(question);
        }
    });

    // Set up textarea auto-resize
    textarea.addEventListener('input', function() {
        this.style.height = 'auto';
        this.style.height = this.scrollHeight + 'px';
    });
}); 