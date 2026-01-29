// TaawaVault Main JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Initialize app
    initThemeToggle();
    initSearch();
    initTooltips();
    initMessageCloseButtons();
});

function initMessageCloseButtons() {
    document.querySelectorAll('[data-close-message]').forEach(function(btn) {
        btn.addEventListener('click', function() {
            var msg = this.closest('[data-message]');
            if (msg) msg.style.display = 'none';
        });
    });
}

function initThemeToggle() {
    const themeToggle = document.querySelector('.icon-btn');
    if (themeToggle && themeToggle.textContent.includes('🌙')) {
        themeToggle.addEventListener('click', function() {
            // Toggle dark/light theme
            document.body.classList.toggle('light-theme');
        });
    }
}

function initSearch() {
    const searchInput = document.querySelector('.search-input');
    if (searchInput) {
        searchInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                // Implement search functionality
                console.log('Search:', this.value);
            }
        });
    }
}

function initTooltips() {
    // Initialize tooltips if needed
}

// Utility functions
function formatCurrency(amount, currency = 'KES') {
    return new Intl.NumberFormat('en-KE', {
        style: 'currency',
        currency: currency
    }).format(amount);
}

function formatDate(date) {
    return new Intl.DateTimeFormat('en-KE', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    }).format(new Date(date));
}
