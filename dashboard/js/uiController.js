/**
 * UI Controller Module
 * Handles all user interface interactions and state management
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
        monthSelect: null
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
        this.elements.fileInput = document.querySelector('#file-input');

        // Verify all elements are found
        Object.entries(this.elements).forEach(([key, element]) => {
            if (!element) {
                console.warn(`UI element not found: ${key}`);
            }
        });
    },

    /**
     * Setup event listeners for all dropdowns
     */
    setupEventListeners() {
        this.elements.boroughSelect.addEventListener('change', (e) => this.onBoroughChange(e));
        this.elements.wardSelect.addEventListener('change', (e) => this.onWardChange(e));
        this.elements.lsoaSelect.addEventListener('change', (e) => this.onLSOAChange(e));
        this.elements.monthSelect.addEventListener('change', (e) => this.onMonthChange(e));

        // File input handler
        if (this.elements.fileInput) {
            this.elements.fileInput.addEventListener('change', (e) => this.onFileSelected(e));
        }

        // Window resize handler for responsive charts and map
        window.addEventListener('resize', () => this.onWindowResize());
    },

    /**
     * Populate borough dropdown with data
     */
    populateBoroughDropdown() {
        try {
            const boroughs = DataService.getBoroughs();

            this.clearDropdown(this.elements.boroughSelect, CONFIG.UI.PLACEHOLDERS.BOROUGH);

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

        // Reset map to London view
        MapController.showLondon();

        if (boroughCode) {
            this.populateWardDropdown(boroughCode);
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
            MapController.showLondon();
        }
    },

    /**
     * Handle LSOA selection change
     * @param {Event} event - Change event
     */
    onLSOAChange(event) {
        const lsoaCode = event.target.value;
        console.log('LSOA selected:', lsoaCode);

        this.state.selectedLSOA = lsoaCode;
        this.state.selectedMonth = null;

        // Reset month dropdown
        this.resetMonthDropdown();

        if (lsoaCode && this.state.selectedWard && this.state.selectedBorough) {
            // Update burglary chart
            const predictions = DataService.getPredictions(
                this.state.selectedBorough,
                this.state.selectedWard,
                lsoaCode
            );
            ChartController.updateBurglaryChart(predictions);

            // Populate month dropdown for officers chart
            const officerData = DataService.getOfficerAssignments(
                this.state.selectedBorough,
                this.state.selectedWard,
                lsoaCode
            );
            this.populateMonthDropdown(officerData);

            // Highlight LSOA on map
            MapController.highlightLSOA(lsoaCode);

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

            // Auto-select latest month if configured
            if (CONFIG.APP.AUTO_SELECT_LATEST_MONTH && months.length > 0) {
                const latestMonth = months[months.length - 1];
                this.elements.monthSelect.value = latestMonth;
                this.state.selectedMonth = latestMonth;

                // Trigger the chart update
                ChartController.updateOfficersChart(officerData.hourly[latestMonth], latestMonth);
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
        this.state = {
            selectedBorough: null,
            selectedWard: null,
            selectedLSOA: null,
            selectedMonth: null
        };

        this.elements.boroughSelect.value = '';
        this.resetWardDropdown();
        this.resetLSOADropdown();
        this.resetMonthDropdown();

        ChartController.clearAllCharts();
        MapController.showLondon();
    }
};