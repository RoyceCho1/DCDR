import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os
import calendar

# Set style
sns.set_theme(style="whitegrid")
plt.rcParams['font.family'] = 'sans-serif'

input_file = 'data/dr_events_1h.csv'
output_dir = 'figures/06_Final_Report'
output_csv = 'data/revenue_capacity_monthly.csv'

if not os.path.exists(output_dir):
    os.makedirs(output_dir)

# --- 1. Monthly Rate Data (Provided by User) ---
# Format: Month: [Low, High]
rates_data = {
    1: [2348.64, 2568.96],
    2: [2276.40, 2490.60],
    3: [1674.40, 1831.60],
    4: [942.26, 1030.26],
    5: [861.60, 942.40],
    6: [1815.45, 1986.07],
    7: [3075.10, 3183.20],
    8: [2654.00, 2748.00],
    9: [2325.40, 2407.02],
    10: [952.02, 985.68],
    11: [1876.20, 1941.60],
    12: [2862.20, 2963.40]
}

def get_weekdays_count(year, month):
    """Returns number of weekdays (Mon-Fri) in a month."""
    cal = calendar.monthcalendar(year, month)
    weekdays_count = 0
    for week in cal:
        # week is a list of 7 days; 0 where day doesn't belong to month
        # Mon=0, ..., Fri=4. Check these indices.
        # But day value must be > 0.
        for i in range(5): # 0 to 4
            if week[i] != 0:
                weekdays_count += 1
    return weekdays_count

