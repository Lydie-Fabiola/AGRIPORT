// Get tab buttons and content sections
const productsTabBtn = document.getElementById('products-tab');
const farmersTabBtn = document.getElementById('farmers-tab');
const productsSection = document.getElementById('products-section');
const farmersSection = document.getElementById('farmers-section');

// Function to switch to Products tab
function showProducts() {
  productsTabBtn.classList.add('active');
  farmersTabBtn.classList.remove('active');
  productsSection.style.display = 'flex';
  farmersSection.style.display = 'none';
}

// Function to switch to Farmers tab
function showFarmers() {
  farmersTabBtn.classList.add('active');
  productsTabBtn.classList.remove('active');
  farmersSection.style.display = 'flex';
  productsSection.style.display = 'none';
}

// Event listeners for tab buttons
productsTabBtn.addEventListener('click', showProducts);
farmersTabBtn.addEventListener('click', showFarmers);

// Initialize default view
showProducts();
