// Global variables
let products = [];
let farmers = [];
let notifications = [];
let notificationCheckInterval;
let searchTimeout;

document.addEventListener('DOMContentLoaded', function () {
  // Check authentication
  if (!window.BuyerAuth || !window.BuyerAuth.isAuthenticated()) {
    window.location.href = 'loginbuyer.html';
    return;
  }

  // Initialize dashboard
  initializeDashboard();

function initializeDashboard() {
  // Update user info in dashboard
  updateUserInfo();

  // Load dashboard data
  loadDashboardData();

  // Initialize existing functionality
  initializeExistingFeatures();
}

function updateUserInfo() {
  const userName = window.BuyerAuth.getUserName();
  const userEmail = window.BuyerAuth.getUserEmail();

  // Update user name displays
  const userNameElements = document.querySelectorAll('.user-name, .buyer-name');
  userNameElements.forEach(element => {
    if (element) {
      element.textContent = userName || 'Buyer';
    }

  });

  // Update email displays
  const userEmailElements = document.querySelectorAll('.user-email');
  userEmailElements.forEach(element => {
    if (element) {
      element.textContent = userEmail || '';
    }
  });
}

async function loadDashboardData() {
  try {
    // Load dashboard stats
    const dashboardData = await window.BuyerAuth.getDashboardData();
    if (dashboardData) {
      updateDashboardStats(dashboardData);
    }

    // Load real products from farmers
    await loadRealProducts();

  } catch (error) {
    console.error('Failed to load dashboard data:', error);
  }
}

async function loadRealProducts() {
  try {
    const response = await fetch('http://localhost:8000/api/products/', {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json'
      }
    });

    const data = await response.json();

    if (data.success) {
      products = data.products;
      window.products = products; // Make products globally accessible
      renderProducts(products);
      console.log(`Loaded ${products.length} real products from farmers`);
    } else {
      console.error('Failed to load products:', data.error);
      showEmptyState('Failed to load products. Please try again later.');
    }
  } catch (error) {
    console.error('Error loading products:', error);
    showEmptyState('Network error. Please check your connection.');
  }
}

function updateDashboardStats(data) {
  // Update dashboard statistics if elements exist
  const statsElements = {
    'pending-reservations': data.pending_reservations,
    'approved-reservations': data.approved_reservations,
    'monthly-spending': `${data.monthly_spending} FCFA`,
    'total-reservations': data.total_reservations
  };

  Object.keys(statsElements).forEach(id => {
    const element = document.getElementById(id);
    if (element) {
      element.textContent = statsElements[id];
    }
  });
}

function initializeExistingFeatures() {
  const productGrid = document.querySelector('.product-grid');
  const farmerGrid = document.querySelector('.farmer-grid');
  const searchButton = document.querySelector('.search-bar button');
  const searchInput = document.querySelector('.search-bar input');
  const farmerCards = document.querySelectorAll('.farmer-card');
  const productsTab = document.getElementById('products-tab');
  const farmersTab = document.getElementById('farmers-tab');

  // Check if required elements exist
  if (!productGrid || !searchInput || !productsTab || !farmersTab) {
    console.warn('Some required dashboard elements not found');
    return;
  }

  // Products and farmers will be loaded from API

  function enableLikeButtons() {
    document.querySelectorAll('.like, .favorite-icon').forEach(button => {
      button.addEventListener('click', () => {
        button.classList.toggle('liked');
        button.style.color = button.classList.contains('liked') ? 'red' : '#999';
      });
    });
  }

  function renderProducts(filteredProducts = products, compact = false) {
    // Clear grid with fade out animation
    productGrid.style.opacity = '0.5';

    setTimeout(() => {
      productGrid.innerHTML = '';

      if (filteredProducts.length === 0) {
        showEmptyState('No products available at the moment.');
        productGrid.style.opacity = '1';
        return;
      }

      // Create product cards with staggered animation
      filteredProducts.forEach((product, index) => {
        const card = createProductCard(product, compact, index);
        productGrid.appendChild(card);
      });

      // Fade in the grid
      productGrid.style.opacity = '1';

      // Enable interactions
      enableLikeButtons();
      enableProductActions();

      // Add scroll-to-top functionality for search results
      if (compact && filteredProducts.length > 0) {
        addScrollToTop();
      }
    }, 200);
  }

  function createProductCard(product, compact = false, index = 0) {
    const card = document.createElement('div');
    card.className = 'product-card' + (compact ? ' compact' : '');
    card.style.animationDelay = `${index * 0.1}s`; // Staggered animation

    // Enhanced product data
    const imageUrl = product.image_url || `https://via.placeholder.com/200x150?text=${encodeURIComponent(product.product_name || product.name)}`;
    const productName = product.product_name || product.name;
    const farmerName = product.farmer_name || product.farm;
    const price = product.price ? `${product.price} FCFA/${product.quantity_unit || 'unit'}` : 'Price not set';
    const isLowStock = product.quantity && product.quantity < 10;
    const isNewProduct = product.created_at && isRecentProduct(product.created_at);
    const farmerVerified = product.farmer_trust_badge;

    if (compact) {
      card.innerHTML = `
        <div class="product-image">
          <img src="${imageUrl}" alt="${productName}" onerror="this.src='https://via.placeholder.com/150x100?text=No+Image'" loading="lazy">
          ${isNewProduct ? '<span class="new-badge">NEW</span>' : ''}
          ${isLowStock ? '<span class="stock-badge low">Low Stock</span>' : ''}
        </div>
        <div class="product-info">
          <h3 title="${productName}">${truncateText(productName, 25)}</h3>
          <p class="farm-name">
            ${farmerVerified ? '<i class="fas fa-check-circle verified-icon" title="Verified Farmer"></i>' : ''}
            ${truncateText(farmerName, 20)}
          </p>
          <p class="price-compact">${price}</p>
        </div>
        <div class="product-actions compact">
          <button class="view-details-btn btn-primary" data-listing-id="${product.listing_id}" title="View Details">
            <i class="fas fa-eye"></i>
          </button>
          <button class="favorite-icon btn-secondary" data-listing-id="${product.listing_id}" title="Add to Favorites">
            <i class="far fa-heart"></i>
          </button>
          <button class="quick-reserve-btn btn-success" data-listing-id="${product.listing_id}" title="Quick Reserve">
            <i class="fas fa-shopping-cart"></i>
          </button>
        </div>
      `;
    } else {
      card.innerHTML = `
        <div class="product-image">
          <img src="${imageUrl}" alt="${productName}" onerror="this.src='https://via.placeholder.com/200x150?text=No+Image'" loading="lazy">
          <button class="favorite-icon floating-btn" data-listing-id="${product.listing_id}" title="Add to Favorites">
            <i class="far fa-heart"></i>
          </button>
          ${isNewProduct ? '<span class="new-badge">NEW</span>' : ''}
          ${isLowStock ? '<span class="stock-badge low">Low Stock</span>' : ''}
        </div>
        <div class="product-info">
          <h3 title="${productName}">${productName}</h3>
          <p class="farm-name">
            ${farmerVerified ? '<i class="fas fa-check-circle verified-icon" title="Verified Farmer"></i>' : ''}
            by ${farmerName}
          </p>
          <p class="price"><strong>${price}</strong></p>
          ${product.quantity ? `<p class="quantity ${isLowStock ? 'low-stock' : ''}">
            <i class="fas fa-box"></i> Available: ${product.quantity} ${product.quantity_unit || 'units'}
          </p>` : ''}
          ${product.farmer_location ? `<p class="location">
            <i class="fas fa-map-marker-alt"></i> ${product.farmer_location}
          </p>` : ''}
          ${product.description ? `<p class="description" title="${product.description}">
            ${truncateText(product.description, 80)}
          </p>` : ''}
        </div>
        <div class="product-actions">
          <button class="view-details-btn btn-primary" data-listing-id="${product.listing_id}">
            <i class="fas fa-eye"></i> View Details
          </button>
          <button class="quick-reserve-btn btn-success" data-listing-id="${product.listing_id}">
            <i class="fas fa-shopping-cart"></i> Reserve
          </button>
        </div>
      `;
    }

    // Add hover effects and interactions
    addCardInteractions(card, product);

    return card;
  }

  // Utility functions for enhanced product grid
  function truncateText(text, maxLength) {
    if (!text) return '';
    return text.length > maxLength ? text.substring(0, maxLength) + '...' : text;
  }

  function isRecentProduct(createdAt) {
    if (!createdAt) return false;
    const productDate = new Date(createdAt);
    const now = new Date();
    const daysDiff = (now - productDate) / (1000 * 60 * 60 * 24);
    return daysDiff <= 7; // Consider products from last 7 days as new
  }

  function addCardInteractions(card, product) {
    // Add loading state on image
    const img = card.querySelector('img');
    img.addEventListener('load', () => {
      img.style.opacity = '1';
    });

    // Add click analytics (optional)
    card.addEventListener('click', (e) => {
      if (!e.target.closest('button')) {
        console.log(`Product viewed: ${product.product_name} by ${product.farmer_name}`);
      }
    });

    // Add keyboard navigation
    card.setAttribute('tabindex', '0');
    card.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        const viewBtn = card.querySelector('.view-details-btn');
        if (viewBtn) viewBtn.click();
      }
    });
  }

  function addScrollToTop() {
    // Remove existing scroll-to-top button
    const existingBtn = document.getElementById('scroll-to-top');
    if (existingBtn) existingBtn.remove();

    // Create scroll-to-top button
    const scrollBtn = document.createElement('button');
    scrollBtn.id = 'scroll-to-top';
    scrollBtn.innerHTML = '<i class="fas fa-arrow-up"></i>';
    scrollBtn.className = 'scroll-to-top-btn';
    scrollBtn.title = 'Scroll to top';

    scrollBtn.addEventListener('click', () => {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });

    document.body.appendChild(scrollBtn);

    // Show/hide based on scroll position
    window.addEventListener('scroll', () => {
      if (window.pageYOffset > 300) {
        scrollBtn.classList.add('visible');
      } else {
        scrollBtn.classList.remove('visible');
      }
    });
  }

  function showEmptyState(message) {
    productGrid.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">🌾</div>
        <h3>No Products Found</h3>
        <p>${message}</p>
        <div class="empty-actions">
          <button onclick="loadRealProducts()" class="retry-btn">
            <i class="fas fa-refresh"></i> Try Again
          </button>
          <button onclick="clearSearch()" class="clear-search-btn">
            <i class="fas fa-times"></i> Clear Search
          </button>
        </div>
      </div>
    `;
  }

  function clearSearch() {
    const searchInput = document.querySelector('.search-bar input');
    if (searchInput) {
      searchInput.value = '';
      searchInput.dispatchEvent(new Event('input'));
    }
  }

  function enableProductActions() {
    // View Details buttons
    document.querySelectorAll('.view-details-btn').forEach(button => {
      button.addEventListener('click', (e) => {
        const listingId = e.target.getAttribute('data-listing-id');
        viewProductDetails(listingId);
      });
    });

    // Quick Reserve buttons
    document.querySelectorAll('.quick-reserve-btn').forEach(button => {
      button.addEventListener('click', (e) => {
        const listingId = e.target.getAttribute('data-listing-id');
        quickReserve(listingId);
      });
    });
  }

  // Enhanced search functionality with debouncing

  function handleSearch() {
    const query = searchInput.value.trim();

    // Clear previous timeout for debouncing
    if (searchTimeout) {
      clearTimeout(searchTimeout);
    }

    // Debounce search for better performance (300ms delay)
    searchTimeout = setTimeout(() => {
      performSearch(query);
    }, 300);
  }

  async function performSearch(query) {
    if (farmersTab.classList.contains('active')) {
      await searchFarmers(query);
    } else if (productsTab.classList.contains('active')) {
      await searchProducts(query);
    }
  }

  async function searchFarmers(query) {
    try {
      if (!query) {
        // Show all farmers when no query
        farmerCards.forEach(card => {
          card.style.display = 'block';
          card.classList.remove('compact');
        });
        removeSearchMessage('no-match-msg');
        return;
      }

      // Show loading indicator
      showSearchLoading('Searching farmers...');

      const response = await fetch(`http://localhost:8000/api/search/?q=${encodeURIComponent(query)}&type=farmer`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json'
        }
      });

      const data = await response.json();
      hideSearchLoading();

      if (data.success) {
        displayFarmerSearchResults(data.results.farmers, query);
      } else {
        // Fallback to local search
        searchFarmersLocally(query);
      }
    } catch (error) {
      console.error('Farmer search error:', error);
      hideSearchLoading();
      // Fallback to local search
      searchFarmersLocally(query);
    }
  }

  function searchFarmersLocally(query) {
    let matchFound = false;

    farmerCards.forEach(card => {
      const text = card.textContent.toLowerCase();
      if (text.includes(query.toLowerCase())) {
        card.style.display = 'block';
        card.classList.add('compact');
        matchFound = true;
      } else {
        card.style.display = 'none';
        card.classList.remove('compact');
      }
    });

    if (!matchFound) {
      showSearchMessage('no-match-msg', `No farmers found for "${query}"`, 'error');
    } else {
      removeSearchMessage('no-match-msg');
    }
  }

  function displayFarmerSearchResults(farmers, query) {
    // Hide all existing farmer cards
    farmerCards.forEach(card => card.style.display = 'none');

    if (farmers.length === 0) {
      showSearchMessage('no-match-msg', `No farmers found for "${query}"`, 'error');
      return;
    }

    removeSearchMessage('no-match-msg');

    // Show search results info
    showSearchMessage('search-info', `Found ${farmers.length} farmers for "${query}"`, 'info');

    // Display matching farmers (for now, show existing cards that match)
    farmers.forEach(farmer => {
      farmerCards.forEach(card => {
        const cardText = card.textContent.toLowerCase();
        if (cardText.includes(farmer.farmer_name.toLowerCase())) {
          card.style.display = 'block';
          card.classList.add('compact');
        }
      });
    });
  }

  async function searchProducts(query) {
    try {
      if (!query) {
        renderProducts(products, false); // full view
        removeSearchMessage('search-info');
        return;
      }

      // Show loading state
      showSearchLoading('Searching products...');

      const response = await fetch(`http://localhost:8000/api/search/?q=${encodeURIComponent(query)}&type=product`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json'
        }
      });

      const data = await response.json();
      hideSearchLoading();

      if (data.success) {
        const searchResults = data.results.products;
        displayProductSearchResults(searchResults, query);
        console.log(`Found ${searchResults.length} products for query: ${query}`);
      } else {
        // Fallback to local search
        searchProductsLocally(query);
      }
    } catch (error) {
      console.error('Product search error:', error);
      hideSearchLoading();
      // Fallback to local search
      searchProductsLocally(query);
    }
  }

  function searchProductsLocally(query) {
    const filtered = products.filter(p =>
      (p.product_name || p.name || '').toLowerCase().includes(query.toLowerCase()) ||
      (p.farmer_name || p.farm || '').toLowerCase().includes(query.toLowerCase()) ||
      (p.description || '').toLowerCase().includes(query.toLowerCase())
    );

    displayProductSearchResults(filtered, query);
  }

  function displayProductSearchResults(searchResults, query) {
    renderProducts(searchResults, true); // compact view for search results

    if (searchResults.length > 0) {
      showSearchMessage('search-info',
        `Found ${searchResults.length} products for "${query}" (ordered by farmer name)`,
        'info'
      );
    } else {
      showSearchMessage('search-info',
        `No products found for "${query}". Try different keywords.`,
        'error'
      );
    }
  }

  // Tab switching
  productsTab.addEventListener('click', () => {
    productsTab.classList.add('active');
    farmersTab.classList.remove('active');
    productGrid.style.display = 'block';
    farmerGrid.style.display = 'none';
    searchInput.value = ''; // Clear search
    clearAllSearchMessages(); // Clear all search messages
    renderProducts(products, false);
  });

  farmersTab.addEventListener('click', () => {
    farmersTab.classList.add('active');
    productsTab.classList.remove('active');
    productGrid.style.display = 'none';
    farmerGrid.style.display = 'flex';
    searchInput.value = ''; // Clear search
    clearAllSearchMessages(); // Clear all search messages
    farmerCards.forEach(card => {
      card.style.display = 'block';
      card.classList.remove('compact');
    });
  });

  // Event listeners
  searchButton.addEventListener('click', handleSearch);
  searchInput.addEventListener('input', handleSearch);

  function activateTabFromHash() {
    if (window.location.hash === '#farmers') {
      farmersTab.click();
    } else {
      productsTab.click(); // default
    }
  }

  activateTabFromHash();
  renderProducts(products, false);
  enableLikeButtons();
  }); // End of initializeExistingFeatures

}); // End of DOMContentLoaded

