import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os

# Set style
sns.set_theme(style="whitegrid")
plt.rcParams['font.family'] = 'sans-serif'

input_file = 'data/dr_simulation_results.csv'
output_dir = 'figures/04_DR_Analysis'

# Ensure output dir exists (it should from previous step)
os.makedirs(output_dir, exist_ok=True)

def visualize_dr_components_no_ess():
    print("Loading DR results...")
    df = pd.read_csv(input_file, parse_dates=['datetime'], index_col='datetime')
    
    # Parameters
    alpha_IT = 0.10
    alpha_cool_summer = 0.15
    alpha_cool_other = 0.10
    alpha_IT_forward = 0.10
    # Q_ESS_fixed = 1250.0  <-- Excluded
    
    comp_list = []
    
    # Combinations to analyze
    combinations = [
        ('Spring', 'Shed'),
        ('Spring', 'Up'),
        ('Summer', 'Shed'),
        ('Fall', 'Up'),
        ('Winter', 'Shed'),
        ('Winter', 'Up')
    ]
    
    print("\nCalculating Components (No ESS)...")
    
    for season, dr_type in combinations:
        if dr_type == 'Shed':
            mask = (df['season'] == season) & df['mask_shed']
            if not mask.any(): continue
            
            p_it = df.loc[mask, 'P_IT_kW']
            p_cool = df.loc[mask, 'P_Cool_kW']
            
            a_cool = alpha_cool_summer if season == 'Summer' else alpha_cool_other
            
            it_dr = p_it * alpha_IT
            cool_dr = p_cool * a_cool
            
        else: # Up
            mask = (df['season'] == season) & df['mask_up']
            if not mask.any(): continue
            
            p_it = df.loc[mask, 'P_IT_kW']
            it_dr = p_it * alpha_IT_forward
            cool_dr = p_it * 0 # No cooling Up
            
        comp_stats = {
            'Label': f"{season}\n({dr_type})",
            'IT_DR (kW)': it_dr.mean(),
            'Cooling_DR (kW)': cool_dr.mean() if isinstance(cool_dr, pd.Series) else 0
        }
        comp_list.append(comp_stats)
        
    comp_df = pd.DataFrame(comp_list)
    print(comp_df.round(2))
    
    # Plot Stacked Bar
    plot_df = comp_df.set_index('Label')
    
    # Colors: IT (Blue-ish), Cooling (Cyan-ish)
    colors = ['#3498db', '#1abc9c']
    
    ax = plot_df.plot(kind='bar', stacked=True, figsize=(8, 6), color=colors, alpha=0.9)
    
    plt.title('DR Capacity Breakdown (Excluding ESS)', fontsize=16, fontweight='bold')
    plt.ylabel('Average Capacity (kW)')
    plt.xlabel('Season (Type)')
    plt.xticks(rotation=0)
    plt.legend(title='Component', loc='upper right')
    plt.grid(axis='y', linestyle='--', alpha=0.5)
    
    # Add value labels
    for c in ax.containers:
        ax.bar_label(c, fmt='%.0f', label_type='center', color='white', fontweight='bold', fontsize=11)
        
    # Add Total Label on top
    totals = plot_df.sum(axis=1)
    for i, v in enumerate(totals):
        ax.text(i, v + 5, f"{v:.0f}", ha='center', va='bottom', fontweight='bold', fontsize=11)

    plt.tight_layout()
    filename = f"{output_dir}/final_figure_3_components_no_ess.png"
    plt.savefig(filename, dpi=300)
    print(f"Saved {filename}")

if __name__ == "__main__":
    visualize_dr_components_no_ess()
