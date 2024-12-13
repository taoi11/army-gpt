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

function updateRateLimits(limits) {
    if (limits) {
        document.getElementById('hourlyRemaining').textContent = 
            limits.hourly === 999 ? '∞' : limits.hourly;
        document.getElementById('dailyRemaining').textContent = 
            limits.daily === 999 ? '∞' : limits.daily;
    }
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
    // Initial credits check
    checkCredits();
    
    // Set up intervals
    setInterval(checkCredits, 5 * 60 * 1000);  // Check credits every 5 minutes

    // Setup expandable textarea if it exists
    const textarea = document.getElementById('userInput');
    if (textarea) {
        setupExpandableTextarea(textarea);
    }
} 