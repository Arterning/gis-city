"""Flask application for POI map visualization."""
from flask import Flask, render_template, jsonify
from sqlalchemy import text
from database import SessionLocal
from models import POI
import json

app = Flask(__name__)


@app.route('/')
def index():
    """Render main map page."""
    return render_template('map.html')


@app.route('/api/pois')
def get_pois():
    """
    Get all POIs as GeoJSON.

    Returns:
        GeoJSON FeatureCollection with all POIs
    """
    db = SessionLocal()
    try:
        # Query all POIs with geometry as GeoJSON
        query = text("""
            SELECT
                id,
                name,
                poi_type,
                address,
                properties,
                ST_AsGeoJSON(geom) as geometry,
                ST_GeometryType(geom) as geom_type
            FROM poi
        """)

        results = db.execute(query).fetchall()

        # Build GeoJSON FeatureCollection
        features = []
        for row in results:
            feature = {
                "type": "Feature",
                "geometry": json.loads(row.geometry),
                "properties": {
                    "id": row.id,
                    "name": row.name,
                    "poi_type": row.poi_type,
                    "address": row.address,
                    "geom_type": row.geom_type,
                    "properties": row.properties
                }
            }
            features.append(feature)

        geojson = {
            "type": "FeatureCollection",
            "features": features
        }

        return jsonify(geojson)

    finally:
        db.close()


@app.route('/api/pois/<int:poi_id>')
def get_poi(poi_id):
    """
    Get a single POI by ID.

    Args:
        poi_id: POI ID

    Returns:
        GeoJSON Feature
    """
    db = SessionLocal()
    try:
        query = text("""
            SELECT
                id,
                name,
                poi_type,
                address,
                properties,
                ST_AsGeoJSON(geom) as geometry,
                ST_GeometryType(geom) as geom_type
            FROM poi
            WHERE id = :poi_id
        """)

        row = db.execute(query, {"poi_id": poi_id}).fetchone()

        if not row:
            return jsonify({"error": "POI not found"}), 404

        feature = {
            "type": "Feature",
            "geometry": json.loads(row.geometry),
            "properties": {
                "id": row.id,
                "name": row.name,
                "poi_type": row.poi_type,
                "address": row.address,
                "geom_type": row.geom_type,
                "properties": row.properties
            }
        }

        return jsonify(feature)

    finally:
        db.close()


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
