import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Set style
sns.set_theme(style="whitegrid")
plt.rcParams['font.family'] = 'sans-serif'

file_path = 'data/data_with_weather.csv'

def get_season(month):
    if month in [3, 4, 5]:
        return 'Spring'
    elif month in [6, 7, 8]:
        return 'Summer'
    elif month in [9, 10, 11]:
        return 'Autumn'
    else:
        return 'Winter'

def visualize_seasonal():
    try:
        print("Loading data for seasonal analysis...")
        df = pd.read_csv(file_path)
        
        # Extract month from date (YYYYMMDD)
        # Convert date to string first to handle int format safely
        df['date_str'] = df['date'].astype(str)
        df['month'] = df['date_str'].str[4:6].astype(int)
        
        # Map to seasons
        df['Season'] = df['month'].apply(get_season)
        
        # Define order for plotting
        season_order = ['Summer', 'Autumn', 'Winter', 'Spring']
        # Filter only existing seasons in data
        existing_seasons = df['Season'].unique()
        plot_order = [s for s in season_order if s in existing_seasons]
        
        print(f"Seasons found: {existing_seasons}")

        # Plot
        plt.figure(figsize=(10, 6))
        sns.boxplot(x='Season', y='measured_kWh', data=df, order=plot_order, palette='Set2')
        
        plt.title('Seasonal Load Distribution', fontsize=16, fontweight='bold')
        plt.xlabel('Season')
        plt.ylabel('Load (kWh)')
        plt.tight_layout()
        
        
        output_file = 'figures/figure_5_seasonal_boxplot.png'
        plt.savefig(output_file, dpi=300)
        print(f"Saved {output_file}")

        # --- New Figure: Seasonal Daily Profile ---
        print("Generating Seasonal Daily Profile...")
        
        # Create full datetime for time extraction
        df['datetime'] = pd.to_datetime(df['date'].astype(str) + ' ' + 
                                        df['hour'].astype(str).str.zfill(2) + ':' + 
                                        df['minute'].astype(str).str.zfill(2))
        
        df['time'] = df['datetime'].dt.time
        
        # Group by Season and Time
        seasonal_profile = df.groupby(['Season', 'time'])['measured_kWh'].mean().reset_index()
        
        # Prepare plot
        plt.figure(figsize=(12, 6))
        
        # Define colors for seasons
        season_colors = {'Summer': '#d62728', 'Autumn': '#ff7f0e', 'Winter': '#1f77b4', 'Spring': '#2ca02c'}
        
        for season in plot_order:
            subset = seasonal_profile[seasonal_profile['Season'] == season]
            # Convert time to string for plotting if needed, or rely on matplotlib handling time objects
            # To be safe and consistent with x-axis labels, better to use string or range
            # Let's use the unique times for x-axis mapping
            
            plt.plot(subset['time'].astype(str), subset['measured_kWh'], 
                     label=season, color=season_colors.get(season, 'black'), linewidth=2)

        plt.title('Average Daily Load Profile by Season', fontsize=16, fontweight='bold')
        plt.xlabel('Time of Day')
        plt.ylabel('Average Load (kWh)')
        plt.legend()
        
        # Format X-axis to not be too crowded (show every 4 hours approx)
        unique_times = sorted(df['time'].astype(str).unique())
        plt.xticks(ticks=range(0, len(unique_times), 8), labels=unique_times[::8], rotation=45)
        
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.tight_layout()
        
        output_file_6 = 'figures/figure_6_seasonal_daily_profile.png'
        plt.savefig(output_file_6, dpi=300)
        print(f"Saved {output_file_6}")

    except FileNotFoundError:

        print(f"Error: File not found at {file_path}")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    visualize_seasonal()
