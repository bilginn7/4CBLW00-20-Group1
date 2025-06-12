/**
 * Enhanced Chart Controller Module
 * Handles all chart-related functionality with historical data integration
 */

const ChartController = {
    charts: {
        burglary: null,
        officers: null
    },

    originalData: {
        historical: {},
        predictions: {}
    },

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

    setupDateFilters() {
        const applyBtn = document.getElementById('apply-filter');
        const resetBtn = document.getElementById('reset-filter');
        if (applyBtn) applyBtn.addEventListener('click', () => this.applyDateFilter());
        if (resetBtn) resetBtn.addEventListener('click', () => this.resetDateFilter());
    },

    applyDateFilter() {
        const startDate = document.getElementById('start-date').value;
        const endDate = document.getElementById('end-date').value;
        if (!startDate || !endDate) return alert('Please select both start and end dates');
        if (startDate > endDate) return alert('Start date must be before end date');
        this.updateBurglaryChart(this.originalData.predictions, this.originalData.historical, startDate, endDate);
    },

    resetDateFilter() {
        document.getElementById('start-date').value = '';
        document.getElementById('end-date').value = '';
        this.updateBurglaryChart(this.originalData.predictions, this.originalData.historical);
    },

    initBurglaryChart() {
        const ctx = document.querySelector(CONFIG.UI.SELECTORS.BURGLARY_CHART).getContext('2d');
        this.charts.burglary = new Chart(ctx, {
            type: CONFIG.CHARTS.BURGLARY.TYPE,
            data: {
                labels: [],
                datasets: [{
                    label: 'Historical Data',
                    data: [],
                    borderColor: '#1E88E5',
                    backgroundColor: '#1E88E5',
                    borderWidth: 2,
                    pointRadius: 3,
                    fill: false,
                    tension: 0.1
                }, {
                    label: 'Predictions',
                    data: [],
                    borderColor: CONFIG.CHARTS.BURGLARY.COLOR,
                    backgroundColor: CONFIG.CHARTS.BURGLARY.BACKGROUND_COLOR,
                    borderWidth: CONFIG.CHARTS.BURGLARY.LINE_WIDTH,
                    pointRadius: CONFIG.CHARTS.BURGLARY.POINT_RADIUS,
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
                                family: 'DM Sans',
                                size: 12,
                                weight: '600'
                                }
                            },
                        grid: {
                            display: true,
                            color: '#e0e0e0'
                        },
                        ticks: {
                            callback: function(value, index, ticks) {
                                const label = this.getLabelForValue(value);
                                const [year, month] = label.split('-');

                                if (month === '01' || index === 0) {
                                    return year.slice(-2);
                                }
                                return '';
                            },
                            maxRotation: 0,
                            autoSkip: false
                        }
                    },
                    y: {
                        title: {
                            display: true,
                            text: 'Burglary Count',
                            font: {
                                family: 'DM Sans',
                                size: 12,
                                weight: '600'
                            }
                        },
                        grid: {
                            display: true,
                            color: '#e0e0e0'
                        },
                        beginAtZero: true
                    }
                },
                interaction: { intersect: false, mode: 'index' },
                elements: { point: { hoverRadius: 8 } },
                plugins: {
                    legend: { display: true, position: 'top', labels: { usePointStyle: true, pointStyle: 'line' } },
                        tooltip: {
                            callbacks: {
                                title: function(context) {
                                    const [year, month] = context[0].label.split('-');
                                    const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                                                      'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
                                    return `${monthNames[parseInt(month) - 1]} ${year}`;
                                },
                                label: function(context) {
                                    const datasetLabel = context.dataset.label;
                                    const value = context.parsed.y;
                                    if (value !== null) {
                                        return `${datasetLabel}: ${value} incidents`;
                                    }
                                    return null;
                                },
                            },

                            // Font settings
                            titleFont: {
                                family: 'DM Sans',
                                size: 14,
                                weight: 'bold',
                                style: 'normal'
                            },

                            bodyFont: {
                                family: 'DM Sans',
                                size: 12,
                                weight: 'normal',
                                style: 'normal'
                            },

                            footerFont: {
                                family: 'DM Sans',
                                size: 11,
                                weight: 'normal',
                                style: 'italic'
                            },

                            // Styling
                            backgroundColor: 'rgba(0, 0, 0, 0.8)',
                            titleColor: 'white',
                            bodyColor: 'white',
                            footerColor: '#cccccc',
                            borderColor: 'black',
                            borderWidth: 1,
                            cornerRadius: 4,
                            displayColors: true,

                            filter: function(tooltipItem) {
                                return tooltipItem.parsed.y !== null;
                            }
                        },
                    annotation: {
                        annotations: {
                            predictionLine: {
                                type: 'line',
                                scaleID: 'x',
                                value: null,
                                borderColor: 'red',
                                borderWidth: 2,
                                borderDash: [5, 5],
                                label: { enabled: true, content: 'Predictions Start', position: 'start', yAdjust: -10, backgroundColor: 'rgba(255, 255, 255, 0.8)', color: 'red', font: { size: 10 } },
                                display: false
                            }
                        }
                    }
                }
            }
        });
    },

    initOfficersChart() {
        const ctx = document.querySelector(CONFIG.UI.SELECTORS.OFFICERS_CHART).getContext('2d');
        this.charts.officers = new Chart(ctx, {
            type: CONFIG.CHARTS.OFFICERS.TYPE,
            data: {
                labels: Array.from({ length: 24 }, (_, i) => i),
                datasets: [{
                    data: Array(24).fill(0),
                    backgroundColor: CONFIG.CHARTS.OFFICERS.COLOR,
                    borderColor: CONFIG.CHARTS.OFFICERS.BORDER_COLOR,
                    borderWidth: CONFIG.CHARTS.OFFICERS.BORDER_WIDTH
                }]
            },
            options: {
                ...CONFIG.CHARTS.COMMON_OPTIONS,
                plugins: {
                    ...CONFIG.CHARTS.COMMON_OPTIONS?.plugins,
                    title: {
                        display: false
                    },
                    tooltip: {
                        callbacks: {
                            // Customize the title that appears at the top of the tooltip
                            title: function(context) {
                                return `Hour: ${context[0].label}:00`;
                            },

                            // Customize the label that shows the value
                            label: function(context) {
                                return `Officers: ${context.parsed.y}`;
                            },
                        },
                        titleFont: {
                            family: 'DM Sans',        // Font family for title
                            size: 14,                 // Font size for title
                            weight: 'bold',           // Font weight: 'normal', 'bold', '600', etc.
                            style: 'normal'           // Font style: 'normal', 'italic', 'oblique'
                        },

                        bodyFont: {
                            family: 'DM Sans',        // Font family for body text (main labels)
                            size: 12,                 // Font size for body
                            weight: 'normal',         // Font weight
                            style: 'normal'           // Font style
                        },

                        footerFont: {
                            family: 'DM Sans',        // Font family for footer (afterLabel text)
                            size: 11,                 // Font size for footer
                            weight: 'normal',         // Font weight
                            style: 'italic'           // Font style
                        },

                        backgroundColor: 'rgba(0, 0, 0, 0.8)',
                        titleColor: 'white',
                        bodyColor: 'white',
                        borderColor: 'black',
                        borderWidth: 1,
                        cornerRadius: 4,
                        displayColors: false
                    }
                },
                scales: {
                    x: {
                        title: {
                            display: true,
                            text: 'Hour of Day',
                            font: {
                                family: 'DM Sans',
                                size: 12,
                                weight: '600'
                            }
                        },
                        grid: {
                            display: true,
                            color: '#e0e0e0'
                            },
                        ticks: {
                            stepSize: 1,
                            maxRotation: 0,
                            minRotation: 0
                            }
                        },
                    y: {
                        title: {
                            display: true,
                            text: 'Num. Officers',
                            font: {
                                family: 'DM Sans',
                                size: 12,
                                weight: '600'
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
                interaction: { intersect: false, mode: 'index' }
            }
        });
    },

    updateBurglaryChart(predictions, historical, startDate = null, endDate = null) {
        if (!predictions || Object.keys(predictions).length === 0) {
            this.showEmptyState('burglary');
            return;
        }
        try {
            this.originalData = { predictions, historical: historical || {} };
            const allLabels = [], historicalValues = [], predictionValues = [];
            const isInDateRange = dateStr => (!startDate || !endDate) || (dateStr >= startDate && dateStr <= endDate);

            if (historical && Object.keys(historical).length > 0) {
                Object.keys(historical).filter(isInDateRange).sort().forEach(month => {
                    allLabels.push(month);
                    historicalValues.push(historical[month]);
                    predictionValues.push(null);
                });
            }
            const predictionStartIndex = allLabels.length;
            const predictionMonths = Object.keys(predictions).filter(isInDateRange).sort();
            predictionMonths.forEach(month => {
                allLabels.push(month);
                historicalValues.push(null);
                predictionValues.push(predictions[month]);
            });

            this.charts.burglary.data.labels = allLabels;
            this.charts.burglary.data.datasets[0].data = historicalValues;
            this.charts.burglary.data.datasets[1].data = predictionValues;

            const line = this.charts.burglary.options.plugins.annotation.annotations.predictionLine;
            line.display = predictionStartIndex > 0 && predictionStartIndex < allLabels.length;
            if (line.display) line.value = allLabels[predictionStartIndex];

            this.charts.burglary.update('active');
            this.showChart('burglary');
        } catch (error) {
            console.error('Error updating burglary chart:', error);
            this.updateBurglaryChartPredictionsOnly(predictions);
        }
    },

    updateBurglaryChartPredictionsOnly(predictions) {
        try {
            const months = Object.keys(predictions).sort();
            const values = months.map(month => predictions[month]);
            this.charts.burglary.data.labels = months;
            this.charts.burglary.data.datasets[0].data = [];
            this.charts.burglary.data.datasets[1].data = values;
            this.charts.burglary.options.plugins.annotation.annotations.predictionLine.display = false;
            this.charts.burglary.update('active');
            this.showChart('burglary');
        } catch (error) {
            console.error('Error updating burglary chart with predictions only:', error);
            this.showEmptyState('burglary');
        }
    },

    updateOfficersChart(hourlyData, month) {
        if (!hourlyData || !Array.isArray(hourlyData) || hourlyData.length !== 24) {
            this.showEmptyState('officers');
            return;
        }
        try {
            this.charts.officers.data.datasets[0].data = hourlyData;
            this.charts.officers.update('active');
            this.showChart('officers');
            console.log(`Officers chart updated for month: ${month}`);
        } catch (error) {
            console.error('Error updating officers chart:', error);
            this.showEmptyState('officers');
        }
    },

    showChart(chartType) {
        const chartEl = document.querySelector(CONFIG.UI.SELECTORS[`${chartType.toUpperCase()}_CHART`]);
        const emptyEl = document.querySelector(CONFIG.UI.SELECTORS[`${chartType.toUpperCase()}_EMPTY`]);
        if (chartEl) chartEl.style.display = 'block';
        if (emptyEl) emptyEl.style.display = 'none';
    },

    showEmptyState(chartType) {
        const chartEl = document.querySelector(CONFIG.UI.SELECTORS[`${chartType.toUpperCase()}_CHART`]);
        const emptyEl = document.querySelector(CONFIG.UI.SELECTORS[`${chartType.toUpperCase()}_EMPTY`]);
        if (chartEl) chartEl.style.display = 'none';
        if (emptyEl) emptyEl.style.display = 'flex';
    },

    clearAllCharts() {
        this.showEmptyState('burglary');
        this.showEmptyState('officers');
        if (this.charts.burglary) {
            this.charts.burglary.data.labels = [];
            this.charts.burglary.data.datasets.forEach(d => d.data = []);
            this.charts.burglary.options.plugins.annotation.annotations.predictionLine.display = false;
            this.charts.burglary.update('none');
        }
        if (this.charts.officers) {
            this.charts.officers.data.datasets[0].data = Array(24).fill(0);
            this.charts.officers.update('none');
        }
    },

    resize() {
        Object.values(this.charts).forEach(chart => chart?.resize());
    },

    destroy() {
        Object.values(this.charts).forEach(chart => chart?.destroy());
        this.charts = { burglary: null, officers: null };
    }
};