import argparse
from pysolar.solar import get_altitude, get_azimuth
import datetime
import pytz
import sys

def calculate_sun_position(lat, lon, timezone_str):
    try:
        tz = pytz.timezone(timezone_str)
        now = datetime.datetime.now(tz)
        
        # Pysolar requires UTC datetime for calculation
        date_utc = now.astimezone(pytz.utc)

        altitude = get_altitude(lat, lon, date_utc)
        azimuth = get_azimuth(lat, lon, date_utc)

        print(f"Location: Lat {lat}, Lon {lon}")
        print(f"Time: {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        print(f"Solar Altitude: {altitude:.2f} degrees")
        print(f"Solar Azimuth: {azimuth:.2f} degrees")
        
        if altitude > 0:
            print("Status: Day (Sun is up)")
        else:
            print("Status: Night (Sun is down)")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Calculate sun position.")
    parser.add_argument("--lat", type=float, required=True, help="Latitude")
    parser.add_argument("--lon", type=float, required=True, help="Longitude")
    parser.add_argument("--timezone", type=str, default="UTC", help="Timezone string (e.g., America/Los_Angeles)")
    
    args = parser.parse_args()
    calculate_sun_position(args.lat, args.lon, args.timezone)
