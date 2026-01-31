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
        POI object or None if not found
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
                "properties": result.properties
            }
        return None

    finally:
        db.close()


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

    print("Searching for containing POI...")
    poi = find_containing_poi(lat, lon)

    if poi:
        print("Found POI:")
        print(f"  Name: {poi['name']}")
        if poi['poi_type']:
            print(f"  Type: {poi['poi_type']}")
        if poi['address']:
            print(f"  Address: {poi['address']}")
        if poi['properties']:
            print(f"  Properties: {poi['properties']}")
    else:
        print("No POI found containing this location.")
        print("The point may be outside all POI boundaries.")


if __name__ == "__main__":
    main()
