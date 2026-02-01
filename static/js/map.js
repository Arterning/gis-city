// Initialize the map
const map = L.map('map').setView([28.2, 112.9], 8); // Default to Hunan, China

// Add OpenStreetMap tile layer
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '© OpenStreetMap contributors'
}).addTo(map);

// Store layer groups
const pointLayer = L.layerGroup().addTo(map);
const lineLayer = L.layerGroup().addTo(map);
const polygonLayer = L.layerGroup().addTo(map);

// Create a feature group for all editable layers
const drawnItems = new L.FeatureGroup();
map.addLayer(drawnItems);

// Store the current drawing layer temporarily
let currentDrawing = null;

// Color palette for polygons
const polygonColors = [
    '#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8',
    '#F7DC6F', '#BB8FCE', '#85C1E2', '#F8B739', '#52B788'
];

let colorIndex = 0;

/**
 * Create popup content for a feature
 */
function createPopupContent(feature) {
    const props = feature.properties;
    let html = `<div class="popup-content">`;
    html += `<h3>${props.name || 'Unnamed POI'}</h3>`;

    if (props.poi_type) {
        html += `<p><strong>Type:</strong> ${props.poi_type}</p>`;
    }

    if (props.address) {
        html += `<p><strong>Address:</strong> ${props.address}</p>`;
    }

    html += `<p><strong>ID:</strong> ${props.id}</p>`;
    html += `<p><strong>Geometry:</strong> ${props.geom_type}</p>`;

    if (props.properties && Object.keys(props.properties).length > 0) {
        html += `<div class="properties">`;
        html += `<strong>Additional Properties:</strong><br>`;
        html += `<pre>${JSON.stringify(props.properties, null, 2)}</pre>`;
        html += `</div>`;
    }

    html += `</div>`;
    return html;
}

/**
 * Get color for polygon
 */
function getPolygonColor() {
    const color = polygonColors[colorIndex % polygonColors.length];
    colorIndex++;
    return color;
}

/**
 * Style function for polygons
 */
function getPolygonStyle(feature) {
    const color = getPolygonColor();
    return {
        fillColor: color,
        fillOpacity: 0.5,
        color: color,
        weight: 2,
        opacity: 0.8
    };
}

/**
 * Load and display POIs on the map
 */
async function loadPOIs() {
    try {
        const response = await fetch('/api/pois');
        const geojson = await response.json();

        if (!geojson.features || geojson.features.length === 0) {
            document.getElementById('poi-count').textContent = 'No POIs found in database';
            return;
        }

        // Update POI count
        document.getElementById('poi-count').textContent =
            `Total POIs: ${geojson.features.length}`;

        // Separate points and polygons
        const points = [];
        const polygons = [];

        geojson.features.forEach(feature => {
            const geomType = feature.properties.geom_type;
            if (geomType === 'ST_Point') {
                points.push(feature);
            } else if (geomType === 'ST_LineString' || geomType === 'ST_MultiLineString') {
                // Add to a separate lines array
                const line = L.geoJSON(feature, {
                    style: {
                        color: '#00ff00',
                        weight: 4,
                        opacity: 0.8
                    }
                });
                line.bindPopup(createPopupContent(feature));
                line.addTo(lineLayer);

                // Add to drawnItems for editing
                line.eachLayer(layer => {
                    layer.feature = feature;
                    drawnItems.addLayer(layer);
                });
            } else {
                polygons.push(feature);
            }
        });

        // Add points
        points.forEach(feature => {
            const marker = L.geoJSON(feature, {
                pointToLayer: function(feature, latlng) {
                    return L.circleMarker(latlng, {
                        radius: 8,
                        fillColor: '#3388ff',
                        color: '#fff',
                        weight: 2,
                        opacity: 1,
                        fillOpacity: 0.8
                    });
                }
            });

            marker.bindPopup(createPopupContent(feature));
            marker.addTo(pointLayer);

            // Add to drawnItems for editing
            marker.eachLayer(layer => {
                layer.feature = feature;
                drawnItems.addLayer(layer);
            });
        });

        // Add polygons
        polygons.forEach(feature => {
            const polygon = L.geoJSON(feature, {
                style: getPolygonStyle
            });

            polygon.bindPopup(createPopupContent(feature));
            polygon.addTo(polygonLayer);

            // Add to drawnItems for editing
            polygon.eachLayer(layer => {
                layer.feature = feature;
                drawnItems.addLayer(layer);
            });
        });

        // Fit map to show all features
        const allLayers = L.featureGroup([pointLayer, lineLayer, polygonLayer]);
        if (allLayers.getBounds().isValid()) {
            map.fitBounds(allLayers.getBounds(), {
                padding: [50, 50]
            });
        }

        const lineCount = geojson.features.filter(f =>
            f.properties.geom_type === 'ST_LineString' ||
            f.properties.geom_type === 'ST_MultiLineString'
        ).length;

        console.log(`Loaded ${points.length} points, ${lineCount} lines, and ${polygons.length} polygons`);

    } catch (error) {
        console.error('Error loading POIs:', error);
        document.getElementById('poi-count').textContent = 'Error loading POIs';
    }
}

