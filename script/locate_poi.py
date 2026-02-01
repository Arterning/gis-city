"""Query which POI contains the current IP location."""
import sys
import requests
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from geoalchemy2.functions import ST_Contains
from database import SessionLocal
from models import POI


def get_current_location():
    """
    Get current location from IP using ipinfo.io API.

    Returns:
        tuple: (latitude, longitude) or None if failed
    """
    try:
        response = requests.get("https://ipinfo.io/json", timeout=5)
        response.raise_for_status()
        data = response.json()

        # ipinfo.io returns loc as "latitude,longitude"
        if "loc" in data:
            lat, lon = data["loc"].split(",")
            return float(lat), float(lon)
        else:
            print(f"Warning: No location data in response: {data}")
            return None

    except Exception as e:
        print(f"Error fetching location from ipinfo.io: {e}")
        return None


def find_containing_poi(latitude: float, longitude: float):
    """
    Find POI that contains the given point.

    Args:
        latitude: Latitude (WGS84)
        longitude: Longitude (WGS84)

    Returns:
        dict: POI info with distance=0, or None if not found
    """
    db = SessionLocal()
    try:
        # Create point geometry in WKT format
        point_wkt = f"POINT({longitude} {latitude})"

        # Query using ST_Contains to find which POI polygon contains this point
        # ST_Contains(geom, point) returns true if geom contains point
        query = text("""
            SELECT id, name, poi_type, address,
                   ST_AsText(geom) as geom_text,
                   properties
            FROM poi
            WHERE ST_Contains(geom, ST_GeomFromText(:point, 4326))
            LIMIT 1
        """)

        result = db.execute(query, {"point": point_wkt}).fetchone()

        if result:
            return {
                "id": result.id,
                "name": result.name,
                "poi_type": result.poi_type,
                "address": result.address,
                "properties": result.properties,
                "distance": 0.0,
                "contained": True
            }
        return None

    finally:
        db.close()


def find_nearest_poi(latitude: float, longitude: float):
    """
    Find the nearest POI to the given point.

    Args:
        latitude: Latitude (WGS84)
        longitude: Longitude (WGS84)

    Returns:
        dict: POI info with distance in meters, or None if no POI found
    """
    db = SessionLocal()
    try:
        # Create point geometry in WKT format
        point_wkt = f"POINT({longitude} {latitude})"

        # Query using ST_Distance to find nearest POI
        # ST_Distance returns distance in degrees, use geography cast for meters
        # Or use ST_Distance_Sphere for approximate distance in meters
        query = text("""
            SELECT id, name, poi_type, address,
                   ST_AsText(geom) as geom_text,
                   properties,
                   ST_Distance(
                       geom::geography,
                       ST_GeomFromText(:point, 4326)::geography
                   ) as distance
            FROM poi
            ORDER BY geom::geography <-> ST_GeomFromText(:point, 4326)::geography
            LIMIT 1
        """)

        result = db.execute(query, {"point": point_wkt}).fetchone()

        if result:
            return {
                "id": result.id,
                "name": result.name,
                "poi_type": result.poi_type,
                "address": result.address,
                "properties": result.properties,
                "distance": result.distance,  # in meters
                "contained": False
            }
        return None

    finally:
        db.close()


def format_distance(distance_meters: float) -> str:
    """Format distance for display."""
    if distance_meters < 1000:
        return f"{distance_meters:.2f} meters"
    else:
        return f"{distance_meters / 1000:.2f} kilometers"


def main():
    """Main entry point."""
    print("Fetching current location from IP...")

    location = get_current_location()

    if not location:
        print("Failed to get current location.")
        sys.exit(1)

    lat, lon = location
    print(f"Current location: {lat}, {lon}")
    print()

    # First, try to find POI that contains the point
    print("Searching for containing POI...")
    poi = find_containing_poi(lat, lon)

    if poi:
        print("✓ Found containing POI:")
        print(f"  Name: {poi['name']}")
        if poi['poi_type']:
            print(f"  Type: {poi['poi_type']}")
        if poi['address']:
            print(f"  Address: {poi['address']}")
        if poi['properties']:
            print(f"  Properties: {poi['properties']}")
        print(f"  Status: Inside this area")
    else:
        # If not contained in any POI, find the nearest one
        print("Not inside any POI. Searching for nearest POI...")
        poi = find_nearest_poi(lat, lon)

        if poi:
            print("✓ Found nearest POI:")
            print(f"  Name: {poi['name']}")
            if poi['poi_type']:
                print(f"  Type: {poi['poi_type']}")
            if poi['address']:
                print(f"  Address: {poi['address']}")
            if poi['properties']:
                print(f"  Properties: {poi['properties']}")
            print(f"  Distance: {format_distance(poi['distance'])}")
        else:
            print("No POI found in database.")


if __name__ == "__main__":
    main()
