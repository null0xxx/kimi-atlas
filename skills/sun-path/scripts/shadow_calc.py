import argparse
import datetime
import pytz
import numpy as np
import matplotlib.pyplot as plt
from shapely.geometry import Polygon, box
from shapely.affinity import rotate, translate
from pysolar.solar import get_altitude, get_azimuth
import sys

def calculate_shadow(lat, lon, time_str, width, depth, height, rotation, output_file):
    try:
        # Parse time
        # Expecting ISO format or similar, defaulting to current time if not specific
        if time_str == "now":
            now = datetime.datetime.now(pytz.utc)
        else:
            try:
                now = datetime.datetime.fromisoformat(time_str)
                if now.tzinfo is None:
                    now = now.replace(tzinfo=pytz.utc)
            except ValueError:
                print(f"Error: Invalid time format '{time_str}'. Use ISO format or 'now'.", file=sys.stderr)
                sys.exit(1)

        # Calculate Sun Position
        altitude = get_altitude(lat, lon, now)
        azimuth = get_azimuth(lat, lon, now)

        print(f"Time: {now}")
        print(f"Sun Altitude: {altitude:.2f} deg")
        print(f"Sun Azimuth: {azimuth:.2f} deg")

        if altitude <= 0:
            print("Sun is below horizon. No shadow.")
            # Still plot the building
            fig, ax = plt.subplots(figsize=(8, 8))
            building = box(-width/2, -depth/2, width/2, depth/2)
            building = rotate(building, rotation, origin='center')
            x, y = building.exterior.xy
            ax.fill(x, y, color='red', alpha=0.7, label='Building')
            ax.set_aspect('equal')
            plt.title(f"Building (Night)\nLat: {lat}, Lon: {lon}")
            plt.savefig(output_file)
            return

        # Calculate Shadow Vector
        # Shadow length on flat ground
        shadow_len = height / np.tan(np.radians(altitude))
        
        # Shadow direction (opposite to sun azimuth)
        # Pysolar azimuth: South=0, West=90, North=180/-180, East=-90 (check docs, usually S=0 in pysolar < 0.8, but N=0 in >= 0.8)
        # Actually pysolar 0.8+ uses N=0, E=90, S=180, W=270.
        # Let's assume standard compass: N=0, E=90, S=180, W=270.
        # Shadow points AWAY from sun.
        shadow_dir_deg = (azimuth + 180) % 360
        shadow_dir_rad = np.radians(90 - shadow_dir_deg) # Convert compass angle to math angle (CCW from East)

        dx = shadow_len * np.cos(shadow_dir_rad)
        dy = shadow_len * np.sin(shadow_dir_rad)

        # Create Building Polygon (centered at 0,0)
        building_base = box(-width/2, -depth/2, width/2, depth/2)
        building_base = rotate(building_base, -rotation, origin='center') # Negative for clockwise rotation usually expected by users

        # Create "Roof" projection (translated base)
        building_roof_proj = translate(building_base, xoff=dx, yoff=dy)

        # Create Shadow Polygon (Convex Hull of Base + Roof Projection)
        # This covers the entire area on ground occluded by the building
        total_shadow = building_base.union(building_roof_proj).convex_hull
        
        # The visible shadow is Total - Base (but for plotting we just layer them)
        
        # Plotting
        fig, ax = plt.subplots(figsize=(10, 10))
        
        # Plot Shadow
        sx, sy = total_shadow.exterior.xy
        ax.fill(sx, sy, color='gray', alpha=0.5, label='Shadow')
        
        # Plot Building
        bx, by = building_base.exterior.xy
        ax.fill(bx, by, color='red', alpha=0.7, label='Building')

        # Add North Arrow
        ax.arrow(width, depth, 0, 5, head_width=2, head_length=2, fc='k', ec='k')
        ax.text(width, depth + 6, 'N', ha='center')

        # Add Sun Direction Arrow (inverse of shadow)
        sun_dx = -dx * 0.2 # Short arrow pointing to sun
        sun_dy = -dy * 0.2
        # ax.arrow(0, 0, sun_dx, sun_dy, head_width=1, color='orange', label='Sun Direction')

        ax.set_aspect('equal')
        ax.legend()
        ax.grid(True, linestyle='--', alpha=0.3)
        
        plt.title(f"Shadow Analysis\nLat: {lat}, Lon: {lon}\nTime: {now.strftime('%Y-%m-%d %H:%M')} UTC\nSun Alt: {altitude:.1f}°, Azi: {azimuth:.1f}°")
        plt.xlabel("Meters")
        plt.ylabel("Meters")
        
        plt.savefig(output_file)
        print(f"Shadow plot saved to {output_file}")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Calculate building shadow.")
    parser.add_argument("--lat", type=float, required=True, help="Latitude")
    parser.add_argument("--lon", type=float, required=True, help="Longitude")
    parser.add_argument("--time", type=str, default="now", help="Time (ISO format or 'now')")
    parser.add_argument("--width", type=float, default=10.0, help="Building width (meters)")
    parser.add_argument("--depth", type=float, default=10.0, help="Building depth (meters)")
    parser.add_argument("--height", type=float, default=20.0, help="Building height (meters)")
    parser.add_argument("--rotation", type=float, default=0.0, help="Building rotation (degrees clockwise from North)")
    parser.add_argument("--output", type=str, default="shadow.png", help="Output image filename")
    
    args = parser.parse_args()
    calculate_shadow(args.lat, args.lon, args.time, args.width, args.depth, args.height, args.rotation, args.output)
