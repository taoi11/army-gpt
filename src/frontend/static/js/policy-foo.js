// Policy Foo functionality
let chatHistory = [];

function initializePolicyFoo() {
    // Setup enter key handlers
    setupKeyHandlers();
    
    // Initialize chat container
    setupChatContainer();
}

// Setup key handlers
function setupKeyHandlers() {
    const searchInput = document.getElementById('searchInput');
    const chatInput = document.getElementById('chatInput');
    
    searchInput?.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            searchPolicies();
        }
    });
    
    chatInput?.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
}

// Setup chat container
function setupChatContainer() {
    const container = document.getElementById('chatMessages');
    if (!container) return;
    
    // Add welcome message
    const welcomeMessage = {
        role: 'assistant',
        content: 'Hello! I can help you understand CAF policies. What would you like to know?'
    };
    addMessageToChat(welcomeMessage);
}

// Search policies
async function searchPolicies() {
    const input = document.getElementById('searchInput');
    const resultsContainer = document.getElementById('searchResults');
    if (!input || !resultsContainer) return;
    
    const query = input.value.trim();
    if (!query) return;
    
    try {
        // Show loading state
        resultsContainer.innerHTML = '<div class="flex justify-center"><div class="loading-spinner"></div></div>';
        
        const response = await fetch('/api/policy/search', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query })
        });
        
        if (!army.handleRateLimit(response)) return;
        
        const results = await response.json();
        
        // Clear loading state and display results
        resultsContainer.innerHTML = '';
        
        if (results.length === 0) {
            resultsContainer.innerHTML = '<p class="text-gray-500">No policies found matching your query.</p>';
            return;
        }
        
        results.forEach(result => {
            const resultElement = document.createElement('div');
            resultElement.className = 'search-result p-4 flex items-start gap-4 cursor-pointer';
            resultElement.innerHTML = `
                <div class="relevance-score bg-blue-100 text-blue-800">
                    ${Math.round(result.relevance * 100)}%
                </div>
                <div>
                    <h3 class="font-semibold">${result.title}</h3>
                    <p class="text-sm text-gray-600">Policy ${result.number}</p>
                </div>
            `;
            resultElement.onclick = () => readPolicy(result.number);
            resultsContainer.appendChild(resultElement);
        });
    } catch (error) {
        console.error('Search error:', error);
        army.showError('Failed to search policies. Please try again.');
    }
}

// Read policy content
async function readPolicy(policyNumber) {
    const contentSection = document.getElementById('policyContent');
    const contentContainer = document.getElementById('policyText');
    if (!contentSection || !contentContainer) return;
    
    try {
        // Show loading state
        contentSection.classList.remove('hidden');
        contentContainer.innerHTML = '<div class="flex justify-center"><div class="loading-spinner"></div></div>';
        
        const response = await fetch('/api/policy/read', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ policyNumber, section: 'all' })
        });
        
        if (!army.handleRateLimit(response)) return;
        
        const content = await response.json();
        
        // Display content
        contentContainer.innerHTML = `
            <div class="policy-content">
                <h2 class="text-2xl font-bold mb-4">Policy ${content.policyNumber}</h2>
                <div class="policy-section">
                    ${content.content}
                </div>
            </div>
        `;
        
        // Scroll to content
        contentSection.scrollIntoView({ behavior: 'smooth' });
    } catch (error) {
        console.error('Read error:', error);
        army.showError('Failed to load policy content. Please try again.');
    }
}

// Send chat message
async function sendMessage() {
    const input = document.getElementById('chatInput');
    const container = document.getElementById('chatMessages');
    if (!input || !container) return;
    
    const message = input.value.trim();
    if (!message) return;
    
    try {
        // Add user message
        const userMessage = { role: 'user', content: message };
        addMessageToChat(userMessage);
        chatHistory.push(userMessage);
        
        // Clear input
        input.value = '';
        
        // Show typing indicator
        const typingElement = document.createElement('div');
        typingElement.className = 'message assistant-message fade-enter';
        typingElement.innerHTML = '<div class="loading-spinner"></div>';
        container.appendChild(typingElement);
        
        // Scroll to bottom
        container.scrollTop = container.scrollHeight;
        
        // Send to API
        const response = await fetch('/api/policy/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message,
                history: chatHistory
            })
        });
        
        if (!army.handleRateLimit(response)) {
            typingElement.remove();
            return;
        }
        
        const result = await response.json();
        
        // Remove typing indicator
        typingElement.remove();
        
        // Add assistant message
        const assistantMessage = {
            role: 'assistant',
            content: result.answer,
            citations: result.citations
        };
        addMessageToChat(assistantMessage);
        chatHistory.push({ role: 'assistant', content: result.answer });
        
        // Handle follow-up if provided
        if (result.followUp) {
            setTimeout(() => {
                const followUpMessage = {
                    role: 'assistant',
                    content: result.followUp
                };
                addMessageToChat(followUpMessage);
                chatHistory.push(followUpMessage);
            }, 500);
        }
    } catch (error) {
        console.error('Chat error:', error);
        army.showError('Failed to send message. Please try again.');
    }
}

// Add message to chat
function addMessageToChat(message) {
    const container = document.getElementById('chatMessages');
    if (!container) return;
    
    const messageElement = document.createElement('div');
    messageElement.className = `message ${message.role}-message fade-enter`;
    
    let content = `<div class="message-content">${message.content}</div>`;
    
    if (message.citations) {
        content += `
            <div class="citations">
                Sources:
                ${message.citations.map(cite => `<div>${cite}</div>`).join('')}
            </div>
        `;
    }
    
    messageElement.innerHTML = content;
    container.appendChild(messageElement);
    
    // Scroll to bottom
    container.scrollTop = container.scrollHeight;
    
    // Trigger animation
    requestAnimationFrame(() => {
        messageElement.classList.add('fade-enter-active');
    });
} 