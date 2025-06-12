/**
 * Enhanced Data Service Module with Improved Parquet Handling
 */

const DataService = {
    // Cache for loaded data
    cache: {
        londonData: null,
        geoData: {
            boroughs: null,
            wards: null,
            lsoas: null
        }
    },

    /**
     * Load all necessary data for the application
     */
    async loadAllData() {
        try {
            console.log('Loading application data...');

            await Promise.all([
                this.loadLondonPredictions(),
                this.loadGeographicalData()
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
        } catch (error)
        {
            console.error('Error loading geographical data:', error);
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

    // --- Data Getter Functions ---

    getBoroughs() {
        if (!this.cache.londonData) throw new Error('London data not loaded');
        return Object.entries(this.cache.londonData).map(([code, data]) => ({
            code,
            name: data.name
        }));
    },

    getWards(boroughCode) {
        if (!this.cache.londonData || !this.cache.londonData[boroughCode]) return [];
        const wards = this.cache.londonData[boroughCode].wards || {};
        return Object.entries(wards).map(([code, data]) => ({
            code,
            name: data.name
        }));
    },

    getLSOAs(boroughCode, wardCode) {
        if (!this.cache.londonData?.[boroughCode]?.wards?.[wardCode]) return [];
        const lsoas = this.cache.londonData[boroughCode].wards[wardCode].lsoas || {};
        return Object.entries(lsoas).map(([code, data]) => ({
            code,
            name: data.name
        }));
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

    getHistoricalData(boroughCode, wardCode, lsoaCode) {
        try {
            return this.cache.londonData[boroughCode].wards[wardCode].lsoas[lsoaCode].historical || {};
        } catch (error) {
            console.warn('Historical data not found for:', { boroughCode, wardCode, lsoaCode });
            return {};
        }
    },

    /**
     * Get combined metadata for a single LSOA from the main JSON data.
     * @param {string} boroughCode
     * @param {string} wardCode
     * @param {string} lsoaCode
     * @returns {Object|null} An object with LSOA metadata, or null if not found.
     */
    getLSOADataFromJSON(boroughCode, wardCode, lsoaCode) {
        try {
            const lsoa = this.cache.londonData[boroughCode].wards[wardCode].lsoas[lsoaCode];
            if (!lsoa) {
                // This check prevents further errors down the line if the LSOA doesn't exist.
                throw new Error(`LSOA ${lsoaCode} not found in data structure.`);
            }

            return {
                code: lsoaCode,
                name: lsoa.name || lsoaCode,
                hasPredictions: !!lsoa.predictions,
                hasOfficerData: !!lsoa.officer_assignments
            };
        } catch (error) {
            // Log a warning but don't crash the application.
            console.warn(`Could not retrieve LSOA metadata for ${lsoaCode}:`, error.message);
            // Return a default object so the map doesn't completely break on hover/highlight.
            return {
                code: lsoaCode,
                name: lsoaCode,
                hasPredictions: false,
                hasOfficerData: false
            };
        }
    }
};