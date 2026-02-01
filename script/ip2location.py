"""Convert IP address to location using ip2region offline database."""
import sys
import argparse
from pathlib import Path
from XdbSearchIP.xdbSearcher import XdbSearcher


class IP2Location:
    """IP to location converter using ip2region xdb database."""

    def __init__(self, xdb_path: str = None):
        """
        Initialize IP2Location with xdb database.

        Args:
            xdb_path: Path to ip2region.xdb file. If None, uses default path.
        """
        if xdb_path is None:
            # Default path: static/ip2region.xdb
            project_root = Path(__file__).parent.parent
            xdb_path = project_root / "static" / "ip2region.xdb"

        self.xdb_path = Path(xdb_path)

        if not self.xdb_path.exists():
            raise FileNotFoundError(f"ip2region database not found: {self.xdb_path}")

        # Load xdb content into memory for better performance
        try:
            with open(self.xdb_path, "rb") as f:
                self.cb_data = f.read()
            self.searcher = XdbSearcher(contentBuff=self.cb_data)
        except Exception as e:
            raise Exception(f"Failed to load ip2region database: {e}")

    def search(self, ip: str) -> dict:
        """
        Search location for given IP address.

        Args:
            ip: IP address string (e.g., "1.2.3.4")

        Returns:
            dict: Location information with parsed fields
                  Format: {
                      'raw': '中国|0|湖南省|长沙市|电信',
                      'country': '中国',
                      'region': '0',
                      'province': '湖南省',
                      'city': '长沙市',
                      'isp': '电信'
                  }
        """
        try:
            result = self.searcher.search(ip)

            # Parse result: format is "country|region|province|city|isp"
            parts = result.split("|")

            return {
                "raw": result,
                "country": parts[0] if len(parts) > 0 else "",
                "region": parts[1] if len(parts) > 1 else "",
                "province": parts[2] if len(parts) > 2 else "",
                "city": parts[3] if len(parts) > 3 else "",
                "isp": parts[4] if len(parts) > 4 else "",
            }
        except Exception as e:
            raise Exception(f"Failed to search IP {ip}: {e}")

    def close(self):
        """Close the searcher."""
        if hasattr(self, 'searcher'):
            self.searcher.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


def format_location(location: dict) -> str:
    """
    Format location dictionary to readable string.

    Args:
        location: Location dictionary from search()

    Returns:
        str: Formatted location string
    """
    parts = []

    if location['country'] and location['country'] != '0':
        parts.append(location['country'])

    if location['province'] and location['province'] != '0':
        parts.append(location['province'])

    if location['city'] and location['city'] != '0':
        parts.append(location['city'])

    if location['isp'] and location['isp'] != '0':
        parts.append(f"({location['isp']})")

    return " ".join(parts) if parts else "Unknown"


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Convert IP address to location using ip2region offline database"
    )
    parser.add_argument(
        "ip",
        nargs="?",
        type=str,
        help="IP address to query (e.g., 8.8.8.8). If not provided, queries current public IP."
    )
    parser.add_argument(
        "--xdb",
        type=str,
        default=None,
        help="Path to ip2region.xdb file (default: static/ip2region.xdb)"
    )
    parser.add_argument(
        "--raw",
        action="store_true",
        help="Show raw result string"
    )

    args = parser.parse_args()

    # Get IP address
    ip_address = args.ip

    if not ip_address:
        # Query current public IP
        try:
            import requests
            print("Fetching current public IP...")
            response = requests.get("https://api.ipify.org?format=json", timeout=5)
            ip_address = response.json()["ip"]
            print(f"Current public IP: {ip_address}\n")
        except Exception as e:
            print(f"Error fetching public IP: {e}")
            print("Please provide an IP address as argument.")
            sys.exit(1)

    # Search location
    try:
        with IP2Location(args.xdb) as converter:
            location = converter.search(ip_address)

            print(f"IP Address: {ip_address}")
            print(f"Location: {format_location(location)}")

            if args.raw:
                print(f"Raw: {location['raw']}")
            else:
                print()
                print("Details:")
                print(f"  Country: {location['country']}")
                if location['region'] != '0':
                    print(f"  Region: {location['region']}")
                print(f"  Province: {location['province']}")
                print(f"  City: {location['city']}")
                print(f"  ISP: {location['isp']}")

    except FileNotFoundError as e:
        print(f"Error: {e}")
        print(f"Please ensure ip2region.xdb file exists at: {args.xdb or 'static/ip2region.xdb'}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
