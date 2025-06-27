// Purchase History Management JavaScript
const API_BASE_URL = 'http://localhost:8000/api';

// Global variables
let currentPage = 1;
let currentFilter = 'all';
let isLoading = false;

document.addEventListener('DOMContentLoaded', function() {
    // Check authentication
    if (!window.BuyerAuth || !window.BuyerAuth.isAuthenticated()) {
        window.location.href = 'loginbuyer.html';
        return;
    }
    
    // Initialize purchase history page
    initializePurchaseHistory();
});

async function initializePurchaseHistory() {
    try {
        // Setup event listeners
        setupEventListeners();
        
        // Load purchase history data
        await loadPurchaseHistory();
        
        console.log('Purchase history page initialized successfully');
    } catch (error) {
        console.error('Failed to initialize purchase history:', error);
        showError('Failed to load purchase history. Please refresh the page.');
    }
}

function setupEventListeners() {
    // Filter buttons
    const filterButtons = document.querySelectorAll('.filter-btn');
    filterButtons.forEach(btn => {
        btn.addEventListener('click', function() {
            const filter = this.dataset.filter;
            setActiveFilter(filter);
            loadPurchaseHistory(1, filter);
        });
    });
    
    // Date filters
    const dateFromInput = document.getElementById('dateFrom');
    const dateToInput = document.getElementById('dateTo');
    
    if (dateFromInput) {
        dateFromInput.addEventListener('change', () => loadPurchaseHistory());
    }
    
    if (dateToInput) {
        dateToInput.addEventListener('change', () => loadPurchaseHistory());
    }
    
    // Search functionality
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        let searchTimeout;
        searchInput.addEventListener('input', function() {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                loadPurchaseHistory();
            }, 300);
        });
    }
}

function setActiveFilter(filter) {
    // Update active filter button
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    
    document.querySelector(`[data-filter="${filter}"]`).classList.add('active');
    currentFilter = filter;
}

async function loadPurchaseHistory(page = 1, statusFilter = null) {
    if (isLoading) return;
    
    try {
        isLoading = true;
        showLoading(true);
        
        // Build query parameters
        const params = new URLSearchParams({
            page: page,
            per_page: 20,
            status: statusFilter || currentFilter
        });
        
        // Add date filters if present
        const dateFrom = document.getElementById('dateFrom')?.value;
        const dateTo = document.getElementById('dateTo')?.value;
        
        if (dateFrom) params.append('date_from', dateFrom);
        if (dateTo) params.append('date_to', dateTo);
        
        const response = await window.BuyerAuth.apiRequest(`/buyer/purchase-history/?${params}`, {
            method: 'GET'
        });
        
        if (response && response.ok) {
            const data = await response.json();
            if (data.success) {
                displayPurchaseHistory(data.purchase_history);
                displaySummary(data.summary);
                displayPagination(data.pagination);
                currentPage = page;
            } else {
                throw new Error(data.error || 'Failed to load purchase history');
            }
        } else {
            throw new Error('Failed to fetch purchase history');
        }
    } catch (error) {
        console.error('Error loading purchase history:', error);
        showError('Failed to load purchase history: ' + error.message);
        displayEmptyState();
    } finally {
        isLoading = false;
        showLoading(false);
    }
}

function displayPurchaseHistory(purchases) {
    const tbody = document.querySelector('table tbody');
    if (!tbody) {
        console.error('Purchase history table not found');
        return;
    }
    
    // Clear existing content
    tbody.innerHTML = '';
    
    if (purchases.length === 0) {
        displayEmptyState();
        return;
    }
    
    purchases.forEach(purchase => {
        const row = createPurchaseRow(purchase);
        tbody.appendChild(row);
    });
}

function createPurchaseRow(purchase) {
    const row = document.createElement('tr');
    row.className = 'purchase-row';
    
    // Format date
    const date = new Date(purchase.date).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
    
    // Status badge
    const statusClass = getStatusClass(purchase.status);
    
    row.innerHTML = `
        <td>
            <div class="date-info">
                <div class="date">${date}</div>
                <div class="time">${purchase.time}</div>
            </div>
        </td>
        <td>
            <div class="product-info">
                <div class="product-name">${purchase.product_name}</div>
                <div class="product-details">${purchase.quantity} units</div>
                ${purchase.category ? `<div class="category">${purchase.category}</div>` : ''}
            </div>
        </td>
        <td>
            <div class="farmer-info">
                <div class="farmer-name">${purchase.farmer_name}</div>
                <div class="farmer-username">@${purchase.farmer_username}</div>
            </div>
        </td>
        <td>
            <div class="amount-info">
                <div class="total-amount">${purchase.total_amount} FCFA</div>
                <div class="unit-price">${purchase.unit_price} FCFA/unit</div>
            </div>
        </td>
        <td>
            <span class="status ${statusClass}">${purchase.status}</span>
            ${purchase.transaction_status !== 'No Transaction' ? 
                `<div class="transaction-status">${purchase.transaction_status}</div>` : ''}
        </td>
        <td>
            <div class="actions">
                <button class="btn-view" onclick="viewPurchaseDetails('${purchase.reservation_id}')">
                    View Details
                </button>
                ${purchase.receipt_url ? 
                    `<button class="btn-receipt" onclick="downloadReceipt('${purchase.receipt_url}')">
                        Receipt
                    </button>` : ''}
            </div>
        </td>
    `;
    
    return row;
}

