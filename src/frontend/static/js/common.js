// Rate limit and credits management
async function checkCredits() {
    try {
        const response = await fetch('/llm/credits');
        const data = await response.json();
        const banner = document.getElementById('creditsBanner');
        
        if (!data.credits_available) {
            banner.classList.remove('hidden');
        } else {
            banner.classList.add('hidden');
        }
    } catch (error) {
        console.error('Error checking credits:', error);
    }
}

// Check rate limits from the API
async function checkRateLimits() {
    try {
        const response = await fetch('/api/limits');
        const data = await response.json();
        updateRateLimits(data);
    } catch (error) {
        console.error('Error checking rate limits:', error);
    }
}

// Update rate limits display
function updateRateLimits(limits) {
    if (!limits) return;

    // Update all hourly limit displays
    document.querySelectorAll('.rate-limit-hourly').forEach(element => {
        element.textContent = limits.hourly_remaining === 999 ? '∞' : limits.hourly_remaining || '--';
    });
    
    // Update all daily limit displays
    document.querySelectorAll('.rate-limit-daily').forEach(element => {
        element.textContent = limits.daily_remaining === 999 ? '∞' : limits.daily_remaining || '--';
    });
}

// Helper function for fetch
async function fetchWithRateLimits(url, options = {}) {
    return fetch(url, options);
}

// Textarea handling
function setupExpandableTextarea(textarea) {
    textarea.addEventListener('input', function() {
        this.style.height = 'auto';
        this.style.height = Math.min(this.scrollHeight, 200) + 'px';
    });
}

// Copy to clipboard
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        alert('Copied to clipboard!');
    }).catch(err => {
        console.error('Failed to copy:', err);
    });
}

// Initialize common features
function initializeCommon() {
    // Initial checks
    checkCredits();
    checkRateLimits();
    
    // Set up intervals
    setInterval(checkCredits, 5 * 60 * 1000);  // Check credits every 5 minutes
    setInterval(checkRateLimits, 60 * 1000);   // Check rate limits every minute

    // Setup expandable textarea if it exists
    const textarea = document.getElementById('userInput');
    if (textarea) {
        setupExpandableTextarea(textarea);
    }
}

// Export functions for use in other modules
window.fetchWithRateLimits = fetchWithRateLimits;
window.updateRateLimits = updateRateLimits;