function showDashboard(element) {
  const iframe = document.getElementById('dashboard-frame');
  const dashboard = document.getElementById('dashboard-content');

  // Show the dashboard content
  dashboard.style.display = 'block';
  // Hide the iframe
  iframe.style.display = 'none';
  iframe.src = '';

  // Update active class in sidebar
  setActiveLink(element);
}

function setActiveLink(element) {
  document.querySelectorAll('.nav-item').forEach(link => link.classList.remove('active'));
  if (element) element.classList.add('active');
}
function showFarmerTabs() {
  console.log('Showing farmer tabs');
  document.getElementById('purchase-tab').style.display = 'block';
  document.getElementById('chat-tab').style.display = 'block';
}

function hideFarmerTabs() {
  console.log('Hiding farmer tabs');
  document.getElementById('purchase-tab').style.display = 'none';
  document.getElementById('chat-tab').style.display = 'none';
}

function loadPage(pageUrl, element) {
  const iframe = document.getElementById('dashboard-frame');
  const dashboard = document.getElementById('dashboard-content');

  dashboard.style.display = 'none';
  iframe.style.display = 'block';
  iframe.src = pageUrl;
  setActiveLink(element);

  iframe.onload = function () {
    console.log('Iframe loaded:', iframe.src);
    if (iframe.src.endsWith('viewfarmerprofile.html')) {
      showFarmerTabs();
    } else {
      hideFarmerTabs();
    }
  };
}
// Duplicate function removed - keeping the original loadPage function above

