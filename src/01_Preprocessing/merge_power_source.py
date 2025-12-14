import pandas as pd
import glob
import os

input_dir = 'power_source_data'
output_file = 'data/power_source_integrated.csv'

def merge_power_source():
    print("Searching for Excel files...")
    # List all xlsx files
    files = sorted(glob.glob(os.path.join(input_dir, '*.xlsx')))
    
    if not files:
        print("No Excel files found!")
        return
        
    print(f"Found {len(files)} files: {[os.path.basename(f) for f in files]}")
    
    all_dfs = []
    
    for f in files:
        print(f"Reading {f}...")
        try:
            # Load excel, skip first row (title), use 2nd row as header
            df = pd.read_excel(f, header=1)
            all_dfs.append(df)
        except Exception as e:
            print(f"Error reading {f}: {e}")
            
    if not all_dfs:
        print("No data loaded.")
        return
    
    print("Concatenating...")
    merged_df = pd.concat(all_dfs, ignore_index=True)
    
    print("\nColumns:", merged_df.columns.tolist())
    
    # Create datetime index from '날짜' and '시간'
    if '날짜' in merged_df.columns and '시간' in merged_df.columns:
        print("Creating datetime index...")
        # '날짜' is likely YYYY-MM-DD, '시간' is likely HH:MM
        merged_df['datetime'] = pd.to_datetime(merged_df['날짜'].astype(str) + ' ' + merged_df['시간'].astype(str))
        merged_df = merged_df.set_index('datetime').sort_index()
        
        # Resample to 15 min using mean (assuming instantaneous MW data)
        print("Resampling to 15-min intervals...")
        # Select numeric columns only for resampling
        numeric_cols = merged_df.select_dtypes(include=['number']).columns
        merged_resampled = merged_df[numeric_cols].resample('15min').mean()
        
        # Drop rows with all NaNs if any (e.g. gaps) - though probably continuous
        merged_resampled = merged_resampled.dropna(how='all')
        
        # Calculate PV_total
        # Columns: '태양광(BTM,추정)', '태양광(PPA,추정)', '태양광(전력시장)'
        # Some might be missing if source file format changes, but assuming they exist based on previous output.
        solar_cols = ['태양광(BTM,추정)', '태양광(PPA,추정)', '태양광(전력시장)']
        existing_solar_cols = [c for c in solar_cols if c in merged_resampled.columns]
        
        if existing_solar_cols:
            print(f"Calculating PV_total from {existing_solar_cols}...")
            merged_resampled['PV_total'] = merged_resampled[existing_solar_cols].sum(axis=1)
        
        # Round to 2 decimal places
        merged_df = merged_resampled.round(2)

    # Save to CSV
    merged_df.to_csv(output_file)
    print(f"Saved merged and resampled data to {output_file}")
    
    print("\nShape:", merged_df.shape)
    print(merged_df.head())

if __name__ == "__main__":
    merge_power_source()
