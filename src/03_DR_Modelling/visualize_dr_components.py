import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Set style
sns.set_theme(style="whitegrid")
plt.rcParams['font.family'] = 'sans-serif'

input_file = 'data/dr_simulation_results.csv'
output_dir = 'figures/04_DR_Analysis'
import os
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

def visualize_dr_components():
    print("Loading DR results...")
    df = pd.read_csv(input_file, parse_dates=['datetime'], index_col='datetime')
    
    # Filter for Shed Windows only
    shed_df = df[df['mask_shed'] == True].copy()
    
    if shed_df.empty:
        print("No Shed windows found!")
        return
        
    print(f"Analyzing {len(shed_df)} shed intervals...")
    
    # Calculate Components based on parameters
    # Alpha constants
    alpha_IT = 0.10
    alpha_cool_summer = 0.15
    alpha_cool_other = 0.10
    Q_ESS_fixed = 1250.0
    
    # 1. IT DR
    shed_df['DR_IT'] = shed_df['P_IT_kW'] * alpha_IT
    
    # 2. Cooling DR
    # Apply conditional alpha
    # Make a series for alpha
    alpha_cool_series = shed_df['season'].map(lambda x: alpha_cool_summer if x == 'Summer' else alpha_cool_other)
    shed_df['DR_Cooling'] = shed_df['P_Cool_kW'] * alpha_cool_series
    
    # 3. ESS DR
    shed_df['DR_ESS'] = Q_ESS_fixed
    
    # Group by Season and Mean
    # We want X-axis: Season (Summer, Fall, Winter)
    # But Fall has no Shed data?
    # Let's see unique seasons
    print("Seasons in Shed Data:", shed_df['season'].unique())
    
    seasonal_means = shed_df.groupby('season')[['DR_IT', 'DR_Cooling', 'DR_ESS']].mean()
    
    # Reindex to ensure order (Summer, Fall, Winter) if possible, 
    # but strictly Fall is missing.
    # If user really wants Fall, we'd need to simulate it with a hypothetical window.
    # Given the prompt's context of "Simulation Results", we plot what exists.
    # We can add 'Fall' with 0s if we want to show it exists but is empty? 
    # Or just omit. Omitting is cleaner.
    
    desired_order = [s for s in ['Summer', 'Fall', 'Winter'] if s in seasonal_means.index]
    seasonal_means = seasonal_means.loc[desired_order]
    
    print("\nMean Breakdown (kW):")
    print(seasonal_means)
    
    # Plot Stacked Bar
    ax = seasonal_means.plot(kind='bar', stacked=True, figsize=(8, 6), colormap='viridis', alpha=0.8)
    
    plt.title('Average DR Capacity Breakdown (Load-shed)', fontsize=16, fontweight='bold')
    plt.xlabel('Season')
    plt.ylabel('Average Capacity (kW)')
    plt.xticks(rotation=0)
    plt.legend(title='Component', loc='upper right')
    plt.grid(axis='y', linestyle='--', alpha=0.5)
    
    # Add value labels
    # Iterate through containers
    for container in ax.containers:
        ax.bar_label(container, fmt='%.0f', label_type='center', color='white', fontsize=10, fontweight='bold')
        
    plt.tight_layout()
    plt.savefig(f"{output_dir}/figure_dr_components_stacked.png", dpi=300)
    print(f"Saved {output_dir}/figure_dr_components_stacked.png")

if __name__ == "__main__":
    visualize_dr_components()
