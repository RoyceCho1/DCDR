import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os

# Set style
sns.set_theme(style="whitegrid")
plt.rcParams['font.family'] = 'sans-serif'

output_dir = 'figures/06_Final_Report'
output_csv = 'data/dcf_30y_projection_50mw.csv'
output_summary_csv = 'data/dcf_summary_metrics_50mw.csv'

if not os.path.exists(output_dir):
    os.makedirs(output_dir)

# --- 1. Parameters (50MW Scale-up) ---
# Base Values (4.5MW)
base_load_mw = 4.5
target_load_mw = 50.0
scale_load = target_load_mw / base_load_mw # 11.111...

# Base Financials (4.5MW)
base_rev_cap = 27_989_920
base_rev_en  = 12_003_998
base_capex_init = -370_000_000
base_capex_re   = -110_000_000

# Scaled Parameters
rev_cap_y1 = base_rev_cap * scale_load
rev_en_y1  = base_rev_en  * scale_load

# CAPEX: Scale * 0.5 (Economy of Scale)
capex_initial  = base_capex_init * scale_load * 0.5
capex_reinvest = base_capex_re   * scale_load * 0.5

# ESS Refurbishment: Scale by ESS Capacity (5MW -> 50MW = 10x)
ess_scale = 50.0 / 5.0
ess_refurbish = -100_000_000 * ess_scale # -1.0 Billion KRW

# OPEX: 2% of New CAPEX
opex_annual = capex_initial * 0.02

# Common Parameters
years = 30
discount_rate = 0.045
g_cap = 0.02
g_en  = -0.01
fee_aggregator = 0.10

def analyze_dcf_50mw():
    print(f"Starting DCF Analysis (50MW Scale-up)...")
    print(f"  Scale Factor (Load): {scale_load:.2f}x")
    print(f"  Scale Factor (ESS):  {ess_scale:.2f}x")
    print(f"  Initial CAPEX: {capex_initial/1e8:,.2f} 억 KRW")
    print(f"  ESS Refurb:    {ess_refurbish/1e8:,.2f} 억 KRW")
    
    # --- 2. Cash Flow Projection ---
    projection = []
    
    # Year 0
    row_0 = {
        'Year': 0,
        'Rev_Gross': 0, 'Rev_Net': 0,
        'OPEX': 0,
        'CAPEX': capex_initial, # Combined column for plot simplicity? No, keep separate
        'CF_Net': capex_initial,
        'CF_Discounted': capex_initial
    }
    projection.append(row_0)
    
    # Year 1 to 30
    for t in range(1, years + 1):
        # Revenue
        r_cap = rev_cap_y1 * ((1 + g_cap) ** (t - 1))
        r_en  = rev_en_y1  * ((1 + g_en)  ** (t - 1))
        r_gross = r_cap + r_en
        r_net = r_gross * (1 - fee_aggregator)
        
        # Costs
        opex = opex_annual
        
        cap_cost = 0
        if t in [10, 20]:
            cap_cost += capex_reinvest
            
        if t == 15:
            cap_cost += ess_refurbish
            
        # Cash Flow
        cf_net = r_net + opex + cap_cost
        
        # Discount
        df = 1 / ((1 + discount_rate) ** t)
        cf_disc = cf_net * df
        
        projection.append({
            'Year': t,
            'Rev_Gross': r_gross,
            'Rev_Net': r_net,
            'OPEX': opex,
            'CAPEX': cap_cost, # Reinvest + ESS combined here for csv
            'CF_Net': cf_net,
            'CF_Discounted': cf_disc
        })
        
    df = pd.DataFrame(projection)
    
    # --- 3. Metrics ---
    npv = df['CF_Discounted'].sum()
    
    # IRR
    t_vals = df['Year'].values
    cf_vals = df['CF_Net'].values
    
    def npv_func(r):
        return np.sum(cf_vals / ((1 + r) ** t_vals))
        
    from scipy import optimize
    try:
        irr = optimize.newton(npv_func, 0.1)
    except:
        irr = np.nan
        
    df['Cumulative_DCF'] = df['CF_Discounted'].cumsum()
    payback_years = df[df['Cumulative_DCF'] >= 0]['Year'].min() if not df[df['Cumulative_DCF'] >= 0].empty else np.nan
    
    print("\n[Economic Indicators - 50MW]")
    print(f"  NPV (30yr, {discount_rate:.1%}): {npv:,.0f} KRW ({npv/1e8:.2f} 억)")
    print(f"  IRR: {irr:.2%}")
    print(f"  Payback Period: {payback_years} Years")
    
    df.to_csv(output_csv, index=False)
    
    # --- 4. Figures ---
    # Cash Flow Plot (50MW)
    plt.figure(figsize=(12, 6))
    years_arr = df['Year']
    
    colors = ['firebrick' if cf < 0 else 'forestgreen' for cf in df['CF_Net']]
    plt.bar(years_arr, df['CF_Net']/1e8, color=colors, alpha=0.6, label='Net Cash Flow')
    plt.plot(years_arr, df['Cumulative_DCF']/1e8, color='navy', linewidth=2.5, marker='o', markersize=4, label='Cumulative Discounted CF')
    
    plt.axhline(0, color='black', linewidth=0.8)
    plt.title('30-Year Cash Flow Projection (50MW Hyperscale)', fontsize=14, fontweight='bold')
    plt.xlabel('Year')
    plt.ylabel('Amount (100 Million KRW)') # Unit adjusted to 'Eok'
    plt.legend()
    plt.grid(True, linestyle='--', alpha=0.6)
    
    if not np.isnan(payback_years):
        plt.axvline(payback_years, color='orange', linestyle='--', alpha=0.8)
        plt.text(payback_years+0.5, df['Cumulative_DCF'].max()/1e8 * 0.5, f'Payback: Year {payback_years}', color='orange', fontweight='bold')
        
    plt.tight_layout()
    plt.savefig(f"{output_dir}/figure_dcf_cashflow_50mw.png", dpi=300)
    print("Figures saved.")

if __name__ == "__main__":
    analyze_dcf_50mw()
