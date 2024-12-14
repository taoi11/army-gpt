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
            
            // Update the cost display
            if (this.costElement) {
                this.costElement.innerHTML = `
                    <div class="main-cost">
                        <h3 class="text-sm font-semibold text-gray-700">Monthly Cost (CAD)</h3>
                        <p class="text-lg text-gray-900">$${costs.total_cad}</p>
                    </div>
                    <div class="cost-details hidden">
                        <div class="text-xs text-gray-500 mt-1">
                            <div>AI Costs: $${costs.api_costs.cad}</div>
                            <div>Cloud Rent: $${costs.server_rent_cad}</div>
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