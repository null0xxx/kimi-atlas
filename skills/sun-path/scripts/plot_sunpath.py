import argparse
import matplotlib.pyplot as plt
import numpy as np
from pysolar.solar import get_altitude, get_azimuth
import datetime
import pytz
import sys

def generate_sunpath_diagram(lat, lon, output_file):
    try:
        # Generate data points for the year (e.g., solstices and equinoxes)
        dates = [
            datetime.datetime(2024, 6, 21, tzinfo=pytz.utc), # Summer Solstice
            datetime.datetime(2024, 12, 21, tzinfo=pytz.utc), # Winter Solstice
            datetime.datetime(2024, 3, 21, tzinfo=pytz.utc)  # Equinox
        ]
        labels = ['Summer Solstice', 'Winter Solstice', 'Equinox']
        colors = ['#FF5733', '#33C1FF', '#FFC300']

        plt.figure(figsize=(10, 8))
        ax = plt.subplot(111, projection='polar')
        
        # Set North to top
        ax.set_theta_zero_location('N')
        ax.set_theta_direction(-1) # Clockwise

        for date, label, color in zip(dates, labels, colors):
            azimuths = []
            altitudes = []
            # Calculate for every hour of the day
            for hour in range(24):
                d = date + datetime.timedelta(hours=hour)
                alt = get_altitude(lat, lon, d)
                if alt > 0: # Only plot when sun is up
                    az = get_azimuth(lat, lon, d)
                    azimuths.append(np.radians(az))
                    altitudes.append(90 - alt) # Polar plot radius: 90 at center (zenith), 0 at edge (horizon)
            
            # Sort by azimuth to connect lines correctly
            if azimuths:
                sorted_indices = np.argsort(azimuths)
                azimuths = np.array(azimuths)[sorted_indices]
                altitudes = np.array(altitudes)[sorted_indices]
                ax.plot(azimuths, altitudes, label=label, color=color, linewidth=2)

        # Customize grid
        ax.set_rlim(0, 90)
        ax.set_yticks(range(0, 91, 15))
        ax.set_yticklabels([]) # Hide radial labels for cleaner look
        
        plt.title(f"Sun Path Diagram\nLat: {lat}, Lon: {lon}", y=1.08)
        plt.legend(loc='lower right', bbox_to_anchor=(1.1, -0.1))
        
        plt.savefig(output_file, bbox_inches='tight', dpi=100)
        print(f"Successfully generated sun path diagram: {output_file}")

    except Exception as e:
        print(f"Error generating plot: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Sun Path Diagram.")
    parser.add_argument("--lat", type=float, required=True, help="Latitude")
    parser.add_argument("--lon", type=float, required=True, help="Longitude")
    parser.add_argument("--output", type=str, default="sunpath.png", help="Output image filename")
    
    args = parser.parse_args()
    generate_sunpath_diagram(args.lat, args.lon, args.output)
