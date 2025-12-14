import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os
import numpy as np

# Set style
sns.set_theme(style="whitegrid")
plt.rcParams['font.family'] = 'sans-serif' # Avoid font issues
# If Korean font issues persist, user might need to install NanumGothic etc, but let's stick to English labels or default.

smp_file = 'data/smp_clean.csv'
power_file = 'data/power_source_integrated.csv'
output_dir = 'figures/04_DR_Analysis'
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

def analyze_dr_potential():
    print("Loading Data...")
    df_smp = pd.read_csv(smp_file, parse_dates=['datetime'], index_col='datetime')
    df_power = pd.read_csv(power_file, parse_dates=['datetime'], index_col='datetime')
    
    # Merge (Inner join to match timestamps)
    df = df_smp.join(df_power, how='inner')
    
    # Calculate Total Generation
    # Exclude 'PV_total' from sum if it's already there to avoid double counting?
    # Or sum components.
    # Columns in power_source_integrated: 
    # ['태양광(BTM,추정)', '태양광(PPA,추정)', '태양광(전력시장)', '양수', '수력', '가스', '풍력', '신재생', '유류', '국내탄', '유연탄', '원자력', 'PV_total']
    
    source_cols = ['태양광(BTM,추정)', '태양광(PPA,추정)', '태양광(전력시장)', 
                   '양수', '수력', '가스', '풍력', '신재생', '유류', '국내탄', '유연탄', '원자력']
    
    # Check if cols exist
    available_cols = [c for c in source_cols if c in df.columns]
    df['Total_Generation'] = df[available_cols].sum(axis=1)
    
    # Add Time Features
    df['month'] = df.index.month
    df['hour'] = df.index.hour
    df['Season'] = df['month'].apply(get_season)
    
    # --- Step 2: Seasonal Average Curves ---
    print("\n--- Step 2: Generating Seasonal Average Curves ---")
    
    metrics = ['SMP', 'PV_total', 'Total_Generation']
    seasons = ['Spring', 'Summer', 'Autumn', 'Winter']
    
    # Create subplots for each metric
    for metric in metrics:
        plt.figure(figsize=(10, 6))
        
        for season in seasons:
            if season not in df['Season'].unique():
                continue
            
            subset = df[df['Season'] == season]
            # Group by hour and mean
            daily_profile = subset.groupby('hour')[metric].mean()
            
            plt.plot(daily_profile.index, daily_profile.values, marker='o', label=season, linewidth=2)
            
        plt.title(f'Seasonal Average Profile: {metric}', fontsize=16, fontweight='bold')
        plt.xlabel('Hour of Day')
        plt.ylabel(metric)
        plt.xticks(range(0, 24))
        plt.legend()
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.tight_layout()
        plt.savefig(f"{output_dir}/figure_seasonal_profile_{metric}.png", dpi=300)
        print(f"Saved {output_dir}/figure_seasonal_profile_{metric}.png")
        
    # --- Step 3: DR Window Derivation ---
    print("\n--- Step 3: Deriving DR Windows ---")
    
    # Define thresholds PER SEASON based on HOURLY profiles? 
    # Or based on RAW data distribution?
    # User said: "SMP top 20%". Usually this means distribution of values.
    # However, for "Windows", we often look at the average curve OR frequent occurrence.
    # Let's use the RAW 15-min data distribution per season to define thresholds.
    
    dr_summary = []
    
    for season in seasons:
        if season not in df['Season'].unique():
            continue
            
        subset = df[df['Season'] == season]
        
        # 1. Load-shed (Peak Reduction): SMP > 80th percentile
        smp_80 = subset['SMP'].quantile(0.80)
        
        # 2. Load-up (Valley Filling) - STRATEGY: High PV + Avoid Top 15% Price (PV >= P75 & SMP <= P85)
        pv_80 = subset['PV_total'].quantile(0.80)
        smp_70  = subset['SMP'].quantile(0.70)
        
        # Identify Matching Hours (Probabilistic Approach)
        
        # For each hour, count frequency of meeting criteria
        hourly_stats = subset.groupby('hour').apply(
            lambda x: pd.Series({
                'prob_shed': (x['SMP'] > smp_80).mean(),
                'prob_up': ((x['PV_total'] >= pv_80) & (x['SMP'] <= smp_70)).mean()
            })
        )
        
        # Define Window: If Probability > 40%
        shed_hours = hourly_stats[hourly_stats['prob_shed'] > 0.4].index.tolist()
        up_hours = hourly_stats[hourly_stats['prob_up'] > 0.4].index.tolist()
        
        # Formatting ranges
        def format_ranges(hours):
            if not hours: return "None"
            ranges = []
            start = hours[0]
            prev = hours[0]
            for h in hours[1:]:
                if h == prev + 1:
                    prev = h
                else:
                    ranges.append(f"{start:02d}~{prev+1:02d}h")
                    start = h
                    prev = h
            ranges.append(f"{start:02d}~{prev+1:02d}h")
            return ", ".join(ranges)

        dr_summary.append({
            'Season': season,
            'Load-shed Criteria': f"SMP > {smp_80:.1f}",
            'Load-shed Windows': format_ranges(shed_hours),
            'Load-up Criteria': f"PV >= {pv_80:.1f} & SMP <= {smp_70:.1f}",
            'Load-up Windows': format_ranges(up_hours)
        })
        
    # Print Report
    print(f"{'Season':<10} | {'Window Type':<15} | {'Criteria':<30} | {'Selected Hours'}")
    print("-" * 80)
    for item in dr_summary:
        print(f"{item['Season']:<10} | {'Load-shed':<15} | {item['Load-shed Criteria']:<30} | {item['Load-shed Windows']}")
        print(f"{item['Season']:<10} | {'Load-up':<15}   | {item['Load-up Criteria']:<30} | {item['Load-up Windows']}")
        print("-" * 80)

if __name__ == "__main__":
    analyze_dr_potential()
