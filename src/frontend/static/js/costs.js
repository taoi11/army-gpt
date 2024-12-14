// Cost display functionality
class CostDisplay {
    constructor() {
        this.costElement = document.querySelector('.cost-display');
        this.updateCosts();
        // Update costs every 5 minutes
        setInterval(() => this.updateCosts(), 5 * 60 * 1000);
    }

    async updateCosts() {
        try {
            const response = await fetch('/api/costs');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const costs = await response.json();
            console.log('Raw costs response:', costs);  // Log raw response
            
            // Update the cost display
            if (this.costElement) {
                if (costs.error) {
                    throw new Error(costs.error);
                }
                
                // Ensure we have valid numbers, defaulting to 0.00 if undefined
                const mainCost = costs.total?.cad || '0.00';
                const aiCost = costs.api_costs?.cad || '0.00';
                const serverRentCost = costs.server_rent?.cad || '0.00';
                
                console.log('Formatted costs:', { mainCost, aiCost, serverRent: serverRentCost });
                
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
            console.error('Error details:', error.message);  // Log error details
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