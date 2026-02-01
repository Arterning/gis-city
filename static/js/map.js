// Initialize the map
const map = L.map('map').setView([28.2, 112.9], 8); // Default to Hunan, China

// Add OpenStreetMap tile layer
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '© OpenStreetMap contributors'
}).addTo(map);

// Store layer groups
const pointLayer = L.layerGroup().addTo(map);
const polygonLayer = L.layerGroup().addTo(map);

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
        });

        // Add polygons
        polygons.forEach(feature => {
            const polygon = L.geoJSON(feature, {
                style: getPolygonStyle
            });

            polygon.bindPopup(createPopupContent(feature));
            polygon.addTo(polygonLayer);
        });

        // Fit map to show all features
        const allLayers = L.featureGroup([pointLayer, polygonLayer]);
        if (allLayers.getBounds().isValid()) {
            map.fitBounds(allLayers.getBounds(), {
                padding: [50, 50]
            });
        }

        console.log(`Loaded ${points.length} points and ${polygons.length} polygons`);

    } catch (error) {
        console.error('Error loading POIs:', error);
        document.getElementById('poi-count').textContent = 'Error loading POIs';
    }
}

// Load POIs when page loads
loadPOIs();

// Add zoom control position
map.zoomControl.setPosition('topleft');