// NEW function for iframe to call to show the dashboard
function showDashboardFromIframe() {
  const iframe = document.getElementById('dashboard-frame');
  const dashboard = document.getElementById('dashboard-content');

  iframe.style.display = 'none';
  iframe.src = ''; // clear iframe src to free memory
  dashboard.style.display = 'block';

  // Also hide purchase and chat tabs
  hideFarmerTabs();

  // Remove active class from all sidebar items since no page loaded now
  setActiveLink(null);
}

// Add logout functionality
function setupLogout() {
  const logoutButtons = document.querySelectorAll('.logout-btn, [data-action="logout"]');
  logoutButtons.forEach(button => {
    button.addEventListener('click', function(e) {
      e.preventDefault();

      if (confirm('Are you sure you want to logout?')) {
        window.BuyerAuth.logout();
      }
    });
  });
}

// Product action functions
async function viewProductDetails(listingId) {
  try {
    console.log('Viewing details for listing:', listingId);

    const response = await fetch(`http://localhost:8000/api/products/${listingId}/`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json'
      }
    });

    const data = await response.json();

    if (data.success) {
      showProductModal(data.product);
    } else {
      alert('Failed to load product details: ' + data.error);
    }
  } catch (error) {
    console.error('Error viewing product details:', error);
    alert('Network error. Please try again.');
  }
}

