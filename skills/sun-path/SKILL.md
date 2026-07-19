---
name: sun-path
version: 1.4.1
description: "Analyzes sunlight and shadows for architectural design, generating sun path diagrams, solar position data, shadow plots, and thermal comfort charts. Triggered by requests about sun position, shadow analysis, annual sun hours, or diagrams for a specific location and time."
author: qrost
permissions:
  - shell:exec
---

# Sun Path & Environmental Analysis

This skill provides comprehensive environmental analysis tools for architects and designers.

## Dependencies

This skill requires Python and the following libraries:

- `pysolar` (solar calculations)
- `matplotlib` (plotting)
- `pytz` (timezone handling)
- `shapely` (geometry calculations for shadows)
- `numpy` (math)
- `rasterio` (for terrain/DEM shadow; optional for DEM features)

**Setup:** OpenClaw does not install Python packages automatically. After installing this skill (e.g. via `clawhub install sun-path`), run once from the skill folder or with the path to it: `pip install -r requirements.txt`. If a script fails with `ModuleNotFoundError`, install the missing package from the list above or from `requirements.txt`.

## Sending images to Telegram

Used from the OpenClaw Telegram conversation. Scripts that produce images (`plot_sunpath.py`, `shadow_calc.py`, `comfort_calc.py`, `annual_sun_hours.py --output`, `terrain_shadow.py --plot`) write PNG/JPG to the path you pass. Run the script with an `--output` (or `--plot` and use the script’s default image path), then **send that image file** to the user via the OpenClaw message/media tool so they see it in chat.

**OpenClaw allowed paths:** The message tool only sends files from allowed dirs (`~/.openclaw/media/`, `~/.openclaw/agents/`, or `/tmp`). Always pass an output path under one of these (e.g. `--output ~/.openclaw/media/sunpath.png` or `/tmp/shadow.png`); do not use the skill install directory or sending will fail.

**Agent behavior:** When the user asks for sun position, sun path diagram, shadow, annual sun hours chart, comfort chart, or terrain shadow, **run the corresponding script directly** with `exec` and pass an image output path under an allowed dir; then send the generated PNG/JPG to the user. Do not ask for confirmation; execute and return the image and a short summary.

## Usage

### 1. Calculate Sun Position

Get the current azimuth and altitude for a specific location.

```bash
python3 scripts/sun_calc.py --lat 34.05 --lon -118.24 --timezone "America/Los_Angeles"
```

### 2. Generate Sun Path Diagram

Create a polar chart showing the sun's path throughout the year.

```bash
python3 scripts/plot_sunpath.py --lat 34.05 --lon -118.24 --output sunpath.png
```

### 3. Shadow Analysis (2D)

Simulate the shadow cast by a simple building (cuboid) at a specific time.

**Parameters:**

- `--lat`, `--lon`: Location coordinates.
- `--time`: Date/Time in ISO format (e.g., "2024-06-21T12:00:00") or "now".
- `--width`, `--depth`: Building footprint dimensions (meters).
- `--height`: Building height (meters).
- `--rotation`: Rotation in degrees clockwise from North.
- `--output`: Output image filename.

```bash
python3 scripts/shadow_calc.py --lat 34.05 --lon -118.24 --time "2024-06-21T15:00:00" --width 15 --depth 10 --height 20 --rotation 45 --output shadow_analysis.png
```

### 4. Annual Sun / Shadow Hours at a Point

Compute how many hours per year a given point is in **direct sun**, in **building shadow**, or **night** (sun below horizon). Uses the same building cuboid and 2D shadow model as Shadow Analysis; point is given in meters from building center.

**Parameters:**

- `--lat`, `--lon`: Location coordinates.
- `--width`, `--depth`, `--height`, `--rotation`: Building dimensions and rotation (same as shadow analysis).
- `--point-x`, `--point-y`: Point to evaluate (meters from building center; e.g. North = positive X if rotation 0).
- `--year`: Year (default: current year).
- `--interval`: Sample interval in minutes (default 60; smaller = more accurate, slower).
- `--timezone`: Timezone for the year (e.g. `Asia/Shanghai`).
- `--output`: Optional; save a monthly bar chart (sun / shadow / night hours) to this file.

