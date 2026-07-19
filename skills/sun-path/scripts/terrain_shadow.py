"""
Terrain shadow from DEM at a given time.
Reads a GeoTIFF DEM, computes sun position, and outputs a binary shadow raster
(1 = in shadow, 0 = in sun) and optional hillshade-style plot.
Designed for modest memory use (process by blocks if needed); single read for small DEMs.
"""
import argparse
import datetime
import math
import sys
import numpy as np
import pytz

try:
    import rasterio
    from rasterio.transform import xy
    from rasterio.windows import Window
except ImportError:
    print("rasterio is required for terrain shadow. Install: pip install rasterio", file=sys.stderr)
    sys.exit(1)

from pysolar.solar import get_altitude, get_azimuth


def _horizontal_distance_m(transform, crs_is_geographic, x0, y0, x1, y1, lat_rad):
    """Approximate horizontal distance in meters between (x0,y0) and (x1,y1)."""
    if crs_is_geographic:
        # (x,y) as (lon, lat); 1 deg lat ~ 111320 m, 1 deg lon ~ 111320*cos(lat)
        dlon = (x1 - x0) * 111320 * math.cos(lat_rad)
        dlat = (y1 - y0) * 111320
        return math.sqrt(dlon * dlon + dlat * dlat)
    return math.sqrt((x1 - x0) ** 2 + (y1 - y0) ** 2)


def compute_shadow_grid(dem, transform, nodata, lat_deg, lon_deg, dt_utc, crs_is_geographic, step_pixels=1):
    """
    Compute binary shadow (1=shadow, 0=sun) for DEM array.
    dem: 2D float array (height, width); row-major [row, col].
    transform: rasterio Affine (col, row) -> (x, y).
    crs_is_geographic: if True, (x,y) are (lon,lat); horizontal distance uses degree-to-meter approx.
    """
    alt = get_altitude(lat_deg, lon_deg, dt_utc)
    az = get_azimuth(lat_deg, lon_deg, dt_utc)
    if alt <= 0:
        return np.ones(dem.shape, dtype=np.uint8), alt, az  # all shadow (night)

    alt_rad = math.radians(alt)
    az_rad = math.radians(az)
    east = math.cos(alt_rad) * math.sin(az_rad)
    north = math.cos(alt_rad) * math.cos(az_rad)
    lat_rad = math.radians(lat_deg)
    rows, cols = dem.shape
    # Step in pixel space so world direction is (east, north)
    cell_x = transform.a if transform.a != 0 else 1e-6
    cell_y = transform.e if transform.e != 0 else -1e-6
    dc = step_pixels * east / cell_x
    dr = step_pixels * north / cell_y
    max_steps = max(rows, cols) * 2
    shadow = np.zeros(dem.shape, dtype=np.uint8)

    for r in range(rows):
        for c in range(cols):
            z0 = dem[r, c]
            if nodata is not None and (np.isnan(z0) or z0 == nodata):
                shadow[r, c] = 1
                continue
            x0, y0 = xy(transform, r, c)
            in_shadow = False
            for k in range(1, max_steps):
                c1 = int(round(c + k * dc))
                r1 = int(round(r + k * dr))
                if r1 < 0 or r1 >= rows or c1 < 0 or c1 >= cols:
                    break
                x1, y1 = xy(transform, r1, c1)
                h_m = _horizontal_distance_m(
                    transform, crs_is_geographic, x0, y0, x1, y1, lat_rad
                )
                z_ray = z0 + h_m * math.tan(alt_rad)
                z_block = dem[r1, c1]
                if nodata is not None and (np.isnan(z_block) or z_block == nodata):
                    continue
                if z_block > z_ray:
                    in_shadow = True
                    break
            shadow[r, c] = 1 if in_shadow else 0
    return shadow, alt, az


def main():
    parser = argparse.ArgumentParser(
        description="Compute terrain shadow from DEM at a given time (sun position)."
    )
    parser.add_argument("dem", help="Path to GeoTIFF DEM")
    parser.add_argument("--lat", type=float, required=True, help="Latitude for sun position")
    parser.add_argument("--lon", type=float, required=True, help="Longitude for sun position")
    parser.add_argument(
        "--time",
        type=str,
        default="now",
        help="Time ISO or 'now' (UTC)",
    )
    parser.add_argument(
        "--timezone",
        type=str,
        default="UTC",
        help="Timezone for --time if not UTC",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="terrain_shadow.tif",
        help="Output shadow raster (GeoTIFF) or PNG base name",
    )
    parser.add_argument(
        "--plot",
        action="store_true",
        help="Also save a PNG visualization",
    )
    parser.add_argument(
        "--step",
        type=float,
        default=1.0,
        help="Ray step in pixels (1=fine, larger=faster, less accurate)",
    )
    args = parser.parse_args()

    if args.time == "now":
        dt_utc = datetime.datetime.now(pytz.UTC)
    else:
        try:
            dt = datetime.datetime.fromisoformat(args.time)
            if dt.tzinfo is None:
                dt = pytz.timezone(args.timezone).localize(dt)
            dt_utc = dt.astimezone(pytz.UTC)
        except Exception as e:
            print(f"Invalid --time: {e}", file=sys.stderr)
            sys.exit(1)

    with rasterio.open(args.dem) as src:
        dem = src.read(1)
        transform = src.transform
        nodata = src.nodata
        profile = src.profile.copy()
        try:
            crs_is_geographic = bool(src.crs and src.crs.is_geographic)
        except Exception:
            crs_is_geographic = True

    shadow, alt, az = compute_shadow_grid(
        dem, transform, nodata, args.lat, args.lon, dt_utc, crs_is_geographic, step_pixels=args.step
    )
    print(f"Time (UTC): {dt_utc}")
    print(f"Sun altitude: {alt:.2f} deg, azimuth: {az:.2f} deg")
    if alt <= 0:
        print("Sun below horizon; output is full shadow.")

    profile.update(dtype=np.uint8, count=1, nodata=None)
    out_path = args.output if args.output.endswith(".tif") or args.output.endswith(".tiff") else args.output + ".tif"
    with rasterio.open(out_path, "w", **profile) as dst:
        dst.write(shadow, 1)
    print(f"Shadow raster written to {out_path}")

    if args.plot:
        try:
            import matplotlib.pyplot as plt
            fig, ax = plt.subplots(figsize=(8, 8))
            ax.imshow(shadow, cmap="gray", vmin=0, vmax=1)
            ax.set_title(f"Terrain shadow\n{dt_utc.strftime('%Y-%m-%d %H:%M')} UTC, alt={alt:.1f}°")
            plot_path = out_path.replace(".tif", ".png").replace(".tiff", ".png")
            if plot_path == out_path:
                plot_path = args.output + ".png"
            plt.savefig(plot_path)
            print(f"Plot saved to {plot_path}")
        except Exception as e:
            print(f"Plot failed: {e}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