function showProductModal(product) {
  const modal = document.createElement('div');
  modal.className = 'product-modal';
  modal.innerHTML = `
    <div class="modal-overlay">
      <div class="modal-content enhanced">
        <div class="modal-header">
          <h2><i class="fas fa-seedling"></i> ${product.product_name}</h2>
          <button class="close-modal"><i class="fas fa-times"></i></button>
        </div>

        <div class="modal-body">
          <div class="product-showcase">
            <div class="product-image-section">
              <img src="${product.image_url || 'https://via.placeholder.com/400x300?text=No+Image'}"
                   alt="${product.product_name}"
                   class="product-main-image"
                   onerror="this.src='https://via.placeholder.com/400x300?text=No+Image'">
              <div class="image-badges">
                ${isRecentProduct(product.created_at) ? '<span class="badge new">NEW</span>' : ''}
                ${product.quantity < 10 ? '<span class="badge low-stock">Low Stock</span>' : ''}
                ${product.farmer.trust_badge ? '<span class="badge verified">Verified</span>' : ''}
              </div>
            </div>

            <div class="product-details-section">
              <div class="price-section">
                <div class="price-main">${product.price} FCFA</div>
                <div class="price-unit">per ${product.quantity_unit}</div>
              </div>

              <div class="availability-section">
                <div class="stock-info ${product.quantity < 10 ? 'low' : ''}">
                  <i class="fas fa-box"></i>
                  <span>${product.quantity} ${product.quantity_unit} available</span>
                </div>
              </div>

              <div class="product-info">
                <h4><i class="fas fa-info-circle"></i> Product Information</h4>
                <div class="info-grid">
                  <div class="info-item">
                    <label>Categories:</label>
                    <span>${product.categories ? product.categories.join(', ') : 'Not specified'}</span>
                  </div>
                  <div class="info-item">
                    <label>Description:</label>
                    <span>${product.description || 'No description available'}</span>
                  </div>
                </div>
              </div>

              <div class="farmer-info">
                <h4><i class="fas fa-user-tie"></i> Farmer Information</h4>
                <div class="farmer-card">
                  <div class="farmer-details">
                    <div class="farmer-name">
                      ${product.farmer.name}
                      ${product.farmer.trust_badge ? '<i class="fas fa-check-circle verified-icon"></i>' : ''}
                    </div>
                    <div class="farmer-location">
                      <i class="fas fa-map-marker-alt"></i> ${product.farmer.location || 'Location not specified'}
                    </div>
                    <div class="farmer-contact">
                      <i class="fas fa-phone"></i> ${product.farmer.phone || 'Contact not available'}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div class="reservation-section">
            <h4><i class="fas fa-shopping-cart"></i> Make a Reservation</h4>
            <div class="reservation-form">
              <div class="quantity-selector">
                <label for="reservation-quantity">Quantity:</label>
                <div class="quantity-input-group">
                  <button type="button" class="quantity-btn minus" onclick="adjustQuantity(-1)">-</button>
                  <input type="number" id="reservation-quantity" min="1" max="${product.quantity}" value="1">
                  <button type="button" class="quantity-btn plus" onclick="adjustQuantity(1)">+</button>
                  <span class="unit-label">${product.quantity_unit}</span>
                </div>
              </div>

              <div class="delivery-options">
                <label>Delivery Method:</label>
                <div class="radio-group">
                  <label class="radio-option">
                    <input type="radio" name="delivery-method" value="pickup" checked>
                    <span class="radio-custom"></span>
                    <i class="fas fa-store"></i> Pickup from Farmer
                  </label>
                  <label class="radio-option">
                    <input type="radio" name="delivery-method" value="delivery">
                    <span class="radio-custom"></span>
                    <i class="fas fa-truck"></i> Home Delivery
                  </label>
                </div>
              </div>

              <div class="total-calculation">
                <div class="total-row">
                  <span>Subtotal:</span>
                  <span class="subtotal">${product.price} FCFA</span>
                </div>
                <div class="total-row final">
                  <span>Total:</span>
                  <span class="total-amount">${product.price} FCFA</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div class="modal-footer">
          <button class="btn-secondary" onclick="closeProductModal()">
            <i class="fas fa-times"></i> Cancel
          </button>
          <button class="btn-chat" onclick="startChatWithFarmer(${product.farmer.farmer_id})">
            <i class="fas fa-comments"></i> Chat with Farmer
          </button>
          <button class="btn-reserve" onclick="processReservation(${product.listing_id})">
            <i class="fas fa-shopping-cart"></i> Reserve Now
          </button>
        </div>
      </div>
    </div>
  `;

  document.body.appendChild(modal);

  // Initialize modal functionality
  initializeProductModal(product);
}

