import csv
import datetime
import statistics

input_file = 'data/data_center_load_clean.csv'

def get_season(month):
    if month in [3, 4, 5]:
        return 'Spring'
    elif month in [6, 7, 8]:
        return 'Summer'
    elif month in [9, 10, 11]:
        return 'Autumn'
    else:
        return 'Winter'

try:
    with open(input_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        header = next(reader)
        
        seasons_data = {'Spring': [], 'Summer': [], 'Autumn': [], 'Winter': []}
        
        for row in reader:
            if not row: continue
            # row: no,date,hour,minute,measured_kWh,realtime_kWh
            # date format: YYYYMMDD
            date_str = row[1]
            month = int(date_str[4:6])
            measured = float(row[4])
            
            season = get_season(month)
            seasons_data[season].append(measured)
            
    print(f"--- Seasonal Analysis Report ---")
    for season in ['Summer', 'Autumn', 'Winter']: # Order by appearance in data
        data = seasons_data[season]
        if data:
            print(f"\n[{season}]")
            print(f"Count: {len(data)}")
            print(f"Mean: {statistics.mean(data):.2f} kWh")
            print(f"Max: {max(data):.2f} kWh")
            print(f"Min: {min(data):.2f} kWh")
        else:
            print(f"\n[{season}] - No Data")

except Exception as e:
    print(f"Error: {e}")
