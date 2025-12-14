import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os

# Set style
sns.set_theme(style="whitegrid")
plt.rcParams['font.family'] = 'sans-serif'

output_dir = 'figures/06_Final_Report'
output_csv = 'data/dcf_sensitivity_results.csv'

if not os.path.exists(output_dir):
    os.makedirs(output_dir)

# --- 1. Base Parameters (4.5MW 30y) ---
base_params = {
    'years': 30,
    'discount_rate': 0.045,
    'rev_cap_y1': 27_989_920,
    'event_hours': 40, 
    'unit_en_rev': 12_003_998 / 40.0, # ~300,100 KRW/h
    'g_cap': 0.02,
    'g_en': -0.01,
    'fee_aggregator': 0.10,
    
    'capex_initial': -370_000_000,
    # Reinvestment Logic
    # Option: Use "Rate of Initial" vs "Fixed Amount"
    # User Request: "Reinvestment Ratio (Year 10/20) ... Base: 30%"
    'capex_reinvest_rate': 0.30, # -111M
    'ess_refurb_cost': -100_000_000, # Year 15
    'opex_rate': 0.02 
}

# Derived or complex logic variables need careful handling
# We will create a simulator function

def calculate_dcf_npv(params):
    # Unpack
    r = params['discount_rate']
    y = params['years']
    
    # Revenue
    # Energy Rev = Unit * Hours
    # Note: User provided fixed Rev_En_Y1 before. Here we make it dynamic:
    rev_en_y1 = params['unit_en_rev'] * params['event_hours']
    rev_cap_y1 = params['rev_cap_y1']
    
    fee = params['fee_aggregator']
    
    # Costs
    # CAPEX
    capex_init = params['capex_initial']
    # Reinvest is ratio of *initial*
    capex_re = capex_init * params['capex_reinvest_rate'] 
    
    ess_cost = params['ess_refurb_cost']
    opex = capex_init * params['opex_rate'] 
    
    # Projection
    npv = 0
    npv += capex_init # Year 0
    
    for t in range(1, y + 1):
        # Rev
        growth_cap = (1 + params['g_cap']) ** (t - 1)
        growth_en  = (1 + params['g_en'])  ** (t - 1)
        
        rev_t = (rev_cap_y1 * growth_cap) + (rev_en_y1 * growth_en)
        net_rev_t = rev_t * (1 - fee)
        
        # Cost
        cost_t = opex
        
        if t in [10, 20]:
            cost_t += capex_re
            
        if t == 15:
            cost_t += ess_cost
            
        cf_net = net_rev_t + cost_t
        
        # Discount
        npv += cf_net / ((1 + r) ** t)
        
    return npv

