document.addEventListener('DOMContentLoaded', function () {
  const productGrid = document.querySelector('.product-grid');
  const farmerGrid = document.querySelector('.farmer-grid');
  const searchButton = document.querySelector('.search-bar button');
  const searchInput = document.querySelector('.search-bar input');
  const farmerCards = document.querySelectorAll('.farmer-card');
  const productsTab = document.getElementById('products-tab');
  const farmersTab = document.getElementById('farmers-tab');
  

  const products = [
    {
      name: 'Tomatoes',
      farm: 'Kwame Organic Farms',
      price: '500FCFA/kg',
      freshness: 'Harvested Today'
    }
  ];

  function enableLikeButtons() {
    document.querySelectorAll('.like, .favorite-icon').forEach(button => {
      button.addEventListener('click', () => {
        button.classList.toggle('liked');
        button.style.color = button.classList.contains('liked') ? 'red' : '#999';
      });
    });
  }

  function renderProducts(filteredProducts = products, compact = false) {
    productGrid.innerHTML = '';
    filteredProducts.forEach(product => {
      const card = document.createElement('div');
card.className = 'product-card' + (compact ? ' compact' : '');


      if (compact) {
        card.innerHTML = `
          <div class="product-image">Product Image</div>
          <div class="product-info">
            <h3>${product.name}</h3>
          </div>
          <div class="product-actions">
            <a href="#" onclick="loadPage('reserveproduct.html',this)" class="reserve">Purchase</a>
            <button class="like">♡</button>
          </div>
        `;
      } else {
        card.innerHTML = `
          <div class="product-image">Product Image</div>
          <div class="product-info">
            <h3>${product.name}</h3>
            <p>${product.farm}</p>
            <p><strong>${product.price}</strong> · ${product.freshness}</p>
          </div>
          <div class="product-actions">
            <a href="#" onclick="loadPage('reserveproduct.html',this)" class="reserve">Purchase</a>
            <button class="like">♡</button>
          </div>
        `;
      }

      productGrid.appendChild(card);
    });

    const existingMsg = document.getElementById('no-product-match-msg');
    if (filteredProducts.length === 0) {
      if (!existingMsg) {
        const msg = document.createElement('p');
        msg.id = 'no-product-match-msg';
        msg.textContent = 'No product matches found.';
        msg.style.color = 'red';
        msg.style.fontWeight = 'bold';
        msg.style.marginTop = '20px';
        productGrid.appendChild(msg);
      }
    } else {
      if (existingMsg) existingMsg.remove();
    }

    enableLikeButtons();
  }

  function handleSearch() {
    const query = searchInput.value.trim().toLowerCase();

    if (farmersTab.classList.contains('active')) {
      let matchFound = false;

      farmerCards.forEach(card => {
        const text = card.textContent.toLowerCase();
        if (text.includes(query)) {
          card.style.display = 'block';
          card.classList.add('compact');
          matchFound = true;
        } else {
          card.style.display = 'none';
          card.classList.remove('compact');
        }
      });

      const existingMsg = document.getElementById('no-match-msg');
      if (!matchFound) {
        if (!existingMsg) {
          const msg = document.createElement('p');
          msg.id = 'no-match-msg';
          msg.textContent = 'No farmer matches found.';
          msg.style.color = 'red';
          msg.style.fontWeight = 'bold';
          msg.style.marginTop = '20px';
          farmerGrid.appendChild(msg);
        }
      } else if (existingMsg) {
        existingMsg.remove();
      }

      if (query === '') {
        farmerCards.forEach(card => {
          card.style.display = 'block';
          card.classList.remove('compact');
        });
        if (existingMsg) existingMsg.remove();
      }

    } else if (productsTab.classList.contains('active')) {
      if (query === '') {
        renderProducts(products, false); // full view
        return;
      }

      const filtered = products.filter(p =>
        p.name.toLowerCase().includes(query) ||
        p.farm.toLowerCase().includes(query) ||
        p.freshness.toLowerCase().includes(query)
      );

      renderProducts(filtered, true); // compact view
    }
  }

  // Tab switching
  productsTab.addEventListener('click', () => {
    productsTab.classList.add('active');
    farmersTab.classList.remove('active');
    productGrid.style.display = 'block';
    farmerGrid.style.display = 'none';
    searchInput.value = ''; // Clear search
    renderProducts(products, false);
    const msg = document.getElementById('no-match-msg');
    if (msg) msg.remove();
  });

  farmersTab.addEventListener('click', () => {
    farmersTab.classList.add('active');
    productsTab.classList.remove('active');
    productGrid.style.display = 'none';
    farmerGrid.style.display = 'flex';
    searchInput.value = ''; // Clear search
    farmerCards.forEach(card => {
      card.style.display = 'block';
      card.classList.remove('compact');
    });
    const msg = document.getElementById('no-product-match-msg');
    if (msg) msg.remove();
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
});
function loadPage(pageUrl, element) {
  const iframe = document.getElementById('dashboard-frame');
  const dashboard = document.getElementById('dashboard-content');

  // Hide the dashboard content
  dashboard.style.display = 'none';
  // Show the iframe and load the page
  iframe.style.display = 'block';
  iframe.src = pageUrl;

  // Update active class in sidebar
  setActiveLink(element);
}

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

