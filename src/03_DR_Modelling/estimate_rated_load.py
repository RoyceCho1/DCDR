import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os

# Set style
sns.set_theme(style="whitegrid")
plt.rcParams['font.family'] = 'sans-serif'

input_file = 'data/data_with_weather.csv'
output_dir = 'figures/05_Capacity_Planning'

if not os.path.exists(output_dir):
    os.makedirs(output_dir)

def estimate_rated_load():
    print("Loading data...")
    df = pd.read_csv(input_file)
    
    # 1. Convert kWh to kW
    # Data is 15-min interval. Power (kW) = Energy (kWh) * (60/15) = kWh * 4
    df['kW'] = df['measured_kWh'] * 4
    
    # 2. Statistics
    loads = df['kW'].values
    p_peak = np.max(loads)
    p_99 = np.percentile(loads, 99)
    p_95 = np.percentile(loads, 95)
    p_median = np.median(loads)
    
    print("\n--- Load Statistics (kW) ---")
    print(f"Absolute Peak (P_peak): {p_peak:,.2f} kW")
    print(f"99th Percentile (P99):  {p_99:,.2f} kW")
    print(f"95th Percentile (P95):  {p_95:,.2f} kW")
    print(f"Median Load:            {p_median:,.2f} kW")
    
    # 3. Rated Load (N) Candidates
    n_scenario_a = 1.1 * p_99  # 1.1 x P99
    n_scenario_b = 1.0 * p_peak # Peak Coverage
    n_scenario_c = p_95 * 1.1   # P95 + 10%
    
    print("\n--- Rated Load (N) Candidates ---")
    print(f"Scenario A (1.1 * P99): {n_scenario_a:,.2f} kW  <-- Recommended")
    print(f"Scenario B (1.0 * P_peak): {n_scenario_b:,.2f} kW")
    print(f"Scenario C (1.1 * P95): {n_scenario_c:,.2f} kW")
    
    # Recommended N
    rated_load_n = n_scenario_a
    
    # 4. Load Duration Curve (LDC)
    print("\nGenerating Load Duration Curve...")
    
    # Sort loads descending
    sorted_loads = np.sort(loads)[::-1]
    # X-axis: Percentage of time (0 to 100)
    x_axis = np.linspace(0, 100, len(sorted_loads))
    
    plt.figure(figsize=(10, 6))
    
    # Plot LDC
    plt.plot(x_axis, sorted_loads, color='#1f77b4', linewidth=2, label='Load Duration Curve')
    
    # Mark lines
    plt.axhline(y=rated_load_n, color='red', linestyle='--', linewidth=1.5, label=f'Rated Load N (1.1xP99) = {rated_load_n:.0f} kW')
    plt.axhline(y=p_peak, color='black', linestyle=':', label=f'Peak = {p_peak:.0f} kW')
    plt.axhline(y=p_99, color='green', linestyle=':', label=f'P99 = {p_99:.0f} kW')
    
    plt.fill_between(x_axis, sorted_loads, alpha=0.1, color='#1f77b4')
    
    plt.title('Load Duration Curve (LDC) & Rated Load', fontsize=16, fontweight='bold')
    plt.xlabel('Duration (%)')
    plt.ylabel('Load (kW)')
    plt.legend()
    plt.grid(True, which='both', linestyle='--', alpha=0.7)
    
    # Text annotation for N
    plt.text(5, rated_load_n + 50, f"Rated Load N\n{rated_load_n:.0f} kW", color='red', fontweight='bold')
    
    plt.tight_layout()
    plt.savefig(f'{output_dir}/figure_load_duration_curve.png', dpi=300)
    print(f"Saved {output_dir}/figure_load_duration_curve.png")

if __name__ == "__main__":
    estimate_rated_load()
