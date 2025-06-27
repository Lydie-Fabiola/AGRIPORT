// Buyer Profile Management JavaScript
const API_BASE_URL = 'http://localhost:8000/api';

document.addEventListener('DOMContentLoaded', function() {
    // Check authentication
    if (!window.BuyerAuth || !window.BuyerAuth.isAuthenticated()) {
        window.location.href = 'loginbuyer.html';
        return;
    }
    
    // Initialize profile page
    initializeProfile();
});

async function initializeProfile() {
    try {
        // Load current profile data
        await loadProfileData();
        
        // Setup event listeners
        setupEventListeners();
        
        console.log('Profile page initialized successfully');
    } catch (error) {
        console.error('Failed to initialize profile:', error);
        showError('Failed to load profile data. Please refresh the page.');
    }
}

async function loadProfileData() {
    try {
        showLoading(true);
        
        const response = await window.BuyerAuth.apiRequest('/buyer/profile/', {
            method: 'GET'
        });
        
        if (response && response.ok) {
            const data = await response.json();
            if (data.success) {
                populateForm(data.profile, data.user);
            } else {
                throw new Error(data.error || 'Failed to load profile');
            }
        } else {
            throw new Error('Failed to fetch profile data');
        }
    } catch (error) {
        console.error('Error loading profile:', error);
        showError('Failed to load profile data: ' + error.message);
    } finally {
        showLoading(false);
    }
}

function populateForm(profile, user) {
    // User data (from CustomUser model)
    if (user) {
        document.getElementById('firstName').value = user.first_name || '';
        document.getElementById('lastName').value = user.last_name || '';
        document.getElementById('email').value = user.email || '';
        document.getElementById('phone').value = user.phone_number || '';
    }
    
    // Profile data (from BuyerProfile model)
    if (profile) {
        document.getElementById('location').value = profile.location || '';
        document.getElementById('deliveryAddress').value = profile.delivery_address || '';
        document.getElementById('preferredDeliveryMethod').value = profile.preferred_delivery_method || '';
        document.getElementById('dateOfBirth').value = profile.date_of_birth || '';
        
        // Set profile picture if available
        if (profile.avatar) {
            document.getElementById('profilePicture').src = profile.avatar;
        }
        
        // Set delivery time preferences
        if (profile.delivery_time_preferences) {
            const preferences = profile.delivery_time_preferences.split(',');
            preferences.forEach(pref => {
                const checkbox = document.querySelector(`input[name="deliveryTimes"][value="${pref.trim()}"]`);
                if (checkbox) checkbox.checked = true;
            });
        }
        
        // Set notification preferences
        document.getElementById('emailNotifications').checked = profile.email_notifications !== false;
        document.getElementById('smsNotifications').checked = profile.sms_notifications === true;
        document.getElementById('marketingEmails').checked = profile.marketing_emails === true;
    }
}

function setupEventListeners() {
    // Profile form submission
    document.getElementById('profileForm').addEventListener('submit', handleFormSubmit);
    
    // Profile picture change
    document.querySelector('.profile-picture-container').addEventListener('click', () => {
        document.getElementById('profilePictureInput').click();
    });
    
    document.getElementById('profilePictureInput').addEventListener('change', handleProfilePictureChange);
    
    // Real-time validation
    setupValidation();
}

function setupValidation() {
    const firstName = document.getElementById('firstName');
    const lastName = document.getElementById('lastName');
    const phone = document.getElementById('phone');
    const location = document.getElementById('location');
    
    firstName.addEventListener('input', () => validateField(firstName, 'firstNameError', validateName));
    lastName.addEventListener('input', () => validateField(lastName, 'lastNameError', validateName));
    phone.addEventListener('input', () => validateField(phone, 'phoneError', validatePhone));
    location.addEventListener('input', () => validateField(location, 'locationError', validateLocation));
}

function validateField(input, errorId, validator) {
    const errorElement = document.getElementById(errorId);
    const result = validator(input.value);
    
    if (result.isValid) {
        input.style.borderColor = '#28a745';
        errorElement.textContent = '';
    } else {
        input.style.borderColor = '#dc3545';
        errorElement.textContent = result.message;
    }
    
    return result.isValid;
}

function validateName(value) {
    if (!value.trim()) {
        return { isValid: false, message: 'This field is required' };
    }
    if (value.trim().length < 2) {
        return { isValid: false, message: 'Must be at least 2 characters' };
    }
    if (!/^[A-Za-z\s]+$/.test(value)) {
        return { isValid: false, message: 'Only letters and spaces allowed' };
    }
    return { isValid: true };
}

