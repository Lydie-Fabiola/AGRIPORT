/**
 * Buyer Authentication and Session Management
 * Handles buyer login, logout, session management, and authentication state
 */

class BuyerAuth {
    constructor() {
        this.API_BASE_URL = 'http://localhost:8000/api';
        this.TOKEN_KEY = 'buyerToken';
        this.USER_DATA_KEY = 'buyerUserData';
        this.PROFILE_KEY = 'buyerProfile';
    }

    /**
     * Check if buyer is authenticated
     */
    isAuthenticated() {
        const token = this.getToken();
        const userData = this.getUserData();
        return !!(token && userData && userData.user_type === 'Buyer');
    }

    /**
     * Get stored authentication token
     */
    getToken() {
        return localStorage.getItem(this.TOKEN_KEY);
    }

    /**
     * Get stored user data
     */
    getUserData() {
        const userData = localStorage.getItem(this.USER_DATA_KEY);
        return userData ? JSON.parse(userData) : null;
    }

    /**
     * Get stored buyer profile
     */
    getProfile() {
        const profile = localStorage.getItem(this.PROFILE_KEY);
        return profile ? JSON.parse(profile) : null;
    }

    /**
     * Get user's full name
     */
    getUserName() {
        const userData = this.getUserData();
        return userData ? userData.full_name : null;
    }

    /**
     * Get user's email
     */
    getUserEmail() {
        const userData = this.getUserData();
        return userData ? userData.email : null;
    }

    /**
     * Get user ID
     */
    getUserId() {
        const userData = this.getUserData();
        return userData ? userData.user_id : null;
    }

    /**
     * Store authentication data after successful login
     */
    storeAuthData(loginResponse) {
        const userData = {
            user_id: loginResponse.user_id,
            user_type: loginResponse.user_type,
            email: loginResponse.email,
            username: loginResponse.username,
            full_name: loginResponse.full_name
        };

        localStorage.setItem(this.TOKEN_KEY, loginResponse.token);
        localStorage.setItem(this.USER_DATA_KEY, JSON.stringify(userData));
        
        if (loginResponse.profile) {
            localStorage.setItem(this.PROFILE_KEY, JSON.stringify(loginResponse.profile));
        }
    }

    /**
     * Clear all authentication data (logout)
     */
    logout() {
        localStorage.removeItem(this.TOKEN_KEY);
        localStorage.removeItem(this.USER_DATA_KEY);
        localStorage.removeItem(this.PROFILE_KEY);
        
        // Redirect to login page
        window.location.href = 'loginbuyer.html';
    }

    /**
     * Get authorization headers for API requests
     */
    getAuthHeaders() {
        const token = this.getToken();
        return {
            'Authorization': `Token ${token}`,
            'Content-Type': 'application/json'
        };
    }

    /**
     * Make authenticated API request
     */
    async apiRequest(endpoint, options = {}) {
        const url = `${this.API_BASE_URL}${endpoint}`;
        const defaultOptions = {
            headers: this.getAuthHeaders()
        };

        const requestOptions = {
            ...defaultOptions,
            ...options,
            headers: {
                ...defaultOptions.headers,
                ...options.headers
            }
        };

        try {
            const response = await fetch(url, requestOptions);
            
            // Handle unauthorized responses
            if (response.status === 401) {
                this.logout();
                return null;
            }

            return response;
        } catch (error) {
            console.error('API request failed:', error);
            throw error;
        }
    }

    /**
     * Update buyer profile
     */
    async updateProfile(profileData) {
        try {
            const response = await this.apiRequest('/buyer/profile/', {
                method: 'PUT',
                body: JSON.stringify(profileData)
            });

            if (response && response.ok) {
                const data = await response.json();
                if (data.success) {
                    // Update stored profile
                    localStorage.setItem(this.PROFILE_KEY, JSON.stringify(data.profile));
                    return data;
                }
            }
            return null;
        } catch (error) {
            console.error('Profile update failed:', error);
            return null;
        }
    }

    /**
     * Get buyer dashboard data
     */
    async getDashboardData() {
        try {
            const response = await this.apiRequest('/buyer/dashboard-data/');
            
            if (response && response.ok) {
                const data = await response.json();
                return data.success ? data.dashboard_data : null;
            }
            return null;
        } catch (error) {
            console.error('Dashboard data fetch failed:', error);
            return null;
        }
    }

    /**
     * Request password reset
     */
    async requestPasswordReset(email) {
        try {
            const response = await fetch(`${this.API_BASE_URL}/buyer/request-password-reset/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ email })
            });

            const data = await response.json();
            return data;
        } catch (error) {
            console.error('Password reset request failed:', error);
            return { success: false, error: 'Network error' };
        }
    }

    /**
     * Reset password with token
     */
    async resetPassword(token, newPassword, confirmPassword) {
        try {
            const response = await fetch(`${this.API_BASE_URL}/buyer/reset-password/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    token,
                    new_password: newPassword,
                    confirm_password: confirmPassword
                })
            });

            const data = await response.json();
            return data;
        } catch (error) {
            console.error('Password reset failed:', error);
            return { success: false, error: 'Network error' };
        }
    }

    /**
     * Verify email with token
     */
    async verifyEmail(token) {
        try {
            const response = await fetch(`${this.API_BASE_URL}/buyer/verify-email/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ token })
            });

            const data = await response.json();
            return data;
        } catch (error) {
            console.error('Email verification failed:', error);
            return { success: false, error: 'Network error' };
        }
    }

    /**
     * Check authentication and redirect if not authenticated
     */
    requireAuth() {
        if (!this.isAuthenticated()) {
            window.location.href = 'loginbuyer.html';
            return false;
        }
        return true;
    }

    /**
     * Initialize authentication state on page load
     */
    init() {
        // Check if on a protected page
        const protectedPages = [
            'buyerdashboard.html',
            'marketplace.html',
            'reserveproduct.html',
            'purchasehistory.html',
            'favorite.html',
            'viewfarmerprofile.html'
        ];

        const currentPage = window.location.pathname.split('/').pop();
        
        if (protectedPages.includes(currentPage)) {
            this.requireAuth();
        }

        // If on login page and already authenticated, redirect to dashboard
        if (currentPage === 'loginbuyer.html' && this.isAuthenticated()) {
            window.location.href = 'buyerdashboard.html';
        }
    }
}

// Create global instance
window.BuyerAuth = new BuyerAuth();

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    window.BuyerAuth.init();
});

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = BuyerAuth;
}
