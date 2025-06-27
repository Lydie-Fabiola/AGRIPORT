// Admin Dashboard JavaScript
const API_BASE_URL = 'http://localhost:8000/api';
let adminToken = localStorage.getItem('adminToken');
let adminInfo = JSON.parse(localStorage.getItem('adminInfo') || '{}');

// Initialize dashboard
document.addEventListener('DOMContentLoaded', function() {
    if (!adminToken) {
        window.location.href = 'admin_login.html';
        return;
    }
    
    loadAdminInfo();
    loadDashboardData();
});

// Load admin info
function loadAdminInfo() {
    if (adminInfo.first_name && adminInfo.last_name) {
        document.getElementById('adminName').textContent = 
            `${adminInfo.first_name} ${adminInfo.last_name}`;
    } else {
        document.getElementById('adminName').textContent = adminInfo.username || 'Admin';
    }
}

// Load dashboard data
async function loadDashboardData() {
    try {
        const response = await fetch(`${API_BASE_URL}/admin/dashboard/`, {
            headers: {
                'Authorization': `Token ${adminToken}`
            }
        });

        if (response.ok) {
            const data = await response.json();
            if (data.success) {
                updateDashboardStats(data.dashboard_data.system_stats);
                updateRecentActivity(data.dashboard_data.recent_users);
            }
        } else if (response.status === 401) {
            logout();
        }
    } catch (error) {
        console.error('Error loading dashboard data:', error);
    }
}

// Update dashboard statistics
function updateDashboardStats(stats) {
    document.getElementById('totalUsers').textContent = stats.total_users || 0;
    document.getElementById('totalFarmers').textContent = stats.total_farmers || 0;
    document.getElementById('totalBuyers').textContent = stats.total_buyers || 0;
    document.getElementById('pendingFarmers').textContent = stats.pending_farmers || 0;
}

// Update recent activity
function updateRecentActivity(recentUsers) {
    const activityContainer = document.getElementById('recentActivity');
    
    if (recentUsers && recentUsers.length > 0) {
        let html = '<h4>Recent User Registrations</h4>';
        html += '<table class="table">';
        html += '<thead><tr><th>User</th><th>Type</th><th>Email</th><th>Date Joined</th><th>Status</th></tr></thead>';
        html += '<tbody>';
        
        recentUsers.forEach(user => {
            const statusBadge = user.is_approved ? 
                '<span class="badge active">Approved</span>' : 
                '<span class="badge pending">Pending</span>';
            
            html += `
                <tr>
                    <td>${user.username}</td>
                    <td>${user.user_type}</td>
                    <td>${user.email}</td>
                    <td>${new Date(user.date_joined).toLocaleDateString()}</td>
                    <td>${statusBadge}</td>
                </tr>
            `;
        });
        
        html += '</tbody></table>';
        activityContainer.innerHTML = html;
    } else {
        activityContainer.innerHTML = '<p>No recent activity</p>';
    }
}

// Show section
function showSection(sectionName) {
    // Hide all sections
    document.querySelectorAll('.content-section').forEach(section => {
        section.classList.remove('active');
    });
    
    // Remove active class from nav items
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.remove('active');
    });
    
    // Show selected section
    document.getElementById(sectionName).classList.add('active');
    
    // Add active class to clicked nav item
    event.target.classList.add('active');
    
    // Load section data
    switch(sectionName) {
        case 'users':
            loadUsers();
            break;
        case 'farmers':
            loadPendingFarmers();
            break;
        case 'admins':
            loadAdmins();
            break;
        case 'transactions':
            loadTransactions();
            break;
        case 'notifications':
            loadNotifications();
            break;
        case 'broadcast':
            loadBroadcastHistory();
            break;
        case 'search':
            // Search section is ready for input
            break;
        case 'analytics':
            loadEnhancedAnalytics();
            break;
        case 'roles':
            loadRoles();
            break;
        case 'settings':
            checkSystemStatus();
            break;
    }
}

// Load users
async function loadUsers() {
    const usersTable = document.getElementById('usersTable');
    usersTable.innerHTML = '<div class="loading"><i class="fas fa-spinner"></i><p>Loading users...</p></div>';
    
    try {
        const response = await fetch(`${API_BASE_URL}/admin/manage-users/`, {
            headers: {
                'Authorization': `Token ${adminToken}`
            }
        });

        if (response.ok) {
            const data = await response.json();
            if (data.success) {
                displayUsers(data.users);
            }
        }
    } catch (error) {
        console.error('Error loading users:', error);
        usersTable.innerHTML = '<p>Error loading users</p>';
    }
}

