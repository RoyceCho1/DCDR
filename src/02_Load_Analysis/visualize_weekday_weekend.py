import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os

# Set style
sns.set_theme(style="whitegrid")
plt.rcParams['font.family'] = 'sans-serif'

file_path = 'data/data_with_weather.csv'
output_dir = 'figures'

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

def analyze_weekday_weekend():
    try:
        print("Loading data...")
        df = pd.read_csv(file_path)
        
        # Datetime conversion
        df['datetime'] = pd.to_datetime(df['date'].astype(str) + ' ' + 
                                        df['hour'].astype(str).str.zfill(2) + ':' + 
                                        df['minute'].astype(str).str.zfill(2))
        
        # Feature Engineering
        df['weekday'] = df['datetime'].dt.weekday # 0=Mon, 6=Sun
        df['day_type'] = df['weekday'].apply(lambda x: 'Weekend' if x >= 5 else 'Weekday')
        
        df['month'] = df['datetime'].dt.month
        df['Season'] = df['month'].apply(get_season)
        df['time'] = df['datetime'].dt.time
        
        print(f"Data ready. Total rows: {len(df)}")
        print(df['day_type'].value_counts())

        # --- Figure 7: Overall Boxplot (Weekday vs Weekend) ---
        plt.figure(figsize=(8, 6))
        sns.boxplot(x='day_type', y='measured_kWh', data=df, palette='pastel', order=['Weekday', 'Weekend'])
        plt.title('Overall Load Distribution: Weekday vs Weekend', fontsize=14, fontweight='bold')
        plt.ylabel('Load (kWh)')
        plt.xlabel('')
        plt.tight_layout()
        plt.savefig(f'{output_dir}/figure_7_overall_weekday_weekend_box.png', dpi=300)
        print("Saved figure_7")

        # --- Figure 8: Overall Daily Profile (Weekday vs Weekend) ---
        profile = df.groupby(['day_type', 'time'])['measured_kWh'].mean().reset_index()
        
        plt.figure(figsize=(12, 6))
        sns.lineplot(data=profile, x=profile['time'].astype(str), y='measured_kWh', hue='day_type', 
                     palette={'Weekday': '#1f77b4', 'Weekend': '#ff7f0e'}, linewidth=2.5)
        
        plt.title('Average Daily Load Profile: Weekday vs Weekend', fontsize=14, fontweight='bold')
        plt.xlabel('Time of Day')
        plt.ylabel('Average Load (kWh)')
        
        # X-axis formatting
        unique_times = sorted(profile['time'].astype(str).unique())
        plt.xticks(ticks=range(0, len(unique_times), 8), labels=unique_times[::8], rotation=45)
        
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.tight_layout()
        plt.savefig(f'{output_dir}/figure_8_overall_weekday_weekend_profile.png', dpi=300)
        print("Saved figure_8")

        # --- Figure 9: Seasonal Weekday vs Weekend (Boxplot) ---
        season_order = ['Summer', 'Autumn', 'Winter', 'Spring']
        existing_seasons = [s for s in season_order if s in df['Season'].unique()]
        
        plt.figure(figsize=(12, 6))
        sns.boxplot(x='Season', y='measured_kWh', hue='day_type', data=df, 
                    order=existing_seasons, palette='muted', hue_order=['Weekday', 'Weekend'])
        
        plt.title('Seasonal Load Distribution: Weekday vs Weekend', fontsize=14, fontweight='bold')
        plt.ylabel('Load (kWh)')
        plt.xlabel('Season')
        plt.legend(title='Day Type')
        plt.tight_layout()
        plt.savefig(f'{output_dir}/figure_9_seasonal_weekday_weekend_box.png', dpi=300)
        print("Saved figure_9")

        # --- Figure 10: Seasonal Daily Profile (Weekday vs Weekend) ---
        print("Generating Figure 10...")
        # Group by Season, day_type, time
        seasonal_day_profile = df.groupby(['Season', 'day_type', 'time'])['measured_kWh'].mean().reset_index()
        
        # --- Figure 10: Seasonal Daily Profile (Separate Files per Season) ---
        print("Generating Figure 10 (Separate files)...")
        # Group by Season, day_type, time
        seasonal_day_profile = df.groupby(['Season', 'day_type', 'time'])['measured_kWh'].mean().reset_index()
        
        seasons_to_plot = [s for s in season_order if s in df['Season'].unique()]
        
        # Define colors consistent with Figure 8
        pal = {'Weekday': '#1f77b4', 'Weekend': '#ff7f0e'}
        
        for season in seasons_to_plot:
            plt.figure(figsize=(10, 6))
            
            subset = seasonal_day_profile[seasonal_day_profile['Season'] == season]
            
            sns.lineplot(data=subset, x=subset['time'].astype(str), y='measured_kWh', hue='day_type', 
                         palette=pal, linewidth=2.5)
            
            plt.title(f'Average Daily Load Profile: {season} (Weekday vs Weekend)', fontsize=15, fontweight='bold')
            plt.xlabel('Time of Day')
            plt.ylabel('Average Load (kWh)')
            plt.legend(title='Day Type')
            
            # X-ticks formatting
            unique_time_strs = sorted(subset['time'].astype(str).unique())
            plt.xticks(ticks=range(0, len(unique_time_strs), 8), labels=unique_time_strs[::8], rotation=45)
            
            plt.grid(True, linestyle='--', alpha=0.7)
            plt.tight_layout()
            
            output_file = f'{output_dir}/figure_10_{season}_profile.png'
            plt.savefig(output_file, dpi=300)
            print(f"Saved {output_file}")
            plt.close() # Close figure to free memory

        # --- Stats Printout ---
        print("\n--- Statistics: Weekday vs Weekend ---")
        print(df.groupby('day_type')['measured_kWh'].describe())
        
        print("\n--- Statistics: Seasonal Weekday vs Weekend (Mean) ---")
        print(df.groupby(['Season', 'day_type'])['measured_kWh'].mean().unstack(level=1).reindex(existing_seasons))

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    analyze_weekday_weekend()