```bash
# Example: point 15 m north of building center, Shanghai, 2024
python3 scripts/annual_sun_hours.py --lat 31.23 --lon 121.47 --width 10 --depth 10 --height 20 --point-x 15 --point-y 0 --year 2024 --timezone Asia/Shanghai

# With monthly chart
python3 scripts/annual_sun_hours.py --lat 31.23 --lon 121.47 --width 10 --depth 10 --height 20 --point-x 15 --point-y 0 --year 2024 --timezone Asia/Shanghai --output annual_hours.png
```

Output: total hours in sun, in shadow, and at night, plus optional monthly breakdown chart.

### 5. Terrain Shadow (DEM)

Compute binary shadow (sun vs shadow) on terrain from a GeoTIFF DEM at a given time. Uses sun position and ray casting; suitable for modest DEM sizes (for 1GB RAM, keep grid under ~2000×2000 or process smaller crops).

**Parameters:**

- `dem`: Path to GeoTIFF DEM.
- `--lat`, `--lon`: Latitude/longitude for sun position.
- `--time`: Time in ISO format or "now" (interpreted in `--timezone` then converted to UTC).
- `--timezone`: Timezone name (e.g. `Asia/Shanghai`).
- `--output`: Output GeoTIFF path (default: `terrain_shadow.tif`).
- `--plot`: Also save a PNG visualization.
- `--step`: Ray step in pixels (default 1; larger = faster, less accurate).

```bash
# Example: shadow at noon local time
python3 scripts/terrain_shadow.py /path/to/dem.tif --lat 31.23 --lon 121.47 --time "2024-06-21T12:00:00" --timezone Asia/Shanghai --output shadow.tif --plot
```

### 6. Comfort Analysis (Psychrometric Chart)

Visualize current temperature and humidity on a psychrometric chart to assess thermal comfort.

**Parameters:**

- `--temp`: Dry bulb temperature (°C).
- `--rh`: Relative humidity (%).
- `--output`: Output image filename.

```bash
python3 scripts/comfort_calc.py --temp 28 --rh 60 --output comfort_chart.png
```

## Examples

**User:** "What is the sun position in Los Angeles right now?"
**Action:**

1. Identify coordinates for Los Angeles (Lat: 34.05, Lon: -118.24).
2. Run `sun_calc.py`.
3. Return azimuth and altitude.

**User:** "Show me the shadow of a 20m tall, 10x10m building in Shanghai on winter solstice at 2 PM."
**Action:**

1. Identify coordinates (Shanghai: 31.23, 121.47).
2. Identify time (Winter Solstice: 2024-12-21 14:00).
3. Run `shadow_calc.py`:

   ```bash
   python3 scripts/shadow_calc.py --lat 31.23 --lon 121.47 --time "2024-12-21T14:00:00" --width 10 --depth 10 --height 20 --output shanghai_shadow.png
   ```

4. Return the image.

**User:** "Is it comfortable in Singapore right now? Temp is 32C, Humidity 80%."
**Action:**

1. Run `comfort_calc.py`:

   ```bash
   python3 scripts/comfort_calc.py --temp 32 --rh 80 --output singapore_comfort.png
   ```

2. Return the image and analysis.

**User:** "How many hours per year is this point in sun vs shadow? Building 10×10×20m, point 15m north."
**Action:**

1. Run `annual_sun_hours.py` with site lat/lon, building dimensions, and `--point-x 15 --point-y 0`.
2. Return the printed summary (direct sun / shadow / night hours) and optionally the monthly chart if `--output` was used.

**User:** "Where is the terrain in shadow at this site at 2 PM? I have a DEM."
**Action:**

1. Run `terrain_shadow.py` with the DEM path, site `--lat`/`--lon`, and `--time` (e.g. 14:00 local), `--timezone`, and `--output`/`--plot`.
2. Return the shadow raster and/or PNG and a short summary.