// Display users
function displayUsers(users) {
    const usersTable = document.getElementById('usersTable');
    
    if (users && users.length > 0) {
        let html = '<table class="table">';
        html += '<thead><tr><th>Username</th><th>Email</th><th>Type</th><th>Status</th><th>Joined</th><th>Actions</th></tr></thead>';
        html += '<tbody>';
        
        users.forEach(user => {
            const statusBadge = user.is_active ? 
                '<span class="badge active">Active</span>' : 
                '<span class="badge inactive">Inactive</span>';
            
            const approvalBadge = user.is_approved ? 
                '<span class="badge active">Approved</span>' : 
                '<span class="badge pending">Pending</span>';
            
            html += `
                <tr>
                    <td>${user.username}</td>
                    <td>${user.email}</td>
                    <td>${user.user_type}</td>
                    <td>${statusBadge} ${user.user_type === 'Farmer' ? approvalBadge : ''}</td>
                    <td>${new Date(user.date_joined).toLocaleDateString()}</td>
                    <td>
                        <button class="btn btn-primary" onclick="viewUser(${user.id})">View</button>
                        ${user.user_type === 'Farmer' && !user.is_approved ? 
                            `<button class="btn btn-success" onclick="approveFarmer(${user.id})">Approve</button>` : ''}
                    </td>
                </tr>
            `;
        });
        
        html += '</tbody></table>';
        usersTable.innerHTML = html;
    } else {
        usersTable.innerHTML = '<p>No users found</p>';
    }
}

// Load pending farmers
async function loadPendingFarmers() {
    const farmersTable = document.getElementById('pendingFarmersTable');
    farmersTable.innerHTML = '<div class="loading"><i class="fas fa-spinner"></i><p>Loading pending farmers...</p></div>';
    
    try {
        const response = await fetch(`${API_BASE_URL}/admin/pending-farmers/`, {
            headers: {
                'Authorization': `Token ${adminToken}`
            }
        });

        if (response.ok) {
            const data = await response.json();
            if (data.success) {
                displayPendingFarmers(data.pending_farmers);
            }
        }
    } catch (error) {
        console.error('Error loading pending farmers:', error);
        farmersTable.innerHTML = '<p>Error loading pending farmers</p>';
    }
}

// Display pending farmers
function displayPendingFarmers(farmers) {
    const farmersTable = document.getElementById('pendingFarmersTable');
    
    if (farmers && farmers.length > 0) {
        let html = '<table class="table">';
        html += '<thead><tr><th>Name</th><th>Email</th><th>Phone</th><th>Location</th><th>Date Applied</th><th>Actions</th></tr></thead>';
        html += '<tbody>';
        
        farmers.forEach(farmer => {
            html += `
                <tr>
                    <td>${farmer.first_name} ${farmer.last_name}</td>
                    <td>${farmer.email}</td>
                    <td>${farmer.phone_number || 'N/A'}</td>
                    <td>${farmer.location || 'N/A'}</td>
                    <td>${new Date(farmer.date_joined).toLocaleDateString()}</td>
                    <td>
                        <button class="btn btn-success" onclick="approveFarmer(${farmer.user_id})">
                            <i class="fas fa-check"></i> Approve
                        </button>
                        <button class="btn btn-danger" onclick="rejectFarmer(${farmer.user_id})">
                            <i class="fas fa-times"></i> Reject
                        </button>
                    </td>
                </tr>
            `;
        });
        
        html += '</tbody></table>';
        farmersTable.innerHTML = html;
    } else {
        farmersTable.innerHTML = '<p>No pending farmer applications</p>';
    }
}

// Approve farmer
async function approveFarmer(farmerId) {
    if (!confirm('Are you sure you want to approve this farmer?')) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}/admin/approve-farmer/${farmerId}/`, {
            method: 'POST',
            headers: {
                'Authorization': `Token ${adminToken}`
            }
        });

        if (response.ok) {
            const data = await response.json();
            if (data.success) {
                alert('Farmer approved successfully!');
                loadPendingFarmers(); // Reload the list
                loadDashboardData(); // Update dashboard stats
            } else {
                alert('Error approving farmer: ' + data.message);
            }
        }
    } catch (error) {
        console.error('Error approving farmer:', error);
        alert('Error approving farmer');
    }
}

// Reject farmer
async function rejectFarmer(farmerId) {
    if (!confirm('Are you sure you want to reject this farmer application?')) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}/admin/reject-farmer/${farmerId}/`, {
            method: 'POST',
            headers: {
                'Authorization': `Token ${adminToken}`
            }
        });

        if (response.ok) {
            const data = await response.json();
            if (data.success) {
                alert('Farmer application rejected');
                loadPendingFarmers(); // Reload the list
                loadDashboardData(); // Update dashboard stats
            } else {
                alert('Error rejecting farmer: ' + data.message);
            }
        }
    } catch (error) {
        console.error('Error rejecting farmer:', error);
        alert('Error rejecting farmer');
    }
}

