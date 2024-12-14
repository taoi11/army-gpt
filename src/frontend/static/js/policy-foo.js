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
    messageDiv.className = `message ${role}-message ${role === 'user' ? 'bg-gray-50' : 'bg-white'} rounded-lg shadow-md max-w-3xl mx-auto`;

    // Create the flex container
    const flexContainer = document.createElement('div');
    flexContainer.className = 'flex items-start space-x-4 p-4';

    // Avatar
    const avatarDiv = document.createElement('div');
    avatarDiv.className = 'flex-shrink-0';
    const avatarIcon = document.createElement('i');
    avatarIcon.className = `fas ${role === 'user' ? 'fa-user' : 'fa-robot'} text-gray-400`;
    avatarDiv.appendChild(avatarIcon);

    // Content container
    const contentDiv = document.createElement('div');
    contentDiv.className = 'flex-1 min-w-0';

    // Message content div (this is what we'll query for later)
    const messageContent = document.createElement('div');
    messageContent.className = 'message-content';

    if (role === 'user') {
        // User message with edit controls
        const messageHeader = document.createElement('div');
        messageHeader.className = 'flex justify-between items-start group';

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
        messageContent.appendChild(messageHeader);

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
        messageContent.appendChild(editContainer);

        setupMessageActions(messageContent, content);
    } else {
        // For assistant messages, we'll just create an empty content div
        // The sections will be added by the streaming code
        messageContent.className = 'message-content prose max-w-none';
    }

    // Assemble the message element
    contentDiv.appendChild(messageContent);
    flexContainer.appendChild(avatarDiv);
    flexContainer.appendChild(contentDiv);
    messageDiv.appendChild(flexContainer);

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

        // Create assistant message element with raw stream display
        const assistantMessage = createMessageElement('assistant', '');
        messagesContainer.appendChild(assistantMessage);
        const messageContent = assistantMessage.querySelector('.message-content');
        
        // Create raw stream display
        const rawStream = document.createElement('div');
        rawStream.className = 'raw-stream whitespace-pre-wrap font-mono text-sm';
        messageContent.appendChild(rawStream);

        // Make API request
        const response = await fetch('/llm/policyfoo/generate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'text/plain'
            },
            body: JSON.stringify({
                content: question,
                conversation_history: conversationHistory
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        // Get response as ReadableStream
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let fullResponse = '';

        // Process the stream
        try {
            while (true) {
                const {value, done} = await reader.read();
                
                if (done) {
                    console.log('Stream complete');
                    break;
                }
                
                // Decode the chunk and update displays
                const chunk = decoder.decode(value, {stream: true});
                console.log('Received chunk:', chunk);
                fullResponse += chunk;
                rawStream.textContent = fullResponse;
                
                // Scroll to bottom
                messagesContainer.scrollTop = messagesContainer.scrollHeight;
            }
        } catch (error) {
            console.error('Error reading stream:', error);
            throw error;
        } finally {
            // Make sure to decode any remaining chunks
            const remaining = decoder.decode();
            if (remaining) {
                fullResponse += remaining;
                rawStream.textContent = fullResponse;
            }
        }

        // Now that we have the complete response, format it
        const formattedContent = document.createElement('div');
        formattedContent.className = 'formatted-content hidden';
        messageContent.appendChild(formattedContent);

        // Extract and format sections
        const answer = extractAnswer(fullResponse);
        const citations = extractCitations(fullResponse);
        const followUpQuestions = extractFollowUp(fullResponse);

        // Create formatted sections
        const answerSection = document.createElement('div');
        answerSection.className = 'answer-section prose max-w-none';
        answerSection.innerHTML = `<p class="text-gray-900">${answer}</p>`;
        formattedContent.appendChild(answerSection);

        if (citations) {
            const citationsSection = document.createElement('div');
            citationsSection.className = 'citations-section text-sm text-gray-600 mt-2';
            citationsSection.innerHTML = `<strong>References:</strong><br>${citations}`;
            formattedContent.appendChild(citationsSection);
        }

        if (followUpQuestions.length > 0) {
            const followUpSection = document.createElement('div');
            followUpSection.className = 'follow-up-section mt-4';
            followUpSection.innerHTML = '<div class="text-sm text-gray-600"><strong>Follow-up Questions:</strong></div>';
            
            const suggestedFollowups = document.createElement('div');
            suggestedFollowups.className = 'suggested-followups flex flex-wrap gap-2 mt-2';
            
            followUpQuestions.forEach(question => {
                const chip = document.createElement('div');
                chip.className = 'followup-chip px-3 py-1 text-sm bg-blue-100 text-blue-700 rounded-full hover:bg-blue-200 transition-colors cursor-pointer';
                chip.textContent = question;
                chip.addEventListener('click', () => {
                    textarea.value = question;
                    textarea.focus();
                });
                suggestedFollowups.appendChild(chip);
            });
            
            followUpSection.appendChild(suggestedFollowups);
            formattedContent.appendChild(followUpSection);
        }

        // Add toggle button
        const toggleButton = document.createElement('button');
        toggleButton.className = 'toggle-view-btn text-sm text-blue-600 hover:text-blue-800 mt-2';
        toggleButton.textContent = 'Show formatted view';
        messageContent.insertBefore(toggleButton, formattedContent);

        toggleButton.addEventListener('click', () => {
            const isRawVisible = !rawStream.classList.contains('hidden');
            if (isRawVisible) {
                rawStream.classList.add('hidden');
                formattedContent.classList.remove('hidden');
                toggleButton.textContent = 'Show raw response';
            } else {
                rawStream.classList.remove('hidden');
                formattedContent.classList.add('hidden');
                toggleButton.textContent = 'Show formatted view';
            }
        });

        // Add to history
        addToHistory('assistant', fullResponse);

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