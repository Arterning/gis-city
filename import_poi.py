"""POI data import script for GeoJSON and Shapefile formats."""
import argparse
import sys
from pathlib import Path
import geopandas as gpd
from sqlalchemy.orm import Session
from geoalchemy2.shape import from_shape
from shapely.geometry import Point
from database import SessionLocal, init_db
from models import POI


def read_geodata(file_path: str) -> gpd.GeoDataFrame:
    """
    Read geospatial data from file.

    Supports:
    - GeoJSON (.geojson, .json)
    - Shapefile (.shp)

    Args:
        file_path: Path to the geospatial file

    Returns:
        GeoDataFrame containing the data
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    suffix = path.suffix.lower()

    if suffix in ['.geojson', '.json']:
        print(f"Reading GeoJSON file: {file_path}")
        gdf = gpd.read_file(file_path, driver='GeoJSON')
    elif suffix == '.shp':
        print(f"Reading Shapefile: {file_path}")
        gdf = gpd.read_file(file_path)
    else:
        raise ValueError(f"Unsupported file format: {suffix}. Supported formats: .geojson, .json, .shp")

    # Ensure CRS is WGS84 (EPSG:4326)
    if gdf.crs is None:
        print("Warning: No CRS defined, assuming EPSG:4326 (WGS84)")
        gdf = gdf.set_crs("EPSG:4326")
    elif gdf.crs.to_epsg() != 4326:
        print(f"Reprojecting from {gdf.crs} to EPSG:4326 (WGS84)")
        gdf = gdf.to_crs("EPSG:4326")

    return gdf


def extract_poi_fields(row, field_mapping: dict = None) -> dict:
    """
    Extract POI fields from a GeoDataFrame row.

    Args:
        row: GeoDataFrame row
        field_mapping: Optional mapping of source fields to POI fields
                      e.g., {'name_field': 'name', 'type_field': 'poi_type'}

    Returns:
        Dictionary with POI fields
    """
    if field_mapping is None:
        field_mapping = {}

    # Default field names
    name_field = field_mapping.get('name', 'name')
    type_field = field_mapping.get('poi_type', 'type')
    address_field = field_mapping.get('address', 'address')

    # Extract basic fields
    poi_data = {
        'name': row.get(name_field, 'Unnamed POI'),
        'poi_type': row.get(type_field),
        'address': row.get(address_field),
    }

    # Extract custom properties (all other fields except geometry and basic fields)
    excluded_fields = {'geometry', name_field, type_field, address_field}
    properties = {}

    for key, value in row.items():
        if key not in excluded_fields and value is not None:
            # Convert to JSON-serializable types
            if hasattr(value, 'item'):  # numpy types
                value = value.item()
            properties[key] = value

    poi_data['properties'] = properties if properties else None

    return poi_data


def import_poi_data(
    file_path: str,
    field_mapping: dict = None,
    batch_size: int = 1000,
    skip_invalid: bool = True
) -> dict:
    """
    Import POI data from GeoJSON or Shapefile into PostGIS database.

    Args:
        file_path: Path to the geospatial file
        field_mapping: Optional mapping of source fields to POI fields
        batch_size: Number of records to insert in each batch
        skip_invalid: Skip invalid geometries instead of raising error

    Returns:
        Dictionary with import statistics
    """
    # Read geospatial data
    gdf = read_geodata(file_path)

    print(f"\nData summary:")
    print(f"  Total records: {len(gdf)}")
    print(f"  Geometry types: {', '.join(gdf.geom_type.unique())}")
    print(f"  CRS: {gdf.crs}")
    print(f"  Columns: {', '.join(gdf.columns)}")

    if len(gdf) == 0:
        print("Error: No geometries found in the file.")
        return {'success': 0, 'failed': 0, 'skipped': 0}

    # Start import
    db: Session = SessionLocal()
    stats = {'success': 0, 'failed': 0, 'skipped': 0}
    batch = []

    try:
        for idx, row in gdf.iterrows():
            try:
                # Extract POI fields
                poi_data = extract_poi_fields(row, field_mapping)

                # Get geometry
                geom = row.geometry
                if geom is None or geom.is_empty:
                    if skip_invalid:
                        stats['skipped'] += 1
                        continue
                    else:
                        raise ValueError(f"Invalid geometry at row {idx}")

                # Create POI object
                poi = POI(
                    name=poi_data['name'],
                    poi_type=poi_data['poi_type'],
                    address=poi_data['address'],
                    geom=from_shape(geom, srid=4326),
                    properties=poi_data['properties']
                )

                batch.append(poi)

                # Batch insert
                if len(batch) >= batch_size:
                    db.bulk_save_objects(batch)
                    db.commit()
                    stats['success'] += len(batch)
                    print(f"  Imported {stats['success']} records...")
                    batch = []

            except Exception as e:
                stats['failed'] += 1
                print(f"  Error processing row {idx}: {e}")
                if not skip_invalid:
                    raise

        # Insert remaining records
        if batch:
            db.bulk_save_objects(batch)
            db.commit()
            stats['success'] += len(batch)

        print(f"\nImport completed:")
        print(f"  Successfully imported: {stats['success']}")
        print(f"  Failed: {stats['failed']}")
        print(f"  Skipped: {stats['skipped']}")

    except Exception as e:
        db.rollback()
        print(f"\nImport failed: {e}")
        raise
    finally:
        db.close()

    return stats


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Import POI data from GeoJSON or Shapefile to PostGIS database"
    )
    parser.add_argument(
        "file",
        type=str,
        help="Path to GeoJSON or Shapefile"
    )
    parser.add_argument(
        "--init-db",
        action="store_true",
        help="Initialize database tables before import"
    )
    parser.add_argument(
        "--name-field",
        type=str,
        default="name",
        help="Field name for POI name (default: name)"
    )
    parser.add_argument(
        "--type-field",
        type=str,
        default="type",
        help="Field name for POI type (default: type)"
    )
    parser.add_argument(
        "--address-field",
        type=str,
        default="address",
        help="Field name for address (default: address)"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=1000,
        help="Batch size for insert operations (default: 1000)"
    )
    parser.add_argument(
        "--no-skip-invalid",
        action="store_true",
        help="Fail on invalid geometries instead of skipping"
    )

    args = parser.parse_args()

    # Initialize database if requested
    if args.init_db:
        print("Initializing database tables...")
        init_db()
        print()

    # Prepare field mapping
    field_mapping = {
        'name': args.name_field,
        'poi_type': args.type_field,
        'address': args.address_field,
    }

    # Import data
    try:
        import_poi_data(
            file_path=args.file,
            field_mapping=field_mapping,
            batch_size=args.batch_size,
            skip_invalid=not args.no_skip_invalid
        )
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
