// Constants
const MAX_MESSAGES = 10;  // Maximum number of messages to keep
let conversationHistory = [];

// Handle form submission
async function handleSubmit(e) {
    e.preventDefault();
    
    const userInput = document.getElementById('userInput').value.trim();
    if (!userInput) return;

    // Reset textarea
    document.getElementById('userInput').value = '';
    document.getElementById('userInput').style.height = 'auto';

    // Add user message to UI and history
    addMessage('user', userInput);
    conversationHistory.push({ role: 'user', content: userInput });

    // Add thinking message
    const thinkingMessage = addMessage('assistant', '', true);

    try {
        const response = await fetch('/llm/policyfoo/generate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                content: userInput,
                temperature: 0.1,
                stream: false
            })
        });

        if (!response.ok) {
            throw new Error('Failed to get response');
        }

        // Check if response is streaming
        const contentType = response.headers.get('content-type');
        if (contentType && contentType.includes('text/event-stream')) {
            // Handle streaming response
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let content = '';

            while (true) {
                const { value, done } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value);
                const lines = chunk.split('\n');

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const data = line.slice(6);
                        if (data === '[DONE]') {
                            // End of stream
                            break;
                        }
                        content += data;
                        updateMessage(thinkingMessage, content);
                    }
                }
            }

            // Add assistant message to history
            conversationHistory.push({ role: 'assistant', content });

        } else {
            // Handle regular JSON response
            const data = await response.json();
            
            if (data.error) {
                throw new Error(data.error);
            }

            // Update UI with response
            updateMessage(thinkingMessage, data.content);

            // Add assistant message to history
            conversationHistory.push({ role: 'assistant', content: data.content });
        }

        // Prune conversation history if needed
        while (conversationHistory.length > MAX_MESSAGES) {
            conversationHistory.shift();
        }

    } catch (error) {
        console.error('Error:', error);
        thinkingMessage.innerHTML = `
            <div class="p-4 bg-red-100 text-red-700 rounded-lg">
                Error: ${error.message || 'Failed to get response'}. Please try again.
            </div>
        `;
    }
}

function addMessage(role, content, isThinking = false) {
    const messagesContainer = document.getElementById('messagesContainer');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message-container p-4 rounded-lg transition-all duration-300 scroll-mt-4 ${
        role === 'user' ? 'bg-gray-100' : 'bg-white'
    }`;
    
    if (isThinking) {
        messageDiv.innerHTML = '<p class="text-gray-500 flex items-center gap-1 thinking">Thinking</p>';
    } else {
        messageDiv.textContent = content;
    }

    messagesContainer.appendChild(messageDiv);
    messageDiv.scrollIntoView({ behavior: 'smooth', block: 'end' });

    // Prune old messages if needed
    const messages = messagesContainer.getElementsByClassName('message-container');
    while (messages.length > MAX_MESSAGES) {
        messagesContainer.removeChild(messages[0]);
    }

    return messageDiv;
}

function updateMessage(messageDiv, content) {
    // Parse XML response
    const parser = new DOMParser();
    const xmlDoc = parser.parseFromString(content, 'text/xml');
    
    // Extract components
    const answer = xmlDoc.querySelector('answer')?.textContent?.trim() || content;
    const citations = xmlDoc.querySelector('citations')?.textContent?.trim() || '';
    const followUp = xmlDoc.querySelector('follow_up')?.textContent?.trim() || '';

    // Build HTML
    let html = `<p class="whitespace-pre-line">${answer}</p>`;
    
    // Add citations if present
    if (citations) {
        html += `
            <div class="policy-reference mt-2">
                <strong>References:</strong>
                ${citations}
            </div>
        `;
    }

    // Add follow-up if present
    if (followUp) {
        html += `
            <div class="suggested-followups mt-2">
                <span class="followup-chip" onclick="useFollowup(this.textContent)">
                    ${followUp}
                </span>
            </div>
        `;
    }

    messageDiv.innerHTML = html;
    messageDiv.scrollIntoView({ behavior: 'smooth', block: 'end' });
}

function useFollowup(text) {
    const textarea = document.getElementById('userInput');
    textarea.value = text;
    textarea.focus();
    // Trigger the auto-expand
    textarea.dispatchEvent(new Event('input'));
}

// Initialize policy foo functionality
function initializePolicyFoo() {
    // Setup form handler
    document.getElementById('queryForm').addEventListener('submit', handleSubmit);

    // Initialize common features
    initializeCommon();
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', initializePolicyFoo); 