import pandas as pd
import numpy as np

input_file = 'data/SMP_system_price.csv'
output_file = 'data/smp_clean.csv'

def clean_smp():
    print("Loading SMP data...")
    # Inspect first few lines to detect header
    try:
        df = pd.read_csv(input_file, encoding='cp949') # Korean usually requires cp949
    except:
        df = pd.read_csv(input_file, encoding='utf-8')
        
    print("Original Columns:", df.columns.tolist())
    print(df.head())
    
    # User said: "Date, Day, 01h ... 24h, Max, Min, Avg"
    # Identify Date column
    # Often '기간', '일자', '구분' etc.
    # Let's verify columns dynamically
    
    # Drop summary columns if they exist
    cols_to_drop = ['최대', '최소', '가중평균', '육지', '제주'] # Common extras
    # Also user said "Max, Min, WeightedAvg" are the last 3.
    
    # Potential column names for hours: '1h', '2h' or '01시', '02시'...
    # Let's try to melt.
    
    # Assume first column is Date
    date_col = df.columns[0]
    
    # Filter only hour columns
    # We need to identify which are hour columns.
    # Usually they are numerical or 'X시'
    
    melted = df.melt(id_vars=[date_col], var_name='Hour_raw', value_name='SMP')
    
    # Clean Hour_raw
    # Remove 'h', '시', space, etc.
    melted['Hour'] = melted['Hour_raw'].astype(str).str.extract(r'(\d+)').astype(float)
    
    # Drop rows where Hour is NaN (likely non-hour columns like 'Day', 'Max', 'Min')
    melted = melted.dropna(subset=['Hour'])
    melted['Hour'] = melted['Hour'].astype(int)
    
    # Correct Date
    # If date_col is just 'Date', good.
    melted['Date'] = pd.to_datetime(melted[date_col])
    
    # Adjust Hour: Data usually 1h = 00:00 - 01:00 or 01:00?
    # Market standard: '01h' means 00:00 ~ 01:00 consumption OR price for that hour.
    # Let's align to start time. 
    # Hour 1 -> 00:00 ? Or Hour 1 -> 01:00?
    # Usually in KR Power Market, 1h is 00:00 ~ 01:00.
    # So timestamp should be Date + (Hour-1) hours.
    
    melted['datetime'] = melted['Date'] + pd.to_timedelta(melted['Hour'] - 1, unit='h')
    
    melted = melted.sort_values('datetime').set_index('datetime')
    
    # Select SMP column
    smp_df = melted[['SMP']].astype(float)
    
    # Upsample to 15 min
    # SMP is constant for the hour. So Forward Fill (ffill) is correct.
    smp_15min = smp_df.resample('15T').ffill()
    
    # Save
    smp_15min.to_csv(output_file)
    print(f"Saved cleaned SMP data to {output_file}")
    print(smp_15min.head())
    print("\nStats:")
    print(smp_15min.describe())

if __name__ == "__main__":
    clean_smp()