function initializeProductModal(product) {
  const modal = document.querySelector('.product-modal');

  // Close modal functionality
  modal.querySelector('.close-modal').addEventListener('click', closeProductModal);
  modal.querySelector('.modal-overlay').addEventListener('click', (e) => {
    if (e.target.classList.contains('modal-overlay')) {
      closeProductModal();
    }
  });

  // Escape key to close
  document.addEventListener('keydown', function escapeHandler(e) {
    if (e.key === 'Escape') {
      closeProductModal();
      document.removeEventListener('keydown', escapeHandler);
    }
  });

  // Initialize quantity calculation
  updateTotalCalculation(product);

  // Add quantity input listener
  const quantityInput = modal.querySelector('#reservation-quantity');
  quantityInput.addEventListener('input', () => updateTotalCalculation(product));

  // Add delivery method listeners
  const deliveryRadios = modal.querySelectorAll('input[name="delivery-method"]');
  deliveryRadios.forEach(radio => {
    radio.addEventListener('change', () => updateTotalCalculation(product));
  });
}

function closeProductModal() {
  const modal = document.querySelector('.product-modal');
  if (modal) {
    modal.classList.add('closing');
    setTimeout(() => {
      document.body.removeChild(modal);
    }, 300);
  }
}

function adjustQuantity(change) {
  const quantityInput = document.getElementById('reservation-quantity');
  const currentValue = parseInt(quantityInput.value) || 1;
  const newValue = Math.max(1, Math.min(parseInt(quantityInput.max), currentValue + change));
  quantityInput.value = newValue;

  // Trigger update
  quantityInput.dispatchEvent(new Event('input'));
}

