/**
 * Chart Controller Module
 * Handles all chart-related functionality using Chart.js
 */

const ChartController = {
    charts: {
        burglary: null,
        officers: null
    },

    /**
     * Initialize all charts
     */
    init() {
        try {
            console.log('Initializing charts...');

            this.initBurglaryChart();
            this.initOfficersChart();

            // Initially hide charts and show empty states
            this.showEmptyState('burglary');
            this.showEmptyState('officers');

            console.log('Charts initialized successfully');

        } catch (error) {
            console.error('Error initializing charts:', error);
            throw new Error(CONFIG.ERRORS.CHART_INIT_FAILED);
        }
    },

    /**
     * Initialize the burglary predictions chart
     */
    initBurglaryChart() {
        const ctx = document.querySelector(CONFIG.UI.SELECTORS.BURGLARY_CHART).getContext('2d');

        this.charts.burglary = new Chart(ctx, {
            type: CONFIG.CHARTS.BURGLARY.TYPE,
            data: {
                labels: [],
                datasets: [{
                    data: [],
                    borderColor: CONFIG.CHARTS.BURGLARY.COLOR,
                    backgroundColor: CONFIG.CHARTS.BURGLARY.BACKGROUND_COLOR,
                    borderWidth: CONFIG.CHARTS.BURGLARY.LINE_WIDTH,
                    pointRadius: CONFIG.CHARTS.BURGLARY.POINT_RADIUS,
                    pointBackgroundColor: CONFIG.CHARTS.BURGLARY.COLOR,
                    fill: false,
                    tension: 0.1
                }]
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
                            text: 'Predicted Burglaries',
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
     * Update burglary chart with new data
     * @param {Object} predictions - Prediction data object
     */
    updateBurglaryChart(predictions) {
        if (!predictions || Object.keys(predictions).length === 0) {
            this.showEmptyState('burglary');
            return;
        }

        try {
            const months = Object.keys(predictions).sort();
            const values = months.map(month => predictions[month]);

            this.charts.burglary.data.labels = months;
            this.charts.burglary.data.datasets[0].data = values;
            this.charts.burglary.update('active');

            this.showChart('burglary');

            console.log('Burglary chart updated with data for months:', months);

        } catch (error) {
            console.error('Error updating burglary chart:', error);
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