def analyze_revenue_monthly():
    print("Loading Data...")
    df = pd.read_csv(input_file, parse_dates=['datetime'], index_col='datetime')
    
    # Add weekday info (0=Mon, 6=Sun) just in case re-loading loses it (it shouldn't if datetime index)
    df['weekday'] = df.index.weekday
    df['month'] = df.index.month
    
    # --- 2. Filter Valid Events ---
    # Condition: is_event_shed == True AND weekday < 5
    valid_mask = (df['is_event_shed']) & (df['weekday'] < 5)
    valid_events = df[valid_mask].copy()
    
    print(f"Total Shed Events: {df['is_event_shed'].sum()}")
    print(f"Valid Weekday Shed Events: {len(valid_events)}")
    
    # --- 3. Calculate Registered Capacity ---
    if valid_events.empty:
        print("WARNING: No valid weekday events found!")
        cap_mean = 0
        cap_p90 = 0
        cap_p95 = 0
    else:
        q_vals = valid_events['Q_shed_kW']
        cap_mean = q_vals.mean()
        cap_p90  = q_vals.quantile(0.90)
        cap_p95  = q_vals.quantile(0.95)
        
    print("\n[Registered Capacity Candidates]")
    print(f"  Conservative (Mean): {cap_mean:,.2f} kW")
    print(f"  Base Case (P90):     {cap_p90:,.2f} kW")
    print(f"  Aggressive (P95):    {cap_p95:,.2f} kW")
    
    # --- 4. Monthly Calculation Loop ---
    # Analysis Period: June 2024 to May 2025
    monthly_results = []
    
    # Define period
    start_date = pd.Timestamp('2024-06-01')
    end_date = pd.Timestamp('2025-05-31')
    current = start_date
    
    total_rev_low = 0
    total_rev_base = 0
    total_rev_high = 0
    
    print("\n[Monthly Revenue Calculation]")
    print(f"{'Month':<10} | {'Rate(Base)':<10} | {'Weekday%':<10} | {'Rev(Base)':<15}")
    
    # Iterate month by month
    while current <= end_date:
        y = current.year
        m = current.month
        
        # 4-1. Availability Factor
        total_days = calendar.monthrange(y, m)[1]
        n_weekdays = get_weekdays_count(y, m)
        avail_factor = n_weekdays / total_days
        
        # 4-2. Rates
        r_low, r_high = rates_data[m]
        r_base = (r_low + r_high) / 2
        
        # 4-3. Revenue (Using Base Capacity P90)
        # However, we want to output LOW/BASE/HIGH scenarios for Annual.
        # But usually 'Scenario' means we vary the CAPACITY definition or the RATE?
        # User request 5-1 says: "Revenue_cap[m, s] ... s in {low, base, high}"
        # It implies varying the RATE (low/base/high provided in table)
        # AND keeping Capacity Fixed (Base Case P90)?
        # "Target 3: Annual Revenue (Conservative/Base/Aggressive)" usually refers to the final outcome range.
        # Let's assume:
        # - Low Scenario: Rate_Low * Capacity_P90 (or Conservative Cap?)
        # User said "Scenario s in {low, base, high}" refers to RATE columns.
        # But Step 6 says "Conservative(low), Base, Aggressive(high)".
        # Let's fix Capacity to P90 for all rate scenarios to isolate Price Sensitivity.
        # Or should we mix? Let's strictly follow User 5-1: Vary Rate. Use Capacity_reg=P90.
        
        rev_m_low  = cap_p90 * r_low * avail_factor
        rev_m_base = cap_p90 * r_base * avail_factor
        rev_m_high = cap_p90 * r_high * avail_factor
        
        monthly_results.append({
            'Year': y,
            'Month': m,
            'Label': f"{y}-{m:02d}",
            'Rate_Low': r_low,
            'Rate_Base': r_base,
            'Rate_High': r_high,
            'Total_Days': total_days,
            'Weekdays': n_weekdays,
            'Avail_Factor': avail_factor,
            'Capacity_Reg_kW': cap_p90,
            'Rev_Low': rev_m_low,
            'Rev_Base': rev_m_base,
            'Rev_High': rev_m_high
        })
        
        print(f"{y}-{m:02d}    | {r_base:<10.2f} | {avail_factor:<10.2f} | {rev_m_base:,.0f}")
        
        # Move to next month
        current += pd.offsets.MonthBegin(1)
        
    df_res = pd.DataFrame(monthly_results)
    df_res.to_csv(output_csv, index=False)
    
    # --- 5. Annual Summary ---
    ann_low = df_res['Rev_Low'].sum()
    ann_base = df_res['Rev_Base'].sum()
    ann_high = df_res['Rev_High'].sum()
    
    print("\n[Annual Capacity Revenue Summary]")
    print(f"  Low Rate Scenario:  {ann_low/1e6:,.2f} M KRW")
    print(f"  Base Rate Scenario: {ann_base/1e6:,.2f} M KRW")
    print(f"  High Rate Scenario: {ann_high/1e6:,.2f} M KRW")
    
    # --- 6. Figures ---
    
    # Fig 1: Monthly Unit Price (Band)
    plt.figure(figsize=(10, 6))
    x = range(len(df_res))
    plt.plot(x, df_res['Rate_Base'], 'o-', color='navy', label='Base Rate')
    plt.fill_between(x, df_res['Rate_Low'], df_res['Rate_High'], color='skyblue', alpha=0.4, label='Rate Range (Low-High)')
    plt.xticks(x, df_res['Label'], rotation=45)
    plt.title('Monthly Capacity Payment Rates (Unit Price)', fontsize=14, fontweight='bold')
    plt.ylabel('Rate (KRW/kW-month)')
    plt.legend()
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.tight_layout()
    plt.savefig(f"{output_dir}/figure_monthly_cp_rates.png", dpi=300)
    
    # Fig 2: Monthly Revenue (Base Case)
    plt.figure(figsize=(10, 6))
    # Bar plot
    bars = plt.bar(x, df_res['Rev_Base']/1e6, color='forestgreen', alpha=0.8)
    plt.xticks(x, df_res['Label'], rotation=45)
    plt.title('Monthly Capacity Revenue (Base Case: P90 Cap)', fontsize=14, fontweight='bold')
    plt.ylabel('Revenue (Million KRW)')
    plt.grid(True, axis='y', linestyle='--', alpha=0.6)
    
    # Add values
    for rect in bars:
        height = rect.get_height()
        plt.text(rect.get_x() + rect.get_width()/2.0, height, f'{height:.1f}', ha='center', va='bottom')
        
    plt.tight_layout()
    plt.savefig(f"{output_dir}/figure_monthly_cp_revenue.png", dpi=300)
    
    # Fig 3: Annual Comparison
    plt.figure(figsize=(8, 6))
    scenarios = ['Low', 'Base', 'High']
    values = [ann_low/1e6, ann_base/1e6, ann_high/1e6]
    colors = ['gray', 'navy', 'red']
    
    plt.bar(scenarios, values, color=colors, alpha=0.8, width=0.5)
    plt.title('Annual Capacity Revenue Scenarios', fontsize=14, fontweight='bold')
    plt.ylabel('Annual Revenue (Million KRW)')
    
    for i, v in enumerate(values):
        plt.text(i, v, f'{v:.1f} M', ha='center', va='bottom', fontweight='bold', fontsize=12)
        
    plt.ylim(0, max(values)*1.15)
    plt.grid(True, axis='y', linestyle='--', alpha=0.6)
    plt.tight_layout()
    plt.savefig(f"{output_dir}/figure_annual_cp_comparison.png", dpi=300)
    
    print("Figures saved.")

if __name__ == "__main__":
    analyze_revenue_monthly()
