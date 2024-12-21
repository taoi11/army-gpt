// Pace Notes functionality
function initializePaceNotes() {
    // Setup key points container
    setupKeyPoints();
    
    // Setup textarea auto-resize
    setupTextareaResize();
    
    // Setup keyboard shortcuts
    setupKeyboardShortcuts();
    
    // Setup counters
    setupCounters();
}

// Setup keyboard shortcuts
function setupKeyboardShortcuts() {
    // Handle Ctrl+Enter to generate
    document.addEventListener('keydown', (e) => {
        if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
            e.preventDefault();
            generatePaceNotes();
        }
    });
    
    // Handle Enter in key points
    document.getElementById('keyPoints')?.addEventListener('keydown', (e) => {
        if (e.target.classList.contains('key-point')) {
            if (e.key === 'Enter') {
                e.preventDefault();
                addKeyPoint();
            } else if (e.key === 'Backspace' && e.target.value === '') {
                e.preventDefault();
                const item = e.target.closest('.key-point-item');
                if (item) removeKeyPoint(item.querySelector('button'));
            }
        }
    });
}

// Setup key points functionality
function setupKeyPoints() {
    const container = document.getElementById('keyPoints');
    if (!container) return;
    
    // Add initial key point input
    addKeyPoint();
}

// Setup textarea auto-resize
function setupTextareaResize() {
    const textarea = document.getElementById('contextInput');
    if (!textarea) return;
    
    textarea.addEventListener('input', function() {
        this.style.height = 'auto';
        this.style.height = Math.min(this.scrollHeight, 400) + 'px';
    });
}

// Setup counters and validation
function setupCounters() {
    const contextInput = document.getElementById('contextInput');
    const contextCounter = document.getElementById('contextCounter');
    const keyPointsCounter = document.getElementById('keyPointsCounter');
    
    // Update context counter
    contextInput?.addEventListener('input', () => {
        if (contextCounter) {
            const length = contextInput.value.length;
            contextCounter.textContent = `${length}/2000`;
            contextCounter.className = length > 1800 ? 'text-amber-500 ml-2' : 'text-gray-500 ml-2';
        }
    });
    
    // Update key points counter
    const observer = new MutationObserver(() => {
        const container = document.getElementById('keyPoints');
        if (container && keyPointsCounter) {
            const count = container.querySelectorAll('.key-point-item').length;
            keyPointsCounter.textContent = `${count}/5`;
            keyPointsCounter.className = count >= 5 ? 'text-amber-500 ml-2' : 'text-gray-500 ml-2';
            
            // Disable add button if max reached
            const addButton = container.querySelector('button:not([onclick*="remove"])');
            if (addButton) {
                addButton.disabled = count >= 5;
                addButton.className = count >= 5 
                    ? 'bg-gray-400 text-white px-4 rounded cursor-not-allowed'
                    : 'bg-green-500 text-white px-4 rounded hover:bg-green-600 transition-colors';
            }
        }
    });
    
    observer.observe(document.getElementById('keyPoints') || document.body, {
        childList: true,
        subtree: true
    });
}

// Add new key point input
function addKeyPoint() {
    const container = document.getElementById('keyPoints');
    if (!container) return;
    
    // Check max limit
    if (container.querySelectorAll('.key-point-item').length >= 5) {
        army.showError('Maximum of 5 key points allowed.');
        return;
    }
    
    // Create new key point item
    const keyPointItem = document.createElement('div');
    keyPointItem.className = 'key-point-item';
    
    keyPointItem.innerHTML = `
        <input type="text" 
               class="key-point flex-1 p-2 border rounded focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
               maxlength="200"
               placeholder="Add a key point...">
        <button onclick="removeKeyPoint(this)"
                class="text-red-500 hover:text-red-600 transition-colors">
            ×
        </button>
    `;
    
    container.appendChild(keyPointItem);
    
    // Focus the new input
    const input = keyPointItem.querySelector('input');
    input.focus();
}

// Remove key point
function removeKeyPoint(button) {
    const item = button.closest('.key-point-item');
    if (!item) return;
    
    // Animate removal
    item.style.opacity = '0';
    item.style.transform = 'translateY(-10px)';
    
    setTimeout(() => {
        item.remove();
        
        // If no key points left, add a new empty one
        const container = document.getElementById('keyPoints');
        if (container && container.children.length === 0) {
            addKeyPoint();
        }
    }, 200);
}

// Generate pace notes with validation
async function generatePaceNotes() {
    const contextInput = document.getElementById('contextInput');
    const keyPoints = document.querySelectorAll('.key-point');
    const toneSelect = document.getElementById('toneSelect');
    const lengthSelect = document.getElementById('lengthSelect');
    const outputSection = document.getElementById('outputSection');
    const generatedContent = document.getElementById('generatedContent');
    
    if (!contextInput || !toneSelect || !lengthSelect || !outputSection || !generatedContent) return;
    
    const context = contextInput.value.trim();
    const points = Array.from(keyPoints)
        .map(input => input.value.trim())
        .filter(Boolean);
    
    // Validation
    if (!context) {
        army.showError('Please provide context for the pace notes.');
        contextInput.focus();
        return;
    }
    
    if (context.length < 50) {
        army.showError('Please provide more detailed context (at least 50 characters).');
        contextInput.focus();
        return;
    }
    
    if (points.length === 0) {
        army.showError('Please add at least one key point.');
        const firstKeyPoint = document.querySelector('.key-point');
        firstKeyPoint?.focus();
        return;
    }
    
    if (points.some(point => point.length < 10)) {
        army.showError('Each key point should be at least 10 characters long.');
        const shortPoint = Array.from(keyPoints).find(input => input.value.trim().length < 10);
        shortPoint?.focus();
        return;
    }
    
    try {
        // Show loading state
        outputSection.classList.remove('hidden');
        generatedContent.innerHTML = '<div class="flex justify-center"><div class="loading-spinner"></div></div>';
        
        // Disable inputs during generation
        const inputs = document.querySelectorAll('input, textarea, select, button');
        inputs.forEach(input => input.disabled = true);
        
        // Scroll to output
        outputSection.scrollIntoView({ behavior: 'smooth' });
        
        const response = await fetch('/api/pace-notes/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                context,
                keyPoints: points,
                tone: toneSelect.value,
                length: lengthSelect.value
            })
        });
        
        if (!army.handleRateLimit(response)) {
            inputs.forEach(input => input.disabled = false);
            return;
        }
        
        const result = await response.json();
        
        // Display generated content
        generatedContent.innerHTML = `
            <div class="generated-content">
                ${result.content}
            </div>
        `;
        
        // Show success message
        army.showSuccess('Pace notes generated successfully!');
        
    } catch (error) {
        console.error('Generation error:', error);
        army.showError('Failed to generate pace notes. Please try again.');
        
        // Hide output section on error
        outputSection.classList.add('hidden');
    } finally {
        // Re-enable inputs
        const inputs = document.querySelectorAll('input, textarea, select, button');
        inputs.forEach(input => input.disabled = false);
    }
}

// Copy to clipboard
async function copyToClipboard() {
    const content = document.querySelector('.generated-content');
    if (!content) return;
    
    try {
        await navigator.clipboard.writeText(content.innerText);
        
        // Show copied state
        const copyButton = document.querySelector('.copy-button');
        if (copyButton) {
            copyButton.classList.add('copied');
            setTimeout(() => {
                copyButton.classList.remove('copied');
            }, 2000);
        }
        
        army.showSuccess('Copied to clipboard!');
    } catch (error) {
        console.error('Copy error:', error);
        army.showError('Failed to copy to clipboard.');
    }
} 