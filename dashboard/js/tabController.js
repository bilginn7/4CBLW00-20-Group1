// Tab Controller
const TabController = {
    init() {
        this.setupTabListeners();
    },

    setupTabListeners() {
        const tabButtons = document.querySelectorAll('.tab-button');
        const helpOverlay = document.getElementById('help-overlay');
        const helpClose = document.getElementById('help-close');

        tabButtons.forEach(button => {
            button.addEventListener('click', () => {
                const tabName = button.getAttribute('data-tab');
                this.switchTab(tabName);
            });
        });

        helpClose?.addEventListener('click', () => {
            this.switchTab('dashboard');
        });

        // Close help overlay when clicking outside
        helpOverlay?.addEventListener('click', (e) => {
            if (e.target === helpOverlay) {
                this.switchTab('dashboard');
            }
        });

        // Keyboard navigation
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && helpOverlay?.classList.contains('active')) {
                this.switchTab('dashboard');
            }
        });
    },

    switchTab(tabName) {
        const tabButtons = document.querySelectorAll('.tab-button');
        const helpOverlay = document.getElementById('help-overlay');

        tabButtons.forEach(button => {
            if (button.getAttribute('data-tab') === tabName) {
                button.classList.add('active');
            } else {
                button.classList.remove('active');
            }
        });

        if (tabName === 'help') {
            helpOverlay?.classList.add('active');
        } else {
            helpOverlay?.classList.remove('active');
        }
    }
};

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    TabController.init();
});