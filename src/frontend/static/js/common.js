// Rate limit and credits management
async function checkCredits() {
    try {
        const response = await fetch('/llm/credits');
        const data = await response.json();
        const banner = document.getElementById('creditsBanner');
        
        if (!data.credits_available) {
            banner?.classList.remove('hidden');
        } else {
            banner?.classList.add('hidden');
        }
    } catch (error) {
        console.error('Error checking credits:', error);
    }
}

// Check rate limits from the API
async function checkRateLimits() {
    try {
        const response = await fetch('/api/limits');
        if (!response.ok) {
            if (response.status === 429) {
                // Handle Cloudflare rate limit
                console.warn('Rate limit reached (Cloudflare)');
                updateRateLimits({ hourly_remaining: 0, daily_remaining: 0 });
                return;
            }
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        updateRateLimits(data);
    } catch (error) {
        console.error('Error checking rate limits:', error);
    }
}

// Update rate limits display
function updateRateLimits(limits) {
    if (!limits) return;

    try {
        // Update all hourly limit displays
        document.querySelectorAll('.rate-limit-hourly').forEach(element => {
            if (element) {
                element.textContent = limits.hourly_remaining === 999 ? '∞' : 
                                    limits.hourly_remaining === 0 ? '0' : 
                                    limits.hourly_remaining || '--';
            }
        });
        
        // Update all daily limit displays
        document.querySelectorAll('.rate-limit-daily').forEach(element => {
            if (element) {
                element.textContent = limits.daily_remaining === 999 ? '∞' : 
                                    limits.daily_remaining === 0 ? '0' : 
                                    limits.daily_remaining || '--';
            }
        });
    } catch (error) {
        console.error('Error updating rate limit display:', error);
    }
}

// Helper function for fetch with retry
async function fetchWithRateLimits(url, options = {}) {
    const maxRetries = 3;
    let lastError;

    for (let i = 0; i < maxRetries; i++) {
        try {
            const response = await fetch(url, options);
            
            // Handle Cloudflare errors
            if (response.status === 429) {
                console.warn('Rate limit reached (Cloudflare)');
                updateRateLimits({ hourly_remaining: 0, daily_remaining: 0 });
                throw new Error('Rate limit reached');
            }
            
            if (response.status === 524) {
                console.warn(`Cloudflare timeout (attempt ${i + 1}/${maxRetries})`);
                continue; // Retry on timeout
            }
            
            return response;
        } catch (error) {
            lastError = error;
            if (i === maxRetries - 1) break;
            await new Promise(resolve => setTimeout(resolve, 1000 * (i + 1))); // Exponential backoff
        }
    }
    
    throw lastError;
}

// Textarea handling
function setupExpandableTextarea(textarea) {
    if (!textarea) return;
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
    setupExpandableTextarea(textarea);
}

// Export functions for use in other modules
window.fetchWithRateLimits = fetchWithRateLimits;
window.updateRateLimits = updateRateLimits;