function getStatusClass(status) {
    const statusClasses = {
        'Pending': 'pending',
        'Approved': 'approved',
        'Completed': 'completed',
        'Rejected': 'rejected',
        'Delivered': 'delivered'
    };
    return statusClasses[status] || 'pending';
}

function displaySummary(summary) {
    // Update summary cards if they exist
    const summaryElements = {
        'total-purchases': summary.total_purchases,
        'pending-count': summary.pending_count,
        'approved-count': summary.approved_count,
        'completed-count': summary.completed_count,
        'total-spent': `${summary.total_spent} FCFA`
    };
    
    Object.keys(summaryElements).forEach(id => {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = summaryElements[id];
        }
    });
}

function displayPagination(pagination) {
    const paginationContainer = document.getElementById('pagination');
    if (!paginationContainer) return;
    
    let paginationHTML = '';
    
    // Previous button
    if (pagination.has_previous) {
        paginationHTML += `
            <button class="pagination-btn" onclick="loadPurchaseHistory(${pagination.current_page - 1})">
                Previous
            </button>
        `;
    }
    
    // Page numbers
    const startPage = Math.max(1, pagination.current_page - 2);
    const endPage = Math.min(pagination.total_pages, pagination.current_page + 2);
    
    for (let i = startPage; i <= endPage; i++) {
        const activeClass = i === pagination.current_page ? 'active' : '';
        paginationHTML += `
            <button class="pagination-btn ${activeClass}" onclick="loadPurchaseHistory(${i})">
                ${i}
            </button>
        `;
    }
    
    // Next button
    if (pagination.has_next) {
        paginationHTML += `
            <button class="pagination-btn" onclick="loadPurchaseHistory(${pagination.current_page + 1})">
                Next
            </button>
        `;
    }
    
    paginationContainer.innerHTML = paginationHTML;
}

function displayEmptyState() {
    const tbody = document.querySelector('table tbody');
    if (!tbody) return;
    
    tbody.innerHTML = `
        <tr>
            <td colspan="6" class="empty-state">
                <div class="empty-message">
                    <h3>No Purchase History Found</h3>
                    <p>You haven't made any purchases yet or no purchases match your current filter.</p>
                    <button class="btn-primary" onclick="window.location.href='buyerdashboard.html'">
                        Start Shopping
                    </button>
                </div>
            </td>
        </tr>
    `;
}

function viewPurchaseDetails(reservationId) {
    // TODO: Implement purchase details modal
    console.log('Viewing details for reservation:', reservationId);
    alert('Purchase details feature will be implemented soon!');
}

function downloadReceipt(receiptUrl) {
    if (receiptUrl) {
        window.open(receiptUrl, '_blank');
    } else {
        alert('Receipt not available for this purchase.');
    }
}

function showLoading(show) {
    const loadingElement = document.getElementById('loading');
    if (loadingElement) {
        loadingElement.style.display = show ? 'block' : 'none';
    }
    
    // Disable/enable filter buttons
    const filterButtons = document.querySelectorAll('.filter-btn');
    filterButtons.forEach(btn => {
        btn.disabled = show;
    });
}

function showError(message) {
    // Create or update error message
    let errorElement = document.getElementById('error-message');
    if (!errorElement) {
        errorElement = document.createElement('div');
        errorElement.id = 'error-message';
        errorElement.className = 'error-message';
        document.querySelector('.container').insertBefore(errorElement, document.querySelector('.card'));
    }
    
    errorElement.innerHTML = `
        <div class="error-content">
            <i class="fas fa-exclamation-triangle"></i>
            <span>${message}</span>
            <button onclick="this.parentElement.parentElement.remove()">×</button>
        </div>
    `;
    
    // Auto-hide after 5 seconds
    setTimeout(() => {
        if (errorElement.parentNode) {
            errorElement.remove();
        }
    }, 5000);
}

// Export functions for global access
window.loadPurchaseHistory = loadPurchaseHistory;
window.viewPurchaseDetails = viewPurchaseDetails;
window.downloadReceipt = downloadReceipt;
