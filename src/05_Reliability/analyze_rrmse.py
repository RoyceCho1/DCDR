import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os

# Set style
sns.set_theme(style="whitegrid")
plt.rcParams['font.family'] = 'sans-serif'

input_file = 'data/dr_events_1h.csv'
output_dir = 'figures/06_Final_Report'
output_csv = 'data/reliability_metrics.csv'

if not os.path.exists(output_dir):
    os.makedirs(output_dir)

def calculate_metrics(A_t, C_t, name="Metric"):
    """
    A_t: Actual Available Capacity Series (kW)
    C_t: Committed Capacity Series (kW) (or Scalar)
    """
    
    # 1. RRMSE
    # RRMSE = sqrt(mean((C-A)^2)) / mean(C)
    # Note: If C is scalar, mean(C) = C.
    mse = np.mean((C_t - A_t)**2)
    rmse = np.sqrt(mse)
    mean_c = np.mean(C_t)
    rrmse = rmse / mean_c if mean_c != 0 else np.nan
    
    # 2. Shortfall Probability (Strict)
    # Pr(A < C)
    shortfall_mask = A_t < C_t
    prob_shortfall = shortfall_mask.mean()
    
    # 3. Expected Shortfall
    # E[max(0, C - A)]
    # We calculate mean shortfall over ALL events (including 0 shortfall)
    shortfall_vals = np.maximum(0, C_t - A_t)
    expected_shortfall = shortfall_vals.mean()
    
    # 4. Tolerance Shortfall (5%)
    # Pr(A < 0.95 * C)
    tol_C_t = 0.95 * C_t
    prob_tol_shortfall = (A_t < tol_C_t).mean()
    
    return {
        'Description': name,
        'Mean_Committed_kW': mean_c,
        'Mean_Actual_kW': A_t.mean(),
        'RRMSE': rrmse,
        'Prob_Shortfall_Strict': prob_shortfall,
        'Prob_Shortfall_Tol_5%': prob_tol_shortfall,
        'Expected_Shortfall_kW': expected_shortfall
    }

def analyze_rrmse():
    print("Loading DR Events...")
    df = pd.read_csv(input_file, parse_dates=['datetime'], index_col='datetime')
    
    # Add weekday info
    df['weekday'] = df.index.weekday
    
    # Filter: Shed Events on Weekdays
    valid_mask = (df['is_event_shed']) & (df['weekday'] < 5)
    events = df[valid_mask].copy()
    
    print(f"Valid Weekday Shed Events: {len(events)}")
    
    if events.empty:
        print("No events found. Exiting.")
        return

    # --- Analysis Targets ---
    # 1. Total Resource (A_t = Q_shed_kW)
    # 2. No-ESS Resource (A_t = Q_shed_kW - 1250)
    
    targets = {
        'Total_Resource': events['Q_shed_kW'],
        'No_ESS_Resource': events['Q_shed_kW'] - 1250.0
    }
    
    metrics_list = []
    
    for label, A_t in targets.items():
        print(f"\nAnalyzing: {label}")
        
        # Scenario 1: Global P90
        C_global = A_t.quantile(0.90) # Scalar
        m1 = calculate_metrics(A_t, C_global, f"{label}_Global_P90")
        metrics_list.append(m1)
        print(f"  [Global P90] RRMSE: {m1['RRMSE']:.4f}, Shortfall%: {m1['Prob_Shortfall_Strict']:.2%}")
        
        # Scenario 2: Seasonal P90
        # Calculate P90 per season, then map back to events
        season_p90_map = A_t.groupby(events['season']).quantile(0.90)
        C_seasonal = events['season'].map(season_p90_map)
        
        m2 = calculate_metrics(A_t, C_seasonal, f"{label}_Seasonal_P90")
        metrics_list.append(m2)
        print(f"  [Seasonal P90] RRMSE: {m2['RRMSE']:.4f}, Shortfall%: {m2['Prob_Shortfall_Strict']:.2%}")

    # Save Metrics
    df_metrics = pd.DataFrame(metrics_list)
    df_metrics = df_metrics.round(4)
    df_metrics.to_csv(output_csv, index=False)
    print(f"\nSaved metrics to {output_csv}")
    print(df_metrics[['Description', 'RRMSE', 'Prob_Shortfall_Strict', 'Prob_Shortfall_Tol_5%']])
    
    # --- Figures: Distribution ---
    # Plot Total Resource Actual vs Global P90
    plt.figure(figsize=(10, 6))
    
    # Plot Histogram of Actual Capacity
    sns.histplot(targets['Total_Resource'], bins=30, kde=True, color='skyblue', label='Actual Capacity (A_t)')
    
    # Plot Committment Line (Global P90)
    C_global = targets['Total_Resource'].quantile(0.90)
    plt.axvline(C_global, color='red', linestyle='--', linewidth=2, label=f'Committed (P90): {C_global:.1f} kW')
    
    plt.title('Reliability Check: Actual Capacity vs Committed (Total Resource)', fontsize=14, fontweight='bold')
    plt.xlabel('Available Capacity (kW)')
    plt.ylabel('Frequency (Event Hours)')
    plt.legend()
    plt.grid(True, linestyle='--', alpha=0.6)
    
    fig_path = f"{output_dir}/figure_reliability_distribution.png"
    plt.savefig(fig_path, dpi=300)
    print(f"Saved {fig_path}")

if __name__ == "__main__":
    analyze_rrmse()
