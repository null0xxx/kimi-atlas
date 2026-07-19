"""
Annual sun/shadow hours at a point.
Given a building (footprint + height + rotation) and a point (x,y in meters from building center),
compute total hours per year the point is in direct sun vs in building shadow vs night.
Samples at configurable interval (default 1 hour) for memory efficiency on 1GB VPS.
"""
import argparse
import datetime
import pytz
import numpy as np
import matplotlib.pyplot as plt
from shapely.geometry import box, Point
from shapely.affinity import rotate, translate
from pysolar.solar import get_altitude, get_azimuth
import sys


def get_shadow_polygon(lat, lon, dt_utc, width, depth, height, rotation):
    """
    Return (sun_altitude_deg, shadow_polygon).
    If sun below horizon, returns (altitude, None).
    Shadow polygon is in same 2D plane as building (meters), building center at (0,0).
    """
    altitude = get_altitude(lat, lon, dt_utc)
    if altitude <= 0:
        return altitude, None
    azimuth = get_azimuth(lat, lon, dt_utc)
    shadow_len = height / np.tan(np.radians(altitude))
    shadow_dir_deg = (azimuth + 180) % 360
    shadow_dir_rad = np.radians(90 - shadow_dir_deg)
    dx = shadow_len * np.cos(shadow_dir_rad)
    dy = shadow_len * np.sin(shadow_dir_rad)
    building_base = box(-width / 2, -depth / 2, width / 2, depth / 2)
    building_base = rotate(building_base, -rotation, origin="center")
    building_roof_proj = translate(building_base, xoff=dx, yoff=dy)
    total_shadow = building_base.union(building_roof_proj).convex_hull
    return altitude, total_shadow


def run_annual(
    lat,
    lon,
    width,
    depth,
    height,
    rotation,
    point_x,
    point_y,
    year,
    interval_minutes,
    tz_name,
):
    """
    Run annual sampling. Returns (hours_sun, hours_shadow, hours_night), and
    list of (month, sun_h, shadow_h, night_h) for optional plotting.
    """
    tz = pytz.timezone(tz_name) if tz_name else pytz.UTC
    start = datetime.datetime(year, 1, 1, 0, 0, 0, tzinfo=tz)
    end = datetime.datetime(year, 12, 31, 23, 59, 59, tzinfo=tz)
    point = Point(point_x, point_y)
    interval = datetime.timedelta(minutes=interval_minutes)
    hours_sun = 0.0
    hours_shadow = 0.0
    hours_night = 0.0
    # Monthly breakdown: month_index (1-12) -> (sun, shadow, night) in hours
    monthly = {m: [0.0, 0.0, 0.0] for m in range(1, 13)}
    current = start
    while current <= end:
        dt_utc = current.astimezone(pytz.UTC)
        alt, shadow_poly = get_shadow_polygon(
            lat, lon, dt_utc, width, depth, height, rotation
        )
        frac = interval.total_seconds() / 3600.0
        month = current.month
        if alt <= 0:
            hours_night += frac
            monthly[month][2] += frac
        elif shadow_poly is not None and shadow_poly.contains(point):
            hours_shadow += frac
            monthly[month][1] += frac
        else:
            hours_sun += frac
            monthly[month][0] += frac
        current += interval
    return (hours_sun, hours_shadow, hours_night), monthly


def main():
    parser = argparse.ArgumentParser(
        description="Annual sun/shadow hours at a point (building shadow only, flat ground)."
    )
    parser.add_argument("--lat", type=float, required=True, help="Latitude")
    parser.add_argument("--lon", type=float, required=True, help="Longitude")
    parser.add_argument("--width", type=float, default=10.0, help="Building width (m)")
    parser.add_argument("--depth", type=float, default=10.0, help="Building depth (m)")
    parser.add_argument("--height", type=float, default=20.0, help="Building height (m)")
    parser.add_argument(
        "--rotation",
        type=float,
        default=0.0,
        help="Building rotation (deg clockwise from North)",
    )
    parser.add_argument(
        "--point-x",
        type=float,
        default=0.0,
        help="Point X in meters from building center (North-South axis)",
    )
    parser.add_argument(
        "--point-y",
        type=float,
        default=0.0,
        help="Point Y in meters from building center (East-West axis)",
    )
    parser.add_argument("--year", type=int, default=None, help="Year (default: current)")
    parser.add_argument(
        "--interval",
        type=int,
        default=60,
        help="Sample interval in minutes (default 60)",
    )
    parser.add_argument(
        "--timezone",
        type=str,
        default="UTC",
        help="Timezone for date range (e.g. Asia/Shanghai)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="",
        help="Optional: save monthly bar chart to this file",
    )
    args = parser.parse_args()
    year = args.year or datetime.datetime.now().year
    (hours_sun, hours_shadow, hours_night), monthly = run_annual(
        args.lat,
        args.lon,
        args.width,
        args.depth,
        args.height,
        args.rotation,
        args.point_x,
        args.point_y,
        year,
        args.interval,
        args.timezone,
    )
    total = hours_sun + hours_shadow + hours_night
    print(f"Annual Sun/Shadow Hours (year={year}, point=({args.point_x}, {args.point_y}) m)")
    print(f"  Direct sun:  {hours_sun:.1f} h  ({100*hours_sun/total:.1f}%)")
    print(f"  In shadow:   {hours_shadow:.1f} h  ({100*hours_shadow/total:.1f}%)")
    print(f"  Night:       {hours_night:.1f} h  ({100*hours_night/total:.1f}%)")
    print(f"  Total:       {total:.1f} h")
    if args.output:
        fig, ax = plt.subplots(figsize=(10, 5))
        months = list(monthly.keys())
        sun_h = [monthly[m][0] for m in months]
        shadow_h = [monthly[m][1] for m in months]
        night_h = [monthly[m][2] for m in months]
        x = np.arange(len(months))
        w = 0.25
        ax.bar(x - w, sun_h, w, label="Sun", color="gold", alpha=0.9)
        ax.bar(x, shadow_h, w, label="Shadow", color="gray", alpha=0.7)
        ax.bar(x + w, night_h, w, label="Night", color="midnightblue", alpha=0.7)
        ax.set_xticks(x)
        ax.set_xticklabels([f"{m}" for m in months])
        ax.set_xlabel("Month")
        ax.set_ylabel("Hours")
        ax.legend()
        ax.set_title(f"Monthly Sun/Shadow/Night at point ({args.point_x}, {args.point_y}) m — {year}")
        plt.tight_layout()
        plt.savefig(args.output)
        print(f"Chart saved to {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
