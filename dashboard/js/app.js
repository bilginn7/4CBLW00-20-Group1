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

            this.showLoadingState();
            this.updateLoadingProgress(0, 'Starting application...');

            this.updateLoadingProgress(20, 'Loading prediction data...');
            await DataService.loadAllData();
            this.updateLoadingProgress(60, 'Processing geographical data...');

            this.updateLoadingProgress(75, 'Initializing map...');
            MapController.init();

            this.updateLoadingProgress(85, 'Setting up charts...');
            ChartController.init();

            this.updateLoadingProgress(95, 'Preparing interface...');
            UIController.init();

            this.updateLoadingProgress(100, 'Dashboard ready!');
            await new Promise(resolve => setTimeout(resolve, 500));

            this.hideLoadingState();
            this.isInitialized = true;
            console.log('Dashboard initialized successfully!');

            this.setupGlobalErrorHandlers();

        } catch (error) {
            console.error('Failed to initialize dashboard:', error);
            this.showError('Failed to initialize dashboard. Please check the console and refresh the page.');
        }
    },

    /**
     * Show loading state by cloning a template from the HTML.
     */
    showLoadingState() {
        console.log('Loading dashboard...');
        const existingOverlay = document.querySelector('.loading-overlay');
        if (existingOverlay) return;

        const template = document.getElementById('loading-overlay-template');
        if (template) {
            const clone = template.content.cloneNode(true);
            document.body.appendChild(clone);
        } else {
            console.error('Loading overlay template not found!');
        }
    },

    /**
     * Update loading progress
     */
    updateLoadingProgress(percentage, message) {
        const progressFill = document.getElementById('loading-progress-fill');
        const percentageElement = document.getElementById('loading-percentage');
        const messageElement = document.getElementById('loading-message');

        if (progressFill) progressFill.style.width = `${percentage}%`;
        if (percentageElement) percentageElement.textContent = `${percentage}%`;
        if (messageElement) messageElement.textContent = message;

        console.log(`Loading: ${percentage}% - ${message}`);
    },

    /**
     * Hide loading state
     */
    hideLoadingState() {
        const loadingOverlay = document.querySelector('.loading-overlay');
        if (loadingOverlay) {
            loadingOverlay.style.opacity = '0';
            setTimeout(() => loadingOverlay.remove(), 500);
        }
    },

    /**
     * Show an error message overlay by cloning a template.
     * @param {string} message - Error message to display
     */
    showError(message) {
        console.error('Application Error:', message);
        this.hideLoadingState();

        const existingOverlay = document.querySelector('.error-overlay');
        if (existingOverlay) return;

        const template = document.getElementById('error-overlay-template');
        if (template) {
            const clone = template.content.cloneNode(true);
            clone.getElementById('error-message-text').textContent = message;
            clone.getElementById('error-reload-btn').onclick = () => location.reload();
            document.body.appendChild(clone);
        } else {
            // Fallback to a simple alert if template is missing
            alert(`CRITICAL ERROR: ${message}`);
        }
    },

    /**
     * Setup global error handlers
     */
    setupGlobalErrorHandlers() {
        const handleError = (event, type) => {
            const error = event.reason || event.error;
            console.error(`Global error caught (${type}):`, error);
            if (CONFIG.APP.DEBUG) {
                const details = {
                    message: event.message,
                    filename: event.filename,
                    lineno: event.lineno,
                    colno: event.colno,
                    stack: error?.stack,
                    type: event.type
                };
                console.error('Error details:', details);
            }
        };

        window.addEventListener('error', (event) => handleError(event, 'uncaught'));
        window.addEventListener('unhandledrejection', (event) => handleError(event, 'promise'));
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
            UIController.resetAllSelections();
            console.log('Application reset successfully');
        } catch (error) {
            console.error('Error resetting application:', error);
        }
    },

    /**
     * Handle browser visibility change
     */
    handleVisibilityChange() {
        if (document.hidden) {
            console.log('Dashboard tab hidden');
        } else {
            console.log('Dashboard tab visible');
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

// Expose modules globally for debugging
if (CONFIG.APP.DEBUG) {
    window.App = App;
    window.DataService = DataService;
    window.MapController = MapController;
    window.ChartController = ChartController;
    window.UIController = UIController;

    console.log('%c🗺️ London Burglary Predictor Dashboard (Debug Mode)', 'color: #0066cc; font-size: 16px; font-weight: bold;');
    console.log('%cAccess modules via window.App, window.DataService, etc.', 'color: #666;');
}