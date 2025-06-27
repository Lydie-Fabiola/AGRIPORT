document.addEventListener('DOMContentLoaded', function() {
    // Smooth scrolling for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            e.preventDefault();
            
            const targetId = this.getAttribute('href');
            const targetElement = document.querySelector(targetId);
            
            if (targetElement) {
                window.scrollTo({
                    top: targetElement.offsetTop - 80, // Adjust for header height
                    behavior: 'smooth'
                });
            }
        });
    });
    
    // Mobile menu toggle (if needed)
    const mobileMenuToggle = document.createElement('button');
    mobileMenuToggle.classList.add('mobile-menu-toggle');
    mobileMenuToggle.innerHTML = '☰';
    
    const nav = document.querySelector('nav');
    const navUl = document.querySelector('nav ul');
    
    if (nav && navUl) {
        nav.insertBefore(mobileMenuToggle, navUl);
        
        mobileMenuToggle.addEventListener('click', function() {
            navUl.classList.toggle('show');
        });
    }
});