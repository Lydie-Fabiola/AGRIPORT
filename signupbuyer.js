// API Configuration
const API_BASE_URL = 'http://localhost:8000/api';

document.addEventListener('DOMContentLoaded', function() {
  const form = document.getElementById('buyerSignupForm');
  
  // Get all form elements
  const firstName = document.getElementById('firstName');
  const lastName = document.getElementById('lastName');
  const phoneNumber = document.getElementById('phoneNumber');
  const email = document.getElementById('email');
  const location = document.getElementById('location');
  
  // Get all error message elements
  const firstNameError = document.getElementById('firstNameError');
  const lastNameError = document.getElementById('lastNameError');
  const phoneNumberError = document.getElementById('phoneNumberError');
  const emailError = document.getElementById('emailError');
  const locationError = document.getElementById('locationError');
  
  // Add event listeners for real-time validation
  firstName.addEventListener('input', validateFirstName);
  lastName.addEventListener('input', validateLastName);
  phoneNumber.addEventListener('input', validatePhoneNumber);
  email.addEventListener('input', validateEmail);
  location.addEventListener('input', validateLocation);
  
  // Form submission
  form.addEventListener('submit', function(event) {
    // Prevent default form submission
    event.preventDefault();
    
    // Validate all fields
    const isFirstNameValid = validateFirstName();
    const isLastNameValid = validateLastName();
    const isPhoneNumberValid = validatePhoneNumber();
    const isEmailValid = validateEmail();
    const isLocationValid = validateLocation();
    
    // If all validations pass, submit the form
    if (isFirstNameValid && isLastNameValid && isPhoneNumberValid && 
        isEmailValid && isLocationValid) {
      
      // Create user object from form data
      const userData = {
        firstName: firstName.value.trim(),
        lastName: lastName.value.trim(),
        phoneNumber: phoneNumber.value.trim(),
        email: email.value.trim(),
        location: location.value.trim()
      };
      
      // Call registration API
      registerBuyer(userData);
    }
  });
  
  // Validation functions
  function validateFirstName() {
    const value = firstName.value.trim();
    let isValid = true;
    
    if (value === '') {
      setError(firstName, firstNameError, 'First name is required');
      isValid = false;
    } else if (value.length < 2) {
      setError(firstName, firstNameError, 'First name must be at least 2 characters');
      isValid = false;
    } else if (!/^[A-Za-z\s]+$/.test(value)) {
      setError(firstName, firstNameError, 'First name should contain only letters');
      isValid = false;
    } else {
      setSuccess(firstName, firstNameError);
    }
    
    return isValid;
  }
  
  function validateLastName() {
    const value = lastName.value.trim();
    let isValid = true;
    
    if (value === '') {
      setError(lastName, lastNameError, 'Last name is required');
      isValid = false;
    } else if (value.length < 2) {
      setError(lastName, lastNameError, 'Last name must be at least 2 characters');
      isValid = false;
    } else if (!/^[A-Za-z\s]+$/.test(value)) {
      setError(lastName, lastNameError, 'Last name should contain only letters');
      isValid = false;
    } else {
      setSuccess(lastName, lastNameError);
    }
    
    return isValid;
  }
  
  function validatePhoneNumber() {
    const value = phoneNumber.value.trim();
    let isValid = true;
    
    // Regex for Cameroon phone numbers (237 followed by 9 digits)
    const phoneRegex = /^(237\s?)?[6-9]\d{8}$/;
    
    if (value === '') {
      setError(phoneNumber, phoneNumberError, 'Phone number is required');
      isValid = false;
    } else if (!phoneRegex.test(value)) {
      setError(phoneNumber, phoneNumberError, 'Please enter a valid Cameroon phone number');
      isValid = false;
    } else {
      setSuccess(phoneNumber, phoneNumberError);
    }
    
    return isValid;
  }
  
  function validateEmail() {
    const value = email.value.trim();
    let isValid = true;
    
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    
    if (value === '') {
      setError(email, emailError, 'Email is required');
      isValid = false;
    } else if (!emailRegex.test(value)) {
      setError(email, emailError, 'Please enter a valid email address');
      isValid = false;
    } else {
      setSuccess(email, emailError);
    }
    
    return isValid;
  }
  
  function validateLocation() {
    const value = location.value.trim();
    let isValid = true;
    
    if (value === '') {
      setError(location, locationError, 'Location is required');
      isValid = false;
    } else if (value.length < 3) {
      setError(location, locationError, 'Location must be at least 3 characters');
      isValid = false;
    } else {
      setSuccess(location, locationError);
    }
    
    return isValid;
  }
  
  // Helper functions
  function setError(input, errorElement, message) {
    input.classList.remove('valid');
    input.classList.add('invalid');
    errorElement.textContent = message;
  }
  
  function setSuccess(input, errorElement) {
    input.classList.remove('invalid');
    input.classList.add('valid');
    errorElement.textContent = '';
  }
});

