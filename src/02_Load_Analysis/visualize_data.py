import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Set style for premium look
sns.set_theme(style="whitegrid")
plt.rcParams['font.family'] = 'sans-serif'

file_path = 'data/data_with_weather.csv'

def clean_and_visualize():
    try:
        # 1. Load Data
        print("Loading cleaned data...")
        df = pd.read_csv(file_path)
        
        # Create datetime index
        # combining date + hour + minute
        df['datetime'] = pd.to_datetime(df['date'].astype(str) + ' ' + 
                                        df['hour'].astype(str).str.zfill(2) + ':' + 
                                        df['minute'].astype(str).str.zfill(2))
        
        df.set_index('datetime', inplace=True)
        
        print(f"Data Loaded. Range: {df.index.min()} to {df.index.max()}")
        print("\n--- Summary Statistics ---")
        print(df[['measured_kWh', 'realtime_kWh']].describe())

        # 2. Plotting
        print("\nGenerating Figures...")

        # Figure 1: Full Time Series
        plt.figure(figsize=(15, 6))
        plt.plot(df.index, df['measured_kWh'], label='Measured Load (kWh)', color='#1f77b4', linewidth=0.8, alpha=0.8)
        plt.title('Data Center Power Consumption (Full Period)', fontsize=16, fontweight='bold')
        plt.xlabel('Date')
        plt.ylabel('Load (kWh)')
        plt.legend()
        plt.tight_layout()
        plt.savefig('figure_1_full_timeseries.png', dpi=300)
        print("Saved figure_1_full_timeseries.png")

        # Figure 2: Daily Load Profile (Average per hour/minute)
        # Group by hour and minute to see the daily shape
        df['time_of_day'] = df.index.time
        daily_profile = df.groupby('time_of_day')['measured_kWh'].mean()
        
        # Prepare x-axis for daily profile (string representation for plotting)
        time_labels = [t.strftime('%H:%M') for t in daily_profile.index]
        
        plt.figure(figsize=(12, 6))
        plt.plot(time_labels, daily_profile.values, color='#ff7f0e', linewidth=2)
        plt.title('Average Daily Load Profile', fontsize=16, fontweight='bold')
        plt.xlabel('Time of Day')
        plt.ylabel('Average Load (kWh)')
        
        # Simplify x-ticks to show every hour
        plt.xticks(ticks=range(0, len(time_labels), 4), labels=time_labels[::4], rotation=45)
        
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.tight_layout()
        plt.savefig('figure_2_daily_profile.png', dpi=300)
        print("Saved figure_2_daily_profile.png")

        # Figure 3: Monthly Distribution (Boxplot)
        df['month'] = df.index.strftime('%Y-%m')
        plt.figure(figsize=(12, 6))
        sns.boxplot(x='month', y='measured_kWh', data=df, palette='viridis')
        plt.title('Monthly Load Distribution', fontsize=16, fontweight='bold')
        plt.xlabel('Month')
        plt.ylabel('Load (kWh)')
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig('figure_3_monthly_dist.png', dpi=300)
        print("Saved figure_3_monthly_dist.png")

        # Figure 4: Load Histogram
        plt.figure(figsize=(10, 6))
        sns.histplot(df['measured_kWh'], bins=50, kde=True, color='#2ca02c')
        plt.title('Load Distribution Histogram', fontsize=16, fontweight='bold')
        plt.xlabel('Load (kWh)')
        plt.ylabel('Frequency')
        plt.tight_layout()
        plt.savefig('figure_4_histogram.png', dpi=300)
        print("Saved figure_4_histogram.png")

        print("\nAll figures generated successfully!")

    except ImportError as e:
        print("Error: Required libraries not found. Please run: pip install pandas matplotlib seaborn")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    clean_and_visualize()
