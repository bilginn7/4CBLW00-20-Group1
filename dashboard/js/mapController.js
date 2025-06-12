/**
 * Map Controller Module with Burglary Location Markers
 * Implements a fluid drill-down with persistent ward context and LSOA parent highlighting.
 */
const MapController = {
    map: null,
    layers: {
        boroughs: null,
        currentWards: [],
        currentLSOAs: [],
        allWards: null,
        allLSOAs: null,
        burglaryMarkers: null
    },
    currentLevel: 'london',
    currentSelection: { borough: null, ward: null },
    currentDateFilter: { start: null, end: null },
    highlightedLSOA: null,
    lsoaInitialZoom: null,
    zoomEndHandler: null,

    init() {
        try {
            console.log('🗺️ Initializing map...');
            this.map = L.map('map', { center: CONFIG.MAP.DEFAULT_CENTER, zoom: CONFIG.MAP.DEFAULT_ZOOM });
            L.tileLayer(CONFIG.MAP.TILE_LAYER, { attribution: CONFIG.MAP.ATTRIBUTION, maxZoom: 18 }).addTo(this.map);

            this.layers.burglaryMarkers = L.layerGroup().addTo(this.map);

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
        this.clearBurglaryMarkers();

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
        this.clearBurglaryMarkers();

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
        const tooltipText = `<strong>${lsoaName}</strong><br>Code: ${lsoaCode}`;

        lsoaLayer.bindTooltip(tooltipText, { className: 'lsoa-tooltip', sticky: true });
        lsoaLayer.on('click', () => UIController.selectLSOA(lsoaCode));

        lsoaLayer.on('mouseover', function() {
            if (UIController.state.selectedLSOA !== this.lsoaCode) {
                 this.setStyle({ weight: 2, fillOpacity: 0.5 });
            }
        });

        lsoaLayer.on('mouseout', function() {
            if (UIController.state.selectedLSOA === this.lsoaCode) {
                // If this is the highlighted LSOA, we need to check if zoom-based opacity is active
                if (MapController.highlightedLSOA === this.lsoaCode && MapController.zoomEndHandler) {
                    // Trigger the zoom handler to reapply the correct opacity
                    MapController.zoomEndHandler();
                } else {
                    // Otherwise, just apply the standard highlighted style
                    this.setStyle(CONFIG.MAP.STYLES.HIGHLIGHTED_LSOA);
                }
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
        this.highlightedLSOA = lsoaCode;

        this.layers.currentLSOAs.forEach(layer => layer.eachLayer(sub => {
            const code = sub.lsoaCode || sub.feature.properties.LSOA21CD;
            const lsoaData = UIController.getLSOADataForHighlight(code);
            const baseStyle = { ...CONFIG.MAP.STYLES.LSOA_BOUNDARY, fillColor: lsoaData.hasPredictions ? '#004D40' : '#004D40' };
            sub.setStyle(code === lsoaCode ? CONFIG.MAP.STYLES.HIGHLIGHTED_LSOA : baseStyle);
        }));

        if (lsoaCode) {
            this.fitToLSOAWithZoomControl(lsoaCode, this.currentSelection.borough, this.currentSelection.ward);
            this.setupZoomBasedOpacity();
        }
    },

    addBurglaryMarkers(boroughCode, wardCode, lsoaCode, startDate = null, endDate = null) {
        this.clearBurglaryMarkers();

        const burglaryLocations = DataService.getBurglaryLocations(boroughCode, wardCode, lsoaCode, startDate, endDate);

        if (burglaryLocations.length === 0) {
            console.log('No burglary locations found for the selected area and date range');
            return;
        }

        // Group by location to handle overlaps
        const locationGroups = {};
        burglaryLocations.forEach(burglary => {
            const locationKey = `${burglary.latitude.toFixed(6)},${burglary.longitude.toFixed(6)}`;
            if (!locationGroups[locationKey]) {
                locationGroups[locationKey] = [];
            }
            locationGroups[locationKey].push(burglary);
        });

        console.log(`Adding ${burglaryLocations.length} burglary markers (${Object.keys(locationGroups).length} unique locations)`);

        Object.entries(locationGroups).forEach(([locationKey, burglaries]) => {
            const [baseLat, baseLng] = locationKey.split(',').map(Number);

            burglaries.forEach((burglary, index) => {
                // Calculate spiral offset for multiple markers at same location
                let offsetLat = baseLat;
                let offsetLng = baseLng;

                if (index > 0) {
                    // Growing radius based on number of markers
                    const baseRadius = 0.00003;
                    const radiusGrowth = 0.00001 * Math.floor(index / 10); // Grow every 5 markers
                    const radius = baseRadius + radiusGrowth;

                    // Random angle
                    const angle = Math.random() * 2 * Math.PI;

                    offsetLat = baseLat + (radius * Math.cos(angle));
                    offsetLng = baseLng + (radius * Math.sin(angle));
                }

                // Vary marker appearance slightly for stacked markers
                const isStacked = index > 0;
                const marker = L.circleMarker([offsetLat, offsetLng], {
                    ...CONFIG.MAP.STYLES.BURGLARY_MARKER,
                    radius: isStacked ? CONFIG.MAP.STYLES.BURGLARY_MARKER.radius - 1 : CONFIG.MAP.STYLES.BURGLARY_MARKER.radius,
                    fillOpacity: isStacked ? 0.6 : CONFIG.MAP.STYLES.BURGLARY_MARKER.fillOpacity,
                    weight: isStacked ? 0.5 : CONFIG.MAP.STYLES.BURGLARY_MARKER.weight
                });

                const tooltipText = burglaries.length > 1
                    ? `<strong>Burglary (${index + 1}/${burglaries.length})</strong><br><strong>Date:</strong>${burglary.month}<br><br><strong>Geolocation:</strong>(${burglary.longitude.toFixed(5)}, ${burglary.latitude.toFixed(5)})`
                    : `<strong>Burglary</strong><br><strong>Date:</strong>${burglary.month}<br><br><strong>Geolocation:</strong>(${burglary.longitude.toFixed(5)}, ${burglary.latitude.toFixed(5)})`;

                marker.bindTooltip(tooltipText, {
                    className: 'burglary-tooltip',
                    sticky: true
                });

                this.layers.burglaryMarkers.addLayer(marker);
            });
        });
    },

    // Clear burglary markers
    clearBurglaryMarkers() {
        if (this.layers.burglaryMarkers) {
            this.layers.burglaryMarkers.clearLayers();
        }
    },

    // Update burglary markers based on date filter
    updateBurglaryMarkersForDateFilter(startDate = null, endDate = null) {
        this.currentDateFilter = { start: startDate, end: endDate };

        if (this.currentSelection.borough && this.currentSelection.ward && UIController.state.selectedLSOA) {
            this.addBurglaryMarkers(
                this.currentSelection.borough,
                this.currentSelection.ward,
                UIController.state.selectedLSOA,
                startDate,
                endDate
            );
        }
    },

    resetToLondon() {
        this.currentLevel = 'london';
        this.currentSelection = { borough: null, ward: null };
        this.currentDateFilter = { start: null, end: null };
        this.highlightedLSOA = null;
        this.lsoaInitialZoom = null;

        // Remove zoom event handler
        if (this.zoomEndHandler) {
            this.map.off('zoomend', this.zoomEndHandler);
            this.zoomEndHandler = null;
        }
        this.clearAllDrillDownLayers();
        this.clearBurglaryMarkers();
        this.setFixedView(false);
        this.map.setView(CONFIG.MAP.DEFAULT_CENTER, CONFIG.MAP.DEFAULT_ZOOM);
    },

    clearLSOALayers() {
        this.layers.currentLSOAs.forEach(layer => this.map.removeLayer(layer));
        this.layers.currentLSOAs = [];
        this.clearBurglaryMarkers();
        // Clear zoom-based opacity handling
        this.highlightedLSOA = null;
        this.lsoaInitialZoom = null;
        if (this.zoomEndHandler) {
            this.map.off('zoomend', this.zoomEndHandler);
            this.zoomEndHandler = null;
        }
    },

    clearAllDrillDownLayers() {
        this.clearLSOALayers();
        this.layers.currentWards.forEach(layer => this.map.removeLayer(layer));
        this.layers.currentWards = [];
    },

    setFixedView(fixed) {
        if (fixed) {
            // At LSOA level - enable zooming within LSOA bounds
            if (this.currentLevel === 'ward' && this.currentSelection.ward) {
                // Get the ward bounds to restrict movement and set zoom limits
                const wardFeature = this.findFeatureByCode(this.allWards, this.currentSelection.ward, ['WD24CD', 'WD21CD', 'WD22CD']);
                if (wardFeature) {
                    const wardBounds = L.geoJSON(wardFeature).getBounds();
                    // Extend bounds slightly for better UX
                    const extendedBounds = wardBounds.pad(0.2); // 20% padding

                    // Set max bounds to restrict panning
                    this.map.setMaxBounds(extendedBounds);

                    // NEW: Enable zooming but with limits
                    this.map.dragging.enable();
                    this.map.scrollWheelZoom.enable(); // Enable scroll wheel zoom
                    this.map.doubleClickZoom.enable(); // Enable double click zoom
                    this.map.boxZoom.enable(); // Enable box zoom
                    this.map.keyboard.enable(); // Enable keyboard navigation

                    // Set zoom limits - allow zooming in to see details, but limit zoom out
                    const currentZoom = this.map.getZoom();
                    const minZoom = Math.max(currentZoom - 1, CONFIG.MAP.WARD_ZOOM); // Can't zoom out much from current level
                    const maxZoom = 20; // Allow deep zoom to see burglary details

                    this.map.setMinZoom(minZoom);
                    this.map.setMaxZoom(maxZoom);

                    // Re-add zoom control for LSOA level
                    if (!this.map.zoomControl) {
                        this.map.zoomControl = L.control.zoom({
                            position: 'topright' // Move to top-right so it doesn't interfere
                        }).addTo(this.map);
                    }

                    console.log(`🔍 LSOA zoom enabled: min=${minZoom}, max=${maxZoom}, current=${currentZoom}`);
                }
            }
        } else {
            // Remove all restrictions when not at LSOA level
            this.map.setMaxBounds(null);
            this.map.setMinZoom(1); // Reset to default
            this.map.setMaxZoom(18); // Reset to default

            // Re-enable all interactions
            Object.keys(CONFIG.MAP.WARD_VIEW_OPTIONS).forEach(option => {
                if (this.map[option]) this.map[option].enable();
            });

            // Re-add zoom control in default position
            if (!this.map.zoomControl) {
                this.map.zoomControl = L.control.zoom().addTo(this.map);
            }
            console.log('🔍 Map restrictions removed, full zoom range restored');
        }
    },

    fitToLSOAWithZoomControl(lsoaCode, boroughCode, wardCode) {
        // Find the specific LSOA bounds for better initial zoom
        const lsoaFeature = this.findFeatureByCode(this.allLSOAs, lsoaCode, ['LSOA21CD']);
        if (lsoaFeature) {
            const lsoaBounds = L.geoJSON(lsoaFeature).getBounds();

            // Fit to LSOA bounds with some padding, but don't zoom too close initially
            this.map.fitBounds(lsoaBounds, {
                padding: [20, 20],
                maxZoom: CONFIG.MAP.WARD_ZOOM + 1, // Slightly closer than ward level
                animate: true,
                duration: 0.5
            });
            this.lsoaInitialZoom = this.map.getZoom();
            console.log(`🎯 Fitted map to LSOA: ${lsoaCode}`);
        }
    },

    setupZoomBasedOpacity() {
        // Remove any existing zoom end listener
        if (this.zoomEndHandler) {
            this.map.off('zoomend', this.zoomEndHandler);
        }

        // Create new zoom end handler
        this.zoomEndHandler = () => {
            if (!this.highlightedLSOA) return;

            const currentZoom = this.map.getZoom();
            const minZoom = this.map.getMinZoom();
            const maxZoom = this.map.getMaxZoom();
            const initialZoom = this.lsoaInitialZoom || CONFIG.MAP.WARD_ZOOM;

            // Calculate opacity based on zoom level
            // At initial zoom (or min zoom), opacity should be the original value (0.6)
            // As we zoom in, opacity decreases to a minimum of 0.2
            const zoomRange = maxZoom - initialZoom;
            const currentZoomOffset = Math.max(0, currentZoom - initialZoom);
            const zoomRatio = currentZoomOffset / zoomRange;

            // Original opacity is 0.6, minimum is 0.2
            const originalOpacity = CONFIG.MAP.STYLES.HIGHLIGHTED_LSOA.fillOpacity;
            const minOpacity = 0.05;
            const opacity = originalOpacity - (zoomRatio * (originalOpacity - minOpacity));

            // Update the highlighted LSOA's opacity
            this.layers.currentLSOAs.forEach(layer => layer.eachLayer(sub => {
                const code = sub.lsoaCode || sub.feature.properties.LSOA21CD;
                if (code === this.highlightedLSOA) {
                    sub.setStyle({
                        ...CONFIG.MAP.STYLES.HIGHLIGHTED_LSOA,
                        fillOpacity: opacity
                    });
                }
            }));

            console.log(`🔍 Zoom: ${currentZoom.toFixed(1)}, Opacity: ${opacity.toFixed(2)}`);
        };

        // Attach the handler
        this.map.on('zoomend', this.zoomEndHandler);
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