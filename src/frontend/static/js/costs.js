// Cost tracking functionality
let costsUpdateInterval;

async function updateCosts() {
    try {
        const response = await fetch('/api/costs');
        const data = await response.json();
        
        // Update main cost display
        const mainCostElement = document.querySelector('.main-cost p');
        if (mainCostElement) {
            const totalCost = (data.api + data.server).toFixed(2);
            mainCostElement.textContent = `$${totalCost}`;
        }
        
        // Update cost details if they exist
        const apiCostElement = document.querySelector('.cost-details .api-cost');
        const serverCostElement = document.querySelector('.cost-details .server-cost');
        
        if (apiCostElement) {
            apiCostElement.textContent = `$${data.api.toFixed(2)}`;
        }
        if (serverCostElement) {
            serverCostElement.textContent = `$${data.server.toFixed(2)}`;
        }
    } catch (error) {
        console.error('Failed to update costs:', error);
    }
}

// Initialize cost tracking
document.addEventListener('DOMContentLoaded', () => {
    // Initial update
    updateCosts();
    
    // Update costs every 5 minutes
    costsUpdateInterval = setInterval(updateCosts, 5 * 60 * 1000);
    
    // Setup cost display interaction
    const costDisplay = document.querySelector('.cost-display');
    const costDetails = document.querySelector('.cost-details');
    
    if (costDisplay && costDetails) {
        costDisplay.addEventListener('click', () => {
            costDetails.classList.toggle('hidden');
        });
    }
}); 