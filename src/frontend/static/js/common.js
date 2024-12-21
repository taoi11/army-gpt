// Common functionality across all pages
function initializeCommon() {
    // Setup credits banner
    setupCreditsBanner();
    
    // Setup error handling
    setupErrorHandling();
}

// Credits banner management
async function setupCreditsBanner() {
    const banner = document.getElementById('creditsBanner');
    if (!banner) return;

    try {
        const response = await fetch('/api/llm/credits');
        const data = await response.json();
        
        if (!data.hasCredits) {
            banner.classList.remove('hidden');
        }
    } catch (error) {
        console.error('Failed to check credits:', error);
    }
}

// Global error handling
function setupErrorHandling() {
    window.addEventListener('unhandledrejection', event => {
        console.error('Unhandled promise rejection:', event.reason);
        showError('An unexpected error occurred. Please try again.');
    });
}

// Show error message
function showError(message, duration = 5000) {
    const container = document.createElement('div');
    container.className = 'fixed bottom-4 right-4 bg-red-500 text-white px-6 py-3 rounded-lg shadow-lg z-50';
    container.textContent = message;
    
    document.body.appendChild(container);
    
    setTimeout(() => {
        container.remove();
    }, duration);
}

// Show success message
function showSuccess(message, duration = 3000) {
    const container = document.createElement('div');
    container.className = 'fixed bottom-4 right-4 bg-green-500 text-white px-6 py-3 rounded-lg shadow-lg z-50';
    container.textContent = message;
    
    document.body.appendChild(container);
    
    setTimeout(() => {
        container.remove();
    }, duration);
}

// Rate limit handling
function handleRateLimit(response) {
    const hourlyRemaining = response.headers.get('X-RateLimit-Remaining-Hour');
    const dailyRemaining = response.headers.get('X-RateLimit-Remaining-Day');
    
    if (hourlyRemaining === '0' || dailyRemaining === '0') {
        showError('Rate limit exceeded. Please try again later.');
        return false;
    }
    
    return true;
}

// Export common utilities
window.army = {
    showError,
    showSuccess,
    handleRateLimit
};