// Initialize the draw control
const drawControl = new L.Control.Draw({
    position: 'topleft',
    draw: {
        polyline: {
            shapeOptions: {
                color: '#00ff00',
                weight: 4
            }
        },
        polygon: {
            allowIntersection: false,
            shapeOptions: {
                color: '#ff8c00',
                fillOpacity: 0.5
            }
        },
        circle: false,
        rectangle: {
            shapeOptions: {
                color: '#ff8c00',
                fillOpacity: 0.5
            }
        },
        marker: true,
        circlemarker: {
            radius: 8,
            fillColor: '#3388ff',
            color: '#fff',
            weight: 2,
            opacity: 1,
            fillOpacity: 0.8
        }
    },
    edit: {
        featureGroup: drawnItems,
        remove: true
    }
});
map.addControl(drawControl);

// Handle draw created event
map.on(L.Draw.Event.CREATED, function (event) {
    const layer = event.layer;
    currentDrawing = layer;
    drawnItems.addLayer(layer);
    openModal();
});

// Handle draw deleted event
map.on(L.Draw.Event.DELETED, function (event) {
    const layers = event.layers;
    layers.eachLayer(function (layer) {
        if (layer.feature && layer.feature.properties.id) {
            deletePOI(layer.feature.properties.id);
        }
    });
});

/**
 * Open modal for POI creation
 */
function openModal() {
    document.getElementById('poi-modal').style.display = 'block';
    document.getElementById('poi-name').focus();
}

/**
 * Close modal
 */
function closeModal() {
    document.getElementById('poi-modal').style.display = 'none';
    document.getElementById('poi-form').reset();

    // Remove the temporary drawing if user cancels
    if (currentDrawing) {
        drawnItems.removeLayer(currentDrawing);
        currentDrawing = null;
    }
}

/**
 * Handle POI form submission
 */
document.getElementById('poi-form').addEventListener('submit', async function(e) {
    e.preventDefault();

    if (!currentDrawing) {
        alert('No geometry drawn');
        return;
    }

    // Get form data
    const name = document.getElementById('poi-name').value;
    const poiType = document.getElementById('poi-type').value;
    const address = document.getElementById('poi-address').value;
    const propertiesText = document.getElementById('poi-properties').value;

    // Parse properties JSON
    let properties = null;
    if (propertiesText.trim()) {
        try {
            properties = JSON.parse(propertiesText);
        } catch (e) {
            alert('Invalid JSON in properties field');
            return;
        }
    }

    // Convert Leaflet layer to GeoJSON
    const geojson = currentDrawing.toGeoJSON();

    // Create POI object
    const poi = {
        name: name,
        poi_type: poiType,
        address: address,
        geometry: geojson.geometry,
        properties: properties
    };

    // Save to backend
    try {
        const response = await fetch('/api/pois', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(poi)
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const result = await response.json();
        console.log('POI created:', result);

        // Close modal and reload POIs
        closeModal();
        currentDrawing = null;

        // Reload all POIs to show the new one
        clearLayers();
        await loadPOIs();

        alert('POI created successfully!');

    } catch (error) {
        console.error('Error creating POI:', error);
        alert('Failed to create POI: ' + error.message);
    }
});

/**
 * Delete POI from backend
 */
async function deletePOI(poiId) {
    if (!confirm('Are you sure you want to delete this POI?')) {
        return;
    }

    try {
        const response = await fetch(`/api/pois/${poiId}`, {
            method: 'DELETE'
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        console.log('POI deleted:', poiId);

        // Reload POIs
        clearLayers();
        await loadPOIs();

    } catch (error) {
        console.error('Error deleting POI:', error);
        alert('Failed to delete POI: ' + error.message);
    }
}

/**
 * Clear all layers
 */
function clearLayers() {
    pointLayer.clearLayers();
    lineLayer.clearLayers();
    polygonLayer.clearLayers();
    drawnItems.clearLayers();
    colorIndex = 0;
}

// Close modal when clicking outside
window.onclick = function(event) {
    const modal = document.getElementById('poi-modal');
    if (event.target === modal) {
        closeModal();
    }
}

// Load POIs when page loads
loadPOIs();

// Add zoom control position
map.zoomControl.setPosition('topleft');
