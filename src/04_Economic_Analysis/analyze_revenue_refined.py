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
output_csv = 'data/revenue_results_refined.csv'

if not os.path.exists(output_dir):
    os.makedirs(output_dir)

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
output_csv = 'data/revenue_results_refined.csv'

if not os.path.exists(output_dir):
    os.makedirs(output_dir)

def analyze_revenue_refined():
    print("Loading Standardized DR Events...")
    df = pd.read_csv(input_file, parse_dates=['datetime'], index_col='datetime')
    
    # 1. Safe Copy
    shed_events = df[df['is_event_shed']].copy()
    up_events   = df[df['is_event_up']].copy()
    
    print(f"Total Shed Events: {len(shed_events)}")
    print(f"Total Up Events:   {len(up_events)}")
    
    # Pre-calculate Revenue Potential per Hour (for Top-N sorting)
    # Energy Revenue = E(kWh) * SMP
    if not shed_events.empty:
        shed_events['rev_per_hour'] = shed_events['E_shed_kWh'] * shed_events['SMP_hourly']
    else:
        shed_events['rev_per_hour'] = 0
        
    # ==========================================
    # 2. Capacity Calculation (Seasonal Approach)
    # ==========================================
    print("\n[1] Capacity Calculation (Seasonal Mean -> Annual Mean)")
    
    # Calc P90 and Mean PER SEASON first
    if shed_events.empty:
        cap_p90 = 0
        cap_mean = 0
    else:
        # Group by season
        seasonal_stats = shed_events.groupby('season')['Q_shed_kW'].agg(['mean', lambda x: x.quantile(0.90)])
        seasonal_stats.columns = ['Mean', 'P90']
        
        print("  Seasonal Stats:\n", seasonal_stats)
        
        # Annual Registered Capacity = Average of Seasonal Capacities
        # (Assuming we register for all available seasons)
        cap_mean = seasonal_stats['Mean'].mean()
        cap_p90  = seasonal_stats['P90'].mean()
        
    print(f"  Annual Base Case (Avg of Seasonal P90):      {cap_p90:,.2f} kW")
    print(f"  Annual Conservative (Avg of Seasonal Mean):  {cap_mean:,.2f} kW")
    
    # ==========================================
    # 3. Revenue Scenarios (Loops)
    # ==========================================
    base_rate_range = [35000, 40000, 45000]
    event_hours_range = [0, 10, 20, 30, 40, 50, 60]
    
    results = []
    
    print("\n[2] Generating Scenarios (Top-N Energy + BaseRate Loop)...")
    
    for base_rate in base_rate_range:
        for hrs in event_hours_range:
            
            # --- Energy Revenue (Top-N) ---
            # Sum of 'rev_per_hour' for the top 'hrs' events
            if hrs > 0 and not shed_events.empty:
                rev_en_shed = shed_events['rev_per_hour'].nlargest(hrs).sum()
            else:
                rev_en_shed = 0
                
            rev_en_up = 0 # Explicitly 0 as requested for now
            
            # --- Capacity Revenue ---
            # Base (P90)
            rev_cap_base = cap_p90 * base_rate
            # Conservative (Mean)
            rev_cap_cons = cap_mean * base_rate
            
            # Append Results
            # Scenario A: Base Cap + Energy
            results.append({
                'Base_Rate': base_rate,
                'Event_Hours': hrs,
                'Scenario': 'Base (P90 Cap)',
                'Capacity_KW': cap_p90,
                'Revenue_Cap_Shed': rev_cap_base,
                'Revenue_En_Shed': rev_en_shed,
                'Revenue_En_Up': rev_en_up,
                'Total_Revenue': rev_cap_base + rev_en_shed + rev_en_up
            })
            
            # Scenario B: Conservative Cap + Energy
            results.append({
                'Base_Rate': base_rate,
                'Event_Hours': hrs,
                'Scenario': 'Conservative (Mean Cap)',
                'Capacity_KW': cap_mean,
                'Revenue_Cap_Shed': rev_cap_cons,
                'Revenue_En_Shed': rev_en_shed, # Energy rev assumes same Top-N performance
                'Revenue_En_Up': rev_en_up,
                'Total_Revenue': rev_cap_cons + rev_en_shed + rev_en_up
            })
            
    res_df = pd.DataFrame(results)
    res_df.to_csv(output_csv, index=False)
    print(res_df.head())
    
    # ==========================================
    # 4. Figures
    # ==========================================
    
    # --- Figure A: Revenue Sensitivity (for BaseRate=40k only for clarity) ---
    plt.figure(figsize=(10, 6))
    
    subset = res_df[res_df['Base_Rate'] == 40000]
    pivot = subset.pivot(index='Event_Hours', columns='Scenario', values='Total_Revenue')
    
    # Plot Lines
    plt.plot(pivot.index, pivot['Base (P90 Cap)']/1e6, 'o-', linewidth=2.5, color='#1f77b4', label='Base (P90 Cap) @ 40k')
    plt.plot(pivot.index, pivot['Conservative (Mean Cap)']/1e6, 's--', linewidth=2, color='#7f7f7f', label='Conservative (Mean Cap) @ 40k')
    
    # Add Range Shading (Min/Max BaseRate for Base Scenario)
    # Filter for Base Scenario across all rates
    base_scen = res_df[res_df['Scenario'] == 'Base (P90 Cap)']
    min_rev = base_scen.groupby('Event_Hours')['Total_Revenue'].min() / 1e6
    max_rev = base_scen.groupby('Event_Hours')['Total_Revenue'].max() / 1e6
    
    plt.fill_between(pivot.index, min_rev, max_rev, color='#1f77b4', alpha=0.1, label='Base Rate Range (35k-45k)')
    
    plt.title('Annual DR Revenue Sensitivity (Top-N Energy, Seasonal Cap)', fontsize=14, fontweight='bold')
    plt.xlabel('Annual Event Hours (h)')
    plt.ylabel('Total Revenue (Million KRW)')
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.legend()
    plt.tight_layout()
    plt.savefig(f"{output_dir}/figure_revenue_sensitivity_refined.png", dpi=300)
    print(f"Saved {output_dir}/figure_revenue_sensitivity_refined.png")
    
    # --- Figure B: SMP Distribution (All vs Event vs Top-40) ---
    plt.figure(figsize=(8, 6))
    
    data_all = df['SMP_hourly']
    data_event = shed_events['SMP_hourly']
    
    # Top 40 Events (by Revenue Potential) - Represents "Realized Events"
    if not shed_events.empty:
        top_40_idx = shed_events.nlargest(40, 'rev_per_hour').index
        data_top40 = df.loc[top_40_idx, 'SMP_hourly']
    else:
        data_top40 = pd.Series([], dtype=float)
    
    # Create DF for Boxplot
    plot_data = pd.DataFrame({
        'SMP': pd.concat([data_all, data_event, data_top40]),
        'Group': ['All Hours'] * len(data_all) + 
                 ['Potential Events'] * len(data_event) + 
                 ['Top 40 Despatch'] * len(data_top40)
    })
    
    sns.boxplot(x='Group', y='SMP', data=plot_data, palette=['lightgray', 'salmon', 'red'], width=0.5)
    plt.title('SMP Distribution: Potential vs Actual Despatch Comparison', fontsize=14, fontweight='bold')
    plt.ylabel('System Marginal Price (KRW/kWh)')
    plt.grid(True, axis='y', linestyle='--', alpha=0.5)
    
    # Add text for Means
    means = plot_data.groupby('Group')['SMP'].mean()
    # Order: All, Potential, Top 40
    # Map index to x-coord: All=0, Pot=1, Top=2
    # But groupby sorts alphabetically? No, order depends on data.
    # Let's verify labels manually or just trust the plot order? 
    # Boxplot order is strictly alphabetical unless specified.
    # Specify order:
    order_list = ['All Hours', 'Potential Events', 'Top 40 Despatch']
    
    # Clear and redo with order
    plt.clf()
    sns.boxplot(x='Group', y='SMP', data=plot_data, order=order_list, palette=['lightgray', 'salmon', 'orangered'], width=0.5)
    plt.title('SMP Distribution: Potential vs Actual Despatch Comparison', fontsize=14, fontweight='bold')
    plt.ylabel('System Marginal Price (KRW/kWh)')
    plt.grid(True, axis='y', linestyle='--', alpha=0.5)
    
    plt.tight_layout()
    plt.savefig(f"{output_dir}/figure_smp_distribution_check.png", dpi=300)
    print(f"Saved {output_dir}/figure_smp_distribution_check.png")

if __name__ == "__main__":
    analyze_revenue_refined()

