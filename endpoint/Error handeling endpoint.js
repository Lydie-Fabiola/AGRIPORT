function showError(message) {
  // Create or use an existing error display element
  const errorDiv = document.createElement('div');
  errorDiv.className = 'api-error';
  errorDiv.style.position = 'fixed';
  errorDiv.style.bottom = '20px';
  errorDiv.style.right = '20px';
  errorDiv.style.padding = '15px';
  errorDiv.style.backgroundColor = '#ffebee';
  errorDiv.style.color = '#c62828';
  errorDiv.style.borderRadius = '4px';
  errorDiv.style.boxShadow = '0 2px 5px rgba(0,0,0,0.2)';
  errorDiv.style.zIndex = '1000';
  errorDiv.textContent = message;
  
  document.body.appendChild(errorDiv);
  
  // Remove after 5 seconds
  setTimeout(() => {
    errorDiv.remove();
  }, 5000);
}

// Then modify makeApiRequest to use this:
async function makeApiRequest(endpoint, method = 'GET', body = null) {
  try {
    // ... existing code ...
  } catch (error) {
    console.error('API Error:', error);
    showError('Failed to load data. Please try again.');
    throw error;
  }
}