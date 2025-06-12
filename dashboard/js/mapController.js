// js/mapController.js - FINAL VERSION WITH BOROUGH HOVER HIGHLIGHTING

/**
 * Map Controller Module
 * Implements a fluid drill-down with persistent ward context and LSOA parent highlighting.
 */
const MapController = {
    map: null,
    layers: {
        boroughs: null,
        currentWards: [],
        currentLSOAs: [],
        allWards: null,
        allLSOAs: null
    },
    currentLevel: 'london',
    currentSelection: { borough: null, ward: null },

    init() {
        try {
            console.log('🗺️ Initializing map...');
            this.map = L.map('map', { center: CONFIG.MAP.DEFAULT_CENTER, zoom: CONFIG.MAP.DEFAULT_ZOOM });
            L.tileLayer(CONFIG.MAP.TILE_LAYER, { attribution: CONFIG.MAP.ATTRIBUTION, maxZoom: 18 }).addTo(this.map);
            this.loadGeographicalBoundaries();
            console.log('✅ Map initialized successfully');
        } catch (error) {
            console.error('❌ Error initializing map:', error);
            throw new Error(CONFIG.ERRORS.MAP_INIT_FAILED);
        }
    },

    loadGeographicalBoundaries() {
        const geoData = DataService.cache.geoData;
        if (!geoData) return console.warn('⚠️ No geographical data available');
        if (geoData.boroughs?.features?.length > 0) this.addBoroughBoundaries(geoData.boroughs);
        this.allWards = geoData.wards;
        this.allLSOAs = geoData.lsoas;
    },

    // <<< THE FIX IS HERE >>>
    addBoroughBoundaries(boroughsGeoJSON) {
        const jsonBoroughCodes = Object.keys(DataService.cache.londonData || {});
        const filteredFeatures = boroughsGeoJSON.features.filter(feature =>
            jsonBoroughCodes.includes(feature.properties.LAD22CD || feature.properties.LAD21CD)
        );
        if (filteredFeatures.length === 0) return;

        this.layers.boroughs = L.geoJSON({ type: "FeatureCollection", features: filteredFeatures }, {
            style: CONFIG.MAP.STYLES.LONDON_BOROUGHS,
            onEachFeature: (feature, layer) => {
                const props = feature.properties;
                const boroughCode = props.LAD22CD || props.LAD21CD;
                const boroughName = props.LAD22NM || props.LAD21NM;
                layer.bindTooltip(`<strong>${boroughName}</strong>`, { className: 'borough-tooltip', sticky: true });
                layer.on('click', () => UIController.selectBorough(boroughCode));

                // Add the mouseover event handler for boroughs
                layer.on('mouseover', function() {
                    this.setStyle({ weight: 3, fillOpacity: 0.3 });
                });

                // Add the mouseout event handler for boroughs
                layer.on('mouseout', function() {
                    this.setStyle(CONFIG.MAP.STYLES.LONDON_BOROUGHS);
                });
            }
        }).addTo(this.map);
    },

    showBoroughWards(boroughCode, boroughName) {
        this.currentLevel = 'borough';
        this.currentSelection = { borough: boroughCode, ward: null };
        this.clearAllDrillDownLayers();

        const wardCodes = Object.keys(DataService.cache.londonData[boroughCode]?.wards || {});
        this.addWardBoundariesForBorough(wardCodes, boroughCode);
        this.fitToBoroughBounds(boroughCode);
        this.setFixedView(false);
    },

    addWardBoundariesForBorough(wardCodes, boroughCode) {
        wardCodes.forEach(wardCode => {
            const wardFeature = this.findFeatureByCode(this.allWards, wardCode, ['WD24CD', 'WD21CD', 'WD22CD']);
            if (wardFeature) {
                const wardLayer = L.geoJSON(wardFeature, { style: CONFIG.MAP.STYLES.CLICKABLE_WARD_BOUNDARY });
                wardLayer.wardCode = wardCode;

                const wardName = wardFeature.properties.WD24NM || wardFeature.properties.WD22NM;
                wardLayer.bindTooltip(`<strong>${wardName}</strong><br><em>Click to view LSOAs</em>`, { className: 'ward-tooltip', sticky: true });
                wardLayer.on('click', e => {
                    UIController.selectWard(wardCode);
                    L.DomEvent.stopPropagation(e);
                });

                wardLayer.on('mouseover', function() {
                    if (MapController.currentSelection.ward !== this.wardCode) {
                        this.setStyle({ weight: 3, fillOpacity: 0.4 });
                    }
                });

                wardLayer.on('mouseout', function() {
                    if (MapController.currentSelection.ward === this.wardCode) {
                        if (UIController.state.selectedLSOA) {
                             this.setStyle(CONFIG.MAP.STYLES.LSOA_PARENT_WARD_BOUNDARY);
                        } else {
                             this.setStyle(CONFIG.MAP.STYLES.ACTIVE_WARD_BOUNDARY);
                        }
                    } else if (MapController.currentLevel === 'borough') {
                        this.setStyle(CONFIG.MAP.STYLES.CLICKABLE_WARD_BOUNDARY);
                    } else {
                        this.setStyle(CONFIG.MAP.STYLES.INACTIVE_WARD_BOUNDARY);
                    }
                });

                wardLayer.addTo(this.map);
                this.layers.currentWards.push(wardLayer);
            }
        });
    },

    showWardLSOAs(wardCode, boroughCode, wardName) {
        const isFirstDrillDown = this.currentLevel === 'borough';
        this.currentLevel = 'ward';
        this.currentSelection.ward = wardCode;
        this.currentSelection.borough = boroughCode;
        this.clearLSOALayers();

        UIController.state.selectedLSOA = null;

        this.layers.currentWards.forEach(wardLayer => {
            if (wardLayer.wardCode === wardCode) {
                wardLayer.setStyle(CONFIG.MAP.STYLES.ACTIVE_WARD_BOUNDARY);
                wardLayer.bringToFront();
            } else {
                wardLayer.setStyle(CONFIG.MAP.STYLES.INACTIVE_WARD_BOUNDARY);
            }
        });

        const lsoaCodes = Object.keys(DataService.cache.londonData[boroughCode]?.wards[wardCode]?.lsoas || {});
        this.addLSOABoundariesByCodes(lsoaCodes, boroughCode, wardCode);

        const activeWardFeature = this.findFeatureByCode(this.allWards, wardCode, ['WD24CD', 'WD21CD', 'WD22CD']);
        if (activeWardFeature) {
            this.panToWard(activeWardFeature, isFirstDrillDown);
        }
        this.setFixedView(true);
    },

    showWard(wardCode, boroughCode) {
        try {
            const needsBoroughSwitch = this.currentLevel === 'london' ||
                                      (this.currentSelection.borough && this.currentSelection.borough !== boroughCode);

            if (needsBoroughSwitch) {
                this.showBoroughWards(boroughCode, '');
                setTimeout(() => this.showWardLSOAs(wardCode, boroughCode, ''), 50);
            } else {
                this.showWardLSOAs(wardCode, boroughCode, '');
            }
        } catch (error) {
            console.error('❌ Error showing ward on map:', error);
        }
    },

    addLSOABoundariesByCodes(lsoaCodes, boroughCode, wardCode) {
        if (!this.allLSOAs || lsoaCodes.length === 0) return;
        lsoaCodes.forEach(lsoaCode => {
            const lsoaFeature = this.findFeatureByCode(this.allLSOAs, lsoaCode, ['LSOA21CD']);
            if (lsoaFeature) this.addLSOABoundary(lsoaFeature, lsoaCode, boroughCode, wardCode);
        });
    },

    addLSOABoundary(lsoaFeature, lsoaCode, boroughCode, wardCode) {
        const lsoaData = DataService.getLSOADataFromJSON(boroughCode, wardCode, lsoaCode);
        const style = { ...CONFIG.MAP.STYLES.LSOA_BOUNDARY, fillColor: lsoaData.hasPredictions ? '#004D40' : '#004D40' };
        const lsoaLayer = L.geoJSON(lsoaFeature, { style }).addTo(this.map);
        lsoaLayer.lsoaCode = lsoaCode;

        const lsoaName = lsoaFeature.properties.LSOA21NM || lsoaData.name;
        lsoaLayer.bindTooltip(`<strong>${lsoaName}</strong><br>Code: ${lsoaCode}`, { className: 'lsoa-tooltip', sticky: true });
        lsoaLayer.on('click', () => UIController.selectLSOA(lsoaCode));

        lsoaLayer.on('mouseover', function() {
            if (UIController.state.selectedLSOA !== this.lsoaCode) {
                 this.setStyle({ weight: 2, fillOpacity: 0.5 });
            }
        });

        lsoaLayer.on('mouseout', function() {
            if (UIController.state.selectedLSOA === this.lsoaCode) {
                this.setStyle(CONFIG.MAP.STYLES.HIGHLIGHTED_LSOA);
            } else {
                const originalLsoaData = UIController.getLSOADataForHighlight(this.lsoaCode);
                this.setStyle({ ...CONFIG.MAP.STYLES.LSOA_BOUNDARY, fillColor: originalLsoaData.hasPredictions ? '#004D40' : '#004D40' });
            }
        });

        this.layers.currentLSOAs.push(lsoaLayer);
    },

    highlightLSOA(lsoaCode) {
        const parentWardLayer = this.layers.currentWards.find(layer => layer.wardCode === this.currentSelection.ward);

        if (lsoaCode && parentWardLayer) {
            parentWardLayer.setStyle(CONFIG.MAP.STYLES.LSOA_PARENT_WARD_BOUNDARY);
        } else if (parentWardLayer) {
            parentWardLayer.setStyle(CONFIG.MAP.STYLES.ACTIVE_WARD_BOUNDARY);
        }

        this.layers.currentLSOAs.forEach(layer => layer.eachLayer(sub => {
            const code = sub.lsoaCode || sub.feature.properties.LSOA21CD;
            const lsoaData = UIController.getLSOADataForHighlight(code);
            const baseStyle = { ...CONFIG.MAP.STYLES.LSOA_BOUNDARY, fillColor: lsoaData.hasPredictions ? '#004D40' : '#004D40' };
            sub.setStyle(code === lsoaCode ? CONFIG.MAP.STYLES.HIGHLIGHTED_LSOA : baseStyle);
        }));
    },

    resetToLondon() {
        this.currentLevel = 'london';
        this.currentSelection = { borough: null, ward: null };
        this.clearAllDrillDownLayers();
        this.setFixedView(false);
        this.map.setView(CONFIG.MAP.DEFAULT_CENTER, CONFIG.MAP.DEFAULT_ZOOM);
    },

    clearLSOALayers() {
        this.layers.currentLSOAs.forEach(layer => this.map.removeLayer(layer));
        this.layers.currentLSOAs = [];
    },

    clearAllDrillDownLayers() {
        this.clearLSOALayers();
        this.layers.currentWards.forEach(layer => this.map.removeLayer(layer));
        this.layers.currentWards = [];
    },

    setFixedView(fixed) {
        if (fixed) {
            // At LSOA level - enable movement but set bounds
            if (this.currentLevel === 'ward' && this.currentSelection.ward) {
                // Get the ward bounds to restrict movement
                const wardFeature = this.findFeatureByCode(this.allWards, this.currentSelection.ward, ['WD24CD', 'WD21CD', 'WD22CD']);
                if (wardFeature) {
                    const wardBounds = L.geoJSON(wardFeature).getBounds();
                    // Extend bounds slightly for better UX
                    const extendedBounds = wardBounds.pad(0.2); // 20% padding

                    // Set max bounds to restrict panning
                    this.map.setMaxBounds(extendedBounds);

                    // Enable dragging but keep other restrictions
                    this.map.dragging.enable();
                    this.map.scrollWheelZoom.disable();
                    this.map.doubleClickZoom.disable();
                    this.map.boxZoom.disable();
                    this.map.keyboard.disable();

                    // Keep zoom control removed
                    if (this.map.zoomControl) {
                        this.map.removeControl(this.map.zoomControl);
                        this.map.zoomControl = null;
                    }
                }
            }
        } else {
            // Remove all restrictions
            this.map.setMaxBounds(null);

            // Re-enable all interactions
            Object.keys(CONFIG.MAP.WARD_VIEW_OPTIONS).forEach(option => {
                if (this.map[option]) this.map[option].enable();
            });

            // Re-add zoom control
            if (!this.map.zoomControl) {
                this.map.zoomControl = L.control.zoom().addTo(this.map);
            }
        }
    },

    findFeatureByCode(geoJSON, code, fields) {
        return geoJSON?.features.find(f => fields.some(field => f.properties[field] === code));
    },

    fitToBoroughBounds(boroughCode) {
        this.layers.boroughs.eachLayer(layer => {
            const props = layer.feature.properties;
            if ((props.LAD22CD || props.LAD21CD) === boroughCode) {
                this.map.fitBounds(layer.getBounds(), { padding: [20, 20], maxZoom: 12, animate: true, duration: 0.4 });
            }
        });
    },

    panToWard(wardFeature, isFirstDrillDown) {
        const layer = L.geoJSON(wardFeature);
        const bounds = layer.getBounds();

        if (isFirstDrillDown) {
            this.map.fitBounds(bounds, { padding: [30, 30], maxZoom: CONFIG.MAP.WARD_ZOOM, animate: true, duration: 0.4 });
        } else {
            this.map.panTo(bounds.getCenter(), { animate: true, duration: 0.4 });
        }
    },

    showLondon() {
        this.resetToLondon();
    },

    resize() {
        if (this.map) this.map.invalidateSize();
    }
};