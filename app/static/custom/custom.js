/**
 * Custom JavaScript for MedFlow
 * Includes global error handlers for unauthorized access
 */

(function() {
    'use strict';

    // ========================================
    // Global 403 Error Interceptor
    // ========================================
    
    // Store original fetch
    const originalFetch = window.fetch;
    
    window.fetch = function(...args) {
        return originalFetch.apply(this, args).then(response => {
            // Check for 403 Forbidden status
            if (response.status === 403) {
                // Check if it's an API request (JSON response)
                const contentType = response.headers.get('content-type');
                if (contentType && contentType.includes('application/json')) {
                    // Clone the response and parse JSON
                    response.clone().json().then(data => {
                        showAccessDeniedPopup(data.detail || 'You do not have permission to access this module. Please contact system administrator.');
                    }).catch(() => {
                        // Fallback if JSON parsing fails
                        showAccessDeniedPopup('You do not have permission to access this module. Please contact system administrator.');
                    });
                }
            }
            return response;
        });
    };

    /**
     * Show SweetAlert2 popup for access denied
     * @param {string} message - The error message to display
     */
    function showAccessDeniedPopup(message) {
        // Check if SweetAlert2 is available
        if (typeof Swal !== 'undefined') {
            Swal.fire({
                icon: 'error',
                title: 'Access Denied',
                text: message,
                confirmButtonText: 'OK',
                confirmButtonColor: '#dc3545',
                allowOutsideClick: false,
                reverseButtons: true
            }).then((result) => {
                if (result.isConfirmed) {
                    // Optionally redirect to dashboard
                    // window.location.href = '/';
                }
            });
        } else {
            // Fallback to native alert if SweetAlert2 is not available
            alert('Access Denied\\n\\n' + message);
        }
    }

    // ========================================
    // AJAX Error Handler for jQuery
    // ========================================
    
    $(document).ajaxError(function(event, jqXHR, ajaxSettings, thrownError) {
        if (jqXHR.status === 403) {
            const errorMessage = jqXHR.responseJSON?.detail || 
                                 'You do not have permission to access this module. Please contact system administrator.';
            showAccessDeniedPopup(errorMessage);
        }
    });

    // ========================================
    // Utility Functions
    // ========================================

    /**
     * Format date to readable string
     * @param {string} dateString - ISO date string
     * @returns {string} Formatted date
     */
    window.formatDate = function(dateString) {
        if (!dateString) return '';
        const date = new Date(dateString);
        return date.toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric'
        });
    };

    /**
     * Format datetime to readable string
     * @param {string} dateString - ISO datetime string
     * @returns {string} Formatted datetime
     */
    window.formatDateTime = function(dateString) {
        if (!dateString) return '';
        const date = new Date(dateString);
        return date.toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    };

    /**
     * Show success notification
     * @param {string} message - Success message
     */
    window.showSuccess = function(message) {
        if (typeof Swal !== 'undefined') {
            Swal.fire({
                icon: 'success',
                title: 'Success',
                text: message,
                timer: 3000,
                timerProgressBar: true,
                showConfirmButton: false
            });
        } else {
            alert('Success: ' + message);
        }
    };

    /**
     * Show warning notification
     * @param {string} message - Warning message
     */
    window.showWarning = function(message) {
        if (typeof Swal !== 'undefined') {
            Swal.fire({
                icon: 'warning',
                title: 'Warning',
                text: message,
                confirmButtonColor: '#ffc107'
            });
        } else {
            alert('Warning: ' + message);
        }
    };

    /**
     * Show info notification
     * @param {string} message - Info message
     */
    window.showInfo = function(message) {
        if (typeof Swal !== 'undefined') {
            Swal.fire({
                icon: 'info',
                title: 'Info',
                text: message
            });
        } else {
            alert('Info: ' + message);
        }
    };

    // ========================================
    // Sidebar Search Functionality
    // ========================================
    
    function initSidebarSearch() {
        const searchInput = document.getElementById('sidebarSearch');
        if (!searchInput) return;
        
        searchInput.addEventListener('keyup', function(e) {
            const searchTerm = e.target.value.toLowerCase().trim();
            const menuItems = document.querySelectorAll('.nav-sidebar > .nav-item, .nav-sidebar > li');
            
            menuItems.forEach(function(item) {
                // Skip headers and non-menu items
                if (item.classList.contains('nav-header')) return;
                
                const link = item.querySelector('.nav-link');
                if (!link) return;
                
                const text = link.textContent.toLowerCase();
                const icon = link.querySelector('.nav-icon');
                
                if (searchTerm === '') {
                    // Show all items
                    item.style.display = '';
                    if (item.classList.contains('has-treeview')) {
                        // Reset treeview state
                        item.classList.remove('menu-open');
                    }
                } else if (text.includes(searchTerm)) {
                    // Show matching item
                    item.style.display = '';
                    // Expand parent treeviews
                    let parent = item.closest('.has-treeview');
                    while (parent) {
                        parent.classList.add('menu-open');
                        parent.style.display = '';
                        parent = parent.closest('.has-treeview');
                    }
                } else {
                    // Hide non-matching items
                    // But don't hide treeview parents if they have visible children
                    const childItems = item.querySelectorAll('.nav-item');
                    let hasVisibleChild = false;
                    childItems.forEach(function(child) {
                        const childText = child.textContent.toLowerCase();
                        if (childText.includes(searchTerm)) {
                            hasVisibleChild = true;
                        }
                    });
                    
                    if (!hasVisibleChild) {
                        item.style.display = 'none';
                    }
                }
            });
        });
        
        // Clear search when pressing Escape
        searchInput.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') {
                searchInput.value = '';
                searchInput.dispatchEvent(new Event('keyup'));
                searchInput.blur();
            }
        });
    }

    // ========================================
    // Sidebar Mobile Improvements
    // ========================================
    
    function initSidebarMobile() {
        // Fix: Mobile touch devices often don't fire click reliably on pushmenu button.
        // Add touchend so sidebar toggles immediately on tap.
        var $pushBtn = $('[data-widget="pushmenu"]');
        if ($pushBtn.length) {
            $pushBtn.on('touchend', function(e) {
                if (window.innerWidth <= 992) {
                    e.preventDefault();
                    $(this).PushMenu('toggle');
                }
            });
        }
        
        // Fix: Treeview dropdowns don't respond on mobile (click rarely fires on touch).
        // Add touchend so tapping a parent menu expands/collapses the submenu.
        var $treeviewParents = $('.nav-sidebar .nav-item.has-treeview > .nav-link');
        $treeviewParents.on('touchend', function(e) {
            if (window.innerWidth <= 992) {
                e.preventDefault();
                $(this).trigger('click');
            }
        });
    }

    // ========================================
    // Global Loading Indicator (form submissions)
    // ========================================
    
    window.showGlobalLoading = function() {
        const overlay = document.getElementById('global-loading');
        if (overlay) overlay.style.display = 'flex';
    };
    window.hideGlobalLoading = function() {
        const overlay = document.getElementById('global-loading');
        if (overlay) overlay.style.display = 'none';
    };

    // ========================================
    // Accessibility: Keyboard shortcuts
    // ========================================
    
    function initKeyboardShortcuts() {
        $(document).on('keydown', function(e) {
            // ? or / - focus search/sidebar search
            if (e.key === '?' || (e.key === '/' && !$(e.target).is('input, textarea, select'))) {
                e.preventDefault();
                var search = document.getElementById('sidebarSearch');
                if (search) {
                    search.focus();
                }
            }
            // Escape - close modal, clear overlay
            if (e.key === 'Escape') {
                var modal = $('.modal.show');
                if (modal.length) {
                    modal.modal('hide');
                }
            }
        });
    }

    // ========================================
    // DOM Ready Handler
    // ========================================
    
    $(document).ready(function() {
        console.log('MedFlow Custom JavaScript loaded successfully');
        
        // Initialize sidebar enhancements
        initSidebarSearch();
        initSidebarMobile();
        initKeyboardShortcuts();
        
        // Global loading: show on POST form submit
        $(document).on('submit', 'form:not([data-no-loading])', function() {
            const form = this;
            const isAjax = $(form).attr('data-ajax') === 'true';
            if (!isAjax && (form.method === 'post' || form.method === 'POST')) {
                window.showGlobalLoading();
            }
        });
    });

})();
