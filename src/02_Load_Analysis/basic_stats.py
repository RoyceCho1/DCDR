import csv
import statistics

input_file = 'data_center_load_clean.csv'

try:
    with open(input_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        header = next(reader)
        
        measured = []
        realtime = []
        
        for row in reader:
            if row:
                measured.append(float(row[4]))
                realtime.append(float(row[5]))
                
    print(f"--- Analysis Report (Pure Python) ---")
    print(f"Data Source: {input_file}")
    print(f"Total Records: {len(measured)}")
    
    print(f"\n[Measured Load (kWh)]")
    print(f"Mean: {statistics.mean(measured):.2f}")
    print(f"Max: {max(measured):.2f}")
    print(f"Min: {min(measured):.2f}")
    
    print(f"\n[Realtime Load (kWh)]")
    print(f"Mean: {statistics.mean(realtime):.2f}")
    print(f"Max: {max(realtime):.2f}")
    print(f"Min: {min(realtime):.2f}")

except Exception as e:
    print(f"Error: {e}")
