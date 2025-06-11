/**
 * Main Application Module
 * Entry point and orchestration for the London Burglary Predictor Dashboard
 */

const App = {
    // Application state
    isInitialized: false,

    /**
     * Initialize the entire application
     */
    async init() {
        try {
            console.log('Initializing London Burglary Predictor Dashboard...');

            // Show loading state with progress bar
            this.showLoadingState();
            this.updateLoadingProgress(0, 'Starting application...');

            // Load all data first with progress updates
            this.updateLoadingProgress(20, 'Loading prediction data...');
            await DataService.loadAllData();
            this.updateLoadingProgress(60, 'Processing geographical data...');

            // Initialize map AFTER data is loaded
            this.updateLoadingProgress(75, 'Initializing map...');
            MapController.init();

            // Initialize charts
            this.updateLoadingProgress(85, 'Setting up charts...');
            ChartController.init();

            // Initialize UI controller
            this.updateLoadingProgress(95, 'Preparing interface...');
            UIController.init();

            // Complete loading
            this.updateLoadingProgress(100, 'Dashboard ready!');

            // Small delay to show completion
            await new Promise(resolve => setTimeout(resolve, 500));

            // Hide loading state
            this.hideLoadingState();

            // Mark as initialized
            this.isInitialized = true;

            console.log('Dashboard initialized successfully!');

            // Optional: Set up global error handlers
            this.setupGlobalErrorHandlers();

        } catch (error) {
            console.error('Failed to initialize dashboard:', error);
            this.showError('Failed to initialize dashboard. Please refresh the page.');
        }
    },

    /**
     * Show loading state with progress bar
     */
    showLoadingState() {
        console.log('Loading dashboard...');

        // Remove any existing loading overlay
        const existingOverlay = document.querySelector('.loading-overlay');
        if (existingOverlay) {
            existingOverlay.remove();
        }

        const container = document.querySelector('.container');
        if (container) {
            const loadingOverlay = document.createElement('div');
            loadingOverlay.className = 'loading-overlay';
            loadingOverlay.innerHTML = `
                <div class="loading-content">
                    <div class="loading-logo">
                        🗺️
                    </div>
                    <h2 class="loading-title">London Burglary Predictor Dashboard</h2>
                    <div class="loading-progress-container">
                        <div class="loading-progress-bar">
                            <div class="loading-progress-fill" id="loading-progress-fill"></div>
                        </div>
                        <div class="loading-percentage" id="loading-percentage">0%</div>
                    </div>
                    <p class="loading-message" id="loading-message">Initializing...</p>
                </div>
            `;

            // Enhanced loading overlay styles
            loadingOverlay.style.cssText = `
                position: fixed;
                top: 0;
                left: 0;
                width: 100vw;
                height: 100vh;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                display: flex;
                align-items: center;
                justify-content: center;
                z-index: 9999;
                font-family: Arial, sans-serif;
                backdrop-filter: blur(10px);
            `;

            document.body.appendChild(loadingOverlay);

            // Add CSS for loading components
            this.addLoadingStyles();
        }
    },

    /**
     * Update loading progress
     */
    updateLoadingProgress(percentage, message) {
        const progressFill = document.getElementById('loading-progress-fill');
        const percentageElement = document.getElementById('loading-percentage');
        const messageElement = document.getElementById('loading-message');

        if (progressFill) {
            progressFill.style.width = `${percentage}%`;
        }

        if (percentageElement) {
            percentageElement.textContent = `${percentage}%`;
        }

        if (messageElement) {
            messageElement.textContent = message;
        }

        console.log(`Loading: ${percentage}% - ${message}`);
    },

    /**
     * Add loading styles to the page
     */
/**
 * Show loading state with progress bar
 */
showLoadingState() {
    console.log('Loading dashboard...');

    // Remove any existing loading overlay
    const existingOverlay = document.querySelector('.loading-overlay');
    if (existingOverlay) {
        existingOverlay.remove();
    }

    const loadingOverlay = document.createElement('div');
    loadingOverlay.className = 'loading-overlay';
    loadingOverlay.innerHTML = `
        <div class="loading-content">
            <div class="loading-logo">
                🗺️
            </div>
            <h2 class="loading-title">London Burglary Predictor Dashboard</h2>
            <div class="loading-progress-container">
                <div class="loading-progress-bar">
                    <div class="loading-progress-fill" id="loading-progress-fill"></div>
                </div>
                <div class="loading-percentage" id="loading-percentage">0%</div>
            </div>
            <p class="loading-message" id="loading-message">Initializing...</p>
        </div>
    `;

    document.body.appendChild(loadingOverlay);
},

    /**
     * Hide loading state
     */
    hideLoadingState() {
        const loadingOverlay = document.querySelector('.loading-overlay');
        if (loadingOverlay) {
            // Fade out animation
            loadingOverlay.style.opacity = '0';
            loadingOverlay.style.transition = 'opacity 0.5s ease';

            setTimeout(() => {
                loadingOverlay.remove();
            }, 500);
        }
    },

    /**
     * Show error message
     * @param {string} message - Error message to display
     */
    showError(message) {
        console.error('Application Error:', message);

        // Hide loading state if showing
        this.hideLoadingState();

        // Show error message
        const errorContainer = document.createElement('div');
        errorContainer.className = 'error-container';
        errorContainer.innerHTML = `
            <div class="error-content">
                <h2>⚠️ Error</h2>
                <p>${message}</p>
                <button onclick="location.reload()">Reload Page</button>
            </div>
        `;
        errorContainer.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(255, 255, 255, 0.95);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 10000;
            font-family: Arial, sans-serif;
            text-align: center;
        `;

        const errorContent = errorContainer.querySelector('.error-content');
        errorContent.style.cssText = `
            background: white;
            padding: 40px;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
            border: 2px solid red;
            max-width: 400px;
        `;

        const button = errorContainer.querySelector('button');
        button.style.cssText = `
            background: red;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 4px;
            cursor: pointer;
            margin-top: 20px;
            font-size: 14px;
        `;

        document.body.appendChild(errorContainer);
    },

    /**
     * Setup global error handlers
     */
    setupGlobalErrorHandlers() {
        // Handle uncaught JavaScript errors
        window.addEventListener('error', (event) => {
            console.error('Global error caught:', event.error);
            if (CONFIG.APP.DEBUG) {
                console.error('Error details:', {
                    message: event.message,
                    filename: event.filename,
                    lineno: event.lineno,
                    colno: event.colno,
                    stack: event.error?.stack
                });
            }
        });

        // Handle unhandled promise rejections
        window.addEventListener('unhandledrejection', (event) => {
            console.error('Unhandled promise rejection:', event.reason);
            if (CONFIG.APP.DEBUG) {
                console.error('Promise rejection details:', event);
            }
        });

        // Handle resource loading errors
        window.addEventListener('error', (event) => {
            if (event.target !== window) {
                console.error('Resource loading error:', event.target.src || event.target.href);
            }
        }, true);
    },

    /**
     * Get application information
     * @returns {Object} Application info
     */
    getInfo() {
        return {
            name: 'London Burglary Predictor Dashboard',
            version: '1.0.0',
            initialized: this.isInitialized,
            modules: {
                DataService: typeof DataService !== 'undefined',
                MapController: typeof MapController !== 'undefined',
                ChartController: typeof ChartController !== 'undefined',
                UIController: typeof UIController !== 'undefined'
            }
        };
    },

    /**
     * Reset the entire application
     */
    reset() {
        try {
            console.log('Resetting application...');

            // Reset UI selections
            UIController.resetAllSelections();

            // Clear charts
            ChartController.clearAllCharts();

            // Reset map
            MapController.showLondon();

            console.log('Application reset successfully');

        } catch (error) {
            console.error('Error resetting application:', error);
        }
    },

    /**
     * Cleanup and destroy application
     */
    destroy() {
        try {
            console.log('Destroying application...');

            // Destroy charts
            ChartController.destroy();

            // Remove map
            if (MapController.map) {
                MapController.map.remove();
            }

            // Reset state
            this.isInitialized = false;

            console.log('Application destroyed successfully');

        } catch (error) {
            console.error('Error destroying application:', error);
        }
    },

    /**
     * Export current dashboard state
     * @returns {Object} Dashboard state
     */
    exportState() {
        return {
            ui: UIController.getState(),
            timestamp: new Date().toISOString(),
            version: this.getInfo().version
        };
    },

    /**
     * Handle browser visibility change
     */
    handleVisibilityChange() {
        if (document.hidden) {
            console.log('Dashboard tab hidden');
        } else {
            console.log('Dashboard tab visible');
            // Resize charts and map when tab becomes visible again
            if (this.isInitialized) {
                setTimeout(() => {
                    ChartController.resize();
                    MapController.resize();
                }, 100);
            }
        }
    }
};

// Auto-initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    App.init();
});

// Handle tab visibility changes
document.addEventListener('visibilitychange', () => {
    App.handleVisibilityChange();
});

// Expose App globally for debugging (optional)
if (CONFIG.APP.DEBUG) {
    window.App = App;
    window.DataService = DataService;
    window.MapController = MapController;
    window.ChartController = ChartController;
    window.UIController = UIController;

    // Add helpful console messages
    console.log('%c🗺️ London Burglary Predictor Dashboard', 'color: #0066cc; font-size: 16px; font-weight: bold;');
    console.log('%cDebug mode enabled. Access modules via:', 'color: #666;');
    console.log('%c- App.getInfo() - Application information', 'color: #666;');
    console.log('%c- App.exportState() - Export current state', 'color: #666;');
    console.log('%c- DataService - Data management', 'color: #666;');
    console.log('%c- MapController - Map operations', 'color: #666;');
    console.log('%c- ChartController - Chart operations', 'color: #666;');
    console.log('%c- UIController - UI state management', 'color: #666;');
}