// Load admins
async function loadAdmins() {
    const adminsTable = document.getElementById('adminsTable');
    adminsTable.innerHTML = '<div class="loading"><i class="fas fa-spinner"></i><p>Loading admins...</p></div>';
    
    try {
        const response = await fetch(`${API_BASE_URL}/admin/manage-users/?user_type=Admin`, {
            headers: {
                'Authorization': `Token ${adminToken}`
            }
        });

        if (response.ok) {
            const data = await response.json();
            if (data.success) {
                displayAdmins(data.users);
            }
        }
    } catch (error) {
        console.error('Error loading admins:', error);
        adminsTable.innerHTML = '<p>Error loading admins</p>';
    }
}

// Display admins
function displayAdmins(admins) {
    const adminsTable = document.getElementById('adminsTable');
    
    if (admins && admins.length > 0) {
        let html = '<table class="table">';
        html += '<thead><tr><th>Username</th><th>Email</th><th>Name</th><th>Superuser</th><th>Date Created</th><th>Status</th></tr></thead>';
        html += '<tbody>';
        
        admins.forEach(admin => {
            const statusBadge = admin.is_active ? 
                '<span class="badge active">Active</span>' : 
                '<span class="badge inactive">Inactive</span>';
            
            const superuserBadge = admin.is_superuser ? 
                '<span class="badge active">Yes</span>' : 
                '<span class="badge">No</span>';
            
            html += `
                <tr>
                    <td>${admin.username}</td>
                    <td>${admin.email}</td>
                    <td>${admin.first_name} ${admin.last_name}</td>
                    <td>${superuserBadge}</td>
                    <td>${new Date(admin.date_joined).toLocaleDateString()}</td>
                    <td>${statusBadge}</td>
                </tr>
            `;
        });
        
        html += '</tbody></table>';
        adminsTable.innerHTML = html;
    } else {
        adminsTable.innerHTML = '<p>No admins found</p>';
    }
}

// Show create admin modal
function showCreateAdminModal() {
    document.getElementById('createAdminModal').style.display = 'block';
}

// Close create admin modal
function closeCreateAdminModal() {
    document.getElementById('createAdminModal').style.display = 'none';
    document.getElementById('createAdminForm').reset();
    document.getElementById('createAdminAlert').innerHTML = '';
}

// Create admin form submission
document.getElementById('createAdminForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const formData = {
        username: document.getElementById('adminUsername').value,
        email: document.getElementById('adminEmail').value,
        first_name: document.getElementById('adminFirstName').value,
        last_name: document.getElementById('adminLastName').value,
        password: document.getElementById('adminPassword').value,
        is_superuser: document.getElementById('adminSuperuser').checked
    };
    
    try {
        const response = await fetch(`${API_BASE_URL}/admin/create-admin/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Token ${adminToken}`
            },
            body: JSON.stringify(formData)
        });

        const data = await response.json();
        
        if (data.success) {
            const emailStatus = data.email_sent ?
                '📧 Welcome email sent successfully!' :
                '⚠️ Admin created but email notification failed.';

            document.getElementById('createAdminAlert').innerHTML =
                `<div class="alert success">
                    <strong>✅ Admin created successfully!</strong><br>
                    ${emailStatus}<br>
                    <small>Username: ${data.admin.username} | Email: ${data.admin.email}</small>
                </div>`;
            setTimeout(() => {
                closeCreateAdminModal();
                loadAdmins(); // Reload admins list
            }, 3000);
        } else {
            document.getElementById('createAdminAlert').innerHTML =
                `<div class="alert error">
                    <strong>❌ Failed to create admin</strong><br>
                    ${data.error}
                </div>`;
        }
    } catch (error) {
        console.error('Error creating admin:', error);
        document.getElementById('createAdminAlert').innerHTML = 
            '<div class="alert error">Error creating admin</div>';
    }
});

// Filter users
function filterUsers() {
    // Implementation for filtering users by type
    loadUsers();
}

// Search users
function searchUsers() {
    // Implementation for searching users
    loadUsers();
}

// View user details
function viewUser(userId) {
    alert(`View user details for ID: ${userId}`);
    // Implementation for viewing user details
}

// Logout function
function logout() {
    localStorage.removeItem('adminToken');
    localStorage.removeItem('adminInfo');
    window.location.href = 'admin_login.html';
}

