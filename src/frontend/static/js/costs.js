// Cost display functionality
class CostDisplay {
    constructor() {
        this.costElement = document.querySelector('.cost-display');
        this.updateCosts();
    }

    async updateCosts() {
        try {
            const response = await fetch('/api/costs');
            const costs = await response.json();
            console.log('Costs response:', costs);  // Debug log
            
            // Update the cost display
            if (this.costElement) {
                // Ensure we have valid numbers, defaulting to 0.00 if undefined
                const mainCost = costs.total?.cad || '0.00';
                const aiCost = costs.api_costs?.cad || '0.00';
                const serverRentCost = costs.server_rent?.cad || '0.00';  // Changed from cloudCost
                
                console.log('Formatted costs:', { mainCost, aiCost, serverRent: serverRentCost });  // Updated debug log
                
                this.costElement.innerHTML = `
                    <div class="main-cost">
                        <h3 class="text-sm font-semibold text-gray-700">Monthly Cost (CAD)</h3>
                        <p class="text-lg text-gray-900">$${mainCost}</p>
                    </div>
                    <div class="cost-details hidden">
                        <div class="text-xs text-gray-500 mt-1">
                            <div>AI Costs: $${aiCost}</div>
                            <div>Server Rent: $${serverRentCost}</div>
                        </div>
                    </div>
                `;

                // Add hover effect
                this.costElement.addEventListener('mouseenter', () => {
                    this.costElement.querySelector('.cost-details').classList.remove('hidden');
                });
                
                this.costElement.addEventListener('mouseleave', () => {
                    this.costElement.querySelector('.cost-details').classList.add('hidden');
                });
            }
        } catch (error) {
            console.error('Error fetching costs:', error);
            if (this.costElement) {
                this.costElement.innerHTML = `
                    <div class="main-cost">
                        <h3 class="text-sm font-semibold text-gray-700">Monthly Cost</h3>
                        <p class="text-gray-900">Error loading costs</p>
                    </div>
                `;
            }
        }
    }
}

// Initialize cost display when the DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new CostDisplay();
}); 