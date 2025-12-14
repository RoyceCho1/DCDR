import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os

# Set style
sns.set_theme(style="whitegrid")
plt.rcParams['font.family'] = 'sans-serif'

input_dr = 'data/dr_simulation_results.csv'
input_smp = 'data/smp_clean.csv'
output_dir = 'figures/06_Final_Report'
output_data = 'data/revenue_results.csv'

if not os.path.exists(output_dir):
    os.makedirs(output_dir)

def analyze_revenue():
    print("Loading Data...")
    df_dr = pd.read_csv(input_dr, parse_dates=['datetime'], index_col='datetime')
    df_smp = pd.read_csv(input_smp, parse_dates=['datetime'], index_col='datetime')
    
    # Merge
    # DR results are 15-min. SMP is 15-min (resampled previously).
    # Inner join to ensure timestamps match
    df = df_dr.join(df_smp, how='inner')
    print(f"Merged Data: {len(df)} rows")
    
    # ---------------------------------------------------------
    # 1. Calculate Registered Capacity (Capacity Payment Base)
    # ---------------------------------------------------------
    # Assumption: Registered Capacity = Average Shed Potential during "Standard" DR windows (Shed)
    # Or should it be Seasonally distinct?
    # KPX Reliability DR usually has a single registered capacity or seasonal.
    # We will calculate "Seasonal Average Registered Capacity".
    
    seasons = ['Spring', 'Summer', 'Fall', 'Winter'] # Ensure Spring is included
    
    reg_cap_map = {}
    print("\n[1] Registered Capacity per Season")
    for season in seasons:
        # Filter for Shed Windows
        mask = (df['season'] == season) & df['mask_shed']
        if mask.any():
            avg_cap = df.loc[mask, 'Q_shed_kW'].mean()
        else:
            avg_cap = 0.0
            
        reg_cap_map[season] = avg_cap
        print(f"  {season}: {avg_cap:,.2f} kW")
        
    # ---------------------------------------------------------
    # 2. Revenue Calculation Function
    # ---------------------------------------------------------
    def calculate_revenue(base_rate, event_hours):
        """
        base_rate: KRW/kW/year
        event_hours: Target hours of DR dispatch per year
        """
        # A. Capacity Payment
        # Cap Revenue = Sum(Seasonal_Cap * Seasonal_Weight?) * BaseRate?
        # Simplification: Average Capacity * Base Rate
        # Or if registered once/year: Max? Min?
        # Let's use Weighted Average or just Average of Active Seasons?
        # Use Simple Average of existing potentials.
        
        valid_caps = [c for c in reg_cap_map.values() if c > 0]
        if not valid_caps:
            final_cap = 0
        else:
            final_cap = np.mean(valid_caps)
            
        rev_cap = final_cap * base_rate
        
        # B. Energy Payment
        # Energy Rev = Energy_Reduced (kWh) * SMP
        # How to distribute 'event_hours' across seasons?
        # Assume pro-rated by season length or just uniform?
        # Let's assume events occur during valid windows.
        # We need "Average Revenue per 1-Hour Event".
        
        # Calculate Avg Revenue/kWh during windows per season
        season_unit_rev = {}
        for season in seasons:
             mask = (df['season'] == season) & df['mask_shed']
             if mask.any():
                 # SMP during windows
                 avg_smp = df.loc[mask, 'SMP'].mean()
                 
                 # Capacity (kW)
                 cap = reg_cap_map[season]
                 
                 # Revenue per hour (KRW/h) = kW * 1h * SMP (KRW/kWh) ?
                 # Actually settlement is Max(SMP, Floor)? Let's just use SMP.
                 unit_rev = cap * avg_smp
             else:
                 unit_rev = 0
             season_unit_rev[season] = unit_rev
        
        # Average Unit Revenue (KRW/h) across active seasons
        valid_units = [u for u in season_unit_rev.values() if u > 0]
        avg_unit_rev = np.mean(valid_units) if valid_units else 0
        
        rev_energy = avg_unit_rev * event_hours
        
        return rev_cap, rev_energy, rev_cap + rev_energy

    # ---------------------------------------------------------
    # 3. Scenarios (Sensitivity)
    # ---------------------------------------------------------
    results = []
    
    # Scenario Params
    base_rate_default = 40000 # KRW/kW
    event_hours_range = [0, 10, 20, 30, 40, 50, 60]
    
    print("\n[2] Calculating Scenarios...")
    for hrs in event_hours_range:
        c_rev, e_rev, t_rev = calculate_revenue(base_rate_default, hrs)
        results.append({
            'Base_Rate': base_rate_default,
            'Event_Hours': hrs,
            'Cap_Revenue': c_rev,
            'Energy_Revenue': e_rev,
            'Total_Revenue': t_rev
        })
        
    res_df = pd.DataFrame(results)
    
    # Save
    res_df.to_csv(output_data, index=False)
    print(res_df)
    
    # ---------------------------------------------------------
    # 4. Visualization (Sensitivity)
    # ---------------------------------------------------------
    plt.figure(figsize=(10, 6))
    
    # Plot Total Revenue
    plt.plot(res_df['Event_Hours'], res_df['Total_Revenue'] / 1e6, 'o-', linewidth=2, label='Total Revenue')
    
    # Stacked Area for Cap vs Energy?
    # plt.stackplot(res_df['Event_Hours'], 
    #               res_df['Cap_Revenue']/1e6, 
    #               res_df['Energy_Revenue']/1e6, 
    #               labels=['Capacity Payment', 'Energy Payment'], alpha=0.3)
    
    # Better: Line plot with components
    plt.plot(res_df['Event_Hours'], res_df['Cap_Revenue'] / 1e6, '--', color='gray', label='Capacity Payment (Fixed)')
    plt.plot(res_df['Event_Hours'], res_df['Energy_Revenue'] / 1e6, ':', color='green', label='Energy Payment (Variable)')

    plt.title(f'Annual DR Revenue Sensitivity (Base Rate: {base_rate_default:,} KRW/kW)', fontsize=14, fontweight='bold')
    plt.xlabel('Annual Event Hours (h)')
    plt.ylabel('Revenue (Million KRW)')
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.legend()
    
    # Add labels
    for i, row in res_df.iterrows():
        if row['Event_Hours'] % 20 == 0: # Label every 20h
            plt.text(row['Event_Hours'], row['Total_Revenue']/1e6 + 2, 
                     f"{row['Total_Revenue']/1e6:.1f} M", ha='center', fontweight='bold')
    
    plt.tight_layout()
    plot_file = f"{output_dir}/figure_revenue_sensitivity.png"
    plt.savefig(plot_file, dpi=300)
    print(f"Saved {plot_file}")

if __name__ == "__main__":
    analyze_revenue()