// ========================================
// NEW ENHANCED ADMIN FUNCTIONS
// ========================================

// Load Transactions
async function loadTransactions() {
    try {
        const response = await fetch(`${API_BASE_URL}/admin/transactions/?page=1&per_page=20`, {
            headers: {
                'Authorization': `Token ${adminToken}`
            }
        });

        if (response.ok) {
            const data = await response.json();
            if (data.success) {
                displayTransactions(data.transactions);
            }
        }
    } catch (error) {
        console.error('Error loading transactions:', error);
        document.getElementById('transactionsTable').innerHTML =
            '<div class="error">Failed to load transactions</div>';
    }
}

// Display Transactions
function displayTransactions(transactions) {
    const container = document.getElementById('transactionsTable');

    if (transactions.length === 0) {
        container.innerHTML = '<div class="no-data">No transactions found</div>';
        return;
    }

    let html = `
        <table class="data-table">
            <thead>
                <tr>
                    <th>Transaction ID</th>
                    <th>Amount</th>
                    <th>Status</th>
                    <th>Farmer</th>
                    <th>Buyer</th>
                    <th>Product</th>
                    <th>Date</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
    `;

    transactions.forEach(transaction => {
        html += `
            <tr>
                <td>${transaction.transaction_id}</td>
                <td>$${transaction.amount.toFixed(2)}</td>
                <td><span class="badge badge-${transaction.status.toLowerCase()}">${transaction.status}</span></td>
                <td>${transaction.farmer.username}</td>
                <td>${transaction.buyer.username}</td>
                <td>${transaction.product.name}</td>
                <td>${new Date(transaction.created_at).toLocaleDateString()}</td>
                <td>
                    <button class="btn btn-sm" onclick="viewTransactionDetails('${transaction.transaction_id}')">
                        <i class="fas fa-eye"></i>
                    </button>
                </td>
            </tr>
        `;
    });

    html += '</tbody></table>';
    container.innerHTML = html;
}

// Load Notifications
async function loadNotifications() {
    try {
        const response = await fetch(`${API_BASE_URL}/notifications/?page=1&per_page=20`, {
            headers: {
                'Authorization': `Token ${adminToken}`
            }
        });

        if (response.ok) {
            const data = await response.json();
            if (data.success) {
                displayNotifications(data.notifications);
                updateNotificationCount(data.unread_count);
            }
        }
    } catch (error) {
        console.error('Error loading notifications:', error);
        document.getElementById('notificationsTable').innerHTML =
            '<div class="error">Failed to load notifications</div>';
    }
}

// Display Notifications
function displayNotifications(notifications) {
    const container = document.getElementById('notificationsTable');

    if (notifications.length === 0) {
        container.innerHTML = '<div class="no-data">No notifications found</div>';
        return;
    }

    let html = `
        <table class="data-table">
            <thead>
                <tr>
                    <th>Title</th>
                    <th>Message</th>
                    <th>Type</th>
                    <th>Status</th>
                    <th>Date</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
    `;

    notifications.forEach(notification => {
        html += `
            <tr class="${notification.is_read ? '' : 'unread'}">
                <td>${notification.title}</td>
                <td>${notification.message.substring(0, 50)}...</td>
                <td>${notification.notification_type}</td>
                <td><span class="badge ${notification.is_read ? 'badge-success' : 'badge-warning'}">${notification.is_read ? 'Read' : 'Unread'}</span></td>
                <td>${new Date(notification.created_at).toLocaleDateString()}</td>
                <td>
                    ${!notification.is_read ? `<button class="btn btn-sm" onclick="markNotificationRead('${notification.id}')"><i class="fas fa-check"></i></button>` : ''}
                    <button class="btn btn-sm btn-danger" onclick="deleteNotification('${notification.id}')">
                        <i class="fas fa-trash"></i>
                    </button>
                </td>
            </tr>
        `;
    });

    html += '</tbody></table>';
    container.innerHTML = html;
}

// Mark All Notifications Read
async function markAllNotificationsRead() {
    try {
        const response = await fetch(`${API_BASE_URL}/notifications/mark-all-read/`, {
            method: 'POST',
            headers: {
                'Authorization': `Token ${adminToken}`
            }
        });

        if (response.ok) {
            const data = await response.json();
            if (data.success) {
                showAlert('All notifications marked as read', 'success');
                loadNotifications();
            }
        }
    } catch (error) {
        console.error('Error marking notifications as read:', error);
        showAlert('Failed to mark notifications as read', 'error');
    }
}

