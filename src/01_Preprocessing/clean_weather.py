import pandas as pd
import os

load_file = 'data/data_center_load_annualized_20240601_20250531.csv'
weather_file = 'data/data_weather.csv'
output_file = 'data/data_with_weather.csv'

def clean_and_merge():
    # 1. Load Power Data
    print("Loading power data...")
    df_load = pd.read_csv(load_file)
    
    # Create datetime index for load
    df_load['datetime'] = pd.to_datetime(df_load['date'].astype(str) + ' ' + 
                                         df_load['hour'].astype(str).str.zfill(2) + ':' + 
                                         df_load['minute'].astype(str).str.zfill(2))
    df_load.set_index('datetime', inplace=True)
    # Ensure is_weekday is boolean if needed, read_csv might load as object/bool
    # It is already in file.

    
    # 2. Load Weather Data
    print("Loading weather data...")
    # Encoding for Korean chars (likely cp949)
    try:
        df_weather = pd.read_csv(weather_file, encoding='cp949')
    except UnicodeDecodeError:
        df_weather = pd.read_csv(weather_file, encoding='utf-8')
        
    # Inspect columns
    # Expected: column containing '일시' for time, '기온' for temp
    time_col = [c for c in df_weather.columns if '일시' in c][0]
    temp_col = [c for c in df_weather.columns if '기온' in c][0]
    humid_col = [c for c in df_weather.columns if '습도' in c][0]
    
    print(f"Weather columns detected: Time='{time_col}', Temp='{temp_col}', Humid='{humid_col}'")
    
    df_weather[time_col] = pd.to_datetime(df_weather[time_col])
    df_weather.set_index(time_col, inplace=True)
    
    # Select temperature and humidity
    df_weather = df_weather[[temp_col, humid_col]].rename(columns={temp_col: 'temperature', humid_col: 'humidity'})
    
    # Remove duplicates if any
    df_weather = df_weather[~df_weather.index.duplicated(keep='first')]
    
    # 3. Resample and Interpolate
    print("Resampling weather data...")
    # Reindex to match load data (15 min)
    combined_index = df_load.index.union(df_weather.index).sort_values()
    df_weather_resampled = df_weather.reindex(combined_index)
    
    # Interpolate (Time method respects distance)
    df_weather_resampled['temperature'] = df_weather_resampled['temperature'].interpolate(method='time')
    df_weather_resampled['humidity'] = df_weather_resampled['humidity'].interpolate(method='time')
    
    # Now filter only the timestamps we need (from load data)
    df_final_weather = df_weather_resampled.loc[df_load.index]
    
    # 4. Merge
    print("Merging datasets...")
    # df_load has [no, date, hour, minute, measured, realtime, is_weekday]
    # Do join
    df_merged = df_load.join(df_final_weather[['temperature', 'humidity']])
    
    # Check for NaNs
    nan_count_t = df_merged['temperature'].isnull().sum()
    nan_count_h = df_merged['humidity'].isnull().sum()
    
    if nan_count_t > 0 or nan_count_h > 0:
        print(f"Warning: Missing values needed fill (Temp: {nan_count_t}, Humid: {nan_count_h})")
        df_merged['temperature'] = df_merged['temperature'].ffill().bfill()
        df_merged['humidity'] = df_merged['humidity'].ffill().bfill()
        
    # Round to 2 decimal places
    df_merged['temperature'] = df_merged['temperature'].round(2)
    df_merged['humidity'] = df_merged['humidity'].round(2)
        
    # Save (index=False to remove datetime column, keeping date/hour/minute/is_weekday columns)
    # df_merged currently has index 'datetime'. Columns are [no, date, hour, minute, measured, realtime, is_weekday, temperature, humidity]
    df_merged.to_csv(output_file) # Saving index=True is actually safer for TS but user pattern was index=False. 
    # But clean_weather.py used `df_merged.to_csv(output_file, index=False)`.
    # And index was 'datetime'. So previous output was MISSING datetime index?
    # Or did it rely on 'date', 'hour', 'minute' columns being present? Yes.
    # df_load still has those columns because set_index(inplace=True) removes the column by default unless drop=False?
    # Default drop=True. 
    # WAIT. pd.read_csv -> set_index(inplace=True) -> 'datetime' becomes index, removes 'date' if it was used? 
    # No, 'date' was used in `pd.to_datetime` contruction but not as `keys`.
    # Actually, `set_index` drops the column used as index. 
    # I created `datetime` column then set it as index. 
    # Original columns `date`, `hour` etc remain unless I explicitly dropped them? No, they remain.
    # Ah, `set_index` removes the column that becomes the index.
    # BUT `date`, `hour` were NOT the index. `datetime` was the new column.
    # So `date`, `hour` etc are safe.
    
    # So simply saving with index=False (default behavior in previous code) is fine.
    df_merged.to_csv(output_file, index=False)
    print(f"Saved merged data to {output_file}")
    print(df_merged.head())
    print("\nTemperature Stats:")
    print(df_merged['temperature'].describe())
    print("\nHumidity Stats:")
    print(df_merged['humidity'].describe())

if __name__ == "__main__":
    clean_and_merge()