def analyze_sensitivity():
    print("Starting Sensitivity Analysis (OAT - 9 Drivers)...")
    
    # Define Variables (Label, ParamKey, Low, Base, High, LowLabel, HighLabel)
    # Categories: Rev(1-4), Cost(5-8), Fin(9)
    
    variables = [
        # A. Revenue Drivers
        ('Capacity Growth', 'g_cap', 0.01, 0.02, 0.03, '1%', '3%'),
        ('Event Hours', 'event_hours', 10, 40, 60, '10h', '60h'),
        ('Energy Growth (SMP)', 'g_en', -0.03, -0.01, 0.01, '-3%', '+1%'),
        ('Aggregator Fee', 'fee_aggregator', 0.05, 0.10, 0.15, '5%', '15%'),
        
        # B. Cost Drivers
        # CAPEX: Base -370M. Low Param (-20% cost) -> -296M. High Param (+20% cost) -> -444M.
        # Math: -444M < -370M < -296M.
        # "Low Value" in sensitivity function usually means Min(X). 
        # Here Min(CAPEX) = -444M (High Cost). Max(CAPEX) = -296M (Low Cost).
        # We want the labels to map correctly. 
        # Low Input (-444M) -> label '+20% Cost'. High Input (-296M) -> label '-20% Cost'.
        ('Initial CAPEX', 'capex_initial', -370_000_000*1.2, -370_000_000, -370_000_000*0.8, '+20% Cost', '-20% Cost'),
        
        ('Reinvest Ratio (Y10/20)', 'capex_reinvest_rate', 0.50, 0.30, 0.10, '50%', '10%'),
        ('OPEX Rate', 'opex_rate', 0.03, 0.02, 0.01, '3%', '1%'),
        
        # ESS Refurb: Base -100M. Range 50M(-50M) ~ 200M(-200M).
        # Low Input (-200M) -> '200M Cost'. High Input (-50M) -> '50M Cost'.
        ('ESS Refurb (Y15)', 'ess_refurb_cost', -200_000_000, -100_000_000, -50_000_000, '200M Cost', '50M Cost'),
        
        # C. Financial
        ('Discount Rate', 'discount_rate', 0.035, 0.045, 0.055, '3.5%', '5.5%')
    ]
    
    results = []
    
    # Run Base Case First to check
    base_npv = calculate_dcf_npv(base_params)
    print(f"Base Case NPV: {base_npv/1e6:,.1f} M KRW")
    
    # Loop
    for label, key, low_val, base_val, high_val, low_lbl, high_lbl in variables:
        # Low Run
        p_low = base_params.copy()
        p_low[key] = low_val
        npv_low = calculate_dcf_npv(p_low)
        
        # High Run
        p_high = base_params.copy()
        p_high[key] = high_val
        npv_high = calculate_dcf_npv(p_high)
        
        # Calc Output Swing
        # We want to enable tornado plotting.
        # Usually Tornado: Width = |High - Low|. 
        # Direction: If High Input > Base NPV, it's positive correlation.
        
        results.append({
            'Variable': label,
            'Range_Width': abs(npv_high - npv_low),
            'NPV_Low_Input': npv_low,
            'NPV_High_Input': npv_high,
            'Low_Label': low_lbl,
            'High_Label': high_lbl
        })
        
    df = pd.DataFrame(results)
    
    # Sort by Range Width for Tornado
    df = df.sort_values('Range_Width', ascending=True) # Ascending for barh plot bottom-to-top
    
    df.to_csv(output_csv, index=False)
    print("\nSensitivity Analysis Complete. Top Drivers:")
    print(df.sort_values('Range_Width', ascending=False)[['Variable', 'Range_Width']].head())
    
    # --- Tornado Chart ---
    plt.figure(figsize=(10, 8))
    
    # Center line = Base NPV
    base_line = base_npv
    
    y = np.arange(len(df))
    
    # For each var, define 'Left' bar and 'Right' bar relative to Base
    # Left Bar: Min(NPV) to Base
    # Right Bar: Base to Max(NPV)
    # Color logic: 
    # If High Input gives High NPV -> Positive Corr (Blue High, Red Low)
    # If High Input gives Low NPV -> Negative Corr (Red High, Blue Low)
    
    for i, row in df.iterrows():
        # Identify Low/High Input NPVs
        val_low = row['NPV_Low_Input'] # Result of Low Input
        val_high = row['NPV_High_Input'] # Result of High Input
        
        # Standardize for color/side:
        # Left Bar: Min -> Base
        # Right Bar: Base -> Max
        min_v = min(val_low, val_high)
        max_v = max(val_low, val_high)
        
        # Determine labels
        # If High Input gave Max NPV (Positive Corr): Right=HighLbl, Left=LowLbl
        # If High Input gave Min NPV (Negative Corr): Right=LowLbl, Left=HighLbl
        
        if val_high > val_low: # Positive Corr
            right_lbl = row['High_Label']
            left_lbl  = row['Low_Label']
        else: # Negative Corr (e.g. Cost)
            right_lbl = row['Low_Label'] # Low Input (Low Cost) -> High NPV
            left_lbl  = row['High_Label'] # High Input (High Cost) -> Low NPV
            
        # Draw Bars
        # Left (Red-ish usually for downside, but here let's use colors for Input Type?)
        # Convention: Tornado often colored by sensitivity or unified.
        # Let's use: Blue for "Result > Base", Red for "Result < Base"
        
        # Left Bar (Min to Base) - Result < Base (Red)
        plt.barh(i, base_line - min_v, left=min_v, color='salmon', alpha=0.9)
        plt.text(min_v - 2e6, i, left_lbl, ha='right', va='center', fontsize=9)
        
        # Right Bar (Base to Max) - Result > Base (Blue)
        plt.barh(i, max_v - base_line, left=base_line, color='skyblue', alpha=0.9)
        plt.text(max_v + 2e6, i, right_lbl, ha='left', va='center', fontsize=9)
            
    plt.yticks(y, df['Variable'])
    plt.axvline(base_line, color='black', linestyle='--', linewidth=1)
    
    # Label Base NPV line
    plt.text(base_line, len(df)-0.5, f'Base NPV: {base_line/1e6:,.1f}M', ha='center', va='bottom', fontweight='bold')
    
    plt.xlabel('NPV (KRW)')
    plt.title('Tornado Analysis: NPV Sensitivity (30y DCF)', fontsize=14, fontweight='bold')
    
    # Format X axis millions
    plt.grid(True, linestyle='--', alpha=0.5)
    plt.tight_layout()
    plt.savefig(f"{output_dir}/figure_dcf_tornado.png", dpi=300)
    print("Saved Tornado Chart.")

if __name__ == "__main__":
    analyze_sensitivity()