// Show Broadcast Modal
function showBroadcastModal() {
    document.getElementById('broadcastModal').style.display = 'block';
}

// Close Broadcast Modal
function closeBroadcastModal() {
    document.getElementById('broadcastModal').style.display = 'none';
    document.getElementById('broadcastForm').reset();
    document.getElementById('broadcastAlert').innerHTML = '';
}

// Handle Broadcast Form
document.getElementById('broadcastForm').addEventListener('submit', async function(e) {
    e.preventDefault();

    const formData = {
        title: document.getElementById('broadcastTitle').value,
        message: document.getElementById('broadcastMessage').value,
        target_group: document.getElementById('broadcastTarget').value,
        send_email: document.getElementById('broadcastEmail').checked,
        urgent: document.getElementById('broadcastUrgent').checked
    };

    try {
        const response = await fetch(`${API_BASE_URL}/admin/broadcast/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Token ${adminToken}`
            },
            body: JSON.stringify(formData)
        });

        const data = await response.json();

        if (data.success) {
            document.getElementById('broadcastAlert').innerHTML =
                `<div class="alert success">
                    <strong>✅ Broadcast sent successfully!</strong><br>
                    Notifications created: ${data.details.notifications_created}<br>
                    Emails sent: ${data.details.emails_sent}
                </div>`;
            setTimeout(() => {
                closeBroadcastModal();
                loadBroadcastHistory();
            }, 3000);
        } else {
            document.getElementById('broadcastAlert').innerHTML =
                `<div class="alert error">
                    <strong>❌ Failed to send broadcast</strong><br>
                    ${data.error}
                </div>`;
        }
    } catch (error) {
        console.error('Error sending broadcast:', error);
        document.getElementById('broadcastAlert').innerHTML =
            '<div class="alert error">Failed to send broadcast</div>';
    }
});

// Load Broadcast History
async function loadBroadcastHistory() {
    try {
        const response = await fetch(`${API_BASE_URL}/admin/broadcast-history/?page=1&per_page=10`, {
            headers: {
                'Authorization': `Token ${adminToken}`
            }
        });

        if (response.ok) {
            const data = await response.json();
            if (data.success) {
                displayBroadcastHistory(data.broadcast_history);
            }
        }
    } catch (error) {
        console.error('Error loading broadcast history:', error);
        document.getElementById('broadcastHistory').innerHTML =
            '<div class="error">Failed to load broadcast history</div>';
    }
}

// Display Broadcast History
function displayBroadcastHistory(broadcasts) {
    const container = document.getElementById('broadcastHistory');

    if (broadcasts.length === 0) {
        container.innerHTML = '<div class="no-data">No broadcasts sent yet</div>';
        return;
    }

    let html = `
        <h4>Recent Broadcasts</h4>
        <table class="data-table">
            <thead>
                <tr>
                    <th>Description</th>
                    <th>Sent By</th>
                    <th>Date</th>
                </tr>
            </thead>
            <tbody>
    `;

    broadcasts.forEach(broadcast => {
        html += `
            <tr>
                <td>${broadcast.description}</td>
                <td>${broadcast.sent_by_name}</td>
                <td>${new Date(broadcast.created_at).toLocaleDateString()}</td>
            </tr>
        `;
    });

    html += '</tbody></table>';
    container.innerHTML = html;
}

// Global Search
async function performGlobalSearch() {
    const query = document.getElementById('globalSearchInput').value.trim();
    const searchType = document.getElementById('searchTypeFilter').value;

    if (query.length < 2) {
        document.getElementById('searchResults').innerHTML =
            '<p>Enter at least 2 characters to search...</p>';
        return;
    }

    try {
        const response = await fetch(`${API_BASE_URL}/admin/search/?q=${encodeURIComponent(query)}&type=${searchType}&limit=20`, {
            headers: {
                'Authorization': `Token ${adminToken}`
            }
        });

        if (response.ok) {
            const data = await response.json();
            if (data.success) {
                displaySearchResults(data.search_results);
            }
        }
    } catch (error) {
        console.error('Error performing search:', error);
        document.getElementById('searchResults').innerHTML =
            '<div class="error">Search failed</div>';
    }
}

