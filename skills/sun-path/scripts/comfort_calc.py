import argparse
import matplotlib.pyplot as plt
import numpy as np
import sys

# Simplified Psychrometric calculations to avoid extra heavy dependencies
def get_saturation_vapor_pressure(temp_c):
    # Magnus formula
    return 6.1094 * np.exp((17.625 * temp_c) / (temp_c + 243.04))

def get_humidity_ratio(temp_c, rh_percent, pressure_pa=101325):
    # rh is 0-100
    es = get_saturation_vapor_pressure(temp_c)
    e = es * (rh_percent / 100.0)
    # Humidity ratio W = 0.622 * e / (p - e)
    # Result in kg_water / kg_dry_air
    return 0.622 * e / ((pressure_pa / 100.0) - e)

def plot_psychrometric(temp, rh, output_file):
    try:
        plt.figure(figsize=(10, 8))
        
        # 1. Draw Saturation Curve (RH=100%)
        t_range = np.linspace(0, 40, 100)
        w_sat = [get_humidity_ratio(t, 100) * 1000 for t in t_range] # g/kg
        plt.plot(t_range, w_sat, 'k-', label='Saturation (100% RH)')

        # 2. Draw other RH curves
        for r in [20, 40, 60, 80]:
            w_r = [get_humidity_ratio(t, r) * 1000 for t in t_range]
            plt.plot(t_range, w_r, 'k--', linewidth=0.5, alpha=0.5)
            plt.text(40, w_r[-1], f'{r}%', fontsize=8)

        # 3. Draw Comfort Zone (Simplified ASHRAE 55 / Adaptive)
        # Assuming roughly 20C-26C and 30%-60% RH
        comfort_t = [20, 26, 26, 20, 20]
        comfort_rh = [30, 30, 60, 60, 30] # This is a box in T-RH space, not quite a polygon in Psychrometric chart
        
        # Convert comfort box to T-W coordinates
        comfort_w = []
        for t, r in zip(comfort_t, comfort_rh):
            comfort_w.append(get_humidity_ratio(t, r) * 1000)
            
        plt.fill(comfort_t, comfort_w, color='green', alpha=0.2, label='Comfort Zone (Approx)')

        # 4. Plot Current Point
        current_w = get_humidity_ratio(temp, rh) * 1000
        plt.plot(temp, current_w, 'ro', markersize=10, label='Current Condition')
        plt.text(temp + 0.5, current_w, f'{temp}°C, {rh}%', fontsize=10, fontweight='bold')

        # Formatting
        plt.xlim(0, 45)
        plt.ylim(0, 30)
        plt.xlabel("Dry Bulb Temperature (°C)")
        plt.ylabel("Humidity Ratio (g water / kg dry air)")
        plt.title("Psychrometric Chart & Comfort Analysis")
        plt.grid(True, which='both', linestyle='--', alpha=0.3)
        plt.legend(loc='upper left')

        plt.savefig(output_file)
        print(f"Comfort analysis plot saved to {output_file}")

    except Exception as e:
        print(f"Error generating plot: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Psychrometric Chart.")
    parser.add_argument("--temp", type=float, required=True, help="Temperature (C)")
    parser.add_argument("--rh", type=float, required=True, help="Relative Humidity (%)")
    parser.add_argument("--output", type=str, default="comfort.png", help="Output image filename")
    
    args = parser.parse_args()
    plot_psychrometric(args.temp, args.rh, args.output)
