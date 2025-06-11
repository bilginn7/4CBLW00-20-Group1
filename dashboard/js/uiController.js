/**
 * Enhanced UI Controller Module
 * Handles all user interface interactions with historical data integration
 */

const UIController = {
    // Current selections
    state: {
        selectedBorough: null,
        selectedWard: null,
        selectedLSOA: null,
        selectedMonth: null
    },

    // UI elements
    elements: {
        boroughSelect: null,
        wardSelect: null,
        lsoaSelect: null,
        monthSelect: null,
        resetButton: null
    },

    /**
     * Initialize UI controller
     */
    init() {
        try {
            console.log('Initializing UI controller...');

            this.cacheElements();
            this.setupEventListeners();
            this.populateBoroughDropdown();

            console.log('UI controller initialized successfully');

        } catch (error) {
            console.error('Error initializing UI controller:', error);
            throw error;
        }
    },

    /**
     * Cache DOM elements for performance
     */
    cacheElements() {
        this.elements.boroughSelect = document.querySelector(CONFIG.UI.SELECTORS.BOROUGH_SELECT);
        this.elements.wardSelect = document.querySelector(CONFIG.UI.SELECTORS.WARD_SELECT);
        this.elements.lsoaSelect = document.querySelector(CONFIG.UI.SELECTORS.LSOA_SELECT);
        this.elements.monthSelect = document.querySelector(CONFIG.UI.SELECTORS.MONTH_SELECT);
        this.elements.resetButton = document.querySelector('#reset-button');
        this.elements.fileInput = document.querySelector('#file-input');

        // Verify all elements are found
        Object.entries(this.elements).forEach(([key, element]) => {
            if (!element) {
                console.warn(`UI element not found: ${key}`);
            }
        });
    },

    /**
     * Setup event listeners for all dropdowns and reset button
     */
    setupEventListeners() {
        this.elements.boroughSelect.addEventListener('change', (e) => this.onBoroughChange(e));
        this.elements.wardSelect.addEventListener('change', (e) => this.onWardChange(e));
        this.elements.lsoaSelect.addEventListener('change', (e) => this.onLSOAChange(e));
        this.elements.monthSelect.addEventListener('change', (e) => this.onMonthChange(e));

        // Reset button handler
        if (this.elements.resetButton) {
            this.elements.resetButton.addEventListener('click', () => {
                console.log('🔄 Reset button clicked!');
                this.onResetClick();
            });
            console.log('✅ Reset button event listener attached');
        } else {
            console.error('❌ Reset button not found! Check HTML ID.');
        }

        // File input handler
        if (this.elements.fileInput) {
            this.elements.fileInput.addEventListener('change', (e) => this.onFileSelected(e));
        }

        // Window resize handler for responsive charts and map
        window.addEventListener('resize', () => this.onWindowResize());
    },

    /**
     * Handle reset button click
     */
    onResetClick() {
        console.log('🔄 Reset button clicked - starting reset process');

        try {
            // Reset all selections
            this.resetAllSelections();

            // Add visual feedback to button
            const button = this.elements.resetButton;
            if (button) {
                button.style.transform = 'scale(0.95)';
                button.style.backgroundColor = '#ff6b6b';
                button.style.color = 'white';

                setTimeout(() => {
                    button.style.transform = 'scale(1)';
                    button.style.backgroundColor = 'white';
                    button.style.color = '#ff6b6b';
                }, 150);
            }

            console.log('✅ Dashboard reset to initial state');

        } catch (error) {
            console.error('❌ Error during reset:', error);
        }
    },

    /**
     * Populate borough dropdown with data
     */
    populateBoroughDropdown() {
        try {
            const boroughs = DataService.getBoroughs();

            this.clearDropdown(this.elements.boroughSelect, CONFIG.UI.PLACEHOLDERS.BOROUGH);

            // Sort boroughs alphabetically by name
            boroughs.sort((a, b) => a.name.localeCompare(b.name));

            boroughs.forEach(borough => {
                const option = this.createOption(borough.name, borough.code);
                this.elements.boroughSelect.appendChild(option);
            });

            console.log(`Populated borough dropdown with ${boroughs.length} boroughs`);

        } catch (error) {
            console.error('Error populating borough dropdown:', error);
        }
    },

    /**
     * Handle borough selection change
     * @param {Event} event - Change event
     */
    onBoroughChange(event) {
        const boroughCode = event.target.value;
        console.log('Borough selected:', boroughCode);

        this.state.selectedBorough = boroughCode;
        this.state.selectedWard = null;
        this.state.selectedLSOA = null;
        this.state.selectedMonth = null;

        // Reset dependent dropdowns
        this.resetWardDropdown();
        this.resetLSOADropdown();
        this.resetMonthDropdown();

        // Clear charts
        ChartController.clearAllCharts();

        if (boroughCode) {
            // Populate ward dropdown
            this.populateWardDropdown(boroughCode);

            // Show wards on map for the selected borough
            MapController.showBoroughWards(boroughCode, '');
        } else {
            // If no borough selected, reset to London view
            MapController.resetToLondon();
        }
    },

    /**
     * Handle ward selection change
     * @param {Event} event - Change event
     */
    onWardChange(event) {
        const wardCode = event.target.value;
        console.log('Ward selected:', wardCode);

        this.state.selectedWard = wardCode;
        this.state.selectedLSOA = null;
        this.state.selectedMonth = null;

        // Reset dependent dropdowns
        this.resetLSOADropdown();
        this.resetMonthDropdown();

        // Clear charts
        ChartController.clearAllCharts();

        if (wardCode && this.state.selectedBorough) {
            this.populateLSOADropdown(this.state.selectedBorough, wardCode);

            // Update map to show ward
            MapController.showWard(wardCode, this.state.selectedBorough);
        } else {
            MapController.resetToLondon();
        }
    },

    /**
     * Handle LSOA selection change - Enhanced with historical data from JSON
     * @param {Event} event - Change event
     */
    async onLSOAChange(event) {
        const lsoaCode = event.target.value;
        console.log('LSOA selected:', lsoaCode);

        this.state.selectedLSOA = lsoaCode;
        this.state.selectedMonth = null;

        this.resetMonthDropdown();

        if (lsoaCode && this.state.selectedWard && this.state.selectedBorough) {
            try {
                // Get both predictions and historical data from JSON
                const predictions = DataService.getPredictions(
                    this.state.selectedBorough,
                    this.state.selectedWard,
                    lsoaCode
                );

                const historical = DataService.getHistoricalData(
                    this.state.selectedBorough,
                    this.state.selectedWard,
                    lsoaCode
                );

                // Update chart with both datasets
                ChartController.updateBurglaryChart(predictions, historical);

                // Populate month dropdown for officers chart
                const officerData = DataService.getOfficerAssignments(
                    this.state.selectedBorough,
                    this.state.selectedWard,
                    lsoaCode
                );
                this.populateMonthDropdown(officerData);

                MapController.highlightLSOA(lsoaCode);

            } catch (error) {
                console.error('Error updating charts for LSOA:', error);
                ChartController.clearAllCharts();
            }
        } else {
            ChartController.clearAllCharts();
        }
    },

    /**
     * Handle month selection change
     * @param {Event} event - Change event
     */
    onMonthChange(event) {
        const month = event.target.value;
        console.log('Month selected:', month);

        this.state.selectedMonth = month;

        if (month && this.state.selectedLSOA && this.state.selectedWard && this.state.selectedBorough) {
            const officerData = DataService.getOfficerAssignments(
                this.state.selectedBorough,
                this.state.selectedWard,
                this.state.selectedLSOA
            );

            if (officerData && officerData.hourly && officerData.hourly[month]) {
                ChartController.updateOfficersChart(officerData.hourly[month], month);
            }
        } else {
            ChartController.showEmptyState('officers');
        }
    },

    /**
     * Handle file selection
     * @param {Event} event - File input change event
     */
    async onFileSelected(event) {
        const file = event.target.files[0];

        if (!file) return;

        if (!file.name.endsWith('.json')) {
            alert('Please select a JSON file');
            return;
        }

        try {
            console.log('📁 Loading file:', file.name);

            // Show loading state
            this.setLoadingState('borough', true);

            // Load the file
            await DataService.loadFromFile(file);

            // Refresh the borough dropdown with new data
            this.populateBoroughDropdown();

            // Reset all selections
            this.resetAllSelections();

            console.log('✅ File loaded successfully!');

        } catch (error) {
            console.error('❌ Error loading file:', error);
            alert(`Error loading file: ${error.message}`);
        } finally {
            this.setLoadingState('borough', false);
        }
    },

    onWindowResize() {
        // Resize charts
        ChartController.resize();

        // Resize map
        MapController.resize();
    },

    /**
     * Populate ward dropdown
     * @param {string} boroughCode - Selected borough code
     */
    populateWardDropdown(boroughCode) {
        try {
            const wards = DataService.getWards(boroughCode);

            this.clearDropdown(this.elements.wardSelect, CONFIG.UI.PLACEHOLDERS.WARD);
            this.elements.wardSelect.disabled = false;

            // Sort wards alphabetically by name
            wards.sort((a, b) => a.name.localeCompare(b.name));

            wards.forEach(ward => {
                const option = this.createOption(ward.name, ward.code);
                this.elements.wardSelect.appendChild(option);
            });

            console.log(`Populated ward dropdown with ${wards.length} wards`);

        } catch (error) {
            console.error('Error populating ward dropdown:', error);
            this.resetWardDropdown();
        }
    },

    /**
     * Populate LSOA dropdown
     * @param {string} boroughCode - Selected borough code
     * @param {string} wardCode - Selected ward code
     */
    populateLSOADropdown(boroughCode, wardCode) {
        try {
            const lsoas = DataService.getLSOAs(boroughCode, wardCode);

            this.clearDropdown(this.elements.lsoaSelect, CONFIG.UI.PLACEHOLDERS.LSOA);
            this.elements.lsoaSelect.disabled = false;

            // Sort LSOAs alphabetically by name
            lsoas.sort((a, b) => a.name.localeCompare(b.name));

            lsoas.forEach(lsoa => {
                const option = this.createOption(lsoa.name, lsoa.code);
                this.elements.lsoaSelect.appendChild(option);
            });

            console.log(`Populated LSOA dropdown with ${lsoas.length} LSOAs`);

        } catch (error) {
            console.error('Error populating LSOA dropdown:', error);
            this.resetLSOADropdown();
        }
    },

    /**
     * Populate month dropdown
     * @param {Object} officerData - Officer assignment data
     */
    populateMonthDropdown(officerData) {
        try {
            if (!officerData || !officerData.hourly) {
                this.resetMonthDropdown();
                return;
            }

            const months = Object.keys(officerData.hourly).sort();

            this.clearDropdown(this.elements.monthSelect, CONFIG.UI.PLACEHOLDERS.MONTH);
            this.elements.monthSelect.disabled = false;

            months.forEach(month => {
                const option = this.createOption(month, month);
                this.elements.monthSelect.appendChild(option);
            });

            // Auto-select earliest month instead of latest
            if (CONFIG.APP.AUTO_SELECT_LATEST_MONTH && months.length > 0) {
                const earliestMonth = months[0]; // First month instead of last
                this.elements.monthSelect.value = earliestMonth;
                this.state.selectedMonth = earliestMonth;

                // Trigger the chart update
                ChartController.updateOfficersChart(officerData.hourly[earliestMonth], earliestMonth);
            }

            console.log(`Populated month dropdown with ${months.length} months`);

        } catch (error) {
            console.error('Error populating month dropdown:', error);
            this.resetMonthDropdown();
        }
    },

    /**
     * Reset ward dropdown to disabled state
     */
    resetWardDropdown() {
        this.clearDropdown(this.elements.wardSelect, CONFIG.UI.PLACEHOLDERS.WARD);
        this.elements.wardSelect.disabled = true;
    },

    /**
     * Reset LSOA dropdown to disabled state
     */
    resetLSOADropdown() {
        this.clearDropdown(this.elements.lsoaSelect, CONFIG.UI.PLACEHOLDERS.LSOA);
        this.elements.lsoaSelect.disabled = true;
    },

    /**
     * Reset month dropdown to disabled state
     */
    resetMonthDropdown() {
        this.clearDropdown(this.elements.monthSelect, CONFIG.UI.PLACEHOLDERS.MONTH);
        this.elements.monthSelect.disabled = true;
    },

    /**
     * Clear dropdown and add placeholder option
     * @param {HTMLSelectElement} selectElement - Select element to clear
     * @param {string} placeholder - Placeholder text
     */
    clearDropdown(selectElement, placeholder) {
        selectElement.innerHTML = '';
        const placeholderOption = this.createOption(placeholder, '');
        selectElement.appendChild(placeholderOption);
    },

    /**
     * Create option element
     * @param {string} text - Option text
     * @param {string} value - Option value
     * @returns {HTMLOptionElement} Option element
     */
    createOption(text, value) {
        const option = document.createElement('option');
        option.textContent = text;
        option.value = value;
        return option;
    },

    /**
     * Get current state
     * @returns {Object} Current UI state
     */
    getState() {
        return { ...this.state };
    },

    /**
     * Set loading state for a dropdown
     * @param {string} dropdownType - 'borough', 'ward', 'lsoa', or 'month'
     * @param {boolean} isLoading - Loading state
     */
    setLoadingState(dropdownType, isLoading) {
        const element = this.elements[`${dropdownType}Select`];
        if (element) {
            if (isLoading) {
                element.innerHTML = '<option value="">Loading...</option>';
                element.disabled = true;
            } else {
                element.disabled = false;
            }
        }
    },

    /**
     * Show error message
     * @param {string} message - Error message to display
     */
    showError(message) {
        console.error('UI Error:', message);
        // In a real application, you might show a toast or modal
        alert(`Error: ${message}`);
    },

    /**
     * Validate current selections
     * @returns {Object} Validation result
     */
    validateSelections() {
        const validation = {
            isValid: true,
            errors: []
        };

        if (!this.state.selectedBorough) {
            validation.errors.push('Borough must be selected');
        }

        if (!this.state.selectedWard) {
            validation.errors.push('Ward must be selected');
        }

        if (!this.state.selectedLSOA) {
            validation.errors.push('LSOA must be selected');
        }

        validation.isValid = validation.errors.length === 0;
        return validation;
    },

    /**
     * Reset all selections
     */
    resetAllSelections() {
        console.log('🔄 Resetting all selections...');

        // Reset internal state
        this.state = {
            selectedBorough: null,
            selectedWard: null,
            selectedLSOA: null,
            selectedMonth: null
        };

        // Reset UI elements
        this.elements.boroughSelect.value = '';
        this.resetWardDropdown();
        this.resetLSOADropdown();
        this.resetMonthDropdown();

        // Clear charts
        console.log('📊 Clearing charts...');
        ChartController.clearAllCharts();

        // Reset map to London view
        console.log('🗺️ Resetting map...');
        MapController.resetToLondon();

        console.log('✅ All selections reset successfully');
    }
};