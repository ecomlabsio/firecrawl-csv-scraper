// Global JavaScript for Firecrawl CSV Scraper

// Utility functions
const utils = {
    // Format file size
    formatFileSize: function(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    },

    // Format timestamp
    formatTimestamp: function(timestamp) {
        return new Date(timestamp).toLocaleString();
    },

    // Show toast notification
    showToast: function(message, type = 'info') {
        // Create toast element
        const toast = document.createElement('div');
        toast.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
        toast.style.top = '20px';
        toast.style.right = '20px';
        toast.style.zIndex = '9999';
        toast.style.minWidth = '300px';
        
        toast.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        document.body.appendChild(toast);
        
        // Auto remove after 5 seconds
        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        }, 5000);
    },

    // Copy text to clipboard
    copyToClipboard: function(text) {
        navigator.clipboard.writeText(text).then(() => {
            this.showToast('Copied to clipboard!', 'success');
        }).catch(() => {
            this.showToast('Failed to copy to clipboard', 'error');
        });
    },

    // Debounce function
    debounce: function(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
};

// Form validation and enhancement
document.addEventListener('DOMContentLoaded', function() {
    // Enhance file input
    const fileInputs = document.querySelectorAll('input[type="file"]');
    fileInputs.forEach(input => {
        input.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (file) {
                // Validate file size
                const maxSize = 16 * 1024 * 1024; // 16MB
                if (file.size > maxSize) {
                    utils.showToast(`File too large. Maximum size is ${utils.formatFileSize(maxSize)}.`, 'danger');
                    e.target.value = '';
                    return;
                }

                // Validate file type
                const allowedTypes = ['text/csv', 'text/plain', 'application/csv'];
                if (!allowedTypes.includes(file.type) && !file.name.toLowerCase().endsWith('.csv')) {
                    utils.showToast('Please select a CSV file.', 'danger');
                    e.target.value = '';
                    return;
                }

                // Show file info
                const fileInfo = `Selected: ${file.name} (${utils.formatFileSize(file.size)})`;
                utils.showToast(fileInfo, 'info');
            }
        });
    });

    // Enhance forms with loading states
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const submitBtn = form.querySelector('button[type="submit"]');
            if (submitBtn) {
                // Store original content
                submitBtn.dataset.originalContent = submitBtn.innerHTML;
                
                // Show loading state
                submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status"></span>Processing...';
                submitBtn.disabled = true;
                
                // Re-enable after a delay if form doesn't redirect
                setTimeout(() => {
                    if (submitBtn.dataset.originalContent) {
                        submitBtn.innerHTML = submitBtn.dataset.originalContent;
                        submitBtn.disabled = false;
                    }
                }, 30000); // 30 seconds timeout
            }
        });
    });

    // Auto-refresh functionality for job pages
    if (window.location.pathname.includes('/job/')) {
        // Add refresh controls
        addRefreshControls();
    }

    // Add tooltips to truncated text
    addTooltips();

    // Initialize copy buttons
    initializeCopyButtons();
});

// Add refresh controls to job status pages
function addRefreshControls() {
    const refreshButton = document.createElement('button');
    refreshButton.className = 'btn btn-outline-secondary btn-sm position-fixed';
    refreshButton.style.top = '100px';
    refreshButton.style.right = '20px';
    refreshButton.style.zIndex = '1000';
    refreshButton.innerHTML = '<i class="fas fa-sync-alt"></i>';
    refreshButton.title = 'Refresh Status';
    
    refreshButton.addEventListener('click', function() {
        if (typeof updateJobStatus === 'function') {
            updateJobStatus();
            utils.showToast('Status refreshed', 'info');
        } else {
            window.location.reload();
        }
    });
    
    document.body.appendChild(refreshButton);
}

// Add tooltips to elements with titles
function addTooltips() {
    const tooltipElements = document.querySelectorAll('[title]');
    tooltipElements.forEach(element => {
        if (element.title && !element.hasAttribute('data-bs-toggle')) {
            element.setAttribute('data-bs-toggle', 'tooltip');
            element.setAttribute('data-bs-placement', 'top');
        }
    });

    // Initialize Bootstrap tooltips
    if (typeof bootstrap !== 'undefined') {
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }
}

// Initialize copy buttons for job IDs and other copyable content
function initializeCopyButtons() {
    const copyableElements = document.querySelectorAll('code[title]');
    copyableElements.forEach(element => {
        if (element.title && element.title.length > element.textContent.length) {
            element.style.cursor = 'pointer';
            element.addEventListener('click', function() {
                utils.copyToClipboard(element.title);
            });
        }
    });
}

// Progressive enhancement for better UX
function enhanceProgressBars() {
    const progressBars = document.querySelectorAll('.progress-bar');
    progressBars.forEach(bar => {
        const width = bar.style.width;
        if (width && width !== '0%') {
            bar.style.transition = 'width 0.5s ease-in-out';
        }
    });
}

// Real-time updates helper
function createWebSocketConnection(jobId) {
    // This could be enhanced with WebSocket support for real-time updates
    // For now, we use polling which is more compatible
    return null;
}

// Error handling for AJAX requests
function handleAjaxError(error, context = '') {
    console.error('AJAX Error:', error);
    utils.showToast(`Error loading ${context}. Please try again.`, 'danger');
}

// Local storage helpers for user preferences
const preferences = {
    get: function(key, defaultValue = null) {
        try {
            const value = localStorage.getItem(`firecrawl_${key}`);
            return value ? JSON.parse(value) : defaultValue;
        } catch (e) {
            return defaultValue;
        }
    },

    set: function(key, value) {
        try {
            localStorage.setItem(`firecrawl_${key}`, JSON.stringify(value));
        } catch (e) {
            console.warn('Failed to save preference:', key);
        }
    }
};

// Remember form values
function rememberFormValues() {
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        const inputs = form.querySelectorAll('input[type="text"], input[type="number"], select');
        inputs.forEach(input => {
            if (input.name && !input.name.includes('password') && !input.name.includes('key')) {
                // Load saved value
                const savedValue = preferences.get(`form_${input.name}`);
                if (savedValue !== null && input.value === input.defaultValue) {
                    input.value = savedValue;
                }

                // Save on change
                input.addEventListener('change', function() {
                    preferences.set(`form_${input.name}`, input.value);
                });
            }
        });
    });
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    rememberFormValues();
    enhanceProgressBars();
});

// Keyboard shortcuts
document.addEventListener('keydown', function(e) {
    // Ctrl/Cmd + R for refresh on job status pages
    if ((e.ctrlKey || e.metaKey) && e.key === 'r' && window.location.pathname.includes('/job/')) {
        e.preventDefault();
        if (typeof updateJobStatus === 'function') {
            updateJobStatus();
        }
    }
    
    // Escape to go back to home
    if (e.key === 'Escape' && !document.querySelector('.modal.show')) {
        if (window.location.pathname !== '/') {
            window.location.href = '/';
        }
    }
});

// Export utilities for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { utils, preferences };
}
