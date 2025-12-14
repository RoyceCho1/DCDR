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

def visualize_dr_profile():
    print("Loading DR results...")
    df = pd.read_csv(input_file, parse_dates=['datetime'], index_col='datetime')
    
    # Calculate Total Load
    # Columns: P_IT_kW, P_Cool_kW, P_Other_kW, Q_shed_kW, Q_up_kW ...
    df['P_Total_kW'] = df['P_IT_kW'] + df['P_Cool_kW'] + df['P_Other_kW']
    
    # Add hour/season if missing (though they should be in file or index)
    df['hour'] = df.index.hour
    
    seasons = ['Spring', 'Summer', 'Fall', 'Winter']
    
    print("Generating Seasonal DR Profiles...")
    
    for season in seasons:
        subset = df[df['season'] == season]
        if subset.empty:
            print(f"No data for {season}")
            continue
            
        # Group by hour
        # We need MEAN values per hour
        hourly_mean = subset.groupby('hour').mean(numeric_only=True)
        
        # Plot
        plt.figure(figsize=(10, 6))
        
        # 1. Loads (Lines)
        plt.plot(hourly_mean.index, hourly_mean['P_Total_kW'], label='Total Load', color='black', linewidth=2.5)
        plt.plot(hourly_mean.index, hourly_mean['P_IT_kW'], label='IT Load', color='blue', linestyle='--', linewidth=1.5)
        plt.plot(hourly_mean.index, hourly_mean['P_Cool_kW'], label='Cooling Load', color='cyan', linestyle=':', linewidth=1.5)
        
        # 2. DR Potentials (Areas)
        # Q_shed: Plot as area from 0 up to Q_shed? Or perhaps hanging from the top?
        # User requested "Area". Plotting magnitude at the bottom is clearest for "Capacity".
        
        # Plot Shed
        plt.fill_between(hourly_mean.index, 0, hourly_mean['Q_shed_kW'], color='salmon', alpha=0.3, label='DR Shed Potential')
        # Add a line for clarity
        plt.plot(hourly_mean.index, hourly_mean['Q_shed_kW'], color='red', linewidth=1, alpha=0.6)
        
        # Plot Up
        # To distinguish, maybe plot Step or just overlay.
        # Fall/Winter might have Up. Summer has None.
        if hourly_mean['Q_up_kW'].sum() > 0:
             plt.fill_between(hourly_mean.index, 0, hourly_mean['Q_up_kW'], color='lightgreen', alpha=0.3, label='DR Up Potential')
             plt.plot(hourly_mean.index, hourly_mean['Q_up_kW'], color='green', linewidth=1, alpha=0.6)

        plt.title(f'Seasonal Average Load & DR Potential ({season})', fontsize=16, fontweight='bold')
        plt.xlabel('Hour of Day')
        plt.ylabel('Power (kW)')
        plt.xticks(range(0, 24))
        plt.legend(loc='upper left', bbox_to_anchor=(1, 1))
        
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.tight_layout()
        
        filename = f"{output_dir}/figure_dr_profile_{season}.png"
        plt.savefig(filename, dpi=300)
        print(f"Saved {filename}")

if __name__ == "__main__":
    visualize_dr_profile()
