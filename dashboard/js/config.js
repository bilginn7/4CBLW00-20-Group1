/**
 * Configuration file for the application
 */

const CONFIG = {
    // API and Data Sources
    DATA_SOURCES: {
        LONDON_PREDICTIONS: './data/london_predictions_with_officers.json',
        BURGLARY_LOCATIONS: './data/london_areas_with_burglaries.json', // NEW
        LAD_SHAPES: './data/geo/LAD_shape.geoparquet',
        WARD_SHAPES: './data/geo/WARD_shape.geoparquet',
        LSOA_SHAPES: './data/geo/LSOA_shape.geoparquet'
    },

    // Map Configuration
    MAP: {
        DEFAULT_CENTER: [51.5074, -0.1278],
        DEFAULT_ZOOM: 10,
        WARD_ZOOM: 14,
        TILE_LAYER: 'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png',
        ATTRIBUTION: '© OpenStreetMap contributors, © CARTO',

        WARD_VIEW_OPTIONS: {
            scrollWheelZoom: false,
            dragging: false,
            doubleClickZoom: false,
            boxZoom: false,
            keyboard: false,
            zoomControl: false
        },

        STYLES: {
            LONDON_BOROUGHS: {
                color: '#1E88E5',
                weight: 2,
                fillOpacity: 0.1,
                fillColor: '#1E88E5'
            },
            CLICKABLE_WARD_BOUNDARY: {
                color: '#DA4C80',
                weight: 2,
                fillOpacity: 0.2,
                fillColor: '#DA4C80'
            },
            ACTIVE_WARD_BOUNDARY: {
                color: '#DE0000',
                weight: 4,
                fillOpacity: 0.1,
                fillColor: '#DE0000'
            },
            INACTIVE_WARD_BOUNDARY: {
                color: '#DA4C80',
                weight: 2,
                fillOpacity: 0.2,
                fillColor: '#DA4C80'
            },
            LSOA_BOUNDARY: {
                color: '#004D40',
                weight: 2,
                fillOpacity: 0.3,
                fillColor: '#004D40'
            },
            HIGHLIGHTED_LSOA: {
                color: '#FFC107',
                weight: 3,
                fillOpacity: 0.6,
                fillColor: '#FFC107'
            },
            BURGLARY_MARKER: {
                color: '#FF4444',
                fillColor: '#FF6666',
                fillOpacity: 0.8,
                radius: 4,
                weight: 1
            }
        }
    },

    // Chart Configuration
    CHARTS: {
        BURGLARY: {
            TYPE: 'line',
            COLOR: 'black',
            POINT_RADIUS: 6,
            LINE_WIDTH: 3,
            BACKGROUND_COLOR: 'black'
        },
        OFFICERS: {
            TYPE: 'bar',
            COLOR: 'red',
            BORDER_COLOR: 'darkred',
            BORDER_WIDTH: 1
        },
        COMMON_OPTIONS: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                }
            }
        }
    },

    // UI Configuration
    UI: {
        SELECTORS: {
            // Main Dropdowns
            BOROUGH_SELECT: '#borough-select',
            WARD_SELECT: '#ward-select',
            LSOA_SELECT: '#lsoa-select',
            // Main Controls
            RESET_BUTTON: '#reset-button',
            // Map
            MAP: '#map',
            // Charts
            BURGLARY_CHART: '#burglary-chart',
            OFFICERS_CHART: '#officers-chart',
            BURGLARY_EMPTY: '#burglary-empty',
            OFFICERS_EMPTY: '#officers-empty',
            // Month Selector Widget
            MONTH_SELECTOR: '#month-selector',
            MONTH_DISPLAY: '#month-display',
            PREV_MONTH_BTN: '#prev-month',
            NEXT_MONTH_BTN: '#next-month',
            // Month Calendar Popup
            MONTH_CALENDAR: '#month-calendar',
            PREV_YEAR_BTN: '#prev-year',
            NEXT_YEAR_BTN: '#next-year',
            CALENDAR_YEAR: '#calendar-year',
            CALENDAR_BODY: '#calendar-body'
        },
        MESSAGES: {
            SELECT_ALL: 'Select Borough, Ward, and LSOA to view data',
            SELECT_WITH_MONTH: 'Select Borough, Ward, LSOA, and Month to view data',
            NO_DATA: 'No data available',
            LOADING: 'Loading...'
        },
        PLACEHOLDERS: {
            BOROUGH: 'Select Borough',
            WARD: 'Select Ward',
            LSOA: 'Select LSOA',
            MONTH: 'Select Month'
        }
    },

    // Application Settings
    APP: {
        DEBUG: true,
        AUTO_SELECT_LATEST_MONTH: true,
    },

    // Error Handling
    ERRORS: {
        DATA_LOAD_FAILED: 'Failed to load data',
        MAP_INIT_FAILED: 'Failed to initialize map',
        CHART_INIT_FAILED: 'Failed to initialize charts',
        INVALID_SELECTION: 'Invalid selection'
    }
};

Object.freeze(CONFIG);