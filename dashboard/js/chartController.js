/**
 * Enhanced Chart Controller Module
 * Handles all chart-related functionality with historical data integration
 */

const ChartController = {
    charts: {
        burglary: null,
        officers: null
    },

    // Store original data for filtering
    originalData: {
        historical: {},
        predictions: {}
    },

    /**
     * Initialize all charts
     */
    init() {
        try {
            console.log('Initializing charts...');

            this.initBurglaryChart();
            this.initOfficersChart();
            this.setupDateFilters();

            this.showEmptyState('burglary');
            this.showEmptyState('officers');

            console.log('Charts initialized successfully');

        } catch (error) {
            console.error('Error initializing charts:', error);
            throw new Error(CONFIG.ERRORS.CHART_INIT_FAILED);
        }
    },

    /**
     * Setup date filter controls
     */
    setupDateFilters() {
        const applyBtn = document.getElementById('apply-filter');
        const resetBtn = document.getElementById('reset-filter');

        if (applyBtn) {
            applyBtn.addEventListener('click', () => this.applyDateFilter());
        }

        if (resetBtn) {
            resetBtn.addEventListener('click', () => this.resetDateFilter());
        }
    },

    /**
     * Apply date range filter to chart
     */
    applyDateFilter() {
        const startDate = document.getElementById('start-date').value;
        const endDate = document.getElementById('end-date').value;

        if (!startDate || !endDate) {
            alert('Please select both start and end dates');
            return;
        }

        if (startDate > endDate) {
            alert('Start date must be before end date');
            return;
        }

        this.updateBurglaryChart(this.originalData.predictions, this.originalData.historical, startDate, endDate);
    },

    /**
     * Reset date filter
     */
    resetDateFilter() {
        document.getElementById('start-date').value = '';
        document.getElementById('end-date').value = '';
        this.updateBurglaryChart(this.originalData.predictions, this.originalData.historical);
    },

    /**
     * Initialize the burglary predictions chart with historical data support
     */
    initBurglaryChart() {
        const ctx = document.querySelector(CONFIG.UI.SELECTORS.BURGLARY_CHART).getContext('2d');

        this.charts.burglary = new Chart(ctx, {
            type: CONFIG.CHARTS.BURGLARY.TYPE,
            data: {
                labels: [],
                datasets: [
                    {
                        label: 'Historical Data',
                        data: [],
                        borderColor: '#666666',
                        backgroundColor: '#666666',
                        borderWidth: 2,
                        pointRadius: 3,
                        pointBackgroundColor: '#666666',
                        fill: false,
                        tension: 0.1
                    },
                    {
                        label: 'Predictions',
                        data: [],
                        borderColor: CONFIG.CHARTS.BURGLARY.COLOR,
                        backgroundColor: CONFIG.CHARTS.BURGLARY.BACKGROUND_COLOR,
                        borderWidth: CONFIG.CHARTS.BURGLARY.LINE_WIDTH,
                        pointRadius: CONFIG.CHARTS.BURGLARY.POINT_RADIUS,
                        pointBackgroundColor: CONFIG.CHARTS.BURGLARY.COLOR,
                        fill: false,
                        tension: 0.1
                    }
                ]
            },
            options: {
                ...CONFIG.CHARTS.COMMON_OPTIONS,
                scales: {
                    x: {
                        title: {
                            display: true,
                            text: 'Month',
                            font: {
                                size: 12,
                                weight: 'bold'
                            }
                        },
                        grid: {
                            display: true,
                            color: '#e0e0e0'
                        }
                    },
                    y: {
                        title: {
                            display: true,
                            text: 'Burglary Count',
                            font: {
                                size: 12,
                                weight: 'bold'
                            }
                        },
                        grid: {
                            display: true,
                            color: '#e0e0e0'
                        },
                        beginAtZero: true
                    }
                },
                interaction: {
                    intersect: false,
                    mode: 'index'
                },
                elements: {
                    point: {
                        hoverRadius: 8
                    }
                },
                plugins: {
                    legend: {
                        display: true,
                        position: 'top',
                        labels: {
                            usePointStyle: true,
                            pointStyle: 'line'
                        }
                    },
                    annotation: {
                        annotations: {
                            predictionLine: {
                                type: 'line',
                                scaleID: 'x',
                                value: null, // Will be set when data is loaded
                                borderColor: 'red',
                                borderWidth: 2,
                                borderDash: [5, 5],
                                label: {
                                    enabled: true,
                                    content: 'Predictions Start',
                                    position: 'start',
                                    yAdjust: -10,
                                    backgroundColor: 'rgba(255, 255, 255, 0.8)',
                                    color: 'red',
                                    font: {
                                        size: 10
                                    }
                                },
                                display: false // Initially hidden
                            }
                        }
                    }
                }
            }
        });
    },

    /**
     * Initialize the officers per hour chart
     */
    initOfficersChart() {
        const ctx = document.querySelector(CONFIG.UI.SELECTORS.OFFICERS_CHART).getContext('2d');

        this.charts.officers = new Chart(ctx, {
            type: CONFIG.CHARTS.OFFICERS.TYPE,
            data: {
                labels: Array.from({length: 24}, (_, i) => i),
                datasets: [{
                    data: Array(24).fill(0),
                    backgroundColor: CONFIG.CHARTS.OFFICERS.COLOR,
                    borderColor: CONFIG.CHARTS.OFFICERS.BORDER_COLOR,
                    borderWidth: CONFIG.CHARTS.OFFICERS.BORDER_WIDTH
                }]
            },
            options: {
                ...CONFIG.CHARTS.COMMON_OPTIONS,
                scales: {
                    x: {
                        title: {
                            display: true,
                            text: 'Hour of Day',
                            font: {
                                size: 12,
                                weight: 'bold'
                            }
                        },
                        grid: {
                            display: true,
                            color: '#e0e0e0'
                        },
                        ticks: {
                            stepSize: 2
                        }
                    },
                    y: {
                        title: {
                            display: true,
                            text: 'Number of Officers',
                            font: {
                                size: 12,
                                weight: 'bold'
                            }
                        },
                        grid: {
                            display: true,
                            color: '#e0e0e0'
                        },
                        beginAtZero: true,
                        ticks: {
                            stepSize: 1
                        }
                    }
                },
                interaction: {
                    intersect: false,
                    mode: 'index'
                }
            }
        });
    },

    /**
     * Update burglary chart with historical data and predictions from JSON
     * @param {Object} predictions - Prediction data object
     * @param {Object} historical - Historical data object
     * @param {string} startDate - Optional start date filter (YYYY-MM)
     * @param {string} endDate - Optional end date filter (YYYY-MM)
     */
    updateBurglaryChart(predictions, historical, startDate = null, endDate = null) {
        if (!predictions || Object.keys(predictions).length === 0) {
            this.showEmptyState('burglary');
            return;
        }

        try {
            // Store original data for filtering
            this.originalData.predictions = predictions;
            this.originalData.historical = historical || {};

            const allLabels = [];
            const historicalValues = [];
            const predictionValues = [];

            // Filter function
            const isInDateRange = (dateStr) => {
                if (!startDate || !endDate) return true;
                return dateStr >= startDate && dateStr <= endDate;
            };

            // Add historical data if available
            if (historical && Object.keys(historical).length > 0) {
                const historicalMonths = Object.keys(historical)
                    .filter(isInDateRange)
                    .sort();

                historicalMonths.forEach(month => {
                    allLabels.push(month);
                    historicalValues.push(historical[month]);
                    predictionValues.push(null);
                });
            }

            // Add prediction data
            const predictionMonths = Object.keys(predictions)
                .filter(isInDateRange)
                .sort();
            const predictionStartIndex = allLabels.length;

            predictionMonths.forEach(month => {
                allLabels.push(month);
                historicalValues.push(null);
                predictionValues.push(predictions[month]);
            });

            // Update chart
            this.charts.burglary.data.labels = allLabels;
            this.charts.burglary.data.datasets[0].data = historicalValues;
            this.charts.burglary.data.datasets[1].data = predictionValues;

            // Show prediction line if we have historical data
            if (predictionStartIndex > 0 && predictionStartIndex < allLabels.length) {
                const predictionStartLabel = allLabels[predictionStartIndex];
                this.charts.burglary.options.plugins.annotation.annotations.predictionLine.value = predictionStartLabel;
                this.charts.burglary.options.plugins.annotation.annotations.predictionLine.display = true;
            } else {
                this.charts.burglary.options.plugins.annotation.annotations.predictionLine.display = false;
            }

            this.charts.burglary.update('active');
            this.showChart('burglary');

            const filterMsg = startDate && endDate ? ` (filtered: ${startDate} to ${endDate})` : '';
            console.log(`Chart updated: ${Object.keys(historical || {}).length} historical + ${predictionMonths.length} predictions${filterMsg}`);

        } catch (error) {
            console.error('Error updating burglary chart:', error);
            this.updateBurglaryChartPredictionsOnly(predictions);
        }
    },

    /**
     * Fallback method to update chart with predictions only
     * @param {Object} predictions - Prediction data object
     */
    updateBurglaryChartPredictionsOnly(predictions) {
        try {
            const months = Object.keys(predictions).sort();
            const values = months.map(month => predictions[month]);

            this.charts.burglary.data.labels = months;
            this.charts.burglary.data.datasets[0].data = []; // No historical data
            this.charts.burglary.data.datasets[1].data = values;

            // Hide prediction line since we have no historical data
            this.charts.burglary.options.plugins.annotation.annotations.predictionLine.display = false;

            this.charts.burglary.update('active');
            this.showChart('burglary');

            console.log('Burglary chart updated with predictions only');
        } catch (error) {
            console.error('Error updating burglary chart with predictions only:', error);
            this.showEmptyState('burglary');
        }
    },



    /**
     * Update officers chart with new data
     * @param {Array} hourlyData - Array of 24 hourly values
     * @param {string} month - Month being displayed
     */
    updateOfficersChart(hourlyData, month) {
        if (!hourlyData || !Array.isArray(hourlyData) || hourlyData.length !== 24) {
            this.showEmptyState('officers');
            return;
        }

        try {
            this.charts.officers.data.datasets[0].data = hourlyData;

            // Update chart title to show the month
            this.charts.officers.options.plugins.title = {
                display: true,
                text: `Officers per Hour (${month})`,
                font: {
                    size: 14,
                    weight: 'bold'
                },
                padding: {
                    top: 10,
                    bottom: 10
                }
            };

            this.charts.officers.update('active');
            this.showChart('officers');

            console.log(`Officers chart updated with data for month: ${month}`);

        } catch (error) {
            console.error('Error updating officers chart:', error);
            this.showEmptyState('officers');
        }
    },

    /**
     * Show chart and hide empty state
     * @param {string} chartType - 'burglary' or 'officers'
     */
    showChart(chartType) {
        const chartElement = document.querySelector(CONFIG.UI.SELECTORS[`${chartType.toUpperCase()}_CHART`]);
        const emptyElement = document.querySelector(CONFIG.UI.SELECTORS[`${chartType.toUpperCase()}_EMPTY`]);

        if (chartElement) chartElement.style.display = 'block';
        if (emptyElement) emptyElement.style.display = 'none';
    },

    /**
     * Hide chart and show empty state
     * @param {string} chartType - 'burglary' or 'officers'
     */
    showEmptyState(chartType) {
        const chartElement = document.querySelector(CONFIG.UI.SELECTORS[`${chartType.toUpperCase()}_CHART`]);
        const emptyElement = document.querySelector(CONFIG.UI.SELECTORS[`${chartType.toUpperCase()}_EMPTY`]);

        if (chartElement) chartElement.style.display = 'none';
        if (emptyElement) emptyElement.style.display = 'flex';
    },

    /**
     * Clear all chart data
     */
    clearAllCharts() {
        this.showEmptyState('burglary');
        this.showEmptyState('officers');

        // Reset chart data
        if (this.charts.burglary) {
            this.charts.burglary.data.labels = [];
            this.charts.burglary.data.datasets[0].data = [];
            this.charts.burglary.data.datasets[1].data = [];
            this.charts.burglary.options.plugins.annotation.annotations.predictionLine.display = false;
            this.charts.burglary.update('none');
        }

        if (this.charts.officers) {
            this.charts.officers.data.datasets[0].data = Array(24).fill(0);
            this.charts.officers.options.plugins.title = { display: false };
            this.charts.officers.update('none');
        }
    },

    /**
     * Resize charts (useful for responsive layouts)
     */
    resize() {
        Object.values(this.charts).forEach(chart => {
            if (chart) {
                chart.resize();
            }
        });
    },

    /**
     * Destroy all charts (cleanup)
     */
    destroy() {
        Object.values(this.charts).forEach(chart => {
            if (chart) {
                chart.destroy();
            }
        });

        this.charts = {
            burglary: null,
            officers: null
        };
    },

    /**
     * Export chart as image
     * @param {string} chartType - 'burglary' or 'officers'
     * @returns {string} Base64 encoded image data
     */
    exportChart(chartType) {
        const chart = this.charts[chartType];
        if (chart) {
            return chart.toBase64Image();
        }
        return null;
    },

    /**
     * Get chart data
     * @param {string} chartType - 'burglary' or 'officers'
     * @returns {Object} Chart data
     */
    getChartData(chartType) {
        const chart = this.charts[chartType];
        if (chart) {
            return {
                labels: chart.data.labels,
                data: chart.data.datasets[0].data
            };
        }
        return null;
    }
};