// Real-time Dashboard Analytics for Agriport Farmers
// Provides comprehensive sales tracking, revenue metrics, and performance insights

class FarmerAnalytics {
    constructor() {
        this.farmerId = Auth.getUserId();
        this.analyticsData = {};
        this.charts = {};
        this.refreshInterval = null;
        this.isInitialized = false;
        
        this.init();
    }
    
    init() {
        this.loadAnalyticsData();
        this.setupRefreshInterval();
        this.isInitialized = true;
        
        console.log('Farmer Analytics initialized');
    }
    
    async loadAnalyticsData() {
        try {
            const response = await fetch(`/api/farmers/${this.farmerId}/analytics`, {
                headers: {
                    'Authorization': `Bearer ${Auth.getToken()}`
                }
            });
            
            if (response.ok) {
                this.analyticsData = await response.json();
                this.updateDashboardMetrics();
                this.renderCharts();
            }
        } catch (error) {
            console.error('Error loading analytics data:', error);
        }
    }
    
    updateDashboardMetrics() {
        const data = this.analyticsData;
        
        // Update quick stats
        this.updateQuickStats(data.quickStats);
        
        // Update performance metrics
        this.updatePerformanceMetrics(data.performance);
        
        // Update recent activity
        this.updateRecentActivity(data.recentActivity);
    }
    
    updateQuickStats(stats) {
        // Update existing stats or create new ones
        const statsContainer = document.querySelector('.quick-stats');
        if (!statsContainer) return;
        
        statsContainer.innerHTML = `
            <div class="stat-item">
                <div class="stat-icon">
                    <i class="fas fa-list"></i>
                </div>
                <div class="stat-content">
                    <div class="number">${stats.activeListings || 0}</div>
                    <div class="label">Active Listings</div>
                    <div class="change ${stats.listingsChange >= 0 ? 'positive' : 'negative'}">
                        <i class="fas fa-${stats.listingsChange >= 0 ? 'arrow-up' : 'arrow-down'}"></i>
                        ${Math.abs(stats.listingsChange || 0)}%
                    </div>
                </div>
            </div>
            
            <div class="stat-item">
                <div class="stat-icon">
                    <i class="fas fa-calendar-check"></i>
                </div>
                <div class="stat-content">
                    <div class="number">${stats.pendingReservations || 0}</div>
                    <div class="label">Pending Reservations</div>
                    <div class="change ${stats.reservationsChange >= 0 ? 'positive' : 'negative'}">
                        <i class="fas fa-${stats.reservationsChange >= 0 ? 'arrow-up' : 'arrow-down'}"></i>
                        ${Math.abs(stats.reservationsChange || 0)}%
                    </div>
                </div>
            </div>
            
            <div class="stat-item">
                <div class="stat-icon">
                    <i class="fas fa-money-bill-wave"></i>
                </div>
                <div class="stat-content">
                    <div class="number">${this.formatCurrency(stats.weeklyRevenue || 0)}</div>
                    <div class="label">Weekly Revenue</div>
                    <div class="change ${stats.revenueChange >= 0 ? 'positive' : 'negative'}">
                        <i class="fas fa-${stats.revenueChange >= 0 ? 'arrow-up' : 'arrow-down'}"></i>
                        ${Math.abs(stats.revenueChange || 0)}%
                    </div>
                </div>
            </div>
            
            <div class="stat-item">
                <div class="stat-icon">
                    <i class="fas fa-star"></i>
                </div>
                <div class="stat-content">
                    <div class="number">${(stats.averageRating || 0).toFixed(1)}</div>
                    <div class="label">Average Rating</div>
                    <div class="rating-stars">
                        ${this.generateStars(stats.averageRating || 0)}
                    </div>
                </div>
            </div>
        `;
    }
    
