/**
 * Map Controller Module - Updated with Real Boundary Support and Drill-Down
 * Handles all map-related functionality using actual GeoParquet data
 */

const MapController = {
    map: null,
    layers: {
        boroughs: null,
        currentWards: [],  // Changed to array for multiple wards
        currentWard: null,
        currentLSOAs: [],
        allWards: null,
        allLSOAs: null
    },
    currentLevel: 'london', // 'london', 'borough', 'ward'
    currentSelection: {
        borough: null,
        ward: null
    },

    /**
     * Initialize the map
     */
    init() {
        try {
            console.log('🗺️ Initializing map...');

            // Create map instance with initial zoom control
            this.map = L.map('map', {
                center: CONFIG.MAP.DEFAULT_CENTER,
                zoom: CONFIG.MAP.DEFAULT_ZOOM,
                zoomControl: true,  // Enable initial zoom control
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

            // Load and add geographical boundaries (data should already be loaded by DataService)
            this.loadGeographicalBoundaries();

            console.log('✅ Map initialized successfully');

        } catch (error) {
            console.error('❌ Error initializing map:', error);
            throw new Error(CONFIG.ERRORS.MAP_INIT_FAILED);
        }
    },

    /**
     * Load and display geographical boundaries from the parquet data
     */
    loadGeographicalBoundaries() {
        try {
            console.log('📦 Setting up geographical boundaries...');

            // Get the geographical data from DataService (should already be loaded)
            const geoData = DataService.cache.geoData;

            if (!geoData) {
                console.warn('⚠️ No geographical data available');
                return;
            }

            // Add borough boundaries (LAD)
            if (geoData.boroughs && geoData.boroughs.features && geoData.boroughs.features.length > 0) {
                this.addBoroughBoundaries(geoData.boroughs);
                console.log(`✅ Added ${geoData.boroughs.features.length} borough boundaries`);
            } else {
                console.warn('⚠️ No borough boundary data available');
            }

            // Store ward and LSOA data for later use
            this.allWards = geoData.wards;
            this.allLSOAs = geoData.lsoas;

            console.log('✅ Geographical boundaries setup complete');
            console.log(`   📊 Available: ${this.allWards?.features?.length || 0} ward boundaries, ${this.allLSOAs?.features?.length || 0} LSOA boundaries`);

        } catch (error) {
            console.error('❌ Error loading geographical boundaries:', error);
            console.warn('⚠️ Map will use simplified boundary display');
        }
    },

    /**
     * Add borough boundaries to the map, filtered by boroughs in JSON data
     */
    addBoroughBoundaries(boroughsGeoJSON) {
        // Get the list of borough codes from the JSON data
        const jsonBoroughCodes = Object.keys(DataService.cache.londonData || {});
        console.log(`🏢 Filtering boroughs to show only those in JSON data:`, jsonBoroughCodes);

        // Filter GeoJSON features to only include boroughs in our JSON data
        const filteredFeatures = boroughsGeoJSON.features.filter(feature => {
            const props = feature.properties;
            const boroughCode = props.LAD22CD || props.LAD21CD || props.code || props.id;
            return jsonBoroughCodes.includes(boroughCode);
        });

        console.log(`📊 Filtered ${filteredFeatures.length}/${boroughsGeoJSON.features.length} borough boundaries`);

        if (filteredFeatures.length === 0) {
            console.warn('⚠️ No matching borough boundaries found!');
            console.log('Sample GeoJSON properties:', boroughsGeoJSON.features.slice(0, 3).map(f => f.properties));
            console.log('JSON borough codes:', jsonBoroughCodes.slice(0, 5));
            return;
        }

        const filteredGeoJSON = {
            type: "FeatureCollection",
            features: filteredFeatures
        };

        this.layers.boroughs = L.geoJSON(filteredGeoJSON, {
            style: CONFIG.MAP.STYLES.LONDON_BOROUGHS,
            onEachFeature: (feature, layer) => {
                // Add popup with borough info
                const props = feature.properties;
                const boroughCode = props.LAD22CD || props.LAD21CD || props.code || props.id;
                const boroughName = props.LAD22NM || props.LAD21NM || props.name || 'Unknown Borough';

                // Get additional info from JSON data
                const jsonBoroughData = DataService.cache.londonData[boroughCode];
                const wardCount = jsonBoroughData ? Object.keys(jsonBoroughData.wards || {}).length : 0;

                layer.bindTooltip(
                    `<strong>${boroughName}</strong><br>Code: ${boroughCode}<br>Wards: ${wardCount}`,
                    {
                        permanent: false,
                        direction: 'center',
                        className: 'borough-tooltip'
                    }
                );

                // Click handler for borough selection
                layer.on('click', () => {
                    console.log('🖱️ Borough clicked:', boroughName, boroughCode);

                    // Update map to show borough drill-down
                    this.showBoroughWards(boroughCode, boroughName);

                    // Auto-select this borough in the dropdown
                    const boroughSelect = document.querySelector(CONFIG.UI.SELECTORS.BOROUGH_SELECT);
                    if (boroughSelect) {
                        boroughSelect.value = boroughCode;
                        boroughSelect.dispatchEvent(new Event('change'));
                    }
                });
            }
        }).addTo(this.map);

        console.log(`✅ Added ${filteredFeatures.length} filtered borough boundaries`);
    },

    /**
     * Show wards within a selected borough (drill-down level 1)
     */
    showBoroughWards(boroughCode, boroughName) {
        try {
            console.log(`🎯 Showing wards for borough: ${boroughName} (${boroughCode})`);

            // Update current state
            this.currentLevel = 'borough';
            this.currentSelection.borough = boroughCode;
            this.currentSelection.ward = null;

            // Clear existing ward and LSOA layers
            this.clearWardLayers();
            this.clearCurrentWards();

            if (!this.allWards) {
                console.warn('⚠️ Ward boundary data not available');
                return;
            }

            // Get ward codes for this borough from JSON structure
            const wardCodes = this.getWardCodesForBorough(boroughCode);
            console.log(`📍 Found ${wardCodes.length} wards for borough ${boroughCode}:`, wardCodes);

            if (wardCodes.length === 0) {
                console.warn('⚠️ No wards found for this borough');
                return;
            }

            // Find and add ward boundaries for this borough
            this.addWardBoundariesForBorough(wardCodes, boroughCode);

            // Fit map to borough bounds
            this.fitToBoroughBounds(boroughCode);

            // Enable map interactions for ward selection
            this.setFixedView(false);

        } catch (error) {
            console.error('❌ Error showing borough wards:', error);
        }
    },

    /**
     * Get ward codes for a specific borough from JSON structure
     */
    getWardCodesForBorough(boroughCode) {
        try {
            const borough = DataService.cache.londonData[boroughCode];
            if (!borough || !borough.wards) {
                console.warn(`⚠️ Borough ${boroughCode} not found in data`);
                return [];
            }

            return Object.keys(borough.wards);
        } catch (error) {
            console.error('❌ Error getting ward codes for borough:', error);
            return [];
        }
    },

    /**
     * Add ward boundaries for a specific borough
     */
    addWardBoundariesForBorough(wardCodes, boroughCode) {
        if (!this.allWards || !this.allWards.features) {
            console.warn('⚠️ No ward data available');
            return;
        }

        console.log(`🔍 Adding ${wardCodes.length} ward boundaries for borough ${boroughCode}`);

        let foundCount = 0;
        wardCodes.forEach(wardCode => {
            const wardFeature = this.findFeatureByCode(
                this.allWards,
                wardCode,
                ['WD24CD', 'WD21CD', 'WD22CD', 'code', 'WARD_CODE']
            );

            if (wardFeature) {
                this.addClickableWardBoundary(wardFeature, wardCode, boroughCode);
                foundCount++;
            } else {
                console.warn(`⚠️ Ward boundary not found: ${wardCode}`);
            }
        });

        console.log(`✅ Added ${foundCount}/${wardCodes.length} ward boundaries for borough drill-down`);
    },

    /**
     * Add a clickable ward boundary for borough drill-down
     */
    addClickableWardBoundary(wardFeature, wardCode, boroughCode) {
        const wardName = wardFeature.properties.WD24NM || wardFeature.properties.WD22NM || wardFeature.properties.name || wardCode;

        // Get ward data from JSON for context
        const wardData = this.getWardDataFromJSON(boroughCode, wardCode);
        const lsoaCount = wardData ? Object.keys(wardData.lsoas || {}).length : 0;

        const wardLayer = L.geoJSON(wardFeature, {
            style: {
                color: '#ff6b6b',
                weight: 2,
                fillOpacity: 0.2,
                fillColor: '#ff6b6b'
            }
        }).addTo(this.map);

        // Add tooltip
        wardLayer.bindTooltip(
            `<strong>${wardName}</strong><br>Code: ${wardCode}<br>LSOAs: ${lsoaCount}<br><em>Click to drill down</em>`,
            {
                permanent: false,
                direction: 'center',
                className: 'ward-tooltip'
            }
        );

        // Add click handler for ward drill-down
        wardLayer.on('click', (e) => {
            console.log('🖱️ Ward clicked for drill-down:', wardName, wardCode);

            // Show LSOAs for this ward
            this.showWardLSOAs(wardCode, boroughCode, wardName);

            // Auto-select this ward in the dropdown
            const wardSelect = document.querySelector(CONFIG.UI.SELECTORS.WARD_SELECT);
            if (wardSelect) {
                wardSelect.value = wardCode;
                wardSelect.dispatchEvent(new Event('change'));
            }

            // Prevent event bubbling
            e.originalEvent.stopPropagation();
        });

        // Add hover effects
        wardLayer.on('mouseover', () => {
            wardLayer.setStyle({
                weight: 3,
                fillOpacity: 0.4
            });
        });

        wardLayer.on('mouseout', () => {
            wardLayer.setStyle({
                weight: 2,
                fillOpacity: 0.2
            });
        });

        this.layers.currentWards.push(wardLayer);
    },

    /**
     * Get ward data from JSON structure
     */
    getWardDataFromJSON(boroughCode, wardCode) {
        try {
            return DataService.cache.londonData[boroughCode].wards[wardCode];
        } catch (error) {
            console.warn(`⚠️ Ward data not found: ${wardCode} in ${boroughCode}`);
            return null;
        }
    },

    /**
     * Show LSOAs within a selected ward (drill-down level 2)
     */
    showWardLSOAs(wardCode, boroughCode, wardName) {
        try {
            console.log(`🎯 Showing LSOAs for ward: ${wardName} (${wardCode})`);

            // Update current state
            this.currentLevel = 'ward';
            this.currentSelection.ward = wardCode;

            // Clear existing LSOA layers
            this.clearWardLayers();

            // Get LSOA codes for this ward
            const lsoaCodes = this.getLSOACodesForWard(boroughCode, wardCode);
            console.log(`📍 Found ${lsoaCodes.length} LSOAs for ward ${wardCode}:`, lsoaCodes);

            // Add LSOA boundaries
            this.addLSOABoundariesByCodes(lsoaCodes, boroughCode, wardCode);

            // Find and fit to ward bounds
            const wardFeature = this.findFeatureByCode(
                this.allWards,
                wardCode,
                ['WD24CD', 'WD21CD', 'WD22CD', 'code', 'WARD_CODE']
            );

            if (wardFeature) {
                this.fitToWardBounds(wardFeature);
            }

            // Set restricted view for LSOA level
            this.setFixedView(true);

        } catch (error) {
            console.error('❌ Error showing ward LSOAs:', error);
        }
    },

    /**
     * Fit map to borough bounds
     */
    fitToBoroughBounds(boroughCode) {
        // Find the borough feature and fit to its bounds
        if (this.layers.boroughs) {
            this.layers.boroughs.eachLayer(layer => {
                if (layer.feature && layer.feature.properties) {
                    const props = layer.feature.properties;
                    const featureBoroughCode = props.LAD22CD || props.LAD21CD || props.code || props.id;

                    if (featureBoroughCode === boroughCode) {
                        const bounds = layer.getBounds();
                        this.map.fitBounds(bounds, {
                            padding: [20, 20],
                            maxZoom: 12
                        });
                    }
                }
            });
        }
    },

    /**
     * Clear current ward layers (for borough drill-down)
     */
    clearCurrentWards() {
        this.layers.currentWards.forEach(layer => {
            this.map.removeLayer(layer);
        });
        this.layers.currentWards = [];
    },

    /**
     * Reset map to London view (drill-up to top level)
     */
    resetToLondon() {
        console.log('🔄 Resetting map to London view');

        // Update state
        this.currentLevel = 'london';
        this.currentSelection.borough = null;
        this.currentSelection.ward = null;

        // Clear all drill-down layers
        this.clearWardLayers();
        this.clearCurrentWards();

        // Enable full map interactions first
        this.setFixedView(false);

        // Reset view to London
        this.map.setView(CONFIG.MAP.DEFAULT_CENTER, CONFIG.MAP.DEFAULT_ZOOM);

        // Make sure borough boundaries are visible and properly styled
        if (this.layers.boroughs) {
            this.layers.boroughs.setStyle(CONFIG.MAP.STYLES.LONDON_BOROUGHS);
        }

        console.log('✅ Map reset to London view complete');
    },

    /**
     * Update map to show selected ward with LSOAs (called from UI dropdown)
     */
    showWard(wardCode, boroughCode) {
        try {
            console.log(`🎯 UI-triggered ward view: ${wardCode} in borough: ${boroughCode}`);

            // If we're not already showing the borough's wards, show them first
            if (this.currentLevel === 'london' || this.currentSelection.borough !== boroughCode) {
                this.showBoroughWards(boroughCode, '');
                // Small delay to let borough wards load, then show ward LSOAs
                setTimeout(() => {
                    this.showWardLSOAs(wardCode, boroughCode, '');
                }, 100);
            } else {
                // We're already at borough level, go directly to ward LSOAs
                this.showWardLSOAs(wardCode, boroughCode, '');
            }

        } catch (error) {
            console.error('❌ Error showing ward on map:', error);
            this.addMockWardGeometry(wardCode, boroughCode);
        }
    },

    /**
     * Get LSOA codes that belong to a specific ward from the JSON structure
     */
    getLSOACodesForWard(boroughCode, wardCode) {
        try {
            const borough = DataService.cache.londonData[boroughCode];
            if (!borough || !borough.wards || !borough.wards[wardCode]) {
                console.warn(`⚠️ Ward ${wardCode} not found in borough ${boroughCode}`);
                return [];
            }

            const ward = borough.wards[wardCode];
            if (!ward.lsoas) {
                console.warn(`⚠️ No LSOAs found for ward ${wardCode}`);
                return [];
            }

            return Object.keys(ward.lsoas);
        } catch (error) {
            console.error('❌ Error getting LSOA codes for ward:', error);
            return [];
        }
    },

    /**
     * Add LSOA boundaries for specific LSOA codes
     */
    addLSOABoundariesByCodes(lsoaCodes, boroughCode, wardCode) {
        if (!this.allLSOAs || !this.allLSOAs.features || lsoaCodes.length === 0) {
            console.warn('⚠️ No LSOA data available or no LSOA codes provided');
            return;
        }

        console.log(`🔍 Searching for LSOA boundaries matching codes:`, lsoaCodes);

        let foundCount = 0;
        lsoaCodes.forEach(lsoaCode => {
            // Find the corresponding LSOA boundary in the GeoParquet data
            const lsoaFeature = this.findFeatureByCode(
                this.allLSOAs,
                lsoaCode,
                ['LSOA21CD', 'LSOA11CD', 'code', 'LSOA_CODE']
            );

            if (lsoaFeature) {
                // Get LSOA metadata from JSON
                const lsoaData = this.getLSOADataFromJSON(boroughCode, wardCode, lsoaCode);
                this.addLSOABoundary(lsoaFeature, lsoaData);
                foundCount++;
            } else {
                console.warn(`⚠️ LSOA boundary not found for code: ${lsoaCode}`);
            }
        });

        console.log(`✅ Added ${foundCount}/${lsoaCodes.length} LSOA boundaries`);
    },

    /**
     * Get LSOA data from JSON structure
     */
    getLSOADataFromJSON(boroughCode, wardCode, lsoaCode) {
        try {
            const lsoaData = DataService.cache.londonData[boroughCode]
                .wards[wardCode]
                .lsoas[lsoaCode];

            return {
                code: lsoaCode,
                name: lsoaData.name || lsoaCode,
                hasPredictions: !!lsoaData.predictions,
                hasOfficerData: !!lsoaData.officer_assignments
            };
        } catch (error) {
            console.warn(`⚠️ LSOA data not found in JSON for: ${lsoaCode}`);
            return {
                code: lsoaCode,
                name: lsoaCode,
                hasPredictions: false,
                hasOfficerData: false
            };
        }
    },

    /**
     * Find a feature by code in GeoJSON data
     */
    findFeatureByCode(geoJSON, code, possibleCodeFields) {
        if (!geoJSON || !geoJSON.features) {
            console.warn('⚠️ No GeoJSON data available for feature search');
            return null;
        }

        const feature = geoJSON.features.find(feature => {
            const props = feature.properties;
            const found = possibleCodeFields.some(field => props[field] === code);
            if (found) {
                console.log(`✅ Found feature for code ${code} using field ${possibleCodeFields.find(field => props[field] === code)}`);
            }
            return found;
        });

        if (!feature) {
            console.warn(`⚠️ Feature not found for code: ${code}`);
            console.log('Available features sample:', geoJSON.features.slice(0, 3).map(f => f.properties));
        }

        return feature;
    },

    /**
     * Add ward boundary to the map
     */
    addWardBoundary(wardFeature, wardCode) {
        const wardName = wardFeature.properties.WD22NM || wardFeature.properties.name || wardCode;

        this.layers.currentWard = L.geoJSON(wardFeature, {
            style: CONFIG.MAP.STYLES.WARD_BOUNDARY
        }).addTo(this.map);

        // Add ward label
        this.layers.currentWard.bindTooltip(`Ward: ${wardName}`, {
            permanent: true,
            direction: 'center',
            className: 'ward-label'
        });

        console.log(`✅ Added ward boundary: ${wardName}`);
    },

    /**
     * Add individual LSOA boundary to the map
     */
    addLSOABoundary(lsoaFeature, lsoaData) {
        const lsoaName = lsoaFeature.properties.LSOA21NM || lsoaFeature.properties.name || lsoaData.name;

        const lsoaLayer = L.geoJSON(lsoaFeature, {
            style: {
                ...CONFIG.MAP.STYLES.LSOA_BOUNDARY,
                // Add some visual distinction based on data availability
                fillColor: lsoaData.hasPredictions ? 'lightblue' : 'lightgray',
                fillOpacity: lsoaData.hasPredictions ? 0.3 : 0.1
            }
        }).addTo(this.map);

        // Add tooltip with LSOA info
        lsoaLayer.bindTooltip(
            `<strong>${lsoaName}</strong><br>
             Code: ${lsoaData.code}<br>
             Predictions: ${lsoaData.hasPredictions ? '✅' : '❌'}<br>
             Officer Data: ${lsoaData.hasOfficerData ? '✅' : '❌'}`,
            {
                permanent: false,
                direction: 'center',
                className: 'lsoa-tooltip'
            }
        );

        // Add click handler for LSOA selection
        lsoaLayer.on('click', () => {
            console.log('🖱️ LSOA clicked:', lsoaData.code);
            // Auto-select this LSOA in the dropdown
            const lsoaSelect = document.querySelector(CONFIG.UI.SELECTORS.LSOA_SELECT);
            if (lsoaSelect) {
                lsoaSelect.value = lsoaData.code;
                lsoaSelect.dispatchEvent(new Event('change'));
            }
        });

        this.layers.currentLSOAs.push(lsoaLayer);
    },

    /**
     * Fit map view to ward bounds
     */
    fitToWardBounds(wardFeature) {
        if (wardFeature && wardFeature.geometry) {
            const layer = L.geoJSON(wardFeature);
            this.map.fitBounds(layer.getBounds(), {
                padding: [20, 20],
                maxZoom: CONFIG.MAP.WARD_ZOOM
            });
        }
    },

    /**
     * Highlight a specific LSOA on the map
     */
    highlightLSOA(lsoaCode) {
        console.log(`🎯 Highlighting LSOA: ${lsoaCode}`);

        // Reset all LSOA styles first
        this.layers.currentLSOAs.forEach(layer => {
            layer.setStyle(CONFIG.MAP.STYLES.LSOA_BOUNDARY);
        });

        // Find and highlight the selected LSOA
        let found = false;
        this.layers.currentLSOAs.forEach(layer => {
            layer.eachLayer(sublayer => {
                const feature = sublayer.feature;
                if (feature && feature.properties) {
                    const props = feature.properties;
                    const featureCode = props.LSOA21CD || props.LSOA11CD || props.code || props.LSOA_CODE;

                    if (featureCode === lsoaCode) {
                        sublayer.setStyle({
                            ...CONFIG.MAP.STYLES.LSOA_BOUNDARY,
                            color: 'orange',
                            weight: 3,
                            fillOpacity: 0.6,
                            fillColor: 'orange'
                        });

                        // Center the map on this LSOA
                        const bounds = sublayer.getBounds();
                        this.map.panTo(bounds.getCenter());

                        found = true;
                        console.log(`✅ Highlighted LSOA: ${lsoaCode}`);
                    }
                }
            });
        });

        if (!found) {
            console.warn(`⚠️ Could not find LSOA boundary to highlight: ${lsoaCode}`);
        }
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
     * Reset map to show all London boroughs (alias for resetToLondon)
     */
    showLondon() {
        this.resetToLondon();
    },

    /**
     * Clean up and remove all zoom controls to prevent duplicates
     */
    cleanupZoomControls() {
        try {
            // Remove any existing zoom controls
            this.map.eachLayer(function(layer) {
                if (layer instanceof L.Control.Zoom) {
                    this.map.removeControl(layer);
                }
            }.bind(this));

            // Also try to remove via the zoomControl property
            if (this.map.zoomControl) {
                try {
                    this.map.removeControl(this.map.zoomControl);
                    this.map.zoomControl = null;
                } catch (e) {
                    // Ignore errors if control already removed
                }
            }
        } catch (error) {
            console.warn('⚠️ Error cleaning zoom controls:', error);
        }
    },

    /**
     * Ensure single zoom control exists
     */
    ensureSingleZoomControl() {
        // Clean up any existing zoom controls first
        this.cleanupZoomControls();

        // Add a single new zoom control
        const zoomControl = L.control.zoom();
        this.map.addControl(zoomControl);
        this.map.zoomControl = zoomControl;
    },

    /**
     * Set map to fixed view (disable interactions) or enable interactions
     */
    setFixedView(fixed) {
        const options = CONFIG.MAP.WARD_VIEW_OPTIONS;

        if (fixed) {
            // Disable interactions for fixed ward view
            Object.keys(options).forEach(option => {
                if (options[option] === false && this.map[option]) {
                    this.map[option].disable();
                } else if (option === 'zoomControl') {
                    // Clean up all zoom controls
                    this.cleanupZoomControls();
                }
            });
        } else {
            // Enable interactions for London/borough view
            this.map.scrollWheelZoom.enable();
            this.map.dragging.enable();
            this.map.doubleClickZoom.enable();
            this.map.boxZoom.enable();
            this.map.keyboard.enable();

            // Ensure we have exactly one zoom control
            this.ensureSingleZoomControl();
        }
    },

    /**
     * Add mock ward geometry for demonstration (fallback)
     */
    addMockWardGeometry(wardCode, boroughCode) {
        console.log('📍 Using mock geometry for demonstration');

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
     * Add mock LSOA geometries within a ward (fallback)
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
     * Get mock center coordinates for a ward (fallback)
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
     * Add custom layer to map
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
     */
    removeLayer(name) {
        if (this.layers.custom && this.layers.custom[name]) {
            this.map.removeLayer(this.layers.custom[name]);
            delete this.layers.custom[name];
        }
    },

    /**
     * Get current map bounds
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
    },

    /**
     * Get map statistics
     */
    getStats() {
        return {
            boroughFeatures: this.layers.boroughs?.getLayers().length || 0,
            wardFeatures: this.layers.currentWard ? 1 : 0,
            lsoaFeatures: this.layers.currentLSOAs.length,
            hasGeographicalData: !!(this.allWards && this.allLSOAs)
        };
    }
};