// Admin Login JavaScript - Agriport
const API_BASE_URL = 'http://localhost:8000/api';

document.getElementById('adminLoginForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    const loginBtn = document.getElementById('loginBtn');
    const loading = document.getElementById('loading');
    const alertMessage = document.getElementById('alertMessage');

    // Validate inputs
    if (!email || !password) {
        showAlert('Please fill in all fields', 'error');
        return;
    }

    // Show loading state
    loginBtn.disabled = true;
    loading.style.display = 'block';
    hideAlert();

    try {
        const response = await fetch(`${API_BASE_URL}/admin/login/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                email: email,
                password: password
            })
        });

        const data = await response.json();

        if (data.success) {
            // Store admin token and info
            localStorage.setItem('adminToken', data.token);
            localStorage.setItem('adminInfo', JSON.stringify(data.admin));
            
            showAlert('Login successful! Redirecting to dashboard...', 'success');
            
            // Redirect to admin dashboard
            setTimeout(() => {
                window.location.href = 'admin_dashboard.html';
            }, 1500);
        } else {
            showAlert(data.error || 'Login failed. Please check your credentials.', 'error');
        }
    } catch (error) {
        console.error('Login error:', error);
        showAlert('Network error. Please check your connection and try again.', 'error');
    } finally {
        loginBtn.disabled = false;
        loading.style.display = 'none';
    }
});

function showAlert(message, type) {
    const alertMessage = document.getElementById('alertMessage');
    alertMessage.textContent = message;
    alertMessage.className = `alert ${type}`;
    alertMessage.style.display = 'block';
}

function hideAlert() {
    const alertMessage = document.getElementById('alertMessage');
    alertMessage.style.display = 'none';
}

// Check if already logged in
window.addEventListener('load', function() {
    const adminToken = localStorage.getItem('adminToken');
    if (adminToken) {
        // Verify token is still valid
        fetch(`${API_BASE_URL}/admin/dashboard/`, {
            headers: {
                'Authorization': `Token ${adminToken}`
            }
        })
        .then(response => {
            if (response.ok) {
                window.location.href = 'admin_dashboard.html';
            } else {
                // Token invalid, clear storage
                localStorage.removeItem('adminToken');
                localStorage.removeItem('adminInfo');
            }
        })
        .catch(error => {
            console.error('Token validation error:', error);
        });
    }
});

// Enhanced security features
document.addEventListener('DOMContentLoaded', function() {
    // Disable right-click context menu for security
    document.addEventListener('contextmenu', function(e) {
        e.preventDefault();
    });
    
    // Disable F12 and other developer tools shortcuts
    document.addEventListener('keydown', function(e) {
        if (e.key === 'F12' || 
            (e.ctrlKey && e.shiftKey && e.key === 'I') ||
            (e.ctrlKey && e.shiftKey && e.key === 'C') ||
            (e.ctrlKey && e.shiftKey && e.key === 'J') ||
            (e.ctrlKey && e.key === 'U')) {
            e.preventDefault();
        }
    });
    
    // Add focus effects
    const inputs = document.querySelectorAll('input');
    inputs.forEach(input => {
        input.addEventListener('focus', function() {
            this.parentElement.classList.add('focused');
        });
        
        input.addEventListener('blur', function() {
            this.parentElement.classList.remove('focused');
        });
    });
    
    // Auto-clear alerts after 5 seconds
    const observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            if (mutation.type === 'attributes' && mutation.attributeName === 'style') {
                const alertElement = mutation.target;
                if (alertElement.style.display === 'block' && alertElement.classList.contains('alert')) {
                    setTimeout(() => {
                        hideAlert();
                    }, 5000);
                }
            }
        });
    });
    
    const alertMessage = document.getElementById('alertMessage');
    if (alertMessage) {
        observer.observe(alertMessage, { attributes: true });
    }
});
