/**
 * BBall Ref Local - Main Application JavaScript
 * Handles dark mode, Tabulator initialization, and HTMX events
 */

(function() {
    'use strict';

    // ============================================
    // Dark Mode Functionality
    // ============================================
    
    const DarkModeManager = {
        storageKey: 'bball-ref-theme',
        toggleBtn: null,
        iconEl: null,

        init() {
            this.toggleBtn = document.getElementById('darkModeToggle');
            this.iconEl = document.getElementById('darkModeIcon');
            
            if (!this.toggleBtn || !this.iconEl) {
                console.warn('Dark mode elements not found');
                return;
            }

            // Load saved preference or system preference
            this.loadTheme();

            // Bind click event
            this.toggleBtn.addEventListener('click', () => this.toggle());
        },

        loadTheme() {
            const savedTheme = localStorage.getItem(this.storageKey);
            const systemPrefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
            
            // Default to dark mode if no preference saved
            const isDark = savedTheme ? savedTheme === 'dark' : systemPrefersDark;
            
            this.applyTheme(isDark);
        },

        toggle() {
            const isDark = document.documentElement.classList.contains('dark');
            this.applyTheme(!isDark);
            localStorage.setItem(this.storageKey, !isDark ? 'dark' : 'light');
        },

        applyTheme(isDark) {
            if (isDark) {
                document.documentElement.classList.add('dark');
                this.iconEl.classList.remove('ph-moon');
                this.iconEl.classList.add('ph-sun');
            } else {
                document.documentElement.classList.remove('dark');
                this.iconEl.classList.remove('ph-sun');
                this.iconEl.classList.add('ph-moon');
            }
        }
    };

    // ============================================
    // Mobile Navigation
    // ============================================
    
    const MobileNavManager = {
        menuBtn: null,
        menu: null,
        iconEl: null,
        isOpen: false,

        init() {
            this.menuBtn = document.getElementById('mobileMenuBtn');
            this.menu = document.getElementById('mobileMenu');
            this.iconEl = document.getElementById('mobileMenuIcon');

            if (!this.menuBtn || !this.menu) {
                console.warn('Mobile menu elements not found');
                return;
            }

            this.menuBtn.addEventListener('click', () => this.toggle());

            // Close menu when clicking outside
            document.addEventListener('click', (e) => {
                if (this.isOpen && !this.menu.contains(e.target) && !this.menuBtn.contains(e.target)) {
                    this.close();
                }
            });

            // Close menu on window resize (if moving to desktop)
            window.addEventListener('resize', () => {
                if (window.innerWidth >= 768 && this.isOpen) {
                    this.close();
                }
            });
        },

        toggle() {
            if (this.isOpen) {
                this.close();
            } else {
                this.open();
            }
        },

        open() {
            this.menu.classList.remove('hidden');
            this.iconEl.classList.remove('ph-list');
            this.iconEl.classList.add('ph-x');
            this.isOpen = true;
        },

        close() {
            this.menu.classList.add('hidden');
            this.iconEl.classList.remove('ph-x');
            this.iconEl.classList.add('ph-list');
            this.isOpen = false;
        }
    };

    // ============================================
    // Tabulator Helper Functions
    // ============================================
    
    window.TabulatorManager = {
        /**
         * Initialize a Tabulator table with default basketball theme settings
         * @param {string|HTMLElement} element - CSS selector or DOM element
         * @param {Object} options - Tabulator options (merged with defaults)
         * @returns {Tabulator} - The Tabulator instance
         */
        init(element, options = {}) {
            const defaultOptions = {
                layout: 'fitColumns',
                responsiveLayout: 'collapse',
                pagination: true,
                paginationSize: 10,
                paginationSizeSelector: [10, 25, 50, 100],
                movableColumns: true,
                resizableColumns: true,
                selectable: 1,
                tooltips: true,
                tooltipGenerationMode: 'hover',
                locale: 'en-us',
                langs: {
                    'en-us': {
                        pagination: {
                            page_size: 'Show',
                            page_title: 'Show Page',
                            first: 'First',
                            first_title: 'First Page',
                            last: 'Last',
                            last_title: 'Last Page',
                            prev: 'Prev',
                            prev_title: 'Prev Page',
                            next: 'Next',
                            next_title: 'Next Page',
                            all: 'All',
                        }
                    }
                },
            };

            // Merge options
            const mergedOptions = { ...defaultOptions, ...options };

            // Initialize Tabulator
            const table = new Tabulator(element, mergedOptions);

            // Add dark mode awareness
            this.setupDarkModeSync(table);

            return table;
        },

        /**
         * Sync table with dark mode changes
         */
        setupDarkModeSync(table) {
            // Redraw table when dark mode toggles (for styling updates)
            const observer = new MutationObserver((mutations) => {
                mutations.forEach((mutation) => {
                    if (mutation.attributeName === 'class') {
                        setTimeout(() => table.redraw(), 50);
                    }
                });
            });

            observer.observe(document.documentElement, {
                attributes: true,
                attributeFilter: ['class']
            });
        },

        /**
         * Format number as integer
         */
        formatInteger(cell) {
            const value = cell.getValue();
            return value !== null && value !== undefined ? Math.round(value) : '-';
        },

        /**
         * Format number with decimals (e.g., for averages)
         */
        formatDecimal(cell, decimalPlaces = 1) {
            const value = cell.getValue();
            return value !== null && value !== undefined ? value.toFixed(decimalPlaces) : '-';
        },

        /**
         * Format percentage
         */
        formatPercent(cell, decimalPlaces = 1) {
            const value = cell.getValue();
            if (value === null || value === undefined) return '-';
            return (value * 100).toFixed(decimalPlaces) + '%';
        },

        /**
         * Format player name with link
         */
        formatPlayerLink(cell) {
            const value = cell.getValue();
            const data = cell.getRow().getData();
            const playerId = data.id || data.player_id;
            
            if (playerId) {
                return `<a href="/players/${playerId}" class="text-bball-orange hover:underline font-medium">${value}</a>`;
            }
            return value;
        }
    };

    // Convenience function for global access
    window.initTabulatorTable = function(element, options) {
        return window.TabulatorManager.init(element, options);
    };

    // ============================================
    // HTMX Event Listeners
    // ============================================
    
    const HTMXManager = {
        init() {
            // Show global loading indicator
            document.body.addEventListener('htmx:beforeRequest', (e) => {
                const indicator = document.getElementById('global-loading');
                if (indicator) {
                    indicator.classList.add('htmx-request');
                }
            });

            // Hide global loading indicator
            document.body.addEventListener('htmx:afterRequest', (e) => {
                const indicator = document.getElementById('global-loading');
                if (indicator) {
                    indicator.classList.remove('htmx-request');
                }
            });

            // Handle errors
            document.body.addEventListener('htmx:responseError', (e) => {
                console.error('HTMX Response Error:', e.detail);
                this.showNotification('Error loading content. Please try again.', 'error');
            });

            document.body.addEventListener('htmx:sendError', (e) => {
                console.error('HTMX Send Error:', e.detail);
                this.showNotification('Network error. Please check your connection.', 'error');
            });

            // After swap - reinitialize any necessary components
            document.body.addEventListener('htmx:afterSwap', (e) => {
                // Add fade-in animation to swapped content
                e.detail.target.classList.add('htmx-added');
                setTimeout(() => {
                    e.detail.target.classList.remove('htmx-added');
                }, 300);
            });
        },

        showNotification(message, type = 'info') {
            // Create notification element
            const notification = document.createElement('div');
            const colors = {
                info: 'bg-blue-500',
                success: 'bg-green-500',
                error: 'bg-red-500',
                warning: 'bg-yellow-500'
            };

            notification.className = `fixed bottom-4 right-4 ${colors[type] || colors.info} text-white px-6 py-3 rounded-lg shadow-lg z-50 transform transition-all duration-300 translate-y-full opacity-0`;
            notification.textContent = message;

            document.body.appendChild(notification);

            // Animate in
            requestAnimationFrame(() => {
                notification.classList.remove('translate-y-full', 'opacity-0');
            });

            // Remove after delay
            setTimeout(() => {
                notification.classList.add('translate-y-full', 'opacity-0');
                setTimeout(() => notification.remove(), 300);
            }, 3000);
        }
    };

    // ============================================
    // Active Navigation Link Highlighting
    // ============================================
    
    const NavigationManager = {
        init() {
            const currentPath = window.location.pathname;
            
            // Desktop nav links
            document.querySelectorAll('.nav-link').forEach(link => {
                if (link.getAttribute('href') === currentPath) {
                    link.classList.add('text-bball-orange', 'bg-gray-100', 'dark:bg-gray-700');
                    link.classList.remove('text-gray-700', 'dark:text-gray-300');
                }
            });

            // Mobile nav links
            document.querySelectorAll('.mobile-nav-link').forEach(link => {
                if (link.getAttribute('href') === currentPath) {
                    link.classList.add('text-bball-orange', 'bg-gray-100', 'dark:bg-gray-700');
                    link.classList.remove('text-gray-700', 'dark:text-gray-300');
                }
            });
        }
    };

    // ============================================
    // Smooth Scroll
    // ============================================
    
    const SmoothScroll = {
        init() {
            document.querySelectorAll('a[href^="#"]').forEach(anchor => {
                anchor.addEventListener('click', function(e) {
                    const targetId = this.getAttribute('href');
                    if (targetId === '#') return;
                    
                    const targetEl = document.querySelector(targetId);
                    if (targetEl) {
                        e.preventDefault();
                        targetEl.scrollIntoView({
                            behavior: 'smooth',
                            block: 'start'
                        });
                    }
                });
            });
        }
    };

    // ============================================
    // Initialize Everything on DOM Ready
    // ============================================
    
    function init() {
        DarkModeManager.init();
        MobileNavManager.init();
        HTMXManager.init();
        NavigationManager.init();
        SmoothScroll.init();

        console.log('🏀 BBall Ref Local initialized!');
    }

    // Run initialization
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