function updateTotalCalculation(product) {
  const quantityInput = document.getElementById('reservation-quantity');
  const quantity = parseInt(quantityInput.value) || 1;
  const deliveryMethod = document.querySelector('input[name="delivery-method"]:checked').value;

  const subtotal = product.price * quantity;
  const deliveryFee = deliveryMethod === 'delivery' ? 500 : 0; // 500 FCFA delivery fee
  const total = subtotal + deliveryFee;

  // Update display
  document.querySelector('.subtotal').textContent = `${subtotal} FCFA`;
  document.querySelector('.total-amount').textContent = `${total} FCFA`;

  // Show delivery fee if applicable
  let deliveryRow = document.querySelector('.delivery-fee-row');
  if (deliveryFee > 0) {
    if (!deliveryRow) {
      deliveryRow = document.createElement('div');
      deliveryRow.className = 'total-row delivery-fee-row';
      deliveryRow.innerHTML = '<span>Delivery Fee:</span><span class="delivery-fee">500 FCFA</span>';
      document.querySelector('.total-row.final').before(deliveryRow);
    }
  } else if (deliveryRow) {
    deliveryRow.remove();
  }
}

async function processReservation(listingId) {
  try {
    const quantityInput = document.getElementById('reservation-quantity');
    const quantity = parseInt(quantityInput.value) || 1;
    const deliveryMethod = document.querySelector('input[name="delivery-method"]:checked').value;

    // Validate quantity
    if (quantity < 1) {
      showModalError('Please enter a valid quantity');
      return;
    }

    // Show loading state
    const reserveBtn = document.querySelector('.btn-reserve');
    const originalText = reserveBtn.innerHTML;
    reserveBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';
    reserveBtn.disabled = true;

    // Call reservation API
    const reservationData = {
      listing_id: listingId,
      quantity: quantity,
      delivery_method: deliveryMethod,
      buyer_id: window.BuyerAuth.getUserId()
    };

    const response = await fetch('http://localhost:8000/api/reservations/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${window.BuyerAuth.getToken()}`
      },
      body: JSON.stringify(reservationData)
    });

    const data = await response.json();

    if (data.success) {
      showReservationSuccess(data);
      closeProductModal();
      // Refresh products to show updated quantities
      loadRealProducts();
    } else {
      showModalError(data.error || 'Failed to create reservation');
    }
  } catch (error) {
    console.error('Reservation error:', error);
    showModalError('Network error. Please try again.');
  } finally {
    // Reset button
    const reserveBtn = document.querySelector('.btn-reserve');
    if (reserveBtn) {
      reserveBtn.innerHTML = '<i class="fas fa-shopping-cart"></i> Reserve Now';
      reserveBtn.disabled = false;
    }
  }
}

function showModalError(message) {
  // Remove existing error messages
  const existingError = document.querySelector('.modal-error');
  if (existingError) existingError.remove();

  const errorDiv = document.createElement('div');
  errorDiv.className = 'modal-error';
  errorDiv.innerHTML = `
    <i class="fas fa-exclamation-triangle"></i>
    <span>${message}</span>
  `;

  const modalFooter = document.querySelector('.modal-footer');
  modalFooter.before(errorDiv);

  // Auto-remove after 5 seconds
  setTimeout(() => {
    if (errorDiv.parentNode) {
      errorDiv.remove();
    }
  }, 5000);
}

function showReservationSuccess(data) {
  // Create success notification
  const notification = document.createElement('div');
  notification.className = 'reservation-success-notification';
  notification.innerHTML = `
    <div class="notification-content">
      <div class="notification-icon">
        <i class="fas fa-check-circle"></i>
      </div>
      <div class="notification-text">
        <h4>Reservation Successful!</h4>
        <p>Your reservation has been sent to the farmer for approval.</p>
        <p><strong>Reservation ID:</strong> ${data.reservation.reservation_id}</p>
        <p><strong>Status:</strong> Pending Approval</p>
      </div>
      <button class="notification-close" onclick="closeNotification(this)">
        <i class="fas fa-times"></i>
      </button>
    </div>
  `;

  document.body.appendChild(notification);

  // Auto-remove after 8 seconds
  setTimeout(() => {
    if (notification.parentNode) {
      closeNotification(notification.querySelector('.notification-close'));
    }
  }, 8000);
}

function closeNotification(button) {
  const notification = button.closest('.reservation-success-notification');
  if (notification) {
    notification.classList.add('closing');
    setTimeout(() => {
      if (notification.parentNode) {
        notification.remove();
      }
    }, 300);
  }
}

