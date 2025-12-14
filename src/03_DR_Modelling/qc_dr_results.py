import pandas as pd
import numpy as np

input_file = 'data/dr_simulation_results.csv'

def qc_dr_results():
    print("Loading DR simulation results for QC...")
    df = pd.read_csv(input_file, parse_dates=['datetime'], index_col='datetime')
    
    # Calculate Total Load for Sanity Check
    # Ensure columns exist
    req_cols = ['P_IT_kW', 'P_Cool_kW', 'P_Other_kW', 'season', 'mask_shed', 'mask_up', 'Q_shed_kW', 'Q_up_kW']
    missing = [c for c in req_cols if c not in df.columns]
    if missing:
        print(f"FAIL: Missing columns {missing}")
        return

    df['P_Total_kW'] = df['P_IT_kW'] + df['P_Cool_kW'] + df['P_Other_kW']
    
    print("\n" + "="*50)
    print(" QUALITY CONTROL REPORT")
    print("="*50)
    
    # 1. Window Validity (Outside Window -> Q=0)
    print("\n[Check 1] Q=0 Outside Windows")
    
    # Shed
    # Check rows where mask_shed is False BUT Q_shed != 0
    # Use small epsilon for float comparison safety
    bad_shed = df[ (~df['mask_shed']) & (df['Q_shed_kW'].abs() > 1e-6) ]
    if bad_shed.empty:
        print("  ✓ Shed Check: PASS (All non-window Q_shed are 0)")
    else:
        print(f"  X Shed Check: FAIL! Found {len(bad_shed)} rows with Q_shed > 0 outside window.")
        print(bad_shed.head())
        
    # Up
    bad_up = df[ (~df['mask_up']) & (df['Q_up_kW'].abs() > 1e-6) ]
    if bad_up.empty:
        print("  ✓ Up Check:   PASS (All non-window Q_up are 0)")
    else:
        print(f"  X Up Check:   FAIL! Found {len(bad_up)} rows with Q_up > 0 outside window.")
    
    # 2. Summer Up Policy (Summer -> Q_up=0)
    print("\n[Check 2] Summer Up Exclusion")
    bad_summer_up = df[ (df['season'] == 'Summer') & (df['Q_up_kW'].abs() > 1e-6) ]
    if bad_summer_up.empty:
        print("  ✓ Summer Check: PASS (Q_up is 0 for all Summer rows)")
    else:
        print(f"  X Summer Check: FAIL! Found {len(bad_summer_up)} Summer rows with Q_up > 0.")
        
    # 3. Overlap Check
    print("\n[Check 3] Mask Overlap")
    overlap = df[ df['mask_shed'] & df['mask_up'] ]
    if overlap.empty:
        print("  ✓ Overlap Check: PASS (No timestamp has both Shed and Up True)")
    else:
        print(f"  X Overlap Check: FAIL! Found {len(overlap)} overlapping timestamps.")
        
    # 4. Unit Sanity (Total Load ~ 3-4.5 MW)
    print("\n[Check 4] Unit Sanity (Total Power)")
    p_min = df['P_Total_kW'].min()
    p_max = df['P_Total_kW'].max()
    p_mean = df['P_Total_kW'].mean()
    
    print(f"  Stats: Min={p_min:.2f} kW, Max={p_max:.2f} kW, Mean={p_mean:.2f} kW")
    
    # Heuristic check: typical range 2000 ~ 5000 kW for a 5MW scale DC
    if p_min > 500 and p_max < 10000:
         print("  ✓ Scale Check:   PASS (Values are within expected MW range)")
    else:
         print("  ? Scale Check:   WARNING (Values might be outliers or wrong unit)")

    # Final Summary
    print("\n" + "="*50)
    print(" QC COMPLETE")
    print("="*50)

if __name__ == "__main__":
    qc_dr_results()
