document.addEventListener('DOMContentLoaded', function() {
    // Mobile menu toggle
    const mobileMenuToggle = document.getElementById('mobileMenuToggle');
    const navMenu = document.querySelector('nav ul');

    if (mobileMenuToggle && navMenu) {
        mobileMenuToggle.addEventListener('click', function() {
            navMenu.classList.toggle('show');
        });
    }

    // Smooth scrolling for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            e.preventDefault();
            
            const targetId = this.getAttribute('href');
            if (targetId === '#') return;
            
            const targetElement = document.querySelector(targetId);
            
            if (targetElement) {
                window.scrollTo({
                    top: targetElement.offsetTop - 80, // Adjust for header height
                    behavior: 'smooth'
                });
                
                // Close mobile menu if open
                if (navMenu && navMenu.classList.contains('show')) {
                    navMenu.classList.remove('show');
                }
            }
        });
    });

    // Animation for team members
    const teamMembers = document.querySelectorAll('.team-member');
    
    function checkScroll() {
        teamMembers.forEach(member => {
            const memberTop = member.getBoundingClientRect().top;
            const windowHeight = window.innerHeight;
            
            if (memberTop < windowHeight - 100) {
                member.style.opacity = '1';
                member.style.transform = 'translateY(0)';
            }
        });
    }
    
    // Initialize team members
    teamMembers.forEach(member => {
        member.style.opacity = '0';
        member.style.transform = 'translateY(20px)';
        member.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
    });
    
    // Check on scroll
    window.addEventListener('scroll', checkScroll);
    
    // Check on initial load
    checkScroll();
});