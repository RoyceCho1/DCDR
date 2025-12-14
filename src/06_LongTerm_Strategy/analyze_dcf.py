import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os

# Set style
sns.set_theme(style="whitegrid")
plt.rcParams['font.family'] = 'sans-serif'

output_dir = 'figures/06_Final_Report'
output_csv = 'data/dcf_30y_projection.csv'
output_summary_csv = 'data/dcf_summary_metrics.csv'

if not os.path.exists(output_dir):
    os.makedirs(output_dir)

# --- 1. Parameters ---
# Analysis Period
years = 30
discount_rate = 0.045

# Revenue (Year 1)
rev_cap_y1 = 27_989_920
rev_en_y1  = 12_003_998
g_cap = 0.02
g_en  = -0.01

fee_aggregator = 0.10

# Costs
capex_initial = -370_000_000  # Year 0
capex_reinvest = -110_000_000 # Year 10, 20
ess_refurbish = -100_000_000  # Year 15
opex_annual   = -7_400_000    # Year 1~30

def calculate_irr(cf_stream):
    """Calculates Internal Rate of Return (IRR)."""
    # Use numpy-financial if available? Or root finding.
    # Simple Newton-Raphson on NPV(r) = 0
    # NPV = sum(CF_t / (1+r)^t)
    
    # Try basic range 0.0 to 1.0 (0% to 100%)
    # If not converging, return nan
    try:
        # np.irr is deprecated, use close equivalent logic
        roots = np.roots(cf_stream[::-1]) # Roots of polynomial
        real_roots = [r.real for r in roots if r.imag == 0 and r.real > 0]
        # r = 1/(1+IRR) => IRR = (1/r) - 1
        # Usually looking for a positive real IRR
        rates = [(1/r - 1) for r in real_roots if r > 0]
        # Filter reasonable rates e.g. -0.5 to 1.5
        valid_rates = [r for r in rates if -0.5 < r < 2.0]
        if valid_rates:
            return min(valid_rates) # Usually the smallest positive one valid? Or largest?
            # Standard financial IRR is the one > -1.
            # Let's assume the one closest to 0.1?
            # Actually, standard project finance usually has one unique IRR.
            # Let's pick the one > -0.9 and closest to plausible.
            return valid_rates[0]
    except:
        pass
    return np.nan

