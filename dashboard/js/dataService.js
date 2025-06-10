/**
 * Data Service Module
 * Handles all data loading and management operations
 */

const DataService = {
    // Cache for loaded data
    cache: {
        londonData: null,
        geoData: {
            boroughs: null,
            wards: null,
            lsoas: null
        },
        // This will now hold the data from features.parquet
        burglaryData: null
    },

    /**
     * Load all necessary data for the application
     */
    async loadAllData() {
        try {
            console.log('Loading application data...');

            await Promise.all([
                this.loadLondonPredictions(),
                this.loadGeographicalData(),
                this.loadBurglaryData() // This function is now simplified
            ]);

            console.log('All data loaded successfully');
            return this.cache;

        } catch (error) {
            console.error('Error loading data:', error);
            throw new Error(CONFIG.ERRORS.DATA_LOAD_FAILED);
        }
    },

    /**
     * Load London predictions data from a JSON file
     */
    async loadLondonPredictions() {
        if (this.cache.londonData) return this.cache.londonData;
        try {
            const response = await fetch(CONFIG.DATA_SOURCES.LONDON_PREDICTIONS);
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            this.cache.londonData = await response.json();
            console.log('London predictions data loaded');
            return this.cache.londonData;
        } catch (error) {
            console.error('Error loading London predictions:', error);
            throw error;
        }
    },

    /**
     * Load geographical boundary data from GeoParquet files
     */
    async loadGeographicalData() {
        if (this.cache.geoData.boroughs) return this.cache.geoData;
        try {
            const [boroughsGeoJSON, wardsGeoJSON, lsoasGeoJSON] = await Promise.all([
                this.loadGeoParquet(CONFIG.DATA_SOURCES.LAD_SHAPES),
                this.loadGeoParquet(CONFIG.DATA_SOURCES.WARD_SHAPES),
                this.loadGeoParquet(CONFIG.DATA_SOURCES.LSOA_SHAPES)
            ]);

            this.cache.geoData = {
                boroughs: boroughsGeoJSON,
                wards: wardsGeoJSON,
                lsoas: lsoasGeoJSON
            };

            console.log('Geographical data loaded and converted to GeoJSON');
            return this.cache.geoData;
        } catch (error) {
            console.error('Error loading geographical data:', error);
            throw error;
        }
    },

    /**
     * REWRITTEN: Load historical burglary data from the single features.parquet file
     */
    async loadBurglaryData() {
        if (this.cache.burglaryData) return this.cache.burglaryData;
        try {
            // Load the single features file
            const featureData = await this.loadStandardParquet(CONFIG.DATA_SOURCES.HISTORICAL_FEATURES);

            this.cache.burglaryData = featureData;
            console.log(`Historical burglary & feature data loaded (${this.cache.burglaryData.length} records)`);
            return this.cache.burglaryData;
        } catch (error) {
            console.error('Error loading historical feature data:', error);
            throw error;
        }
    },

    // Helper to load a GeoParquet file
    async loadGeoParquet(url) {
        const response = await fetch(url);
        if (!response.ok) throw new Error(`Failed to fetch ${url}: ${response.statusText}`);
        const arrayBuffer = await response.arrayBuffer();
        return geoparquet.decode(arrayBuffer);
    },

    // Helper to load a standard Parquet file
    async loadStandardParquet(url) {
        const response = await fetch(url);
        if (!response.ok) throw new Error(`Failed to fetch ${url}: ${response.statusText}`);
        const arrayBuffer = await response.arrayBuffer();
        const parquetFile = await parquet.readParquet(new Uint8Array(arrayBuffer));
        return parquetFile.toObject();
    },

    // --- All getter methods remain unchanged as they read from the cached JSON data ---
    getBoroughs() {
        if (!this.cache.londonData) throw new Error('London data not loaded');
        return Object.entries(this.cache.londonData).map(([code, data]) => ({ code, name: data.name, wards: Object.keys(data.wards || {}).length }));
    },

    getWards(boroughCode) {
        if (!this.cache.londonData || !this.cache.londonData[boroughCode]) return [];
        const wards = this.cache.londonData[boroughCode].wards || {};
        return Object.entries(wards).map(([code, data]) => ({ code, name: data.name, lsoas: Object.keys(data.lsoas || {}).length }));
    },

    getLSOAs(boroughCode, wardCode) {
        if (!this.cache.londonData || !this.cache.londonData[boroughCode] || !this.cache.londonData[boroughCode].wards[wardCode]) return [];
        const lsoas = this.cache.londonData[boroughCode].wards[wardCode].lsoas || {};
        return Object.entries(lsoas).map(([code, data]) => ({ code, name: data.name, hasPredictions: !!data.predictions, hasOfficerData: !!data.officer_assignments }));
    },

    getPredictions(boroughCode, wardCode, lsoaCode) {
        try {
            return this.cache.londonData[boroughCode].wards[wardCode].lsoas[lsoaCode].predictions || null;
        } catch (error) {
            console.warn('Predictions not found for:', { boroughCode, wardCode, lsoaCode });
            return null;
        }
    },

    getOfficerAssignments(boroughCode, wardCode, lsoaCode) {
        try {
            return this.cache.londonData[boroughCode].wards[wardCode].lsoas[lsoaCode].officer_assignments || null;
        } catch (error) {
            console.warn('Officer assignments not found for:', { boroughCode, wardCode, lsoaCode });
            return null;
        }
    },
};