// API Functions
async function registerBuyer(userData) {
  try {
    // Show loading state
    showLoading(true);

    // Transform data to match API format
    const apiData = {
      first_name: userData.firstName,
      last_name: userData.lastName,
      email: userData.email,
      phone_number: userData.phoneNumber,
      location: userData.location
    };

    const response = await fetch(`${API_BASE_URL}/buyer/register/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCsrfToken()
      },
      body: JSON.stringify(apiData)
    });

    const data = await response.json();

    if (data.success) {
      showSuccess(data.message);

      // Clear form
      document.getElementById('buyerSignupForm').reset();
      clearAllValidationStates();

      // Redirect to login page after 3 seconds
      setTimeout(() => {
        window.location.href = 'loginbuyer.html';
      }, 3000);
    } else {
      // Handle validation errors
      if (data.errors) {
        handleValidationErrors(data.errors);
      } else {
        showGeneralError(data.error || 'Registration failed. Please try again.');
      }
    }
  } catch (error) {
    console.error('Registration error:', error);
    showGeneralError('Network error. Please check your connection and try again.');
  } finally {
    showLoading(false);
  }
}

function handleValidationErrors(errors) {
  // Map API field names to form field names
  const fieldMapping = {
    'first_name': 'firstName',
    'last_name': 'lastName',
    'email': 'email',
    'phone_number': 'phoneNumber',
    'location': 'location'
  };

  // Show field-specific errors
  Object.keys(errors).forEach(field => {
    const formFieldName = fieldMapping[field];
    if (formFieldName && errors[field].length > 0) {
      const input = document.getElementById(formFieldName);
      const errorElement = document.getElementById(formFieldName + 'Error');
      if (input && errorElement) {
        setError(input, errorElement, errors[field][0]);
      }
    }
  });
}

function showLoading(show) {
  const submitBtn = document.querySelector('button[type="submit"]');

  if (show) {
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Creating Account...';
  } else {
    submitBtn.disabled = false;
    submitBtn.innerHTML = 'Create Account';
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
  const form = document.getElementById('buyerSignupForm');

  // Remove existing success message
  const existingSuccess = form.querySelector('.success-message');
  if (existingSuccess) {
    existingSuccess.remove();
  }

  form.insertBefore(successDiv, form.firstChild);

  // Remove after 10 seconds
  setTimeout(() => {
    if (successDiv.parentNode) {
      successDiv.remove();
    }
  }, 10000);
}

function showGeneralError(message) {
  const errorDiv = document.createElement('div');
  errorDiv.className = 'general-error-message';
  errorDiv.innerHTML = `
    <i class="fas fa-exclamation-triangle"></i>
    <span>${message}</span>
  `;

  // Insert at top of form
  const form = document.getElementById('buyerSignupForm');

  // Remove existing general error
  const existingError = form.querySelector('.general-error-message');
  if (existingError) {
    existingError.remove();
  }

  form.insertBefore(errorDiv, form.firstChild);

  // Remove after 10 seconds
  setTimeout(() => {
    if (errorDiv.parentNode) {
      errorDiv.remove();
    }
  }, 10000);
}

function clearAllValidationStates() {
  const inputs = document.querySelectorAll('input');
  const errorElements = document.querySelectorAll('[id$="Error"]');

  inputs.forEach(input => {
    input.classList.remove('valid', 'invalid');
  });

  errorElements.forEach(element => {
    element.textContent = '';
  });
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
