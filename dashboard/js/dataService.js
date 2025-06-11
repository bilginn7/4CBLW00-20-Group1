/**
 * Enhanced Data Service Module with Improved Parquet Handling
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
        } catch (error) {
            console.error('Error loading geographical data:', error);
            throw error;
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
     * Alternative parquet loading method using different compression handling
     */
    async loadParquetAlternative(url) {
        console.log('🔄 Trying alternative parquet loading method...');

        const response = await fetch(url);
        if (!response.ok) throw new Error(`Failed to fetch ${url}: ${response.statusText}`);

        const arrayBuffer = await response.arrayBuffer();
        const uint8Array = new Uint8Array(arrayBuffer);

        // Try with different parquet reading options
        try {
            // Option 1: Try with minimal options
            const parquetFile = await parquet.readParquet(uint8Array);
            return parquetFile.toObject();
        } catch (error1) {
            console.warn('Minimal options failed:', error1.message);

            try {
                // Option 2: Try reading as table first
                const parquetFile = await parquet.readParquet(uint8Array);
                const table = parquetFile.toTable();
                return table.toArray();
            } catch (error2) {
                console.warn('Table method failed:', error2.message);
                throw new Error(`Both alternative methods failed: ${error1.message}, ${error2.message}`);
            }
        }
    },

    // Helper to load a GeoParquet file
    async loadGeoParquet(url) {
        const response = await fetch(url);
        if (!response.ok) throw new Error(`Failed to fetch ${url}: ${response.statusText}`);
        const arrayBuffer = await response.arrayBuffer();
        return geoparquet.decode(arrayBuffer);
    },

    // Helper to load a standard Parquet file with better error handling
    async loadStandardParquet(url) {
        console.log(`🔄 Loading parquet file: ${url}`);

        const response = await fetch(url);
        if (!response.ok) throw new Error(`Failed to fetch ${url}: ${response.statusText}`);

        const arrayBuffer = await response.arrayBuffer();
        const uint8Array = new Uint8Array(arrayBuffer);

        try {
            const parquetFile = await parquet.readParquet(uint8Array);
            const result = parquetFile.toObject();

            console.log(`✅ Successfully loaded parquet file with ${result.length} records`);
            return result;

        } catch (error) {
            // Enhanced error reporting for compression issues
            if (error.message.includes('compression') || error.message.includes('codec')) {
                throw new Error(`Unsupported compression in parquet file. Error: ${error.message}. Try recompressing with SNAPPY or GZIP compression.`);
            } else if (error.message.includes('undefined') && error.message.includes('stack_pointer')) {
                throw new Error(`Parquet file format issue. This might be due to unsupported compression (like ZSTD). Error: ${error.message}`);
            } else {
                throw new Error(`Parquet reading failed: ${error.message}`);
            }
        }
    },

    // --- All getter methods remain unchanged ---
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

    /**
     * Get detailed information about the loaded data for debugging
     */
    getDataInfo() {
        const info = {
            londonData: {
                loaded: !!this.cache.londonData,
                boroughCount: this.cache.londonData ? Object.keys(this.cache.londonData).length : 0
            },
            geoData: {
                boroughs: !!this.cache.geoData.boroughs,
                wards: !!this.cache.geoData.wards,
                lsoas: !!this.cache.geoData.lsoas
            },
            burglaryData: {
                loaded: !!this.cache.burglaryData,
                recordCount: this.cache.burglaryData ? this.cache.burglaryData.length : 0,
                sampleColumns: this.cache.burglaryData && this.cache.burglaryData.length > 0 ? Object.keys(this.cache.burglaryData[0]) : []
            }
        };

        console.log('📊 Data Service Info:', info);
        return info;
    }
};