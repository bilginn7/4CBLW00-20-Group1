/**
 * Map Controller Module
 * Handles all map-related functionality using Leaflet
 */

const MapController = {
    map: null,
    layers: {
        boroughs: null,
        currentWard: null,
        currentLSOAs: []
    },

    /**
     * Initialize the map
     */
    init() {
        try {
            console.log('Initializing map...');

            // Create map instance
            this.map = L.map('map', {
                center: CONFIG.MAP.DEFAULT_CENTER,
                zoom: CONFIG.MAP.DEFAULT_ZOOM,
                zoomControl: true,
                scrollWheelZoom: true,
                dragging: true,
                doubleClickZoom: true,
                boxZoom: true,
                keyboard: true
            });

            // Add tile layer
            L.tileLayer(CONFIG.MAP.TILE_LAYER, {
                attribution: CONFIG.MAP.ATTRIBUTION,
                maxZoom: 18
            }).addTo(this.map);

            // Add initial London borough boundaries
            this.addLondonBoroughs();

            console.log('Map initialized successfully');

        } catch (error) {
            console.error('Error initializing map:', error);
            throw new Error(CONFIG.ERRORS.MAP_INIT_FAILED);
        }
    },

    /**
     * Add London borough boundaries to the map
     */
    addLondonBoroughs() {
        // In a real application, you would load GeoJSON data from your parquet files
        // For now, we'll add a simplified London boundary

        const londonBounds = [
            [51.28, -0.489],
            [51.28, 0.236],
            [51.686, 0.236],
            [51.686, -0.489]
        ];

        this.layers.boroughs = L.rectangle(londonBounds, CONFIG.MAP.STYLES.LONDON_BOROUGHS)
            .addTo(this.map)
            .bindTooltip('London Boroughs', { permanent: false, direction: 'center' });
    },

    /**
     * Update map to show selected ward with LSOAs
     * @param {string} wardCode - Ward code to display
     * @param {string} boroughCode - Borough code
     */
    showWard(wardCode, boroughCode) {
        try {
            console.log(`Updating map for ward: ${wardCode} in borough: ${boroughCode}`);

            // Clear existing ward and LSOA layers
            this.clearWardLayers();

            // In a real application, you would:
            // 1. Load ward geometry from your GeoJSON/parquet files
            // 2. Load LSOA geometries for that ward
            // 3. Add them to the map
            // 4. Fit map bounds to the ward

            // Mock implementation for demonstration
            this.addMockWardGeometry(wardCode, boroughCode);

            // Disable map interactions for fixed view
            this.setFixedView(true);

        } catch (error) {
            console.error('Error showing ward on map:', error);
        }
    },

    /**
     * Add mock ward geometry for demonstration
     * @param {string} wardCode - Ward code
     * @param {string} boroughCode - Borough code
     */
    addMockWardGeometry(wardCode, boroughCode) {
        // Mock ward bounds based on ward code (in real app, load from data)
        const mockCenter = this.getMockWardCenter(wardCode);
        const wardBounds = [
            [mockCenter[0] - 0.01, mockCenter[1] - 0.015],
            [mockCenter[0] + 0.01, mockCenter[1] + 0.015]
        ];

        // Add ward boundary
        this.layers.currentWard = L.rectangle(wardBounds, {
            ...CONFIG.MAP.STYLES.WARD_BOUNDARY,
            className: 'ward-boundary'
        }).addTo(this.map);

        // Add mock LSOAs within the ward
        this.addMockLSOAs(wardCode, boroughCode, mockCenter);

        // Fit map to ward bounds
        this.map.fitBounds(wardBounds, { padding: [20, 20] });
        this.map.setZoom(CONFIG.MAP.WARD_ZOOM);
    },

    /**
     * Add mock LSOA geometries within a ward
     * @param {string} wardCode - Ward code
     * @param {string} boroughCode - Borough code
     * @param {Array} center - Ward center coordinates
     */
    addMockLSOAs(wardCode, boroughCode, center) {
        // Get LSOAs for this ward from data service
        const lsoas = DataService.getLSOAs(boroughCode, wardCode);

        // Create mock LSOA boundaries
        lsoas.forEach((lsoa, index) => {
            const offset = index * 0.003;
            const lsoaBounds = [
                [center[0] - 0.005 + offset, center[1] - 0.007],
                [center[0] + 0.005 + offset, center[1] + 0.007]
            ];

            const lsoaLayer = L.rectangle(lsoaBounds, {
                ...CONFIG.MAP.STYLES.LSOA_BOUNDARY,
                className: 'lsoa-boundary'
            })
            .addTo(this.map)
            .bindTooltip(`${lsoa.name}<br>Code: ${lsoa.code}`, {
                permanent: false,
                direction: 'center'
            });

            this.layers.currentLSOAs.push(lsoaLayer);
        });
    },

    /**
     * Get mock center coordinates for a ward
     * @param {string} wardCode - Ward code
     * @returns {Array} [lat, lng] coordinates
     */
    getMockWardCenter(wardCode) {
        // Mock centers based on ward codes (in real app, calculate from geometry)
        const mockCenters = {
            'E05013944': [51.395, -0.295], // Surbiton Hill
            'E05013945': [51.385, -0.285], // Tolworth and Hook Rise
            'E05013946': [51.455, -0.115], // Brixton North
        };

        return mockCenters[wardCode] || CONFIG.MAP.DEFAULT_CENTER;
    },

    /**
     * Clear ward and LSOA layers from map
     */
    clearWardLayers() {
        if (this.layers.currentWard) {
            this.map.removeLayer(this.layers.currentWard);
            this.layers.currentWard = null;
        }

        this.layers.currentLSOAs.forEach(layer => {
            this.map.removeLayer(layer);
        });
        this.layers.currentLSOAs = [];
    },

    /**
     * Reset map to show all London boroughs
     */
    showLondon() {
        console.log('Resetting map to show London');

        // Clear ward layers
        this.clearWardLayers();

        // Enable map interactions
        this.setFixedView(false);

        // Reset view to London
        this.map.setView(CONFIG.MAP.DEFAULT_CENTER, CONFIG.MAP.DEFAULT_ZOOM);
    },

    /**
     * Set map to fixed view (disable interactions) or enable interactions
     * @param {boolean} fixed - Whether to fix the view
     */
    setFixedView(fixed) {
        const options = CONFIG.MAP.WARD_VIEW_OPTIONS;

        if (fixed) {
            // Disable interactions for fixed ward view
            Object.keys(options).forEach(option => {
                if (options[option] === false) {
                    this.map[option].disable();
                } else if (option === 'zoomControl') {
                    this.map.zoomControl.remove();
                }
            });
        } else {
            // Enable interactions for London view
            this.map.scrollWheelZoom.enable();
            this.map.dragging.enable();
            this.map.doubleClickZoom.enable();
            this.map.boxZoom.enable();
            this.map.keyboard.enable();
            this.map.addControl(L.control.zoom());
        }
    },

    /**
     * Highlight a specific LSOA on the map
     * @param {string} lsoaCode - LSOA code to highlight
     */
    highlightLSOA(lsoaCode) {
        // Reset all LSOA styles
        this.layers.currentLSOAs.forEach(layer => {
            layer.setStyle(CONFIG.MAP.STYLES.LSOA_BOUNDARY);
        });

        // Find and highlight the selected LSOA
        // In a real application, you would match by LSOA code
        // For now, we'll highlight the first LSOA as an example
        if (this.layers.currentLSOAs.length > 0) {
            this.layers.currentLSOAs[0].setStyle({
                ...CONFIG.MAP.STYLES.LSOA_BOUNDARY,
                color: 'orange',
                weight: 3,
                fillOpacity: 0.6
            });
        }
    },

    /**
     * Add custom layer to map
     * @param {Object} layer - Leaflet layer object
     * @param {string} name - Layer name for reference
     */
    addLayer(layer, name) {
        layer.addTo(this.map);
        if (!this.layers.custom) {
            this.layers.custom = {};
        }
        this.layers.custom[name] = layer;
    },

    /**
     * Remove custom layer from map
     * @param {string} name - Layer name to remove
     */
    removeLayer(name) {
        if (this.layers.custom && this.layers.custom[name]) {
            this.map.removeLayer(this.layers.custom[name]);
            delete this.layers.custom[name];
        }
    },

    /**
     * Get current map bounds
     * @returns {Object} Map bounds
     */
    getBounds() {
        return this.map.getBounds();
    },

    /**
     * Resize map (useful for responsive layouts)
     */
    resize() {
        if (this.map) {
            this.map.invalidateSize();
        }
    }
};