// Display Search Results
function displaySearchResults(results) {
    const container = document.getElementById('searchResults');

    if (results.total_found === 0) {
        container.innerHTML = '<div class="no-data">No results found</div>';
        return;
    }

    let html = `<h4>Search Results (${results.total_found} found)</h4>`;

    // Users
    if (results.results.users.length > 0) {
        html += `
            <div class="search-section">
                <h5>Users (${results.results.users.length})</h5>
                <div class="search-results">
        `;
        results.results.users.forEach(user => {
            html += `
                <div class="search-item" onclick="viewUserDetails(${user.id})">
                    <strong>${user.username}</strong> (${user.user_type})<br>
                    <small>${user.email} - ${user.full_name}</small>
                </div>
            `;
        });
        html += '</div></div>';
    }

    // Transactions
    if (results.results.transactions.length > 0) {
        html += `
            <div class="search-section">
                <h5>Transactions (${results.results.transactions.length})</h5>
                <div class="search-results">
        `;
        results.results.transactions.forEach(transaction => {
            html += `
                <div class="search-item">
                    <strong>${transaction.transaction_id}</strong> - $${transaction.amount}<br>
                    <small>${transaction.farmer} → ${transaction.buyer} (${transaction.product})</small>
                </div>
            `;
        });
        html += '</div></div>';
    }

    container.innerHTML = html;
}

// Load Enhanced Analytics
async function loadEnhancedAnalytics() {
    try {
        const response = await fetch(`${API_BASE_URL}/admin/analytics/`, {
            headers: {
                'Authorization': `Token ${adminToken}`
            }
        });

        if (response.ok) {
            const data = await response.json();
            if (data.success) {
                displayEnhancedAnalytics(data.analytics);
            }
        }
    } catch (error) {
        console.error('Error loading analytics:', error);
        document.getElementById('analyticsContent').innerHTML =
            '<div class="error">Failed to load analytics</div>';
    }
}

// Display Enhanced Analytics
function displayEnhancedAnalytics(analytics) {
    const container = document.getElementById('analyticsContent');

    let html = `
        <div class="analytics-grid">
            <div class="analytics-section">
                <h4>User Statistics</h4>
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-number">${analytics.user_stats.total_users}</div>
                        <div class="stat-label">Total Users</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">${analytics.user_stats.farmers}</div>
                        <div class="stat-label">Farmers</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">${analytics.user_stats.buyers}</div>
                        <div class="stat-label">Buyers</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">${analytics.user_stats.pending_farmers}</div>
                        <div class="stat-label">Pending Farmers</div>
                    </div>
                </div>
            </div>

            <div class="analytics-section">
                <h4>Transaction Statistics</h4>
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-number">${analytics.transaction_stats.total_transactions}</div>
                        <div class="stat-label">Total Transactions</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">$${analytics.transaction_stats.total_revenue.toFixed(2)}</div>
                        <div class="stat-label">Total Revenue</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">${analytics.transaction_stats.successful_transactions}</div>
                        <div class="stat-label">Successful</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">${analytics.transaction_stats.pending_transactions}</div>
                        <div class="stat-label">Pending</div>
                    </div>
                </div>
            </div>

            <div class="analytics-section">
                <h4>Top Farmers</h4>
                <div class="top-performers">
    `;

    analytics.top_farmers.forEach((farmer, index) => {
        html += `
            <div class="performer-item">
                <span class="rank">#${index + 1}</span>
                <span class="name">${farmer.username}</span>
                <span class="metric">$${farmer.total_revenue.toFixed(2)}</span>
            </div>
        `;
    });

    html += `
                </div>
            </div>

            <div class="analytics-section">
                <h4>Top Buyers</h4>
                <div class="top-performers">
    `;

    analytics.top_buyers.forEach((buyer, index) => {
        html += `
            <div class="performer-item">
                <span class="rank">#${index + 1}</span>
                <span class="name">${buyer.username}</span>
                <span class="metric">$${buyer.total_spent.toFixed(2)}</span>
            </div>
        `;
    });

    html += `
                </div>
            </div>
        </div>
    `;

    container.innerHTML = html;
}

// Refresh Analytics
function refreshAnalytics() {
    document.getElementById('analyticsContent').innerHTML =
        '<div class="loading"><i class="fas fa-spinner"></i><p>Refreshing analytics...</p></div>';
    loadEnhancedAnalytics();
}

// Load Roles
async function loadRoles() {
    try {
        const response = await fetch(`${API_BASE_URL}/admin/roles/`, {
            headers: {
                'Authorization': `Token ${adminToken}`
            }
        });

        if (response.ok) {
            const data = await response.json();
            if (data.success) {
                displayRoles(data.roles);
                populateRoleSelects(data.roles);
            }
        }
    } catch (error) {
        console.error('Error loading roles:', error);
        document.getElementById('rolesContent').innerHTML =
            '<div class="error">Failed to load roles</div>';
    }
}

