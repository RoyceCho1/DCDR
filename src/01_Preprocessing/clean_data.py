import csv
import datetime
from datetime import timedelta

input_file = 'data_center_load.csv'
output_file = 'data_center_load_clean.csv'

def parse_row(row):
    # row: [no, date, hour, minute, measured_kWh, realtime_kWh]
    d_str, h_str, m_str = row[1], row[2], row[3]
    try:
        dt = datetime.datetime.strptime(f"{d_str} {h_str}:{m_str}", "%Y%m%d %H:%M")
        m_kwh = float(row[4])
        r_kwh = float(row[5])
        return {'dt': dt, 'measured': m_kwh, 'realtime': r_kwh, 'orig_row': row}
    except ValueError:
        return None

try:
    with open(input_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        header = next(reader)
        
        data_map = {}
        for row in reader:
            parsed = parse_row(row)
            if parsed:
                data_map[parsed['dt']] = parsed

    # Determine range
    all_dts = sorted(list(data_map.keys()))
    start_dt = all_dts[0]
    end_dt = all_dts[-1]
    
    print(f"Range: {start_dt} ~ {end_dt}")
    
    # Generate complete timeline
    current = start_dt
    cleaned_rows = []
    
    # We'll assign a new 'no' sequence
    new_no = 1
    missing_count = 0
    
    while current <= end_dt:
        if current in data_map:
            # Existing data
            item = data_map[current]
            # Reconstruct row with new 'no' to keep it clean, or keep original?
            # Let's keep original structure: no,date,hour,minute,measured_kWh,realtime_kWh
            # But update 'no' to be continuous
            
            # Format date, hour, minute
            d_str = current.strftime("%Y%m%d")
            h_str = str(current.hour)
            m_str = str(current.minute)
            
            row = [
                new_no, d_str, h_str, m_str, 
                f"{item['measured']:.2f}", f"{item['realtime']:.2f}"
            ]
            cleaned_rows.append(row)
            
        else:
            # Missing data (Interpolate)
            prev_dt = current - timedelta(minutes=15)
            next_dt = current + timedelta(minutes=15)
            
            if prev_dt in data_map and next_dt in data_map:
                prev_val = data_map[prev_dt]
                next_val = data_map[next_dt]
                
                # Average
                interp_measured = (prev_val['measured'] + next_val['measured']) / 2
                interp_realtime = (prev_val['realtime'] + next_val['realtime']) / 2
                
                d_str = current.strftime("%Y%m%d")
                h_str = str(current.hour)
                m_str = str(current.minute)
                
                row = [
                    new_no, d_str, h_str, m_str, 
                    f"{interp_measured:.2f}", f"{interp_realtime:.2f}"
                ]
                cleaned_rows.append(row)
                missing_count += 1
            else:
                # Can't interpolate (edge case or large gap), just copy previous or skip?
                # For this dataset we know it's just single gaps.
                # If we can't interpolate, we might leave it or fill 0?
                # Let's fill 0 for safety but notify
                print(f"Warning: Could not interpolate for {current}")
                pass

        current += timedelta(minutes=15)
        new_no += 1

    # Write output
    with open(output_file, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(cleaned_rows)

    print(f"Done. Filled {missing_count} missing intervals.")
    print(f"Saved to {output_file}")

except Exception as e:
    print(f"Error: {e}")