function validatePhone(value) {
    if (!value.trim()) {
        return { isValid: false, message: 'Phone number is required' };
    }
    const phoneRegex = /^(237\s?)?[6-9]\d{8}$/;
    if (!phoneRegex.test(value.replace(/\s+/g, ''))) {
        return { isValid: false, message: 'Please enter a valid Cameroon phone number' };
    }
    return { isValid: true };
}

function validateLocation(value) {
    if (!value.trim()) {
        return { isValid: false, message: 'Location is required' };
    }
    if (value.trim().length < 3) {
        return { isValid: false, message: 'Location must be at least 3 characters' };
    }
    return { isValid: true };
}

async function handleFormSubmit(event) {
    event.preventDefault();
    
    // Validate all fields
    const isValid = validateAllFields();
    if (!isValid) {
        showError('Please fix the errors in the form before submitting.');
        return;
    }
    
    try {
        showLoading(true);
        
        // Collect form data
        const formData = collectFormData();
        
        // Submit to API
        const response = await window.BuyerAuth.apiRequest('/buyer/profile/', {
            method: 'PUT',
            body: JSON.stringify(formData)
        });
        
        if (response && response.ok) {
            const data = await response.json();
            if (data.success) {
                showSuccessModal();
                console.log('Profile updated successfully');
            } else {
                throw new Error(data.error || 'Failed to update profile');
            }
        } else {
            throw new Error('Failed to update profile');
        }
    } catch (error) {
        console.error('Error updating profile:', error);
        showError('Failed to update profile: ' + error.message);
    } finally {
        showLoading(false);
    }
}

function validateAllFields() {
    const firstName = validateField(document.getElementById('firstName'), 'firstNameError', validateName);
    const lastName = validateField(document.getElementById('lastName'), 'lastNameError', validateName);
    const phone = validateField(document.getElementById('phone'), 'phoneError', validatePhone);
    const location = validateField(document.getElementById('location'), 'locationError', validateLocation);
    
    return firstName && lastName && phone && location;
}

function collectFormData() {
    // Get delivery time preferences
    const deliveryTimes = Array.from(document.querySelectorAll('input[name="deliveryTimes"]:checked'))
        .map(cb => cb.value);
    
    return {
        // User fields
        first_name: document.getElementById('firstName').value.trim(),
        last_name: document.getElementById('lastName').value.trim(),
        phone_number: document.getElementById('phone').value.trim(),
        
        // Profile fields
        location: document.getElementById('location').value.trim(),
        delivery_address: document.getElementById('deliveryAddress').value.trim(),
        preferred_delivery_method: document.getElementById('preferredDeliveryMethod').value,
        date_of_birth: document.getElementById('dateOfBirth').value || null,
        delivery_time_preferences: deliveryTimes.join(', '),
        email_notifications: document.getElementById('emailNotifications').checked,
        sms_notifications: document.getElementById('smsNotifications').checked,
        marketing_emails: document.getElementById('marketingEmails').checked
    };
}

async function handleProfilePictureChange(event) {
    const file = event.target.files[0];
    if (!file) return;
    
    // Validate file
    if (!file.type.startsWith('image/')) {
        showError('Please select a valid image file.');
        return;
    }
    
    if (file.size > 5 * 1024 * 1024) { // 5MB limit
        showError('Image file must be less than 5MB.');
        return;
    }
    
    try {
        // Preview image
        const reader = new FileReader();
        reader.onload = function(e) {
            document.getElementById('profilePicture').src = e.target.result;
        };
        reader.readAsDataURL(file);
        
        // TODO: Upload to server
        console.log('Profile picture selected:', file.name);
        showSuccess('Profile picture updated! Don\'t forget to save your profile.');
        
    } catch (error) {
        console.error('Error handling profile picture:', error);
        showError('Failed to update profile picture.');
    }
}

function resetForm() {
    if (confirm('Are you sure you want to reset all changes? This will reload your current profile data.')) {
        loadProfileData();
    }
}

function showLoading(show) {
    const overlay = document.getElementById('loadingOverlay');
    overlay.style.display = show ? 'flex' : 'none';
}

function showSuccessModal() {
    document.getElementById('successModal').style.display = 'flex';
}

function closeSuccessModal() {
    document.getElementById('successModal').style.display = 'none';
}

function showError(message) {
    alert('Error: ' + message);
    // TODO: Replace with better error display
}

function showSuccess(message) {
    alert('Success: ' + message);
    // TODO: Replace with better success display
}