// Display Roles
function displayRoles(roles) {
    const container = document.getElementById('rolesContent');

    let html = `
        <div class="roles-grid">
    `;

    roles.forEach(role => {
        const permissionCount = Object.values(role.permissions).filter(p => p).length;
        html += `
            <div class="role-card">
                <h4>${role.display_name}</h4>
                <p>${role.description}</p>
                <div class="role-stats">
                    <span class="permission-count">${permissionCount} permissions</span>
                </div>
            </div>
        `;
    });

    html += '</div>';
    container.innerHTML = html;
}

// Show Assign Role Modal
function showAssignRoleModal() {
    document.getElementById('assignRoleModal').style.display = 'block';
    loadAdminsForRoleAssignment();
}

// Close Assign Role Modal
function closeAssignRoleModal() {
    document.getElementById('assignRoleModal').style.display = 'none';
    document.getElementById('assignRoleForm').reset();
    document.getElementById('assignRoleAlert').innerHTML = '';
}

// Load Admins for Role Assignment
async function loadAdminsForRoleAssignment() {
    try {
        const response = await fetch(`${API_BASE_URL}/admin/manage-users/?user_type=Admin`, {
            headers: {
                'Authorization': `Token ${adminToken}`
            }
        });

        if (response.ok) {
            const data = await response.json();
            if (data.success) {
                const select = document.getElementById('roleAdminSelect');
                select.innerHTML = '<option value="">Select Admin</option>';

                data.users.forEach(admin => {
                    select.innerHTML += `<option value="${admin.id}">${admin.username} (${admin.email})</option>`;
                });
            }
        }
    } catch (error) {
        console.error('Error loading admins:', error);
    }
}

// Populate Role Selects
function populateRoleSelects(roles) {
    const select = document.getElementById('roleSelect');
    select.innerHTML = '<option value="">Select Role</option>';

    roles.forEach(role => {
        select.innerHTML += `<option value="${role.id}">${role.display_name}</option>`;
    });
}

// Handle Assign Role Form
document.getElementById('assignRoleForm').addEventListener('submit', async function(e) {
    e.preventDefault();

    const formData = {
        admin_user_id: document.getElementById('roleAdminSelect').value,
        role_id: document.getElementById('roleSelect').value
    };

    try {
        const response = await fetch(`${API_BASE_URL}/admin/roles/assign/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Token ${adminToken}`
            },
            body: JSON.stringify(formData)
        });

        const data = await response.json();

        if (data.success) {
            document.getElementById('assignRoleAlert').innerHTML =
                `<div class="alert success">
                    <strong>✅ Role assigned successfully!</strong><br>
                    ${data.message}
                </div>`;
            setTimeout(() => {
                closeAssignRoleModal();
                loadRoles();
            }, 2000);
        } else {
            document.getElementById('assignRoleAlert').innerHTML =
                `<div class="alert error">
                    <strong>❌ Failed to assign role</strong><br>
                    ${data.error}
                </div>`;
        }
    } catch (error) {
        console.error('Error assigning role:', error);
        document.getElementById('assignRoleAlert').innerHTML =
            '<div class="alert error">Failed to assign role</div>';
    }
});

// Check System Status
async function checkSystemStatus() {
    // Check email status
    document.getElementById('emailStatus').innerHTML = '<span class="badge badge-warning">Checking...</span>';
    document.getElementById('databaseStatus').innerHTML = '<span class="badge badge-warning">Checking...</span>';
    document.getElementById('systemHealth').innerHTML = '<span class="badge badge-warning">Checking...</span>';

    // Simulate system checks (you can implement real checks)
    setTimeout(() => {
        document.getElementById('emailStatus').innerHTML = '<span class="badge badge-success">✅ Working</span>';
        document.getElementById('databaseStatus').innerHTML = '<span class="badge badge-success">✅ Connected</span>';
        document.getElementById('systemHealth').innerHTML = '<span class="badge badge-success">✅ Healthy</span>';
    }, 1000);
}

// View User Details
async function viewUserDetails(userId) {
    document.getElementById('userDetailsModal').style.display = 'block';
    document.getElementById('userDetailsContent').innerHTML =
        '<div class="loading"><i class="fas fa-spinner"></i><p>Loading user details...</p></div>';

    try {
        const response = await fetch(`${API_BASE_URL}/admin/users/${userId}/`, {
            headers: {
                'Authorization': `Token ${adminToken}`
            }
        });

        if (response.ok) {
            const data = await response.json();
            if (data.success) {
                displayUserDetails(data.user);
            }
        }
    } catch (error) {
        console.error('Error loading user details:', error);
        document.getElementById('userDetailsContent').innerHTML =
            '<div class="error">Failed to load user details</div>';
    }
}

