// Reset Password JavaScript
const API_BASE_URL = 'http://localhost:8000/api';

document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('resetPasswordForm');
    const newPasswordInput = document.getElementById('newPassword');
    const confirmPasswordInput = document.getElementById('confirmPassword');
    const newPasswordError = document.getElementById('newPasswordError');
    const confirmPasswordError = document.getElementById('confirmPasswordError');
    
    // Get token from URL
    const urlParams = new URLSearchParams(window.location.search);
    const token = urlParams.get('token');
    
    if (!token) {
        showGeneralError('Invalid or missing reset token. Please request a new password reset.');
        return;
    }
    
    // Password toggle functionality
    setupPasswordToggle('toggleNewPassword', 'newPassword');
    setupPasswordToggle('toggleConfirmPassword', 'confirmPassword');
    
    // Add real-time validation
    newPasswordInput.addEventListener('input', validateNewPassword);
    confirmPasswordInput.addEventListener('input', validateConfirmPassword);
    
    // Form submission
    form.addEventListener('submit', function(event) {
        event.preventDefault();
        
        const isNewPasswordValid = validateNewPassword();
        const isConfirmPasswordValid = validateConfirmPassword();
        
        if (isNewPasswordValid && isConfirmPasswordValid) {
            resetPassword();
        }
    });
    
    function setupPasswordToggle(toggleId, inputId) {
        const toggle = document.getElementById(toggleId);
        const input = document.getElementById(inputId);
        
        toggle.addEventListener('click', function() {
            if (input.type === 'password') {
                input.type = 'text';
                toggle.textContent = '🔒';
            } else {
                input.type = 'password';
                toggle.textContent = '👁️';
            }
        });
    }
    
    function validateNewPassword() {
        const password = newPasswordInput.value;
        let isValid = true;
        
        if (!password) {
            setError(newPasswordInput, newPasswordError, 'New password is required');
            isValid = false;
        } else if (password.length < 8) {
            setError(newPasswordInput, newPasswordError, 'Password must be at least 8 characters long');
            isValid = false;
        } else if (!isStrongPassword(password)) {
            setError(newPasswordInput, newPasswordError, 'Password must include uppercase, lowercase, number, and special character');
            isValid = false;
        } else {
            setSuccess(newPasswordInput, newPasswordError);
        }
        
        // Re-validate confirm password if it has a value
        if (confirmPasswordInput.value) {
            validateConfirmPassword();
        }
        
        return isValid;
    }
    
    function validateConfirmPassword() {
        const password = newPasswordInput.value;
        const confirmPassword = confirmPasswordInput.value;
        let isValid = true;
        
        if (!confirmPassword) {
            setError(confirmPasswordInput, confirmPasswordError, 'Please confirm your password');
            isValid = false;
        } else if (password !== confirmPassword) {
            setError(confirmPasswordInput, confirmPasswordError, 'Passwords do not match');
            isValid = false;
        } else {
            setSuccess(confirmPasswordInput, confirmPasswordError);
        }
        
        return isValid;
    }
    
    function isStrongPassword(password) {
        const hasUpperCase = /[A-Z]/.test(password);
        const hasLowerCase = /[a-z]/.test(password);
        const hasNumbers = /\d/.test(password);
        const hasSpecialChar = /[!@#$%^&*(),.?":{}|<>]/.test(password);
        
        return hasUpperCase && hasLowerCase && hasNumbers && hasSpecialChar;
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
    
    async function resetPassword() {
        const newPassword = newPasswordInput.value;
        const confirmPassword = confirmPasswordInput.value;
        
        try {
            showLoading(true);
            
            const response = await fetch(`${API_BASE_URL}/buyer/reset-password/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken()
                },
                body: JSON.stringify({
                    token: token,
                    new_password: newPassword,
                    confirm_password: confirmPassword
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                showSuccess(
                    'Your password has been reset successfully! You can now login with your new password.'
                );
                
                // Clear the form
                form.reset();
                
                // Redirect to login after 3 seconds
                setTimeout(() => {
                    window.location.href = 'loginbuyer.html';
                }, 3000);
            } else {
                if (data.errors) {
                    handleValidationErrors(data.errors);
                } else {
                    showGeneralError(data.error || 'Failed to reset password. Please try again.');
                }
            }
        } catch (error) {
            console.error('Password reset failed:', error);
            showGeneralError('Network error. Please check your connection and try again.');
        } finally {
            showLoading(false);
        }
    }
    
    function handleValidationErrors(errors) {
        if (errors.new_password) {
            setError(newPasswordInput, newPasswordError, errors.new_password[0]);
        }
        if (errors.confirm_password) {
            setError(confirmPasswordInput, confirmPasswordError, errors.confirm_password[0]);
        }
        if (errors.token) {
            showGeneralError('Invalid or expired reset token. Please request a new password reset.');
        }
    }
});

function showLoading(show) {
    const submitBtn = document.querySelector('button[type="submit"]');
    
    if (show) {
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Resetting Password...';
    } else {
        submitBtn.disabled = false;
        submitBtn.innerHTML = '<i class="fas fa-key"></i> Reset Password';
    }
}

function showSuccess(message) {
    const successDiv = document.createElement('div');
    successDiv.className = 'success-message';
    successDiv.innerHTML = `
        <i class="fas fa-check-circle"></i>
        <span>${message}</span>
    `;
    
    const form = document.getElementById('resetPasswordForm');
    
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
    
    const form = document.getElementById('resetPasswordForm');
    
    // Remove existing messages
    const existingMessage = form.querySelector('.success-message, .general-error-message');
    if (existingMessage) {
        existingMessage.remove();
    }
    
    form.insertBefore(errorDiv, form.firstChild);
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
