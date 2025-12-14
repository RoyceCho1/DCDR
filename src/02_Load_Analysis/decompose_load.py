import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.linear_model import LinearRegression

# Set style
sns.set_theme(style="whitegrid")
plt.rcParams['font.family'] = 'sans-serif'

file_path = 'data/data_with_weather.csv'
output_csv = 'data/data_decomposition.csv'
output_fig = 'figures/figure_decomposition.png'

def calculate_enthalpy(temp_c, rel_humid_percent):
    """
    Calculate specific enthalpy of moist air (kJ/kg).
    Formula approximate: h = 1.006*T + W*(2501 + 1.86*T)
    Where W (mixing ratio) ~= 0.622 * (Pv / (Patm - Pv))
    Pv (Vapor Pressure) = P_sat * (RH/100)
    P_sat (Saturation Pressure) ~= 0.6112 * exp(17.67*T / (T + 243.5)) * 10 (hPa -> kPa? No, standard formula uses different units)
    
    Let's use a standard approximation for Enthalpy in kJ/kg:
    h = 1.006*T + W*(2501 + 1.86*T)
    
    W calculation:
    $P_{ws}$ (Saturation Vapor Pressure in hPa) uses Magnus formula:
    $P_{ws} = 6.112 \times \exp(\frac{17.67 \times T}{T + 243.5})$
    $P_v = P_{ws} \times \frac{RH}{100}$
    $P_{atm} \approx 1013.25$ hPa (Standard Pressure)
    $W = 0.622 \times \frac{P_v}{P_{atm} - P_v}$ (kg_water / kg_dry_air)
    """
    
    # 1. Saturation Vapor Pressure (hPa)
    es = 6.112 * np.exp((17.67 * temp_c) / (temp_c + 243.5))
    
    # 2. Actual Vapor Pressure (hPa)
    e = es * (rel_humid_percent / 100.0)
    
    # 3. Mixing Ratio (kg/kg) - assuming standard pressure at sea level approx
    p_atm = 1013.25 
    w = 0.622 * (e / (p_atm - e))
    
    # 4. Enthalpy (kJ/kg)
    # Cp_air = 1.006 kJ/kg.K
    # Latent_heat = 2501 kJ/kg
    # Cp_vapor = 1.86 kJ/kg.K
    h = 1.006 * temp_c + w * (2501 + 1.86 * temp_c)
    
    return h

