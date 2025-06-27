// Forgot Password JavaScript
const API_BASE_URL = 'http://localhost:8000/api';

document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('forgotPasswordForm');
    const emailInput = document.getElementById('email');
    const emailError = document.getElementById('emailError');
    
    // Add real-time validation
    emailInput.addEventListener('input', validateEmail);
    
    // Form submission
    form.addEventListener('submit', function(event) {
        event.preventDefault();
        
        if (validateEmail()) {
            requestPasswordReset();
        }
    });
    
    function validateEmail() {
        const email = emailInput.value.trim();
        let isValid = true;
        
        if (!email) {
            setError(emailInput, emailError, 'Email address is required');
            isValid = false;
        } else if (!isValidEmail(email)) {
            setError(emailInput, emailError, 'Please enter a valid email address');
            isValid = false;
        } else {
            setSuccess(emailInput, emailError);
        }
        
        return isValid;
    }
    
    function isValidEmail(email) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    }
    
    function setError(input, errorElement, message) {
        input.parentElement.classList.remove('valid');
        input.parentElement.classList.add('invalid');
        errorElement.textContent = message;
    }
    
    function setSuccess(input, errorElement) {
        input.parentElement.classList.remove('invalid');
        input.parentElement.classList.add('valid');
        errorElement.textContent = '';
    }
});

async function requestPasswordReset() {
    const email = document.getElementById('email').value.trim();
    
    try {
        showLoading(true);
        
        const response = await fetch(`${API_BASE_URL}/buyer/request-password-reset/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            body: JSON.stringify({ email })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showSuccess(
                'Password reset instructions have been sent to your email address. ' +
                'Please check your inbox and follow the instructions to reset your password.'
            );
            
            // Clear the form
            document.getElementById('forgotPasswordForm').reset();
            
            // Redirect to login after 5 seconds
            setTimeout(() => {
                window.location.href = 'loginbuyer.html';
            }, 5000);
        } else {
            if (data.errors && data.errors.email) {
                const emailInput = document.getElementById('email');
                const emailError = document.getElementById('emailError');
                setError(emailInput, emailError, data.errors.email[0]);
            } else {
                showGeneralError(data.error || 'Failed to send reset instructions. Please try again.');
            }
        }
    } catch (error) {
        console.error('Password reset request failed:', error);
        showGeneralError('Network error. Please check your connection and try again.');
    } finally {
        showLoading(false);
    }
}

function showLoading(show) {
    const submitBtn = document.querySelector('button[type="submit"]');
    
    if (show) {
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Sending...';
    } else {
        submitBtn.disabled = false;
        submitBtn.innerHTML = '<i class="fas fa-paper-plane"></i> Send Reset Instructions';
    }
}

function showSuccess(message) {
    const successDiv = document.createElement('div');
    successDiv.className = 'success-message';
    successDiv.innerHTML = `
        <i class="fas fa-check-circle"></i>
        <span>${message}</span>
    `;
    
    const form = document.getElementById('forgotPasswordForm');
    
    // Remove existing messages
    const existingMessage = form.querySelector('.success-message, .general-error-message');
    if (existingMessage) {
        existingMessage.remove();
    }
    
    form.insertBefore(successDiv, form.firstChild);
}

function showGeneralError(message) {
    const errorDiv = document.createElement('div');
    errorDiv.className = 'general-error-message';
    errorDiv.innerHTML = `
        <i class="fas fa-exclamation-triangle"></i>
        <span>${message}</span>
    `;
    
    const form = document.getElementById('forgotPasswordForm');
    
    // Remove existing messages
    const existingMessage = form.querySelector('.success-message, .general-error-message');
    if (existingMessage) {
        existingMessage.remove();
    }
    
    form.insertBefore(errorDiv, form.firstChild);
    
    // Remove after 8 seconds
    setTimeout(() => {
        if (errorDiv.parentNode) {
            errorDiv.remove();
        }
    }, 8000);
}

function setError(input, errorElement, message) {
    input.parentElement.classList.remove('valid');
    input.parentElement.classList.add('invalid');
    errorElement.textContent = message;
}

function getCsrfToken() {
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]');
    if (csrfToken) {
        return csrfToken.value;
    }
    
    const cookies = document.cookie.split(';');
    for (let cookie of cookies) {
        const [name, value] = cookie.trim().split('=');
        if (name === 'csrftoken') {
            return value;
        }
    }
    
    return '';
}
