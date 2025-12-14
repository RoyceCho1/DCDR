import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os

# Set style
sns.set_theme(style="whitegrid")
plt.rcParams['font.family'] = 'sans-serif'

input_file = 'data/dr_simulation_results.csv'
output_dir = 'figures/06_Final_Report'

def analyze_dr_final():
    print("Loading DR Simulation Results...")
    df = pd.read_csv(input_file, parse_dates=['datetime'], index_col='datetime')
    df['hour'] = df.index.hour
    
    # Calculate Total Load
    df['P_Total_kW'] = df['P_IT_kW'] + df['P_Cool_kW'] + df['P_Other_kW']
    
    # Ensure params used in simulation are available or re-defined ?
    # We can infer components if not saved, but we only saved Q. 
    # BUT, we saved P_IT_kW, P_Cool_kW. We know alpha parameters.
    # Re-defining parameters for component decomp:
    alpha_IT = 0.10
    alpha_cool_summer = 0.15
    alpha_cool_other = 0.10
    alpha_IT_forward = 0.10
    Q_ESS_fixed = 1250.0
    
    season_order = ['Spring', 'Summer', 'Fall', 'Winter']
    
    # ==========================================
    # 1. Summary Statistics (Season x DR Type)
    # ==========================================
    print("\n[1] Summary Statistics (Season x Type)")
    stats_list = []
    
    # Iterate over combinations
    # Summer Shed, Fall Up, Winter Shed, Winter Up, Spring?
    # Assuming Spring acts like Fall (Up) or Winter (Shed/Up)?
    # Simulate DR logic: Spring (3,4,5).
    # simulate_dr.py logic for Spring: "Winter Shed (Fall has no shed...)" -> checks != Summer.
    # So Spring might have Shed if mask_shed is True.
    # But mask_shed is initialized False.
    # simulate_dr.py only sets mask_shed for Summer and Winter.
    # simulate_dr.py only sets mask_up for Fall and Winter.
    # So Spring has NO DR unless I update simulate_dr.py.
    
    combinations = [
        ('Spring', 'Shed'), # Placeholder if added
        ('Spring', 'Up'),   # Placeholder if added
        ('Summer', 'Shed'),
        ('Fall', 'Up'),
        ('Winter', 'Shed'),
        ('Winter', 'Up')
    ]
    
    for season, dr_type in combinations:
        # Filter
        if dr_type == 'Shed':
            mask = (df['season'] == season) & df['mask_shed']
            col = 'Q_shed_kW'
        else:
            mask = (df['season'] == season) & df['mask_up']
            col = 'Q_up_kW'
            
        subset = df[mask]
        if subset.empty:
            continue
            
        data = subset[col]
        
        avg_val = data.mean()
        std_val = data.std()
        cv_val = std_val / avg_val if avg_val > 0 else 0
        
        stats = {
            'Season': season,
            'Type': dr_type,
            'Avg (kW)': avg_val,
            'P90 (kW)': data.quantile(0.90),
            'P95 (kW)': data.quantile(0.95),
            'Max (kW)': data.max(),
            'Std (kW)': std_val,
            'CV': cv_val
        }
        stats_list.append(stats)
        
    stats_df = pd.DataFrame(stats_list)
    print(stats_df.round(2))
    stats_df.to_csv('data/dr_final_stats_summary.csv', index=False)
    
    # ==========================================
    # 2. Energy per Event (kWh/event)
    # ==========================================
    print("\n[2] Energy per Event (1-hour Rolling)")
    # Logic: Filter window -> Calculate energy (kW * 0.25h) -> Rolling sum (4 steps)
    # BUT rolling across non-continuous windows is wrong.
    # However, windows are usually continuous blocks in a day.
    # If we apply rolling on the full dataframe, masked values are 0.
    # So rolling sum of 0s and Qs will work, assuming 1h event can start anytime inside window.
    # But strictly, if window is 11-12 (4 steps), we have only 1 valid 1-hour block? 
    # Or sliding? "Event duration 1.0h". 
    # Let's do rolling on full series, then filter for times where ALL 4 steps were valid?
    # Or simpler: rolling sum of Q_kW * 0.25. If any part is 0, sum is < max?
    # No, Q is 0 outside. So if rolling window crosses boundary, energy will be lower.
    # We want "Fully Inside" events? Or just capabilities?
    # User said: "window 시점만 대상으로... 1시간짜리 연속 블록".
    # Let's calculate Rolling 1h Energy on the whole series.
    # E_1h(t) = Sum(Q(t-3)...Q(t)) * 0.25 ? Or forward?
    # Let's use backward rolling corresponding to "Event ending at t" or forward "Event starting at t".
    # Let's use Forward rolling for "Event starting at t".
    
    # 15min energy
    df['E_shed_15m'] = df['Q_shed_kW'] * 0.25
    df['E_up_15m'] = df['Q_up_kW'] * 0.25
    
    # Rolling 4 (1 hour). Shifted so index is start time?
    # rolling(4).sum() gives value at index=end.
    # To represent "Start at t", we can use use index shift or just interpret "at t, calculation is valid".
    # Let's stick to standard pandas rolling (label=right).
    
    # To identify valid 1-hour blocks that fit entirely in window:
    # We need a mask that is 1 if inside window. Rolling sum of mask should be 4.
    
    df['mask_shed_int'] = df['mask_shed'].astype(int)
    df['mask_up_int'] = df['mask_up'].astype(int)
    
    # Rolling validity
    indexer = pd.api.indexers.FixedForwardWindowIndexer(window_size=4)
    df['valid_shed_1h'] = df['mask_shed_int'].rolling(window=indexer).sum() == 4
    df['valid_up_1h'] = df['mask_up_int'].rolling(window=indexer).sum() == 4
    
    # Rolling Energy (Forward)
    df['E_shed_1h'] = df['E_shed_15m'].rolling(window=indexer).sum()
    df['E_up_1h'] = df['E_up_15m'].rolling(window=indexer).sum()
    
    energy_stats_list = []
    
    for season, dr_type in combinations:
        if dr_type == 'Shed':
            # Filter for rows where valid_shed_1h is True
            mask = (df['season'] == season) & df['valid_shed_1h']
            col = 'E_shed_1h'
        else:
            mask = (df['season'] == season) & df['valid_up_1h']
            col = 'E_up_1h'
            
        subset = df[mask]
        if subset.empty:
            continue
            
        # Daily Max/Mean
        # Regroup by Date
        daily_max = subset.groupby(subset.index.date)[col].max()
        daily_mean = subset.groupby(subset.index.date)[col].mean()
        
        # Overall Summary
        e_mean = subset[col].mean()
        e_p90 = subset[col].quantile(0.90)
        e_max = subset[col].max()
        
        energy_stats = {
            'Season': season,
            'Type': dr_type,
            'Mean (kWh)': e_mean,
            'P90 (kWh)': e_p90,
            'Max (kWh)': e_max,
            'Daily Max Mean (kWh)': daily_max.mean(), # Mean of daily maxes
        }
        energy_stats_list.append(energy_stats)
        
    en_curr_df = pd.DataFrame(energy_stats_list)
    print(en_curr_df.round(2))
    
    # ==========================================
    # 3. Component Breakdown (Mean kW)
    # ==========================================
    print("\n[3] Component Breakdown")
    # Logic: For each row in window, calc breakdown, then average.
    # Re-calculate components (since they weren't saved per row except P_kW)
    
    comp_list = []
    
    for season, dr_type in combinations:
        if dr_type == 'Shed':
            mask = (df['season'] == season) & df['mask_shed']
            p_it = df.loc[mask, 'P_IT_kW']
            p_cool = df.loc[mask, 'P_Cool_kW']
            
            # Alpha
            a_cool = alpha_cool_summer if season == 'Summer' else alpha_cool_other
            
            it_dr = p_it * alpha_IT
            cool_dr = p_cool * a_cool
            ess_dr = Q_ESS_fixed # Scalar, implies mean is scalar
            
        else: # Up
            mask = (df['season'] == season) & df['mask_up']
            p_it = df.loc[mask, 'P_IT_kW']
            
            it_dr = p_it * alpha_IT_forward
            cool_dr = p_it * 0 # No cooling in Up
            ess_dr = Q_ESS_fixed
        
        if p_it.empty:
            continue
            
        comp_stats = {
            'Season': season,
            'Type': dr_type,
            'IT_DR (kW)': it_dr.mean(),
            'Cooling_DR (kW)': cool_dr.mean() if isinstance(cool_dr, pd.Series) else 0,
            'ESS_DR (kW)': ess_dr
        }
        comp_list.append(comp_stats)
        
    comp_df = pd.DataFrame(comp_list)
    print(comp_df.round(2))
    comp_df.to_csv('data/dr_final_components.csv', index=False)
    
    # ==========================================
    # 4. Figures (1, 2, 3)
    # ==========================================
    print("\n[4] Generating Figures...")
    
    # --- Figure 1: Seasonal Profile (Line + Area) ---
    # We already did this via visualize_dr_profile.py
    # Re-generating with consistent naming if needed or skip?
    # User asked for "Figure 1", "Figure 2", "Figure 3". 
    # Let's just create them specifically named 'final_figure_X.png'
    
    # Fig 1 loop
    for season in ['Spring', 'Summer', 'Fall', 'Winter']:
        subset = df[df['season'] == season]
        if subset.empty: continue
        hourly = subset.groupby('hour').mean(numeric_only=True)
        
        plt.figure(figsize=(10, 6))
        plt.plot(hourly.index, hourly['P_Total_kW'], 'k-', lw=2, label='Total Load')
        plt.plot(hourly.index, hourly['P_IT_kW'], 'b--', lw=1, label='IT Load')
        plt.plot(hourly.index, hourly['P_Cool_kW'], 'c:', lw=1, label='Cooling Load')
        
        # Area
        plt.fill_between(hourly.index, 0, hourly['Q_shed_kW'], color='salmon', alpha=0.3, label='Shed Pot')
        if hourly['Q_up_kW'].sum() > 0:
            # Shift Up potential for visibility? Or just plot from 0?
            # User said "Area".
             plt.fill_between(hourly.index, 0, hourly['Q_up_kW'], color='lightgreen', alpha=0.3, label='Up Pot')

        plt.title(f'Figure 1. Seasonal Average Profile ({season})')
        plt.legend(loc='upper right')
        plt.xlabel('Hour')
        plt.ylabel('kW')
        plt.grid(True, alpha=0.5)
        plt.tight_layout()
        plt.savefig(f'{output_dir}/final_figure_1_profile_{season}.png', dpi=300)
        
    # --- Figure 2: Boxplot (Shed / Up Distribution) ---
    # Merge Shed and Up into one long format for plotting?
    # Or two subplots?
    # User said: "Two separate boxplots or select one". 
    # Let's do 2 Subplots side-by-side.
    
    fig, axes = plt.subplots(1, 2, figsize=(12, 6))
    
    # Shed
    shed_data = df[df['mask_shed']]
    sns.boxplot(data=shed_data, x='season', y='Q_shed_kW', order=season_order, ax=axes[0], palette='Reds')
    axes[0].set_title('Shed Potential Distribution')
    
    # Up
    up_data = df[df['mask_up']]
    if not up_data.empty:
        # Filter season order to only existing
        up_seasons = [s for s in season_order if s in up_data['season'].unique()]
        sns.boxplot(data=up_data, x='season', y='Q_up_kW', order=up_seasons, ax=axes[1], palette='Greens')
    axes[1].set_title('Up Potential Distribution')
    
    plt.tight_layout()
    plt.savefig(f'{output_dir}/final_figure_2_boxplot.png', dpi=300)
    
    # --- Figure 3: Stacked Bar Components ---
    # Use comp_df
    # We need to reshape for plotting
    # Comp_df has 'Season', 'Type', 'IT', 'Cool..', 'ESS'
    # Create a unique label 'Season-Type'
    comp_df['Label'] = comp_df['Season'] + '\n(' + comp_df['Type'] + ')'
    
    # Plot
    # Reorganize for stacked plot: index=Label, cols=[IT, Cooling, ESS]
    plot_df = comp_df.set_index('Label')[['IT_DR (kW)', 'Cooling_DR (kW)', 'ESS_DR (kW)']]
    
    ax = plot_df.plot(kind='bar', stacked=True, figsize=(10, 6), colormap='viridis', alpha=0.8)
    plt.title('Figure 3. DR Component Breakdown (Mean kW)')
    plt.ylabel('Capacity (kW)')
    plt.xticks(rotation=0)
    plt.grid(axis='y', alpha=0.5)
    
    # Labels
    for c in ax.containers:
        ax.bar_label(c, fmt='%.0f', label_type='center', color='white', fontweight='bold')
        
    plt.tight_layout()
    plt.savefig(f'{output_dir}/final_figure_3_components.png', dpi=300)
    
    print("\nAnalysis Complete. Figures saved to figures/final_figure_*.png")

if __name__ == "__main__":
    analyze_dr_final()