async function startChatWithFarmer(farmerId) {
  // Close modal first
  closeProductModal();

  try {
    console.log(`Starting chat with farmer ID: ${farmerId}`);

    // Check if conversation already exists
    const response = await window.BuyerAuth.apiRequest('/messages/conversations/', {
      method: 'GET'
    });

    if (response && response.ok) {
      const data = await response.json();
      if (data.success) {
        const existingConversation = data.conversations.find(conv =>
          conv.other_participant && conv.other_participant.user_id === farmerId
        );

        if (existingConversation) {
          // Navigate to existing conversation
          sessionStorage.setItem('openConversationId', existingConversation.conversation_id);
        } else {
          // Store farmer ID to start new conversation
          sessionStorage.setItem('startChatWithFarmerId', farmerId);
        }
      }
    }

    // Navigate to chat page
    window.location.href = 'buyerchat.html';

  } catch (error) {
    console.error('Error starting chat:', error);
    // Fallback: just navigate to chat page
    sessionStorage.setItem('startChatWithFarmerId', farmerId);
    window.location.href = 'buyerchat.html';
  }
}

async function quickReserve(listingId) {
  try {
    // Find product in the global products array
    let product = null;
    if (window.products && window.products.length > 0) {
      product = window.products.find(p => p.listing_id == listingId);
    }

    if (!product) {
      // Fallback: fetch product details from API
      const response = await fetch(`http://localhost:8000/api/products/${listingId}/`);
      const data = await response.json();
      if (data.success) {
        product = data.product;
      } else {
        alert('Product not found');
        return;
      }
    }

    const quantity = prompt(`How many ${product.quantity_unit} of ${product.product_name} would you like to reserve?\n\nAvailable: ${product.quantity} ${product.quantity_unit}`);

    if (quantity && !isNaN(quantity) && quantity > 0) {
      if (quantity > product.quantity) {
        alert(`Sorry, only ${product.quantity} ${product.quantity_unit} available.`);
        return;
      }

      // Here you would call the reservation API
      console.log(`Reserving ${quantity} ${product.quantity_unit} of ${product.product_name}`);
      alert(`Reservation request sent for ${quantity} ${product.quantity_unit} of ${product.product_name}!\n\nThe farmer will be notified and you'll receive a confirmation soon.`);

      // Optionally reload products to show updated quantities
      loadRealProducts();
    }
  } catch (error) {
    console.error('Error making reservation:', error);
    alert('Failed to make reservation. Please try again.');
  }
}

// Duplicate function removed - keeping the original startChatWithFarmer function above

// Search utility functions
function showSearchLoading(message = 'Searching...') {
  const loadingDiv = document.createElement('div');
  loadingDiv.id = 'search-loading';
  loadingDiv.style.cssText = `
    text-align: center;
    padding: 40px;
    color: #666;
    background: #f8f9fa;
    border-radius: 8px;
    margin: 20px 0;
  `;
  loadingDiv.innerHTML = `
    <i class="fas fa-spinner fa-spin" style="font-size: 24px; color: #77c34f; margin-bottom: 10px;"></i>
    <p style="margin: 0; font-size: 16px;">${message}</p>
  `;

  // Insert at the top of the active grid
  const activeGrid = farmersTab.classList.contains('active') ? farmerGrid : productGrid;
  activeGrid.insertBefore(loadingDiv, activeGrid.firstChild);
}

function hideSearchLoading() {
  const loadingDiv = document.getElementById('search-loading');
  if (loadingDiv) {
    loadingDiv.remove();
  }
}

function showSearchMessage(id, message, type = 'info') {
  removeSearchMessage(id);

  const messageDiv = document.createElement('div');
  messageDiv.id = id;

  const styles = {
    info: 'background: #e8f5e8; border-left: 4px solid #77c34f; color: #2d5a2d;',
    error: 'background: #f8d7da; border-left: 4px solid #dc3545; color: #721c24;',
    warning: 'background: #fff3cd; border-left: 4px solid #ffc107; color: #856404;'
  };

  messageDiv.style.cssText = `
    margin: 20px 0;
    padding: 15px;
    border-radius: 5px;
    ${styles[type] || styles.info}
    font-weight: 500;
  `;

  const icon = {
    info: '<i class="fas fa-info-circle"></i>',
    error: '<i class="fas fa-exclamation-triangle"></i>',
    warning: '<i class="fas fa-exclamation-circle"></i>'
  };

  messageDiv.innerHTML = `${icon[type] || icon.info} ${message}`;

  // Insert at the top of the active grid
  const activeGrid = farmersTab.classList.contains('active') ? farmerGrid : productGrid;
  activeGrid.insertBefore(messageDiv, activeGrid.firstChild);
}

function removeSearchMessage(id) {
  const messageDiv = document.getElementById(id);
  if (messageDiv) {
    messageDiv.remove();
  }
}

function clearAllSearchMessages() {
  removeSearchMessage('search-info');
  removeSearchMessage('no-match-msg');
  removeSearchMessage('search-loading');
}

// Notification System (variables declared at top of file)

function initializeNotificationSystem() {
  // Load initial notifications
  loadNotifications();

  // Set up periodic checking for new notifications
  notificationCheckInterval = setInterval(loadNotifications, 30000); // Check every 30 seconds

  // Close notification dropdown when clicking outside
  document.addEventListener('click', (e) => {
    const dropdown = document.getElementById('notification-dropdown');
    const bell = document.querySelector('.notification-bell');

    if (!dropdown.contains(e.target) && !bell.contains(e.target)) {
      dropdown.style.display = 'none';
    }
  });
}

