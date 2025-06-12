/**
 * Enhanced UI Controller Module with Burglary Marker Integration
 * Handles all user interface interactions and orchestrates updates.
 */
const UIController = {
    state: {
        selectedBorough: null,
        selectedWard: null,
        selectedLSOA: null,
        selectedMonth: null,
        monthsList: [],
        yearsList: [],
        currentMonthIdx: -1,
        currentYear: null
    },

    elements: {},

    init() {
        try {
            console.log('Initializing UI controller…');
            this.cacheElements();
            this.setupEventListeners();
            this.populateBoroughDropdown();
            console.log('UI controller initialised successfully');
        } catch (error) {
            console.error('Error initialising UI controller:', error);
            throw error;
        }
    },

    /** Cache DOM elements for performance, using CONFIG for selectors */
    cacheElements() {
        const selectors = CONFIG.UI.SELECTORS;
        for (const key in selectors) {
            const propName = key.toLowerCase().replace(/_([a-z])/g, g => g[1].toUpperCase());
            this.elements[propName] = document.querySelector(selectors[key]);
        }
    },

    /** Attach event listeners */
    setupEventListeners() {
        this.elements.boroughSelect.addEventListener('change', e => this.onBoroughChange(e.target.value));
        this.elements.wardSelect.addEventListener('change', e => this.onWardChange(e.target.value));
        this.elements.lsoaSelect.addEventListener('change', e => this.onLSOAChange(e.target.value));
        this.elements.resetButton?.addEventListener('click', () => this.onResetClick());
        this.elements.prevMonthBtn.addEventListener('click', () => this.changeMonth(-1));
        this.elements.nextMonthBtn.addEventListener('click', () => this.changeMonth(1));
        this.elements.monthDisplay.addEventListener('click', () => this.toggleCalendar());
        this.elements.prevYearBtn.addEventListener('click', () => this.changeYear(-1));
        this.elements.nextYearBtn.addEventListener('click', () => this.changeYear(1));
        document.addEventListener('click', e => {
            if (!this.elements.monthSelector.contains(e.target)) this.toggleCalendar(false);
        });
        window.addEventListener('resize', () => {
            ChartController.resize();
            MapController.resize();
        });
    },

    /** Handle borough selection from UI or Map */
    onBoroughChange(boroughCode) {
        console.log('Borough selected:', boroughCode);
        this.state.selectedBorough = boroughCode;
        this._resetDownstream('borough');

        if (boroughCode) {
            this.populateWardDropdown(boroughCode);
            MapController.showBoroughWards(boroughCode, this.elements.boroughSelect.options[this.elements.boroughSelect.selectedIndex].text);
        }
    },

    /** Handle ward selection from UI or Map */
    onWardChange(wardCode) {
        console.log('Ward selected:', wardCode);
        this.state.selectedWard = wardCode;
        this._resetDownstream('ward');

        if (wardCode && this.state.selectedBorough) {
            this.populateLSOADropdown(this.state.selectedBorough, wardCode);
            MapController.showWard(wardCode, this.state.selectedBorough);
        }
    },

    /** Handle LSOA selection from UI or Map */
    async onLSOAChange(lsoaCode) {
        console.log('LSOA selected:', lsoaCode);
        this.state.selectedLSOA = lsoaCode;
        this._resetDownstream('lsoa');

        if (lsoaCode) {
            try {
                const { selectedBorough, selectedWard } = this.state;
                const predictions = DataService.getPredictions(selectedBorough, selectedWard, lsoaCode);
                const historical = DataService.getHistoricalData(selectedBorough, selectedWard, lsoaCode);

                // Check if there's an active date filter
                const startDate = document.getElementById('start-date').value || null;
                const endDate = document.getElementById('end-date').value || null;

                // Update chart with date filter if it exists
                ChartController.updateBurglaryChart(predictions, historical, startDate, endDate);

                const officerData = DataService.getOfficerAssignments(selectedBorough, selectedWard, lsoaCode);
                this.populateMonthWidget(officerData);

                MapController.highlightLSOA(lsoaCode);

                this.addBurglaryMarkersForCurrentSelection();

            } catch (error) {
                console.error('Error updating charts for LSOA:', error);
                ChartController.clearAllCharts();
            }
        }
    },

    // Add burglary markers for current selection considering date filter
    addBurglaryMarkersForCurrentSelection() {
        const { selectedBorough, selectedWard, selectedLSOA } = this.state;
        if (!selectedBorough || !selectedWard || !selectedLSOA) return;

        // Get current date filter values
        const startDate = document.getElementById('start-date').value || null;
        const endDate = document.getElementById('end-date').value || null;

        // Add burglary markers to map
        MapController.addBurglaryMarkers(selectedBorough, selectedWard, selectedLSOA, startDate, endDate);
    },

    /** Directly update the officers chart when a month is chosen */
    updateOfficersChartForMonth(month) {
        this.state.selectedMonth = month;
        console.log('Month selected:', month);
        if (!month) return ChartController.showEmptyState('officers');

        const { selectedBorough, selectedWard, selectedLSOA } = this.state;
        const officerData = DataService.getOfficerAssignments(selectedBorough, selectedWard, selectedLSOA);
        const hourlyData = officerData?.hourly?.[month];

        if (hourlyData) {
            ChartController.updateOfficersChart(hourlyData, month);
        } else {
            ChartController.showEmptyState('officers');
        }
    },

    // --- Dropdown Population & Reset ---
    populateBoroughDropdown() {
        const boroughs = DataService.getBoroughs().sort((a, b) => a.name.localeCompare(b.name));
        this._populateDropdown(this.elements.boroughSelect, boroughs, CONFIG.UI.PLACEHOLDERS.BOROUGH);
    },

    populateWardDropdown(boroughCode) {
        const wards = DataService.getWards(boroughCode).sort((a, b) => a.name.localeCompare(b.name));
        this._populateDropdown(this.elements.wardSelect, wards, CONFIG.UI.PLACEHOLDERS.WARD);
        this.elements.wardSelect.disabled = false;
    },

    populateLSOADropdown(boroughCode, wardCode) {
        const lsoas = DataService.getLSOAs(boroughCode, wardCode).sort((a, b) => a.name.localeCompare(b.name));
        this._populateDropdown(this.elements.lsoaSelect, lsoas, CONFIG.UI.PLACEHOLDERS.LSOA);
        this.elements.lsoaSelect.disabled = false;
    },

    resetAllSelections() {
        console.log('🔄 Resetting all selections...');
        this.state.selectedBorough = null;
        this.elements.boroughSelect.value = '';
        this._resetDownstream('borough'); // This will reset everything else
        MapController.resetToLondon();
        document.getElementById('start-date').value = '';
        document.getElementById('end-date').value = '';
    },

    // --- Month Selector Widget Logic ---
    populateMonthWidget(officerData) {
        if (!officerData?.hourly) return this.resetMonthWidget();
        this.state.monthsList = Object.keys(officerData.hourly).sort();
        if (this.state.monthsList.length === 0) return this.resetMonthWidget();

        this.state.yearsList = [...new Set(this.state.monthsList.map(m => m.slice(0, 4)))].sort();
        this.state.currentYear = this.state.yearsList[0];

        this.buildCalendarGrid(this.state.currentYear);
        this.selectMonth(0); // Select the first available month by default
    },

    resetMonthWidget() {
        Object.assign(this.state, { monthsList: [], yearsList: [], currentMonthIdx: -1, currentYear: null, selectedMonth: null });
        this.elements.monthDisplay.textContent = CONFIG.UI.PLACEHOLDERS.MONTH;
        this.elements.prevMonthBtn.disabled = true;
        this.elements.nextMonthBtn.disabled = true;
        this.elements.calendarBody.innerHTML = '';
        this.elements.calendarYear.textContent = '—';
        this.toggleCalendar(false);
    },

    selectMonth(idx) {
        if (idx < 0 || idx >= this.state.monthsList.length) return;
        this.state.currentMonthIdx = idx;
        const month = this.state.monthsList[idx];
        this.state.currentYear = month.slice(0, 4);

        this.elements.monthDisplay.textContent = month;
        this.updateMonthArrowStates();
        this.buildCalendarGrid(this.state.currentYear); // Rebuild to highlight selected

        // CHANGE: Direct call to update chart, no more hidden select event
        this.updateOfficersChartForMonth(month);
    },

    changeMonth(delta) { this.selectMonth(this.state.currentMonthIdx + delta); },

    changeYear(delta) {
        const yearIdx = this.state.yearsList.indexOf(this.state.currentYear) + delta;
        if (yearIdx >= 0 && yearIdx < this.state.yearsList.length) {
            this.state.currentYear = this.state.yearsList[yearIdx];
            this.refreshCalendarHeader();
            this.buildCalendarGrid(this.state.currentYear);
        }
    },

    buildCalendarGrid(year) {
        const body = this.elements.calendarBody;
        body.innerHTML = '';
        for (let m = 1; m <= 12; m++) {
            const value = `${year}-${String(m).padStart(2, '0')}`;
            const cell = document.createElement('div');
            cell.className = 'month-cell';
            cell.textContent = new Date(year, m - 1).toLocaleString('default', { month: 'short' });

            const idx = this.state.monthsList.indexOf(value);
            if (idx === -1) {
                cell.classList.add('disabled');
            } else {
                cell.addEventListener('click', () => {
                    this.selectMonth(idx);
                    this.toggleCalendar(false);
                });
            }
            if (value === this.state.monthsList[this.state.currentMonthIdx]) cell.classList.add('selected');
            body.appendChild(cell);
        }
        this.refreshCalendarHeader();
    },

    refreshCalendarHeader() {
        const yearIdx = this.state.yearsList.indexOf(this.state.currentYear);
        this.elements.calendarYear.textContent = this.state.currentYear;
        this.elements.prevYearBtn.disabled = yearIdx <= 0;
        this.elements.nextYearBtn.disabled = yearIdx >= this.state.yearsList.length - 1;
    },

    updateMonthArrowStates() {
        this.elements.prevMonthBtn.disabled = this.state.currentMonthIdx <= 0;
        this.elements.nextMonthBtn.disabled = this.state.currentMonthIdx >= this.state.monthsList.length - 1;
    },

    toggleCalendar(force) { this.elements.monthCalendar.classList.toggle('active', force); },

    // --- Public Selectors (for map clicks) & Helpers ---
    selectBorough(boroughCode) { this.elements.boroughSelect.value = boroughCode; this.onBoroughChange(boroughCode); },
    selectWard(wardCode) { this.elements.wardSelect.value = wardCode; this.onWardChange(wardCode); },
    selectLSOA(lsoaCode) { this.elements.lsoaSelect.value = lsoaCode; this.onLSOAChange(lsoaCode); },
    getLSOADataForHighlight(lsoaCode) { return DataService.getLSOADataFromJSON(this.state.selectedBorough, this.state.selectedWard, lsoaCode); },
    onResetClick() { this.resetAllSelections(); },

    _populateDropdown(selectEl, items, placeholder) {
        selectEl.innerHTML = '';
        selectEl.appendChild(this._createOption(placeholder, ''));
        items.forEach(item => selectEl.appendChild(this._createOption(item.name, item.code)));
    },

    _createOption(text, value) {
        const option = document.createElement('option');
        option.textContent = text;
        option.value = value;
        return option;
    },

    /** Helper to reset dropdowns and state below a certain level */
    _resetDownstream(level) {
        const levels = ['borough', 'ward', 'lsoa', 'month'];
        const startIndex = levels.indexOf(level) + 1;

        for (let i = startIndex; i < levels.length; i++) {
            const currentLevel = levels[i];
            this.state[`selected${currentLevel.charAt(0).toUpperCase() + currentLevel.slice(1)}`] = null;

            if (currentLevel === 'month') {
                this.resetMonthWidget();
            } else {
                const selectEl = this.elements[`${currentLevel}Select`];
                if (selectEl) {
                    this._populateDropdown(selectEl, [], CONFIG.UI.PLACEHOLDERS[currentLevel.toUpperCase()]);
                    selectEl.disabled = true;
                }
            }
        }
        ChartController.clearAllCharts();
        MapController.clearBurglaryMarkers();
    }
};