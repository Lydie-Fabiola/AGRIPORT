document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('farmerRegistrationForm');
    
    if (form) {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            
            // Clear previous error messages
            clearErrors();
            
            // Validate form
            if (validateForm()) {
                // Collect form data
                const formData = new FormData(form);
                const formDataObj = {};
                
                formData.forEach((value, key) => {
                    // Handle checkboxes (products)
                    if (key === 'products') {
                        if (!formDataObj[key]) {
                            formDataObj[key] = [];
                        }
                        formDataObj[key].push(value);
                    } else {
                        formDataObj[key] = value;
                    }
                });
                
                // Show loading state
                const submitButton = form.querySelector('button[type="submit"]');
                const originalButtonText = submitButton.textContent;
                submitButton.textContent = 'Creating Account...';
                submitButton.disabled = true;
                
                // Simulate API call (replace with actual API call)
                setTimeout(() => {
                    console.log('Form data to be sent to API:', formDataObj);
                    
                    // Simulate successful registration
                    // In production, this would be the API response handler
                    showSuccessMessage();
                    
                    // Reset form
                    form.reset();
                    
                    // Reset button
                    submitButton.textContent = originalButtonText;
                    submitButton.disabled = false;
                    
                    // Redirect to dashboard after delay
                    setTimeout(() => {
                        window.location.href = 'farmer-dashboard.html';
                    }, 2000);
                    
                }, 1500);
            }
        });
    }
    
    // Form validation
    function validateForm() {
        let isValid = true;
        
        // Validate full name
        const fullName = document.getElementById('fullName');
        if (!fullName.value.trim()) {
            showError(fullName, 'Full name is required');
            isValid = false;
        }
        
        // Validate email
        const email = document.getElementById('email');
        if (!email.value.trim()) {
            showError(email, 'Email is required');
            isValid = false;
        } else if (!isValidEmail(email.value)) {
            showError(email, 'Please enter a valid email address');
            isValid = false;
        }
        
        // Validate phone
        const phone = document.getElementById('phone');
        if (!phone.value.trim()) {
            showError(phone, 'Phone number is required');
            isValid = false;
        }
        
        // Validate location
        const location = document.getElementById('location');
        if (!location.value) {
            showError(location, 'Please select your region');
            isValid = false;
        }
        
        // Validate farm size
        const farmSize = document.getElementById('farmSize');
        if (!farmSize.value) {
            showError(farmSize, 'Farm size is required');
            isValid = false;
        }
        
        // Validate products
        const products = document.querySelectorAll('input[name="products"]:checked');
        if (products.length === 0) {
            const productsGroup = document.querySelector('.checkbox-group');
            showErrorForGroup(productsGroup, 'Please select at least one product');
            isValid = false;
        }
        
        // Validate password
        const password = document.getElementById('password');
        const confirmPassword = document.getElementById('confirmPassword');
        
        if (!password.value) {
            showError(password, 'Password is required');
            isValid = false;
        } else if (password.value.length < 8) {
            showError(password, 'Password must be at least 8 characters');
            isValid = false;
        }
        
        if (!confirmPassword.value) {
            showError(confirmPassword, 'Please confirm your password');
            isValid = false;
        } else if (password.value !== confirmPassword.value) {
            showError(confirmPassword, 'Passwords do not match');
            isValid = false;
        }
        
        // Validate terms agreement
        const terms = document.querySelector('input[name="terms"]');
        if (!terms.checked) {
            const termsContainer = terms.closest('.checkbox-container');
            showErrorForGroup(termsContainer, 'You must agree to the terms');
            isValid = false;
        }
        
        return isValid;
    }
    
    function isValidEmail(email) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    }
    
    function showError(inputElement, message) {
        inputElement.classList.add('error');
        
        const errorElement = document.createElement('div');
        errorElement.className = 'error-message';
        errorElement.textContent = message;
        
        const parentElement = inputElement.parentElement;
        parentElement.appendChild(errorElement);
    }
    
    function showErrorForGroup(groupElement, message) {
        const errorElement = document.createElement('div');
        errorElement.className = 'error-message';
        errorElement.textContent = message;
        
        groupElement.appendChild(errorElement);
    }
    
    function clearErrors() {
        // Remove all error classes
        const errorInputs = document.querySelectorAll('.error');
        errorInputs.forEach(input => {
            input.classList.remove('error');
        });
        
        // Remove all error messages
        const errorMessages = document.querySelectorAll('.error-message');
        errorMessages.forEach(message => {
            message.remove();
        });
    }
    
    function showSuccessMessage() {
        // Create success message
        const successMessage = document.createElement('div');
        successMessage.className = 'success-message';
        successMessage.style.backgroundColor = '#4CAF50';
        successMessage.style.color = 'white';
        successMessage.style.padding = '15px';
        successMessage.style.borderRadius = '5px';
        successMessage.style.marginTop = '20px';
        successMessage.style.textAlign = 'center';
        successMessage.textContent = 'Registration successful! Redirecting to your dashboard...';
        
        // Insert before form footer
        const formFooter = document.querySelector('.form-footer');
        form.insertBefore(successMessage, formFooter);
    }
});