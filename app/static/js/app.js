/**
 * BBall Ref Local - Main Application JavaScript
 * Handles dark mode, Tabulator initialization, and HTMX events
 */

(function() {
    'use strict';

    // ============================================
    // Utility Functions
    // ============================================

    /**
     * Debounce function to limit how often a function can fire
     * @param {Function} func - The function to debounce
     * @param {number} wait - The debounce delay in milliseconds
     * @returns {Function} - The debounced function
     */
    function debounce(func, wait) {
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

    // ============================================
    // Dark Mode Functionality
    // ============================================

    const DarkModeManager = {
        storageKey: 'bball-ref-theme',
        toggleBtn: null,
        iconEl: null,
        listeners: [],

        init() {
            this.toggleBtn = document.getElementById('darkModeToggle');
            this.iconEl = document.getElementById('darkModeIcon');

            if (!this.toggleBtn || !this.iconEl) {
                console.warn('Dark mode elements not found');
                return;
            }

            // Load saved preference or system preference
            this.loadTheme();

            // Bind click event and store reference for cleanup
            const clickHandler = () => this.toggle();
            this.toggleBtn.addEventListener('click', clickHandler);
            this.listeners.push({ element: this.toggleBtn, event: 'click', handler: clickHandler });
        },

        cleanup() {
            // Remove all stored event listeners
            this.listeners.forEach(({ element, event, handler }) => {
                element.removeEventListener(event, handler);
            });
            this.listeners = [];
            this.toggleBtn = null;
            this.iconEl = null;
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
        listeners: [],
        resizeHandler: null,

        init() {
            this.menuBtn = document.getElementById('mobileMenuBtn');
            this.menu = document.getElementById('mobileMenu');
            this.iconEl = document.getElementById('mobileMenuIcon');

            if (!this.menuBtn || !this.menu) {
                console.warn('Mobile menu elements not found');
                return;
            }

            // Store bound handlers for cleanup
            const clickHandler = () => this.toggle();
            this.menuBtn.addEventListener('click', clickHandler);
            this.listeners.push({ element: this.menuBtn, event: 'click', handler: clickHandler });

            // Close menu when clicking outside
            const outsideClickHandler = (e) => {
                if (this.isOpen && !this.menu.contains(e.target) && !this.menuBtn.contains(e.target)) {
                    this.close();
                }
            };
            document.addEventListener('click', outsideClickHandler);
            this.listeners.push({ element: document, event: 'click', handler: outsideClickHandler });

            // Close menu on window resize (if moving to desktop) - debounced
            this.resizeHandler = debounce(() => {
                if (window.innerWidth >= 768 && this.isOpen) {
                    this.close();
                }
            }, 250);
            window.addEventListener('resize', this.resizeHandler);
        },

        cleanup() {
            // Remove all stored event listeners
            this.listeners.forEach(({ element, event, handler }) => {
                element.removeEventListener(event, handler);
            });
            this.listeners = [];

            // Remove resize handler
            if (this.resizeHandler) {
                window.removeEventListener('resize', this.resizeHandler);
                this.resizeHandler = null;
            }

            this.menuBtn = null;
            this.menu = null;
            this.iconEl = null;
            this.isOpen = false;
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
            // Store observer reference on the table for cleanup
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

            // Store observer reference for later cleanup
            table.__darkModeObserver = observer;
        },

        /**
         * Disconnect the dark mode observer for a table
         * @param {Tabulator} table - The Tabulator instance
         */
        disconnectDarkModeSync(table) {
            if (table && table.__darkModeObserver) {
                table.__darkModeObserver.disconnect();
                delete table.__darkModeObserver;
            }
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
        listeners: [],

        init() {
            // Show global loading indicator
            const beforeRequestHandler = (e) => {
                const indicator = document.getElementById('global-loading');
                if (indicator) {
                    indicator.classList.add('htmx-request');
                }
            };
            document.body.addEventListener('htmx:beforeRequest', beforeRequestHandler);
            this.listeners.push({ element: document.body, event: 'htmx:beforeRequest', handler: beforeRequestHandler });

            // Hide global loading indicator
            const afterRequestHandler = (e) => {
                const indicator = document.getElementById('global-loading');
                if (indicator) {
                    indicator.classList.remove('htmx-request');
                }
            };
            document.body.addEventListener('htmx:afterRequest', afterRequestHandler);
            this.listeners.push({ element: document.body, event: 'htmx:afterRequest', handler: afterRequestHandler });

            // Handle errors
            const responseErrorHandler = (e) => {
                console.error('HTMX Response Error:', e.detail);
                this.showNotification('Error loading content. Please try again.', 'error');
            };
            document.body.addEventListener('htmx:responseError', responseErrorHandler);
            this.listeners.push({ element: document.body, event: 'htmx:responseError', handler: responseErrorHandler });

            const sendErrorHandler = (e) => {
                console.error('HTMX Send Error:', e.detail);
                this.showNotification('Network error. Please check your connection.', 'error');
            };
            document.body.addEventListener('htmx:sendError', sendErrorHandler);
            this.listeners.push({ element: document.body, event: 'htmx:sendError', handler: sendErrorHandler });

            // After swap - reinitialize any necessary components
            const afterSwapHandler = (e) => {
                // Add fade-in animation to swapped content
                e.detail.target.classList.add('htmx-added');
                setTimeout(() => {
                    e.detail.target.classList.remove('htmx-added');
                }, 300);
            };
            document.body.addEventListener('htmx:afterSwap', afterSwapHandler);
            this.listeners.push({ element: document.body, event: 'htmx:afterSwap', handler: afterSwapHandler });
        },

        cleanup() {
            // Remove all stored HTMX event listeners
            this.listeners.forEach(({ element, event, handler }) => {
                element.removeEventListener(event, handler);
            });
            this.listeners = [];
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
    // Export Dropdown Manager
    // ============================================

    const ExportDropdownManager = {
        containers: [],
        _documentClickHandler: null,
        _documentKeydownHandler: null,
        _afterSwapHandler: null,

        init() {
            // Set up single document-level handlers for close-on-click and close-on-escape
            this._documentClickHandler = (e) => {
                this.containers.forEach(container => {
                    if (!container.contains(e.target)) {
                        const dropdown = container.querySelector('.export-dropdown-menu');
                        if (dropdown) dropdown.classList.add('hidden');
                    }
                });
            };
            document.addEventListener('click', this._documentClickHandler);

            this._documentKeydownHandler = (e) => {
                if (e.key === 'Escape') {
                    this.containers.forEach(container => {
                        const dropdown = container.querySelector('.export-dropdown-menu');
                        if (dropdown) dropdown.classList.add('hidden');
                    });
                }
            };
            document.addEventListener('keydown', this._documentKeydownHandler);

            this.setupDropdowns();

            // Re-setup after HTMX swaps
            this._afterSwapHandler = () => {
                this.setupDropdowns();
            };
            document.body.addEventListener('htmx:afterSwap', this._afterSwapHandler);
        },

        setupDropdowns() {
            document.querySelectorAll('.export-dropdown-container').forEach(container => {
                // Skip if already initialized
                if (container.dataset.initialized) return;
                container.dataset.initialized = 'true';
                this.containers.push(container);

                const toggleBtn = container.querySelector('.export-toggle-btn');
                const dropdown = container.querySelector('.export-dropdown-menu');

                if (!toggleBtn || !dropdown) return;

                // Toggle on click (per-element, no leak)
                toggleBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    dropdown.classList.toggle('hidden');
                });
            });
        },

        cleanup() {
            // Remove document-level handlers
            if (this._documentClickHandler) {
                document.removeEventListener('click', this._documentClickHandler);
                this._documentClickHandler = null;
            }
            if (this._documentKeydownHandler) {
                document.removeEventListener('keydown', this._documentKeydownHandler);
                this._documentKeydownHandler = null;
            }
            if (this._afterSwapHandler) {
                document.body.removeEventListener('htmx:afterSwap', this._afterSwapHandler);
                this._afterSwapHandler = null;
            }
            this.containers.forEach(container => {
                delete container.dataset.initialized;
            });
            this.containers = [];
        }
    };

    // ============================================
    // Game Log Manager (for sorting, pagination, filtering)
    // ============================================

    const GameLogManager = {
        init() {
            this.setupGameLogControls();
            // Re-setup after HTMX swaps
            document.body.addEventListener('htmx:afterSwap', () => {
                this.setupGameLogControls();
            });
        },

        setupGameLogControls() {
            const container = document.getElementById('player-game-log');
            if (!container) return;

            // Handle sort clicks
            container.querySelectorAll('.sortable-header').forEach(header => {
                header.addEventListener('click', () => {
                    const sortBy = header.dataset.sortBy;
                    const currentOrder = header.dataset.sortOrder || 'desc';
                    const newOrder = currentOrder === 'asc' ? 'desc' : 'asc';

                    // Get current URL params
                    const url = new URL(window.location.href);
                    url.searchParams.set('sort_by', sortBy);
                    url.searchParams.set('sort_order', newOrder);

                    // Trigger HTMX request
                    htmx.ajax('GET', url.toString(), {
                        target: '#player-game-log-container',
                        indicator: '#game-log-loading'
                    });
                });
            });

            // Handle page size changes
            const pageSizeSelect = container.querySelector('#page-size-select');
            if (pageSizeSelect) {
                pageSizeSelect.addEventListener('change', () => {
                    const url = new URL(window.location.href);
                    url.searchParams.set('page_size', pageSizeSelect.value);
                    url.searchParams.set('page', '1'); // Reset to page 1

                    htmx.ajax('GET', url.toString(), {
                        target: '#player-game-log-container',
                        indicator: '#game-log-loading'
                    });
                });
            }

            // Handle filter changes
            container.querySelectorAll('.game-log-filter').forEach(filter => {
                filter.addEventListener('change', () => {
                    const url = new URL(window.location.href);
                    const filterName = filter.dataset.filterName;
                    const filterValue = filter.value;

                    if (filterValue && filterValue !== 'all') {
                        url.searchParams.set(filterName, filterValue);
                    } else {
                        url.searchParams.delete(filterName);
                    }
                    url.searchParams.set('page', '1'); // Reset to page 1

                    htmx.ajax('GET', url.toString(), {
                        target: '#player-game-log-container',
                        indicator: '#game-log-loading'
                    });
                });
            });
        }
    };

    // ============================================
    // Smooth Scroll
    // ============================================

    const SmoothScroll = {
        listeners: [],

        init() {
            document.querySelectorAll('a[href^="#"]').forEach(anchor => {
                const clickHandler = function(e) {
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
                };
                anchor.addEventListener('click', clickHandler);
                this.listeners.push({ element: anchor, event: 'click', handler: clickHandler });
            });
        },

        cleanup() {
            this.listeners.forEach(({ element, event, handler }) => {
                element.removeEventListener(event, handler);
            });
            this.listeners = [];
        }
    };

    // ============================================
    // Global Cleanup Function
    // ============================================

    window.BBallApp = {
        cleanup() {
            DarkModeManager.cleanup();
            MobileNavManager.cleanup();
            HTMXManager.cleanup();
            SmoothScroll.cleanup();
            ExportDropdownManager.cleanup();
        },
        managers: {
            DarkModeManager,
            MobileNavManager,
            HTMXManager,
            NavigationManager,
            SmoothScroll,
            ExportDropdownManager,
            GameLogManager
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
        ExportDropdownManager.init();
        GameLogManager.init();

        console.log('🏀 BBall Ref Local initialized!');
    }

    // Run initialization
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