async function loadNotifications() {
  try {
    const response = await fetch('http://localhost:8000/api/buyer/notifications/', {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${window.BuyerAuth.getToken()}`
      }
    });

    const data = await response.json();

    if (data.success) {
      notifications = data.notifications;
      updateNotificationUI();
    }
  } catch (error) {
    console.error('Error loading notifications:', error);
  }
}

function updateNotificationUI() {
  const countElement = document.getElementById('notification-count');
  const listElement = document.getElementById('notification-list');

  // Count unread notifications
  const unreadCount = notifications.filter(n => !n.is_read).length;

  // Update notification count
  if (unreadCount > 0) {
    countElement.textContent = unreadCount > 99 ? '99+' : unreadCount;
    countElement.style.display = 'block';
  } else {
    countElement.style.display = 'none';
  }

  // Update notification list
  if (notifications.length === 0) {
    listElement.innerHTML = `
      <div class="no-notifications">
        <i class="fas fa-bell-slash"></i>
        <p>No new notifications</p>
      </div>
    `;
  } else {
    listElement.innerHTML = notifications.map(notification => `
      <div class="notification-item ${notification.is_read ? 'read' : 'unread'}"
           data-notification-id="${notification.notification_id}">
        <div class="notification-icon ${getNotificationIconClass(notification.notification_type)}">
          <i class="${getNotificationIcon(notification.notification_type)}"></i>
        </div>
        <div class="notification-content">
          <div class="notification-title">${notification.title}</div>
          <div class="notification-message">${notification.message}</div>
          <div class="notification-time">${formatNotificationTime(notification.created_at)}</div>
        </div>
        ${!notification.is_read ? '<div class="unread-indicator"></div>' : ''}
      </div>
    `).join('');

    // Add click handlers for notifications
    document.querySelectorAll('.notification-item').forEach(item => {
      item.addEventListener('click', () => {
        const notificationId = item.getAttribute('data-notification-id');
        handleNotificationClick(notificationId);
      });
    });
  }
}

function getNotificationIconClass(type) {
  const iconClasses = {
    'reservation_approved': 'success',
    'reservation_rejected': 'error',
    'reservation_pending': 'info',
    'new_message': 'message',
    'product_available': 'product',
    'urgent_sale': 'urgent'
  };
  return iconClasses[type] || 'info';
}

function getNotificationIcon(type) {
  const icons = {
    'reservation_approved': 'fas fa-check-circle',
    'reservation_rejected': 'fas fa-times-circle',
    'reservation_pending': 'fas fa-clock',
    'new_message': 'fas fa-comment',
    'product_available': 'fas fa-seedling',
    'urgent_sale': 'fas fa-bolt'
  };
  return icons[type] || 'fas fa-info-circle';
}

function formatNotificationTime(timestamp) {
  const date = new Date(timestamp);
  const now = new Date();
  const diffMs = now - date;
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString();
}

function toggleNotifications() {
  const dropdown = document.getElementById('notification-dropdown');
  const isVisible = dropdown.style.display === 'block';

  if (isVisible) {
    dropdown.style.display = 'none';
  } else {
    dropdown.style.display = 'block';
    // Mark notifications as read when opened
    markVisibleNotificationsAsRead();
  }
}

async function markVisibleNotificationsAsRead() {
  const unreadNotifications = notifications.filter(n => !n.is_read);

  if (unreadNotifications.length === 0) return;

  try {
    const response = await fetch('http://localhost:8000/api/buyer/notifications/mark-read/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${window.BuyerAuth.getToken()}`
      },
      body: JSON.stringify({
        notification_ids: unreadNotifications.map(n => n.notification_id)
      })
    });

    if (response.ok) {
      // Update local notifications
      notifications.forEach(n => n.is_read = true);
      updateNotificationUI();
    }
  } catch (error) {
    console.error('Error marking notifications as read:', error);
  }
}

async function markAllNotificationsRead() {
  try {
    const response = await fetch('http://localhost:8000/api/buyer/notifications/mark-all-read/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${window.BuyerAuth.getToken()}`
      }
    });

    if (response.ok) {
      notifications.forEach(n => n.is_read = true);
      updateNotificationUI();
    }
  } catch (error) {
    console.error('Error marking all notifications as read:', error);
  }
}

function handleNotificationClick(notificationId) {
  const notification = notifications.find(n => n.notification_id == notificationId);
  if (!notification) return;

  // Handle different notification types
  switch (notification.notification_type) {
    case 'reservation_approved':
    case 'reservation_rejected':
    case 'reservation_pending':
      // Navigate to purchase history
      document.querySelector('a[onclick*="purchasehistory.html"]').click();
      break;
    case 'new_message':
      // Navigate to chat
      const chatTab = document.getElementById('chat-tab');
      if (chatTab) chatTab.click();
      break;
    case 'product_available':
    case 'urgent_sale':
      // Navigate to marketplace
      document.querySelector('a[onclick*="showDashboard"]').click();
      break;
  }

  // Close dropdown
  document.getElementById('notification-dropdown').style.display = 'none';
}

// Initialize logout functionality when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
  setupLogout();
  initializeNotificationSystem();
});

