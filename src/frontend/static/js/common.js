// Rate limit and credits management
async function checkCredits() {
    try {
        const baseUrl = window.location.origin;
        const response = await fetch(`${baseUrl}/llm/credits`);
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
        const baseUrl = window.location.origin;
        const response = await fetch(`${baseUrl}/api/limits`);
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
        // Find rate limit elements
        const hourlyElements = document.querySelectorAll('.rate-limit-hourly');
        const dailyElements = document.querySelectorAll('.rate-limit-daily');

        if (hourlyElements.length === 0 || dailyElements.length === 0) {
            console.warn('Rate limit elements not found, retrying in 500ms');
            // Retry once after a short delay
            setTimeout(() => {
                const retryHourly = document.querySelectorAll('.rate-limit-hourly');
                const retryDaily = document.querySelectorAll('.rate-limit-daily');
                if (retryHourly.length > 0 && retryDaily.length > 0) {
                    updateRateLimitElements(retryHourly, retryDaily, limits);
                }
            }, 500);
            return;
        }

        updateRateLimitElements(hourlyElements, dailyElements, limits);
    } catch (error) {
        console.error('Error updating rate limit display:', error);
    }
}

// Helper function to update rate limit elements
function updateRateLimitElements(hourlyElements, dailyElements, limits) {
    // Update hourly elements
    hourlyElements.forEach(element => {
        if (element) {
            element.textContent = limits.hourly_remaining === 999 ? '∞' : 
                                limits.hourly_remaining === 0 ? '0' : 
                                limits.hourly_remaining || '--';
        }
    });
    
    // Update daily elements
    dailyElements.forEach(element => {
        if (element) {
            element.textContent = limits.daily_remaining === 999 ? '∞' : 
                                limits.daily_remaining === 0 ? '0' : 
                                limits.daily_remaining || '--';
        }
    });
}

// Helper function for fetch with retry
async function fetchWithRateLimits(url, options = {}) {
    const maxRetries = 3;
    let lastError;

    // Ensure absolute URL
    const baseUrl = window.location.origin;
    const absoluteUrl = url.startsWith('http') ? url : `${baseUrl}${url}`;

    for (let i = 0; i < maxRetries; i++) {
        try {
            const response = await fetch(absoluteUrl, {
                ...options,
                headers: {
                    ...options.headers,
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });
            
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
    // Initial checks with retry
    setTimeout(() => {
        checkCredits();
        checkRateLimits();
    }, 500); // Small delay to ensure DOM is ready
    
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