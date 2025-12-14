import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os
import calendar

# Set style
sns.set_theme(style="whitegrid")
plt.rcParams['font.family'] = 'sans-serif'

input_events = 'data/dr_events_1h.csv'
output_dir = 'figures/06_Final_Report'
output_csv = 'data/revenue_results_final.csv'

if not os.path.exists(output_dir):
    os.makedirs(output_dir)

# --- Monthly Rate Data ---
rates_data = {
    1: [2348.64, 2568.96], 2: [2276.40, 2490.60], 3: [1674.40, 1831.60],
    4: [942.26, 1030.26],  5: [861.60, 942.40],   6: [1815.45, 1986.07],
    7: [3075.10, 3183.20], 8: [2654.00, 2748.00], 9: [2325.40, 2407.02],
    10: [952.02, 985.68],  11: [1876.20, 1941.60], 12: [2862.20, 2963.40]
}

def get_weekdays_count(year, month):
    cal = calendar.monthcalendar(year, month)
    count = 0
    for week in cal:
        for i in range(5):
            if week[i] != 0: count += 1
    return count

def analyze_revenue_final():
    print("Loading Standardized DR Events...")
    df = pd.read_csv(input_events, parse_dates=['datetime'], index_col='datetime')
    
    # Enable Month/Year access
    df['month'] = df.index.month
    df['year'] = df.index.year
    df['weekday'] = df.index.weekday # 0=Mon
    
    # 1. Capacity Calculation (Monthly Detailed)
    # Filter Valid Events for Capacity Reg
    valid_mask = (df['is_event_shed']) & (df['weekday'] < 5)
    valid_events = df[valid_mask].copy()
    
    # Registered Capacity (P90)
    if valid_events.empty:
        reg_cap_kw = 0
    else:
        # P90 of valid weekday shed events
        reg_cap_kw = valid_events['Q_shed_kW'].quantile(0.90)
        
    print(f"Registered Capacity (P90): {reg_cap_kw:,.2f} kW")
    
    # Calculate Annual Base Capacity Revenue
    # Loop months
    total_rev_cap = {'Low': 0.0, 'Base': 0.0, 'High': 0.0}
    
    start_date = pd.Timestamp('2024-06-01')
    end_date = pd.Timestamp('2025-05-31')
    current = start_date
    
    while current <= end_date:
        y, m = current.year, current.month
        
        # Availability
        total_days = calendar.monthrange(y, m)[1]
        n_weekdays = get_weekdays_count(y, m)
        avail = n_weekdays / total_days
        
        # Rates
        r_low, r_high = rates_data[m]
        r_base = (r_low + r_high) / 2
        
        total_rev_cap['Low']  += reg_cap_kw * r_low * avail
        total_rev_cap['Base'] += reg_cap_kw * r_base * avail
        total_rev_cap['High'] += reg_cap_kw * r_high * avail
        
        current += pd.offsets.MonthBegin(1)
        
    print(f"Annual Capacity Revenue (Base): {total_rev_cap['Base']/1e6:,.2f} M KRW")
    
    # 2. Energy Calculation (Top-N)
    # Pre-calc revenue potential
    shed_events = df[df['is_event_shed']].copy()
    if not shed_events.empty:
        shed_events['rev_per_hour'] = shed_events['E_shed_kWh'] * shed_events['SMP_hourly']
    else:
        shed_events['rev_per_hour'] = 0
        
    # 3. Create Scenarios
    # Varies: Rate Scenario (Low/Base/High) AND Event Hours (0..60)
    
    results = []
    event_hours_range = [0, 10, 20, 30, 40, 50, 60]
    scenarios = ['Low', 'Base', 'High']
    colors = {'Low': 'gray', 'Base': '#1f77b4', 'High': 'red'}
    
    for scen in scenarios:
        cap_rev = total_rev_cap[scen]
        
        for hrs in event_hours_range:
            # Energy Rev Top-N
            if hrs > 0 and not shed_events.empty:
                en_rev = shed_events['rev_per_hour'].nlargest(hrs).sum()
            else:
                en_rev = 0
            
            results.append({
                'Rate_Scenario': scen,
                'Event_Hours': hrs,
                'Capacity_Revenue': cap_rev,
                'Energy_Revenue': en_rev,
                'Total_Revenue': cap_rev + en_rev
            })
            
    res_df = pd.DataFrame(results)
    res_df.to_csv(output_csv, index=False)
    
    # 4. Visualization
    plt.figure(figsize=(10, 6))
    
    pivot = res_df.pivot(index='Event_Hours', columns='Rate_Scenario', values='Total_Revenue')
    
    # Plot Lines
    for scen in ['Low', 'Base', 'High']:
        plt.plot(pivot.index, pivot[scen]/1e6, 'o-', linewidth=2, color=colors[scen], label=f'{scen} Rate Scenario')
        
    # Shade Range
    plt.fill_between(pivot.index, pivot['Low']/1e6, pivot['High']/1e6, color='gray', alpha=0.15)
    
    plt.title('Annual DR Revenue Sensitivity (Final Monthly Detailed)', fontsize=14, fontweight='bold')
    plt.xlabel('Annual Event Hours (h)')
    plt.ylabel('Total Revenue (Million KRW)')
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.legend()
    plt.tight_layout()
    
    plot_path = f"{output_dir}/figure_revenue_sensitivity_final.png"
    plt.savefig(plot_path, dpi=300)
    print(f"Saved {plot_path}")

if __name__ == "__main__":
    analyze_revenue_final()
