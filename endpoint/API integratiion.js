// Base API URL (replace with your actual backend URL)
const API_BASE_URL = 'http://localhost:8000/api';

// Authentication token (you'll need to implement login functionality)
let authToken = localStorage.getItem('authToken') || '';

// Common headers for API requests
const commonHeaders = {
  'Content-Type': 'application/json',
  'Authorization': `Token ${authToken}`
};

// Check online status
window.addEventListener('online', () => {
  showError('Connection restored. Syncing data...');
  loadDashboardData();
});

window.addEventListener('offline', () => {
  showError('You are offline. Changes will be saved locally and synced later.');
});

// Utility function for API requests
async function makeApiRequest(endpoint, method = 'GET', body = null) {
  if (!navigator.onLine) {
    // Store requests for later when offline
    const pendingRequests = JSON.parse(localStorage.getItem('pendingRequests') || '[]');
    pendingRequests.push({ endpoint, method, body, timestamp: Date.now() });
    localStorage.setItem('pendingRequests', JSON.stringify(pendingRequests));
    
    throw new Error('Offline: Request queued for later');
  }

  try {
    const options = {
      method,
      headers: commonHeaders
    };
    
    if (body) {
      options.body = JSON.stringify(body);
    }
    
    const response = await fetch(`${API_BASE_URL}${endpoint}`, options);
    
    if (!response.ok) {
      throw new Error(`API request failed: ${response.status}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error('API Error:', error);
    showError('Failed to load data. Please try again.');
    throw error;
  }
}

// Dashboard Data
async function loadDashboardData() {
  try {
    // Fetch all data needed for the dashboard
    const [stats, listings, reservations, recentSales] = await Promise.all([
      getFarmerStats(),
      getActiveListings(),
      getPendingReservations(),
      getRecentSales()
    ]);
    
    // Update the UI with the fetched data
    updateQuickStats(stats);
    updateActiveListings(listings);
    updatePendingReservations(reservations);
    updateRecentSales(recentSales);
    
  } catch (error) {
    console.error('Failed to load dashboard data:', error);
    // You might want to show an error message to the user
  }
}

// Farmer Statistics
async function getFarmerStats() {
  return makeApiRequest('/farmers/stats');
}

// Product Listings
async function getActiveListings() {
  return makeApiRequest('/products/active');
}

async function createNewListing(productData) {
  return makeApiRequest('/products', 'POST', productData);
}

async function updateListing(productId, updateData) {
  return makeApiRequest(`/products/${productId}`, 'PUT', updateData);
}

// Reservations
async function getPendingReservations() {
  return makeApiRequest('/reservations/pending');
}

async function approveReservation(reservationId) {
  return makeApiRequest(`/reservations/${reservationId}/approve`, 'POST');
}

async function rejectReservation(reservationId) {
  return makeApiRequest(`/reservations/${reservationId}/reject`, 'POST');
}

// Sales
async function getRecentSales() {
  return makeApiRequest('/sales/recent');
}

// UI Update Functions
function updateQuickStats(stats) {
  document.querySelector('.stat-item:nth-child(1) .number').textContent = stats.activeListings;
  document.querySelector('.stat-item:nth-child(2) .number').textContent = stats.pendingReservations;
  document.querySelector('.stat-item:nth-child(3) .number').textContent = stats.weeklySales;
}

function updateActiveListings(listings) {
  const productListContainer = document.querySelector('.product-list');
  
  // Clear existing content (except the first template card if you want to keep it)
  productListContainer.innerHTML = '';
  
  listings.forEach(product => {
    const productCard = document.createElement('div');
    productCard.className = 'product-card';
    productCard.innerHTML = `
      <div class="product-image">
        <i class="fas fa-${product.icon || 'shopping-basket'}"></i>
      </div>
      <div class="product-details">
        <div class="product-name">${product.name}</div>
        <div class="product-price">${product.price} ${product.currency || 'FCFA'}</div>
        <div class="product-quantity">${product.quantity} available</div>
        <div>
          ${product.tags.map(tag => `<span class="product-tag">${tag}</span>`).join('')}
        </div>
        <div class="product-actions">
          <button class="edit-btn" data-product-id="${product.id}">Edit</button>
          <button data-product-id="${product.id}">Details</button>
        </div>
        ${product.offline ? `
        <div class="offline-indicator">
          <div class="dot"></div>
          <span>Offline changes saved</span>
        </div>` : ''}
      </div>
    `;
    
    productListContainer.appendChild(productCard);
  });
  
  // Add event listeners to the new buttons
  document.querySelectorAll('.product-actions .edit-btn').forEach(button => {
    button.addEventListener('click', () => editProduct(button.dataset.productId));
  });
}

function updatePendingReservations(reservations) {
  const reservationsContainer = document.querySelector('.reservation-list');
  reservationsContainer.innerHTML = '';
  
  reservations.forEach(reservation => {
    const reservationItem = document.createElement('div');
    reservationItem.className = 'reservation-item';
    reservationItem.innerHTML = `
      <div class="reservation-avatar">
        <i class="fas fa-user"></i>
      </div>
      <div class="reservation-details">
        <div class="reservation-product">${reservation.productName}</div>
        <div class="reservation-info">${reservation.customerName} • ${reservation.pickupTime}</div>
      </div>
      <div class="reservation-actions">
        <button class="approve-btn" data-reservation-id="${reservation.id}">Approve</button>
        <button class="reject-btn" data-reservation-id="${reservation.id}">Reject</button>
      </div>
    `;
    
    reservationsContainer.appendChild(reservationItem);
  });
  
  // Add event listeners to the new buttons
  document.querySelectorAll('.reservation-actions .approve-btn').forEach(button => {
    button.addEventListener('click', () => approveReservation(button.dataset.reservationId));
  });
  
  document.querySelectorAll('.reservation-actions .reject-btn').forEach(button => {
    button.addEventListener('click', () => rejectReservation(button.dataset.reservationId));
  });
}

function updateRecentSales(sales) {
  const salesContainer = document.querySelectorAll('.reservation-list')[1];
  salesContainer.innerHTML = '';
  
  sales.forEach(sale => {
    const saleItem = document.createElement('div');
    saleItem.className = 'reservation-item';
    saleItem.innerHTML = `
      <div class="reservation-avatar">
        <i class="fas fa-user"></i>
      </div>
      <div class="reservation-details">
        <div class="reservation-product">${sale.productName}</div>
        <div class="reservation-info">${sale.amount} • ${sale.paymentStatus}</div>
      </div>
      <div class="reservation-actions">
        ${sale.receiptPending ? `
        <button class="approve-btn" data-sale-id="${sale.id}">Upload Receipt</button>
        ` : ''}
        <button data-sale-id="${sale.id}">Mark Sold</button>
      </div>
    `;
    
    salesContainer.appendChild(saleItem);
  });
}

function showError(message) {
  // Create or use an existing error display element
  const errorDiv = document.createElement('div');
  errorDiv.className = 'api-error';
  errorDiv.style.position = 'fixed';
  errorDiv.style.bottom = '20px';
  errorDiv.style.right = '20px';
  errorDiv.style.padding = '15px';
  errorDiv.style.backgroundColor = '#ffebee';
  errorDiv.style.color = '#c62828';
  errorDiv.style.borderRadius = '4px';
  errorDiv.style.boxShadow = '0 2px 5px rgba(0,0,0,0.2)';
  errorDiv.style.zIndex = '1000';
  errorDiv.textContent = message;
  
  document.body.appendChild(errorDiv);
  
  // Remove after 5 seconds
  setTimeout(() => {
    errorDiv.remove();
  }, 5000);
}

// Event Listeners
document.addEventListener('DOMContentLoaded', () => {
  // Load all dashboard data when page loads
  loadDashboardData();
  
  // Add new product button
  document.querySelector('.quick-action-btn').addEventListener('click', () => {
    // You would redirect to your add product page or show a modal
    window.location.href = 'addproduct.html';
  });
});

// Example function for editing a product
async function editProduct(productId) {
  // You would redirect to your edit page or show a modal
  window.location.href = `editproduct.html?id=${productId}`;
}



