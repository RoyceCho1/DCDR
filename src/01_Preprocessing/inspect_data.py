import csv
import datetime
import statistics

file_path = 'data_center_load.csv'

def parse_row(row):
    # row: [no, date, hour, minute, measured_kWh, realtime_kWh]
    # Handle byte order mark in header or first key if using DictReader
    # But here we use reader, so header is separated.
    
    # Date: YYYYMMDD
    d_str = row[1]
    h_str = row[2]
    m_str = row[3]
    
    try:
        dt = datetime.datetime.strptime(f"{d_str} {h_str}:{m_str}", "%Y%m%d %H:%M")
        m_kwh = float(row[4]) if row[4] else None
        r_kwh = float(row[5]) if row[5] else None
        return dt, m_kwh, r_kwh
    except ValueError:
        return None, None, None

try:
    with open(file_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        header = next(reader)
        print(f"Header: {header}")
        
        data = []
        for row in reader:
            if not row: continue
            data.append(parse_row(row))
            
    # Remove None parse failures if any
    data = [d for d in data if d[0] is not None]
    
    timestamps = [d[0] for d in data]
    measured = [d[1] for d in data if d[1] is not None]
    realtime = [d[2] for d in data if d[2] is not None]
    
    print(f"\n--- Total Rows: {len(data)} ---")
    
    # Missing values
    missing_measured = len(data) - len(measured)
    missing_realtime = len(data) - len(realtime)
    print(f"Missing measured_kWh: {missing_measured}")
    print(f"Missing realtime_kWh: {missing_realtime}")
    
    # Duplicates
    if len(timestamps) != len(set(timestamps)):
        print(f"Duplicate timestamps found! Unique: {len(set(timestamps))}")
    else:
        print("No duplicate timestamps.")
        
    # Continuity
    timestamps.sort()
    start_time = timestamps[0]
    end_time = timestamps[-1]
    expected_count = int((end_time - start_time).total_seconds() / 900) + 1 # 15 min = 900 sec
    
    print(f"\n--- Time Range: {start_time} to {end_time} ---")
    print(f"Expected count (15min intervals): {expected_count}")
    print(f"Actual count: {len(timestamps)}")
    
    if len(timestamps) != expected_count:
        print(f"MISSING INTERVALS: {expected_count - len(timestamps)}")
        # Find holes
        current = start_time
        missing_count = 0
        timestamp_set = set(timestamps)
        while current <= end_time:
            if current not in timestamp_set:
                if missing_count < 5:
                    print(f"Missing: {current}")
                missing_count += 1
            current += datetime.timedelta(minutes=15)
        if missing_count >= 5:
            print("...")
            
    # Stats
    if measured:
        print(f"\nMeasured kWh: Min={min(measured)}, Max={max(measured)}, Mean={statistics.mean(measured):.2f}")
    if realtime:
        print(f"\nRealtime kWh: Min={min(realtime)}, Max={max(realtime)}, Mean={statistics.mean(realtime):.2f}")

except Exception as e:
    print(f"Error: {e}")
