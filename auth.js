// Centralized authentication module
const Auth = {
  // API endpoint for auth
  API_URL: 'http://localhost:8000/api/auth',
  
  // Get current auth token
  getToken() {
    return localStorage.getItem('authToken');
  },
  
  // Get current user type (Farmer, Buyer, Admin)
  getUserType() {
    return localStorage.getItem('userType');
  },
  
  // Get current user name
  getUserName() {
    return localStorage.getItem('userName');
  },
  
  // Get user ID
  getUserId() {
    return localStorage.getItem('userId');
  },
  
  // Check if user is authenticated
  isAuthenticated() {
    return !!this.getToken();
  },
  
  // Login user
  async login(credentials) {
    try {
      const response = await fetch(`${this.API_URL}/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(credentials)
      });
      
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.message || 'Login failed');
      }
      
      const data = await response.json();
      
      // Store auth data
      localStorage.setItem('authToken', data.token);
      localStorage.setItem('userType', data.userType);
      localStorage.setItem('userName', data.userName);
      localStorage.setItem('userId', data.userId);
      
      return data;
    } catch (error) {
      console.error('Login error:', error);
      throw error;
    }
  },
  
  // Register user
  async register(userData) {
    try {
      const response = await fetch(`${this.API_URL}/register`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(userData)
      });
      
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.message || 'Registration failed');
      }
      
      return await response.json();
    } catch (error) {
      console.error('Registration error:', error);
      throw error;
    }
  },
  
  // Logout user
  logout() {
    localStorage.removeItem('authToken');
    localStorage.removeItem('userType');
    localStorage.removeItem('userName');
    localStorage.removeItem('userId');
    
    // Redirect based on user type
    const userType = this.getUserType();
    if (userType === 'Farmer') {
      window.location.href = '/Farmer/loginfarmer.html';
    } else if (userType === 'Buyer') {
      window.location.href = '/Buyer/loginbuyer.html';
    } else {
      window.location.href = '/index.html';
    }
  },
  
  // Redirect if not authenticated
  requireAuth() {
    if (!this.isAuthenticated()) {
      const userType = this.getUserType() || 'Buyer';
      if (userType === 'Farmer') {
        window.location.href = '/Farmer/loginfarmer.html';
      } else {
        window.location.href = '/Buyer/loginbuyer.html';
      }
      return false;
    }
    return true;
  },
  
  // Redirect if already authenticated
  redirectIfAuth() {
    if (this.isAuthenticated()) {
      const userType = this.getUserType();
      if (userType === 'Farmer') {
        window.location.href = '/Farmer/farmer dashboard.html';
      } else if (userType === 'Buyer') {
        window.location.href = '/Buyer/buyerdashboard.html';
      }
      return true;
    }
    return false;
  }
};

// Add to window for global access
window.Auth = Auth;