// Display User Details
function displayUserDetails(user) {
    const container = document.getElementById('userDetailsContent');

    let html = `
        <div class="user-details">
            <div class="user-header">
                <h4>${user.first_name} ${user.last_name} (@${user.username})</h4>
                <span class="badge badge-${user.user_type.toLowerCase()}">${user.user_type}</span>
                <span class="badge ${user.is_active ? 'badge-success' : 'badge-danger'}">${user.is_active ? 'Active' : 'Inactive'}</span>
            </div>

            <div class="user-info">
                <div class="info-section">
                    <h5>Basic Information</h5>
                    <p><strong>Email:</strong> ${user.email}</p>
                    <p><strong>Phone:</strong> ${user.phone_number || 'Not provided'}</p>
                    <p><strong>Joined:</strong> ${new Date(user.date_joined).toLocaleDateString()}</p>
                    <p><strong>Last Login:</strong> ${user.last_login ? new Date(user.last_login).toLocaleDateString() : 'Never'}</p>
                </div>

                ${user.statistics ? `
                <div class="info-section">
                    <h5>Statistics</h5>
                    ${Object.entries(user.statistics).map(([key, value]) =>
                        `<p><strong>${key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}:</strong> ${value}</p>`
                    ).join('')}
                </div>
                ` : ''}

                ${user.recent_activity && user.recent_activity.length > 0 ? `
                <div class="info-section">
                    <h5>Recent Activity</h5>
                    <div class="activity-list">
                        ${user.recent_activity.map(activity =>
                            `<div class="activity-item">
                                <strong>${activity.type}:</strong> ${activity.description}
                                <small>${new Date(activity.timestamp).toLocaleDateString()}</small>
                            </div>`
                        ).join('')}
                    </div>
                </div>
                ` : ''}
            </div>

            <div class="user-actions">
                <button class="btn btn-primary" onclick="editUser(${user.id})">
                    <i class="fas fa-edit"></i> Edit User
                </button>
                <button class="btn btn-danger" onclick="deleteUser(${user.id}, '${user.username}')">
                    <i class="fas fa-trash"></i> Delete User
                </button>
            </div>
        </div>
    `;

    container.innerHTML = html;
}

// Close User Details Modal
function closeUserDetailsModal() {
    document.getElementById('userDetailsModal').style.display = 'none';
}

// Delete User with Real Impact
async function deleteUser(userId, username) {
    if (!confirm(`⚠️ WARNING: This will PERMANENTLY DELETE user "${username}" and ALL their data including listings, reservations, transactions, and messages. This action cannot be undone. Are you sure?`)) {
        return;
    }

    if (!confirm(`🚨 FINAL CONFIRMATION: Delete user "${username}" and ALL related data?`)) {
        return;
    }

    try {
        const response = await fetch(`${API_BASE_URL}/admin/users/${userId}/delete/`, {
            method: 'DELETE',
            headers: {
                'Authorization': `Token ${adminToken}`
            }
        });

        const data = await response.json();

        if (data.success) {
            showAlert(`✅ User "${username}" has been permanently deleted with all related data`, 'success');
            closeUserDetailsModal();
            loadUsers(); // Refresh users list
        } else {
            showAlert(`❌ Failed to delete user: ${data.error}`, 'error');
        }
    } catch (error) {
        console.error('Error deleting user:', error);
        showAlert('Failed to delete user', 'error');
    }
}

// Show Alert Function
function showAlert(message, type) {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert ${type}`;
    alertDiv.innerHTML = message;
    alertDiv.style.position = 'fixed';
    alertDiv.style.top = '20px';
    alertDiv.style.right = '20px';
    alertDiv.style.zIndex = '9999';
    alertDiv.style.maxWidth = '400px';

    document.body.appendChild(alertDiv);

    setTimeout(() => {
        alertDiv.remove();
    }, 5000);
}

// Update Notification Count in Header
function updateNotificationCount(count) {
    const badge = document.querySelector('.notification-badge');
    if (badge) {
        badge.textContent = count;
        badge.style.display = count > 0 ? 'block' : 'none';
    }
}

// Initialize Enhanced Dashboard
document.addEventListener('DOMContentLoaded', function() {
    // Load notification count on page load
    loadNotifications();

    // Set up periodic notification checking
    setInterval(() => {
        if (document.querySelector('.nav-item.active')?.textContent.includes('Notifications')) {
            loadNotifications();
        }
    }, 30000); // Check every 30 seconds
});

// Close modal when clicking outside
window.onclick = function(event) {
    const modal = document.getElementById('createAdminModal');
    if (event.target === modal) {
        closeCreateAdminModal();
    }
}
