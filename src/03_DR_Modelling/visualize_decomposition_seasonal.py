import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os

# Set style
sns.set_theme(style="whitegrid")
plt.rcParams['font.family'] = 'sans-serif'

input_file = 'data/data_decomposition.csv'
output_dir = 'figures/03_Load_Decomposition'

if not os.path.exists(output_dir):
    os.makedirs(output_dir)

def get_season(month):
    if month in [3, 4, 5]:
        return 'Spring'
    elif month in [6, 7, 8]:
        return 'Summer'
    elif month in [9, 10, 11]:
        return 'Autumn'
    else:
        return 'Winter'

def visualize_seasonal_decomposition():
    print("Loading decomposition data...")
    # 'datetime' is likely the index in the CSV based on previous steps
    df = pd.read_csv(input_file, parse_dates=['datetime'], index_col='datetime')
    
    # Add Season and Time
    df['month'] = df.index.month
    df['Season'] = df['month'].apply(get_season)
    df['time'] = df.index.time
    
    seasons = ['Spring', 'Summer', 'Autumn', 'Winter']
    existing_seasons = [s for s in seasons if s in df['Season'].unique()]
    
    print(f"Seasons found: {existing_seasons}")
    
    for season in existing_seasons:
        print(f"Generating figure for {season}...")
        
        # Filter by season
        subset = df[df['Season'] == season]
        
        # Calculate Average Daily Profile for components
        # Resample/Group by time
        daily_profile = subset.groupby('time')[['IT', 'Other', 'Cooling']].mean()
        
        # Prepare Plot
        plt.figure(figsize=(10, 6))
        
        # Stackplot
        # Check order: usually IT (Base) -> Other -> Cooling (Variable Top)
        # Colors: IT=Blue, Other=Gray, Cooling=Orange
        plt.stackplot(daily_profile.index.astype(str), 
                      daily_profile['IT'], 
                      daily_profile['Other'], 
                      daily_profile['Cooling'],
                      labels=['IT Load', 'Other Load', 'Cooling Load'],
                      colors=['#1f77b4', '#7f7f7f', '#ff7f0e'], 
                      alpha=0.85)
        
        plt.title(f'Average Daily Load Composition: {season}', fontsize=16, fontweight='bold')
        plt.ylabel('Load (kWh)')
        plt.xlabel('Time of Day')
        plt.legend(loc='upper left', frameon=True)
        
        # Y-axis limit for consistency? 
        # Optional: set constant ylim across seasons for easier comparison
        # plt.ylim(0, 1200) 
        
        # X-ticks formatting
        times = daily_profile.index.astype(str)
        plt.xticks(ticks=range(0, len(times), 8), labels=times[::8], rotation=45)
        
        plt.tight_layout()
        
        filename = f"{output_dir}/figure_decomposition_{season}.png"
        plt.savefig(filename, dpi=300)
        print(f"Saved {filename}")
        plt.close()

if __name__ == "__main__":
    visualize_seasonal_decomposition()
