import pandas as pd
import numpy as np
import warnings

# Suppress warnings
warnings.filterwarnings('ignore')

# Configuration
INPUT_FILE = 'data/data_center_load_clean.csv'
OUTPUT_FILE = 'data/data_center_load_annualized_20240601_20250531.csv'
SEED = 42
TARGET_END_DATE = '2025-05-31'

def get_season(month):
    if month in [6, 7, 8]:
        return 'Summer'
    elif month in [9, 10, 11]:
        return 'Fall'
    elif month in [12, 1]:
        return 'Winter'
    else:
         # For profile extraction (existing data), existing months are 6,7,8,9,10,11,12,1.
         # So we cover all existing.
         # For generation (Mar, Apr, May), we assign them 'Spring' typically, 
         # but here we map them to Fall Profile later. 
         # We'll handle generation mapping separately.
        return 'Spring' 

def generate_annual_load():
    np.random.seed(SEED)
    print("Loading existing data...")
    # Load data
    df = pd.read_csv(INPUT_FILE)
    
    # Create datetime from columns if needed, or parse if 'date' is YYYYMMDD
    # 'date' column is int YYYYMMDD. 'hour', 'minute'.
    # Let's create a proper datetime index
    df['datetime'] = pd.to_datetime(df['date'].astype(str) + ' ' + 
                                   df['hour'].astype(str).str.zfill(2) + ':' + 
                                   df['minute'].astype(str).str.zfill(2))
    df = df.set_index('datetime').sort_index()
    
    # 1. Feature Engineering for Profile Extraction
    df['month'] = df.index.month
    df['season'] = df['month'].apply(get_season)
    df['is_weekend'] = df.index.weekday >= 5 # 5=Sat, 6=Sun
    df['hour'] = df.index.hour
    df['minute'] = df.index.minute
    
    print(f"Existing Data Range: {df.index.min()} to {df.index.max()}")
    
    # 2. Extract Profiles
    # Group by [Season, IsWeekend, Hour, Minute]
    # We only care about Summer, Fall, Winter in existing data.
    # Spring (if any) shouldn't exist in source 2024-06 to 2025-01.
    
    # Calculate Mean, Std, P05, P95
    # Only use measured_kWh
    groups = df.groupby(['season', 'is_weekend', 'hour', 'minute'])['measured_kWh']
    
    profile_mean = groups.mean()
    profile_std = groups.std()
    profile_p05 = groups.quantile(0.05)
    profile_p95 = groups.quantile(0.95)
    
    print("Seasonal Profiles extracted.")
    
    # 3. Define Generation Period
    last_date = df.index.max()
    start_gen = last_date + pd.Timedelta(minutes=15)
    end_gen = pd.Timestamp(TARGET_END_DATE) + pd.Timedelta(hours=23, minutes=45)
    
    print(f"Generating Data from {start_gen} to {end_gen}...")
    
    gen_index = pd.date_range(start=start_gen, end=end_gen, freq='15min')
    gen_df = pd.DataFrame(index=gen_index)
    
    # 4. Generate Data
    generated_loads = []
    
    for ts in gen_index:
        month = ts.month
        hour = ts.hour
        minute = ts.minute
        is_weekend = ts.weekday() >= 5
        
        # Determine Profile to Use & Noise Scale
        # Rules:
        # Jan-Feb -> Winter Profile (Noise * 0.7)
        # Mar-May -> Fall Profile (Fall Proxy)
        
        if month in [1, 2]:
            season_key = 'Winter'
            noise_scale = 0.7
        elif month in [3, 4, 5]:
            season_key = 'Fall'
            noise_scale = 1.0 # Standard noise for Fall proxy
        elif month in [6, 7, 8]: # Should check if we need to generate Summer? End date is May 31.
            season_key = 'Summer'
            noise_scale = 1.0
        else:
             # Fall
            season_key = 'Fall'
            noise_scale = 1.0
            
        # Get Stats
        try:
            # profile keys: (season, is_weekend, hour, minute)
            mean_val = profile_mean.loc[(season_key, is_weekend, hour, minute)]
            std_val = profile_std.loc[(season_key, is_weekend, hour, minute)]
            p05_val = profile_p05.loc[(season_key, is_weekend, hour, minute)]
            p95_val = profile_p95.loc[(season_key, is_weekend, hour, minute)]
        except KeyError:
            # Fallback if specific key missing (unlikely if data is complete)
            # Use just hour/minute mean ignoring season/weekend? Or surrounding?
            # Assuming complete data for simplification
            mean_val = 1000 # dummy
            std_val = 0
            p05_val = 1000
            p95_val = 1000
            print(f"Warning: Missing profile for {ts}")

        # Generate Noise
        noise = np.random.normal(0, std_val * noise_scale)
        
        # Base Load
        load = mean_val + noise
        
        # Clip
        # Clip between P05 and P95 to remove extreme outliers
        # Ensure P05 <= P95 (sanity)
        lower = min(p05_val, p95_val)
        upper = max(p05_val, p95_val)
        
        # Apply strict clip? Or soft clip?
        # User suggested: "Clip(Load, P05, P95)"
        load = np.clip(load, lower, upper)
        
        # Ensure non-negative
        load = max(0, load)
        
        generated_loads.append(load)
        
    gen_df['measured_kWh'] = generated_loads
    gen_df['realtime_kWh'] = generated_loads # Assuming forecast matches actual for generation
    
    # 5. Combine
    # Prepare generated dataframe to match existing format
    # Columns: no, date, hour, minute, measured_kWh, realtime_kWh
    # 'no' needs to continue
    last_no = df['no'].max()
    gen_df['no'] = range(last_no + 1, last_no + 1 + len(gen_df))
    gen_df['date'] = gen_df.index.strftime('%Y%m%d').astype(int)
    gen_df['hour'] = gen_df.index.hour
    gen_df['minute'] = gen_df.index.minute
    
    # Append
    final_df = pd.concat([df[['no', 'date', 'hour', 'minute', 'measured_kWh', 'realtime_kWh']], 
                          gen_df[['no', 'date', 'hour', 'minute', 'measured_kWh', 'realtime_kWh']]])
    
    # 6. Final Polish
    # Sort
    final_df = final_df.sort_index()
    
    # Add 'is_weekday' column as requested (Important!)
    # Re-calculate on full index
    final_df['is_weekday'] = final_df.index.weekday < 5
    
    # Round to 2 decimal places
    final_df['measured_kWh'] = final_df['measured_kWh'].round(2)
    final_df['realtime_kWh'] = final_df['realtime_kWh'].round(2)
    
    # Save
    print(f"Saving to {OUTPUT_FILE}...")
    final_df.to_csv(OUTPUT_FILE, index=False) # Index is datetime, but we want 'date', 'hour', 'minute' columns. 
    # Usually we don't save the index if date/hour/minute are columns.
    
    print("Annual Load Generation Complete.")
    print(final_df.head())
    print(final_df.tail())
    print(f"Total Rows: {len(final_df)}")

if __name__ == "__main__":
    generate_annual_load()