def analyze_dcf():
    print("Starting DCF Analysis (30 Years)...")
    
    # --- 2. Cash Flow Projection ---
    projection = []
    
    # Year 0
    row_0 = {
        'Year': 0,
        'Rev_Cap': 0, 'Rev_En': 0, 'Rev_Gross': 0, 'Rev_Net': 0,
        'OPEX': 0,
        'CAPEX_Init': capex_initial,
        'CAPEX_Reinvest': 0,
        'ESS_Refurb': 0,
        'CF_Net': capex_initial,
        'Discount_Factor': 1.0,
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
        
        cap_re = 0
        if t in [10, 20]:
            cap_re = capex_reinvest
            
        ess_cost = 0
        if t == 15:
            ess_cost = ess_refurbish
            
        # Cash Flow
        cf_net = r_net + opex + cap_re + ess_cost # Costs are negative
        
        # Discount
        df = 1 / ((1 + discount_rate) ** t)
        cf_disc = cf_net * df
        
        projection.append({
            'Year': t,
            'Rev_Cap': r_cap,
            'Rev_En': r_en,
            'Rev_Gross': r_gross,
            'Rev_Net': r_net,
            'OPEX': opex,
            'CAPEX_Init': 0,
            'CAPEX_Reinvest': cap_re,
            'ESS_Refurb': ess_cost,
            'CF_Net': cf_net,
            'Discount_Factor': df,
            'CF_Discounted': cf_disc
        })
        
    df = pd.DataFrame(projection)
    
    # --- 3. Metrics ---
    npv = df['CF_Discounted'].sum()
    
    # IRR
    # Quick impl of IRR using finance library approach approximation
    t_vals = df['Year'].values
    cf_vals = df['CF_Net'].values
    
    # Using simple iterative search for IRR
    # NPV(rate) function
    def npv_func(r):
        return np.sum(cf_vals / ((1 + r) ** t_vals))
        
    from scipy import optimize
    try:
        irr = optimize.newton(npv_func, 0.1)
    except:
        irr = np.nan
        
    # Cumulative DCF
    df['Cumulative_DCF'] = df['CF_Discounted'].cumsum()
    
    # Payback Period (Discounted)
    # Year where Cumulative DCF becomes positive
    payback_years = df[df['Cumulative_DCF'] >= 0]['Year'].min() if not df[df['Cumulative_DCF'] >= 0].empty else np.nan
    
    print("\n[Economic Indicators]")
    print(f"  NPV (30yr, {discount_rate:.1%}): {npv:,.0f} KRW")
    print(f"  IRR: {irr:.2%}")
    print(f"  Payback Period (Discounted): {payback_years} Years")
    
    # Save CSV
    df.to_csv(output_csv, index=False)
    
    # Save Summary
    summary = pd.DataFrame([{
        'Metric': 'NPV', 'Value': npv, 'Unit': 'KRW'
    }, {
        'Metric': 'IRR', 'Value': irr*100, 'Unit': '%'
    }, {
        'Metric': 'Payback', 'Value': payback_years, 'Unit': 'Years'
    }])
    summary.to_csv(output_summary_csv, index=False)
    
    # --- 4. Figures ---
    
    # Fig 1: Cash Flow Waterfall / Bar & Line
    plt.figure(figsize=(12, 6))
    
    years_arr = df['Year']
    
    # Plot Net Cash Flow Bars
    # Color: Blue for positive, Red for negative
    colors = ['firebrick' if cf < 0 else 'forestgreen' for cf in df['CF_Net']]
    plt.bar(years_arr, df['CF_Net']/1e6, color=colors, alpha=0.6, label='Net Cash Flow')
    
    # Plot Cumulative Discounted CF Line
    plt.plot(years_arr, df['Cumulative_DCF']/1e6, color='navy', linewidth=2.5, marker='o', markersize=4, label='Cumulative Discounted CF')
    
    plt.axhline(0, color='black', linewidth=0.8)
    plt.title('30-Year Cash Flow Projection & Break-even', fontsize=14, fontweight='bold')
    plt.xlabel('Year')
    plt.ylabel('Amount (Million KRW)')
    plt.legend()
    plt.grid(True, linestyle='--', alpha=0.6)
    
    # Mark payback
    if not np.isnan(payback_years):
        plt.axvline(payback_years, color='orange', linestyle='--', alpha=0.8)
        plt.text(payback_years+0.5, df['Cumulative_DCF'].max()/1e6 * 0.5, f'Payback: Year {payback_years}', color='orange', fontweight='bold')
        
    plt.tight_layout()
    plt.savefig(f"{output_dir}/figure_dcf_cashflow.png", dpi=300)
    
    # Fig 2: Revenue Composition Area Chart
    # Stacked Area: Cap vs En
    plt.figure(figsize=(10, 6))
    
    # Only years 1-30
    df_op = df[df['Year'] >= 1]
    x = df_op['Year']
    
    plt.stackplot(x, df_op['Rev_Cap']/1e6, df_op['Rev_En']/1e6, labels=['Capacity Revenue', 'Energy Revenue'], colors=['#1f77b4', '#ff7f0e'], alpha=0.8)
    
    plt.title('Projected Annual Revenue Composition (30 Years)', fontsize=14, fontweight='bold')
    plt.xlabel('Year')
    plt.ylabel('Revenue (Million KRW)')
    plt.legend(loc='upper left')
    plt.grid(True, linestyle='--', alpha=0.6)
    
    plt.tight_layout()
    plt.savefig(f"{output_dir}/figure_dcf_revenue_composition.png", dpi=300)
    
    print("Figures saved.")

if __name__ == "__main__":
    analyze_dcf()
