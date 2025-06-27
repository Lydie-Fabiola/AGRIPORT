document.addEventListener('DOMContentLoaded', function() {
    // Check if user is authenticated
    if (!Auth.isAuthenticated()) {
        window.location.href = 'loginbuyer.html';
        return;
    }

    const container = document.querySelector('.container');
    const productTemplate = document.querySelector('.product-card');
    
    // Remove the template product
    if (productTemplate) {
        productTemplate.remove();
    }
    
    // Show loading state
    const loadingElement = document.createElement('div');
    loadingElement.className = 'loading';
    loadingElement.innerHTML = '<p>Loading urgent sales...</p>';
    container.appendChild(loadingElement);
    
    // Fetch urgent sales from API
    fetch('http://localhost:8000/api/urgent-sales', {
        headers: {
            'Authorization': `Bearer ${Auth.getToken()}`
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Failed to fetch urgent sales');
        }
        return response.json();
    })
    .then(data => {
        // Remove loading element
        loadingElement.remove();
        
        if (data.length === 0) {
            const noSales = document.createElement('div');
            noSales.className = 'no-sales';
            noSales.innerHTML = '<p>No urgent sales available at the moment. Please check back later!</p>';
            container.appendChild(noSales);
            return;
        }
        
        // Create product cards for each urgent sale
        data.forEach(sale => {
            const productCard = createProductCard(sale);
            container.appendChild(productCard);
        });
    })
    .catch(error => {
        console.error('Error fetching urgent sales:', error);
        loadingElement.innerHTML = '<p>Failed to load urgent sales. Please try again later.</p>';
    });
    
    // Function to create a product card
    function createProductCard(sale) {
        const card = document.createElement('div');
        card.className = 'product-card';
        
        // Format date
        const bestBefore = new Date(sale.best_before);
        const formattedDate = bestBefore.toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'long',
            day: 'numeric'
        });
        
        card.innerHTML = `
            <div class="date-badge">Best before: ${formattedDate}</div>
            <div class="image-box">
                <img src="${sale.image_url || 'assets/placeholder.jpg'}" alt="${sale.product_name}">
            </div>
            <h2>${sale.product_name}</h2>
            <p class="farmer">${sale.farmer_name}</p>
            <div class="price">
                <span class="old">GH¢${sale.original_price}/${sale.quantity_unit}</span>
                <span class="new">GH¢${sale.reduced_price}/${sale.quantity_unit}</span>
            </div>
            <p class="note">${sale.reason}</p>
            <div class="quantity-selector">
                <label for="quantity-${sale.urgent_sale_id}">Quantity:</label>
                <input type="number" id="quantity-${sale.urgent_sale_id}" min="1" max="${sale.quantity}" value="1">
                <span class="unit">${sale.quantity_unit}</span>
            </div>
            <div class="actions">
                <button class="buy" data-id="${sale.urgent_sale_id}">Quick Buy</button>
            </div>
        `;
        
        // Add event listener to buy button
        const buyButton = card.querySelector('.buy');
        buyButton.addEventListener('click', function() {
            const saleId = this.getAttribute('data-id');
            const quantityInput = card.querySelector(`#quantity-${saleId}`);
            const quantity = parseInt(quantityInput.value);
            
            if (isNaN(quantity) || quantity < 1) {
                alert('Please enter a valid quantity');
                return;
            }
            
            // Show confirmation dialog
            if (confirm(`Are you sure you want to purchase ${quantity} ${sale.quantity_unit} of ${sale.product_name}?`)) {
                purchaseUrgentSale(saleId, quantity);
            }
        });
        
        return card;
    }
    
    // Function to purchase an urgent sale
    function purchaseUrgentSale(saleId, quantity) {
        fetch(`http://localhost:8000/api/urgent-sales/${saleId}/purchase`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${Auth.getToken()}`
            },
            body: JSON.stringify({
                quantity: quantity
            })
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to purchase product');
            }
            return response.json();
        })
        .then(data => {
            alert('Purchase successful! The farmer will contact you soon.');
            // Refresh the page to update available products
            window.location.reload();
        })
        .catch(error => {
            console.error('Error purchasing product:', error);
            alert('Failed to complete purchase. Please try again.');
        });
    }
});