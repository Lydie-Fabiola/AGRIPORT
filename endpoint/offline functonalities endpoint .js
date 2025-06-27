// Check online status
window.addEventListener('online', () => {
  showError('Connection restored. Syncing data...');
  loadDashboardData();
});

window.addEventListener('offline', () => {
  showError('You are offline. Changes will be saved locally and synced later.');
});

// Modify makeApiRequest to use local storage when offline
async function makeApiRequest(endpoint, method = 'GET', body = null) {
  if (!navigator.onLine) {
    // Store requests for later when offline
    const pendingRequests = JSON.parse(localStorage.getItem('pendingRequests') || []);
    pendingRequests.push({ endpoint, method, body, timestamp: Date.now() });
    localStorage.setItem('pendingRequests', JSON.stringify(pendingRequests));
    
    throw new Error('Offline: Request queued for later');
  }
  
  // ... rest of the existing code ...
}