    updatePerformanceMetrics(performance) {
        // Create or update performance section
        let performanceSection = document.querySelector('.performance-section');
        
        if (!performanceSection) {
            performanceSection = document.createElement('div');
            performanceSection.className = 'section performance-section';
            
            const dashboardSections = document.querySelector('.dashboard-sections');
            if (dashboardSections) {
                dashboardSections.appendChild(performanceSection);
            }
        }
        
        performanceSection.innerHTML = `
            <div class="section-header">
                <h2><i class="fas fa-chart-line"></i> Performance Analytics</h2>
                <div class="time-filter">
                    <select id="analyticsTimeFilter">
                        <option value="7">Last 7 days</option>
                        <option value="30">Last 30 days</option>
                        <option value="90">Last 3 months</option>
                        <option value="365">Last year</option>
                    </select>
                </div>
            </div>
            
            <div class="analytics-grid">
                <div class="analytics-card">
                    <h3>Sales Overview</h3>
                    <canvas id="salesChart" width="400" height="200"></canvas>
                </div>
                
                <div class="analytics-card">
                    <h3>Revenue Trends</h3>
                    <canvas id="revenueChart" width="400" height="200"></canvas>
                </div>
                
                <div class="analytics-card">
                    <h3>Top Products</h3>
                    <div class="top-products-list">
                        ${this.generateTopProductsList(performance.topProducts || [])}
                    </div>
                </div>
                
                <div class="analytics-card">
                    <h3>Customer Insights</h3>
                    <div class="customer-metrics">
                        <div class="metric">
                            <span class="metric-label">Total Customers</span>
                            <span class="metric-value">${performance.totalCustomers || 0}</span>
                        </div>
                        <div class="metric">
                            <span class="metric-label">Repeat Customers</span>
                            <span class="metric-value">${performance.repeatCustomers || 0}</span>
                        </div>
                        <div class="metric">
                            <span class="metric-label">Customer Retention</span>
                            <span class="metric-value">${(performance.retentionRate || 0).toFixed(1)}%</span>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        // Set up time filter
        this.setupTimeFilter();
    }
    
    generateTopProductsList(topProducts) {
        return topProducts.map((product, index) => `
            <div class="top-product-item">
                <div class="product-rank">${index + 1}</div>
                <div class="product-info">
                    <div class="product-name">${product.name}</div>
                    <div class="product-stats">
                        <span class="sales-count">${product.salesCount} sales</span>
                        <span class="revenue">${this.formatCurrency(product.revenue)}</span>
                    </div>
                </div>
                <div class="product-trend ${product.trend >= 0 ? 'up' : 'down'}">
                    <i class="fas fa-${product.trend >= 0 ? 'arrow-up' : 'arrow-down'}"></i>
                    ${Math.abs(product.trend)}%
                </div>
            </div>
        `).join('');
    }
    
    updateRecentActivity(recentActivity) {
        // Create or update recent activity section
        let activitySection = document.querySelector('.recent-activity-section');
        
        if (!activitySection) {
            activitySection = document.createElement('div');
            activitySection.className = 'section recent-activity-section';
            
            const dashboardSections = document.querySelector('.dashboard-sections');
            if (dashboardSections) {
                dashboardSections.appendChild(activitySection);
            }
        }
        
        activitySection.innerHTML = `
            <div class="section-header">
                <h2><i class="fas fa-clock"></i> Recent Activity</h2>
                <a href="#sales" class="action">View All</a>
            </div>
            
            <div class="activity-list">
                ${this.generateActivityList(recentActivity || [])}
            </div>
        `;
    }
    
    generateActivityList(activities) {
        if (activities.length === 0) {
            return '<div class="no-activity">No recent activity</div>';
        }
        
        return activities.map(activity => `
            <div class="activity-item">
                <div class="activity-icon ${activity.type}">
                    <i class="fas fa-${this.getActivityIcon(activity.type)}"></i>
                </div>
                <div class="activity-content">
                    <div class="activity-title">${activity.title}</div>
                    <div class="activity-description">${activity.description}</div>
                    <div class="activity-time">${this.getTimeAgo(activity.timestamp)}</div>
                </div>
                <div class="activity-value">
                    ${activity.value ? this.formatCurrency(activity.value) : ''}
                </div>
            </div>
        `).join('');
    }
    
    renderCharts() {
        // Render sales chart
        this.renderSalesChart();
        
        // Render revenue chart
        this.renderRevenueChart();
    }
    
    renderSalesChart() {
        const canvas = document.getElementById('salesChart');
        if (!canvas) return;
        
        const ctx = canvas.getContext('2d');
        const data = this.analyticsData.charts?.sales || {};
        
        // Simple chart implementation (you can replace with Chart.js for more features)
        this.drawLineChart(ctx, data, {
            title: 'Daily Sales',
            color: '#2c5530',
            backgroundColor: 'rgba(44, 85, 48, 0.1)'
        });
    }
    
    renderRevenueChart() {
        const canvas = document.getElementById('revenueChart');
        if (!canvas) return;
        
        const ctx = canvas.getContext('2d');
        const data = this.analyticsData.charts?.revenue || {};
        
        this.drawLineChart(ctx, data, {
            title: 'Daily Revenue',
            color: '#28a745',
            backgroundColor: 'rgba(40, 167, 69, 0.1)'
        });
    }
    
    drawLineChart(ctx, data, options) {
        const canvas = ctx.canvas;
        const width = canvas.width;
        const height = canvas.height;
        const padding = 40;
        
        // Clear canvas
        ctx.clearRect(0, 0, width, height);
        
        if (!data.labels || !data.values || data.labels.length === 0) {
            // Draw "No data" message
            ctx.fillStyle = '#666';
            ctx.font = '14px Arial';
            ctx.textAlign = 'center';
            ctx.fillText('No data available', width / 2, height / 2);
            return;
        }
        
        const chartWidth = width - 2 * padding;
        const chartHeight = height - 2 * padding;
        
        const maxValue = Math.max(...data.values);
        const minValue = Math.min(...data.values);
        const valueRange = maxValue - minValue || 1;
        
        // Draw background
        ctx.fillStyle = options.backgroundColor;
        ctx.fillRect(padding, padding, chartWidth, chartHeight);
        
        // Draw grid lines
        ctx.strokeStyle = '#e0e0e0';
        ctx.lineWidth = 1;
        
        // Horizontal grid lines
        for (let i = 0; i <= 5; i++) {
            const y = padding + (chartHeight / 5) * i;
            ctx.beginPath();
            ctx.moveTo(padding, y);
            ctx.lineTo(width - padding, y);
            ctx.stroke();
        }
        
        // Draw line
        ctx.strokeStyle = options.color;
        ctx.lineWidth = 2;
        ctx.beginPath();
        
        data.values.forEach((value, index) => {
            const x = padding + (chartWidth / (data.values.length - 1)) * index;
            const y = padding + chartHeight - ((value - minValue) / valueRange) * chartHeight;
            
            if (index === 0) {
                ctx.moveTo(x, y);
            } else {
                ctx.lineTo(x, y);
            }
        });
        
        ctx.stroke();
        
        // Draw points
        ctx.fillStyle = options.color;
        data.values.forEach((value, index) => {
            const x = padding + (chartWidth / (data.values.length - 1)) * index;
            const y = padding + chartHeight - ((value - minValue) / valueRange) * chartHeight;
            
            ctx.beginPath();
            ctx.arc(x, y, 3, 0, 2 * Math.PI);
            ctx.fill();
        });
        
        // Draw labels
        ctx.fillStyle = '#666';
        ctx.font = '12px Arial';
        ctx.textAlign = 'center';
        
        data.labels.forEach((label, index) => {
            const x = padding + (chartWidth / (data.labels.length - 1)) * index;
            ctx.fillText(label, x, height - 10);
        });
    }
    
    setupTimeFilter() {
        const timeFilter = document.getElementById('analyticsTimeFilter');
        if (timeFilter) {
            timeFilter.addEventListener('change', (e) => {
                this.loadAnalyticsData(e.target.value);
            });
        }
    }
    
    setupRefreshInterval() {
        // Refresh analytics data every 5 minutes
        this.refreshInterval = setInterval(() => {
            this.loadAnalyticsData();
        }, 300000);
    }
    
    // Utility functions
    formatCurrency(amount) {
        return new Intl.NumberFormat('fr-CM', {
            style: 'currency',
            currency: 'XAF',
            minimumFractionDigits: 0
        }).format(amount);
    }
    
    generateStars(rating) {
        const fullStars = Math.floor(rating);
        const hasHalfStar = rating % 1 >= 0.5;
        const emptyStars = 5 - fullStars - (hasHalfStar ? 1 : 0);
        
        let stars = '';
        
        // Full stars
        for (let i = 0; i < fullStars; i++) {
            stars += '<i class="fas fa-star"></i>';
        }
        
        // Half star
        if (hasHalfStar) {
            stars += '<i class="fas fa-star-half-alt"></i>';
        }
        
        // Empty stars
        for (let i = 0; i < emptyStars; i++) {
            stars += '<i class="far fa-star"></i>';
        }
        
        return stars;
    }
    
    getActivityIcon(type) {
        const icons = {
            'sale': 'money-bill-wave',
            'reservation': 'calendar-check',
            'listing': 'plus-circle',
            'urgent_sale': 'exclamation-triangle',
            'review': 'star',
            'message': 'comment'
        };
        return icons[type] || 'circle';
    }
    
    getTimeAgo(timestamp) {
        const now = new Date();
        const time = new Date(timestamp);
        const diffInSeconds = Math.floor((now - time) / 1000);
        
        if (diffInSeconds < 60) return 'Just now';
        if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)}m ago`;
        if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)}h ago`;
        return `${Math.floor(diffInSeconds / 86400)}d ago`;
    }
    
    // Public methods
    refresh() {
        this.loadAnalyticsData();
    }
    
    destroy() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
        }
    }
}

// Initialize analytics when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Initialize analytics if user is authenticated as farmer
    if (Auth.isAuthenticated() && Auth.getUserType() === 'Farmer') {
        window.farmerAnalytics = new FarmerAnalytics();
    }
});

// Export for use in other modules
window.FarmerAnalytics = FarmerAnalytics;
