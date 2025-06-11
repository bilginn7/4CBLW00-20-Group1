/**
 * Configuration file with CSV fallback for historical data
 */

const CONFIG = {
    // API and Data Sources - Historical data now comes from JSON
    DATA_SOURCES: {
        LONDON_PREDICTIONS: './data/london_predictions_with_officers.json',
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
                color: 'blue',
                weight: 2,
                fillOpacity: 0.1,
                fillColor: 'lightblue'
            },
            WARD_BOUNDARY: {
                color: 'red',
                weight: 3,
                fillOpacity: 0.1,
                fillColor: 'red'
            },
            LSOA_BOUNDARY: {
                color: 'blue',
                weight: 1,
                fillOpacity: 0.3,
                fillColor: 'lightblue'
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
            BOROUGH_SELECT: '#borough-select',
            WARD_SELECT: '#ward-select',
            LSOA_SELECT: '#lsoa-select',
            MONTH_SELECT: '#month-select',
            MAP: '#map',
            BURGLARY_CHART: '#burglary-chart',
            OFFICERS_CHART: '#officers-chart',
            BURGLARY_EMPTY: '#burglary-empty',
            OFFICERS_EMPTY: '#officers-empty'
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
        ENABLE_LOGGING: true,
        USE_CSV_FALLBACK: true
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