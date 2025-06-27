// API Configuration
const API_BASE_URL = 'http://localhost:8000/api';

document.addEventListener('DOMContentLoaded', function() {
  const form = document.getElementById('buyerLoginForm');
  const username = document.getElementById('username');
  const password = document.getElementById('password');
  const usernameError = document.getElementById('usernameError');
  const passwordError = document.getElementById('passwordError');
  const togglePassword = document.getElementById('togglePassword');
  
  // Add event listeners for real-time validation
  username.addEventListener('input', validateUsername);
  password.addEventListener('input', validatePassword);
  
  // Toggle password visibility
  togglePassword.addEventListener('click', function() {
    if (password.type === 'password') {
      password.type = 'text';
      togglePassword.textContent = '🔒';
    } else {
      password.type = 'password';
      togglePassword.textContent = '👁️';
    }
  });
  
  // Form submission
  form.addEventListener('submit', function(event) {
    event.preventDefault();
    
    const isUsernameValid = validateUsername();
    const isPasswordValid = validatePassword();
    
    if (isUsernameValid && isPasswordValid) {
      // Create login data object
      const loginData = {
        username: username.value.trim(),
        password: password.value
      };
      
      // Call login API
      loginBuyer(loginData);
    }
  });
  
  function validateUsername() {
    const value = username.value.trim();
    let isValid = true;
    
    if (value === '') {
      setError(username.parentElement, usernameError, 'Username or email is required');
      isValid = false;
    } else {
      setSuccess(username.parentElement, usernameError);
    }
    
    return isValid;
  }
  
  function validatePassword() {
    const value = password.value;
    let isValid = true;
    
    if (value === '') {
      setError(password.parentElement, passwordError, 'Password is required');
      isValid = false;
    } else {
      setSuccess(password.parentElement, passwordError);
    }
    
    return isValid;
  }
  
  function setError(inputGroup, errorElement, message) {
    inputGroup.classList.remove('valid');
    inputGroup.classList.add('invalid');
    errorElement.textContent = message;
  }
  
  function setSuccess(inputGroup, errorElement) {
    inputGroup.classList.remove('invalid');
    inputGroup.classList.add('valid');
    errorElement.textContent = '';
  }
});

// API Functions
async function loginBuyer(loginData) {
  try {
    // Show loading state
    showLoading(true);

    // Transform data to match API format
    const apiData = {
      email: loginData.username, // API expects email
      password: loginData.password
    };

    const response = await fetch(`${API_BASE_URL}/buyer/login/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCsrfToken()
      },
      body: JSON.stringify(apiData)
    });

    const data = await response.json();

    if (data.success) {
      // Store authentication data using BuyerAuth
      window.BuyerAuth.storeAuthData(data);

      showSuccess('Login successful! Redirecting to dashboard...');

      // Redirect to dashboard after 1 second
      setTimeout(() => {
        window.location.href = 'buyerdashboard.html';
      }, 1000);
    } else {
      // Handle login errors
      if (data.errors) {
        handleLoginErrors(data.errors);
      } else {
        showGeneralError(data.error || 'Login failed. Please try again.');
      }
    }
  } catch (error) {
    console.error('Login error:', error);
    showGeneralError('Network error. Please check your connection and try again.');
  } finally {
    showLoading(false);
  }
}

function handleLoginErrors(errors) {
  const username = document.getElementById('username');
  const password = document.getElementById('password');
  const usernameError = document.getElementById('usernameError');
  const passwordError = document.getElementById('passwordError');

  // Show field-specific errors
  if (errors.email) {
    setError(username.parentElement, usernameError, errors.email[0]);
  }
  if (errors.password) {
    setError(password.parentElement, passwordError, errors.password[0]);
  }
  if (errors.non_field_errors) {
    showGeneralError(errors.non_field_errors[0]);
  }
}

function showLoading(show) {
  const submitBtn = document.querySelector('button[type="submit"]');

  if (show) {
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Signing In...';
  } else {
    submitBtn.disabled = false;
    submitBtn.innerHTML = 'Sign In';
  }
}

function showSuccess(message) {
  const successDiv = document.createElement('div');
  successDiv.className = 'success-message';
  successDiv.innerHTML = `
    <i class="fas fa-check-circle"></i>
    <span>${message}</span>
  `;

  // Insert at top of form
  const form = document.getElementById('buyerLoginForm');

  // Remove existing success message
  const existingSuccess = form.querySelector('.success-message');
  if (existingSuccess) {
    existingSuccess.remove();
  }

  form.insertBefore(successDiv, form.firstChild);

  // Remove after 5 seconds
  setTimeout(() => {
    if (successDiv.parentNode) {
      successDiv.remove();
    }
  }, 5000);
}

function showGeneralError(message) {
  const errorDiv = document.createElement('div');
  errorDiv.className = 'general-error-message';
  errorDiv.innerHTML = `
    <i class="fas fa-exclamation-triangle"></i>
    <span>${message}</span>
  `;

  // Insert at top of form
  const form = document.getElementById('buyerLoginForm');

  // Remove existing general error
  const existingError = form.querySelector('.general-error-message');
  if (existingError) {
    existingError.remove();
  }

  form.insertBefore(errorDiv, form.firstChild);

  // Remove after 8 seconds
  setTimeout(() => {
    if (errorDiv.parentNode) {
      errorDiv.remove();
    }
  }, 8000);
}

function getCsrfToken() {
  // Get CSRF token from cookie or meta tag
  const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]');
  if (csrfToken) {
    return csrfToken.value;
  }

  // Fallback: get from cookie
  const cookies = document.cookie.split(';');
  for (let cookie of cookies) {
    const [name, value] = cookie.trim().split('=');
    if (name === 'csrftoken') {
      return value;
    }
  }

  return '';
}