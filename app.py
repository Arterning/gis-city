"""Flask application for POI map visualization."""
from flask import Flask, render_template, jsonify, request
from sqlalchemy import text
from geoalchemy2.shape import from_shape
from shapely.geometry import shape
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


@app.route('/api/pois', methods=['POST'])
def create_poi():
    """
    Create a new POI.

    Request body:
        {
            "name": "POI name",
            "poi_type": "POI type",
            "address": "Address",
            "geometry": GeoJSON geometry object,
            "properties": {...}
        }

    Returns:
        Created POI as GeoJSON Feature
    """
    db = SessionLocal()
    try:
        data = request.get_json()

        # Validate required fields
        if not data.get('name'):
            return jsonify({"error": "Name is required"}), 400

        if not data.get('geometry'):
            return jsonify({"error": "Geometry is required"}), 400

        # Convert GeoJSON geometry to Shapely geometry
        try:
            shapely_geom = shape(data['geometry'])
        except Exception as e:
            return jsonify({"error": f"Invalid geometry: {str(e)}"}), 400

        # Create POI object
        poi = POI(
            name=data['name'],
            poi_type=data.get('poi_type'),
            address=data.get('address'),
            geom=from_shape(shapely_geom, srid=4326),
            properties=data.get('properties')
        )

        db.add(poi)
        db.commit()
        db.refresh(poi)

        # Return created POI as GeoJSON
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

        row = db.execute(query, {"poi_id": poi.id}).fetchone()

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

        return jsonify(feature), 201

    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500

    finally:
        db.close()


@app.route('/api/pois/<int:poi_id>', methods=['DELETE'])
def delete_poi(poi_id):
    """
    Delete a POI by ID.

    Args:
        poi_id: POI ID

    Returns:
        Success message
    """
    db = SessionLocal()
    try:
        poi = db.query(POI).filter(POI.id == poi_id).first()

        if not poi:
            return jsonify({"error": "POI not found"}), 404

        db.delete(poi)
        db.commit()

        return jsonify({"message": "POI deleted successfully"}), 200

    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500

    finally:
        db.close()


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