def decompose_load():
    print("Loading data...")
    df = pd.read_csv(file_path)
    # No datetime index in file, create one for plotting
    df['datetime'] = pd.to_datetime(df['date'].astype(str) + ' ' + 
                                    df['hour'].astype(str).str.zfill(2) + ':' + 
                                    df['minute'].astype(str).str.zfill(2))
    df.set_index('datetime', inplace=True)
    
    # 1. Feature Engineering: Enthalpy
    print("Calculating Enthalpy...")
    df['enthalpy'] = calculate_enthalpy(df['temperature'].values, df['humidity'].values)
    
    print(f"Enthalpy Stats: Min={df['enthalpy'].min():.2f}, Max={df['enthalpy'].max():.2f}, Mean={df['enthalpy'].mean():.2f}")
    
    # 2. Change-Point Regression
    # Model: Load = Base + Sensitivity * max(0, Enthalpy - Threshold)
    
    best_r2 = -100
    best_threshold = 20 # Initial guess
    best_model = None
    
    # Search range for Enthalpy Threshold (e.g., 20 to 60 kJ/kg)
    search_range = np.arange(10, 60, 1)
    
    print("Optimizing Enthalpy Threshold...")
    y = df['measured_kWh'].values
    
    for t in search_range:
        X = np.maximum(0, df['enthalpy'].values - t).reshape(-1, 1)
        
        reg = LinearRegression()
        reg.fit(X, y)
        r2 = reg.score(X, y)
        
        if r2 > best_r2:
            best_r2 = r2
            best_threshold = t
            best_model = reg
            
    print(f"Best Enthalpy Threshold: {best_threshold} kJ/kg (R2={best_r2:.4f})")
    print(f"Cooling Sensitivity: {best_model.coef_[0]:.2f} kWh per kJ/kg")
    print(f"Intercept (Base Load): {best_model.intercept_:.2f} kWh")
    
    # 3. Calculate Components
    # Strategy: Tune k (Other/IT ratio) to match Target PUE = 1.35
    target_pue = 1.35
    
    # Calculate Cooling first (Model)
    # Cooling is fixed based on regression
    df['Cooling'] = best_model.coef_[0] * np.maximum(0, df['enthalpy'] - best_threshold)
    
    total_energy = df['measured_kWh'].sum()
    cooling_energy = df['Cooling'].sum()
    cooling_ratio = cooling_energy / total_energy
    
    print(f"\nTotal Energy: {total_energy:,.0f} kWh")
    print(f"Cooling Energy (Regression): {cooling_energy:,.0f} kWh ({cooling_ratio*100:.2f}%)")
    
    # PUE Formula derivation:
    # PUE = Total / IT
    # IT = (Total - Cooling) / (1 + k)
    # PUE = Total / [(Total - Cooling) / (1 + k)]
    # PUE = (Total / (Total - Cooling)) * (1 + k)
    # PUE = (1 / (1 - cooling_ratio)) * (1 + k)
    # (1 + k) = PUE * (1 - cooling_ratio)
    # k = PUE * (1 - cooling_ratio) - 1
    
    calculated_k = target_pue * (1 - cooling_ratio) - 1
    
    print(f"\n[PUE Calibration]")
    print(f"Target PUE: {target_pue}")
    print(f"Required k (Other/IT): {calculated_k:.4f}")
    
    if calculated_k < 0:
        print("Warning: Target PUE is too low given the estimated Cooling load. Forcing k=0 (PUE will be higher than target).")
        k = 0
    else:
        k = calculated_k

    # Calculate remaining Base Load
    base_load_series = df['measured_kWh'] - df['Cooling']
    base_load_series = base_load_series.clip(lower=0)
    
    # Apply k
    df['IT'] = base_load_series / (1 + k)
    df['Other'] = base_load_series * k / (1 + k)
    
    # Final Stats
    final_it_sum = df['IT'].sum()
    final_pue = total_energy / final_it_sum
    
    print("\n--- Component Summary (Average) ---")
    print(df[['measured_kWh', 'IT', 'Cooling', 'Other']].mean())
    print(f"\nFinal PUE: {final_pue:.4f}")
    print(f"Other/IT Ratio: {k:.4f}")
    
    # Save Results
    df_save = df[['measured_kWh', 'IT', 'Cooling', 'Other', 'temperature', 'humidity', 'enthalpy']]
    df_save.to_csv(output_csv)
    print(f"Saved results to {output_csv}")
    
    # 4. Visualization
    print("Generating Figure...")
    # Resample to Daily Mean for stackplot
    daily = df[['IT', 'Other', 'Cooling']].resample('D').mean()
    
    # Also plot Enthalpy on twin axis?
    daily_h = df['enthalpy'].resample('D').mean()
    
    fig, ax1 = plt.subplots(figsize=(12, 6))
    
    # Stackplot
    ax1.stackplot(daily.index, daily['IT'], daily['Other'], daily['Cooling'],
                  labels=['IT Load', 'Other Load', 'Cooling Load'],
                  colors=['#1f77b4', '#7f7f7f', '#ff7f0e'], alpha=0.85)
    
    ax1.set_ylabel('Power Load (kWh)', fontsize=12)
    ax1.set_title('Daily Load Decomposition (Enthalpy-Based)', fontsize=16, fontweight='bold')
    ax1.legend(loc='upper left', frameon=True)
    
    # Add Enthalpy Line Overlay
    ax2 = ax1.twinx()
    ax2.plot(daily.index, daily_h, color='red', linestyle='--', linewidth=1.5, label='Enthalpy (kJ/kg)')
    ax2.set_ylabel('Enthalpy (kJ/kg)', color='red', fontsize=12)
    ax2.tick_params(axis='y', labelcolor='red')
    # ax2.legend(loc='upper right')
    
    plt.tight_layout()
    plt.savefig(output_fig, dpi=300)
    print(f"Saved figure to {output_fig}")

if __name__ == "__main__":
    decompose_load()
