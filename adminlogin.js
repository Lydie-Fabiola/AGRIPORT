document.addEventListener('DOMContentLoaded', function() {
  const form = document.getElementById('adminLoginForm');
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
      
      console.log('Admin login attempt:', loginData);
      
      // Here you would typically send this data to your backend API
      // For now, simulate successful login and redirect
      
      // This is just for demonstration - in a real app, you'd verify credentials with the server
      if (loginData.username === 'admin' && loginData.password === 'admin123') {
        alert('Admin login successful!');
        window.location.href = 'admindashboard.html';
      } else {
        setError(username, usernameError, 'Invalid admin credentials');
        setError(password, passwordError, '');
      }
    }
  });
  
  function validateUsername() {
    const value = username.value.trim();
    let isValid = true;
    
    if (value === '') {
      setError(username, usernameError, 'Admin username is required');
      isValid = false;
    } else {
      setSuccess(username, usernameError);
    }
    
    return isValid;
  }
  
  function validatePassword() {
    const value = password.value;
    let isValid = true;
    
    if (value === '') {
      setError(password, passwordError, 'Password is required');
      isValid = false;
    } else {
      setSuccess(password, passwordError);
    }
    
    return isValid;
  }
  
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

