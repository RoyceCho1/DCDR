import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os

# Set style
sns.set_theme(style="whitegrid")
plt.rcParams['font.family'] = 'sans-serif'

input_file = 'data/dr_simulation_results.csv'
output_dir = 'figures/04_DR_Analysis'
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

def visualize_dr_distribution():
    print("Loading DR results...")
    df = pd.read_csv(input_file, parse_dates=['datetime'], index_col='datetime')
    
    # Define order
    season_order = ['Spring', 'Summer', 'Fall', 'Winter']
    
    # 1. Prepare Data for Shed
    # Only include rows where mask_shed is True
    shed_data = df[df['mask_shed'] == True].copy()
    
    # 2. Prepare Data for Up
    # Only include rows where mask_up is True
    up_data = df[df['mask_up'] == True].copy()
    
    print(f"Shed Data Points: {len(shed_data)}")
    print(f"Up Data Points:   {len(up_data)}")
    
    # --- Plot 1: Shed Potential Distribution ---
    if not shed_data.empty:
        plt.figure(figsize=(8, 6))
        # Violin plot with inner box
        sns.violinplot(data=shed_data, x='season', y='Q_shed_kW', order=season_order, palette='Reds', inner='quartile', alpha=0.6)
        # Overlay strip plot for data density (optional, maybe too crowded)
        # sns.stripplot(data=shed_data, x='season', y='Q_shed_kW', order=season_order, color='black', alpha=0.1, size=2)
        
        # Calculate stats for annotation
        stats = shed_data.groupby('season')['Q_shed_kW'].agg(['mean', 'std'])
        print("\n--- Shed Stats ---")
        print(stats)
        
        # Add text annotations
        # (Implementation omitted for simplicity in visual, detailed in print)
        
        plt.title('Distribution of Load-shed Potential (kW)', fontsize=16, fontweight='bold')
        plt.ylabel('Potential (kW)')
        plt.xlabel('Season')
        plt.tight_layout()
        plt.savefig(f"{output_dir}/figure_dr_distribution_shed.png", dpi=300)
        print(f"Saved {output_dir}/figure_dr_distribution_shed.png")
    
    # --- Plot 2: Up Potential Distribution ---
    if not up_data.empty:
        plt.figure(figsize=(8, 6))
        sns.violinplot(data=up_data, x='season', y='Q_up_kW', order=season_order, palette='Greens', inner='quartile', alpha=0.6)
        
        stats_up = up_data.groupby('season')['Q_up_kW'].agg(['mean', 'std'])
        print("\n--- Up Stats ---")
        print(stats_up)
        
        plt.title('Distribution of Load-up Potential (kW)', fontsize=16, fontweight='bold')
        plt.ylabel('Potential (kW)')
        plt.xlabel('Season')
        plt.tight_layout()
        plt.savefig(f"{output_dir}/figure_dr_distribution_up.png", dpi=300)
        print(f"Saved {output_dir}/figure_dr_distribution_up.png")

if __name__ == "__main__":
    visualize_dr_distribution()
