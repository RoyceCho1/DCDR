import pandas as pd
import numpy as np
import os

input_dr = 'data/dr_simulation_results.csv'
input_smp = 'data/smp_clean.csv'
output_file = 'data/dr_events_1h.csv'

def process_dr_events_1h():
    print("Loading Data...")
    df_dr = pd.read_csv(input_dr, parse_dates=['datetime'], index_col='datetime')
    df_smp = pd.read_csv(input_smp, parse_dates=['datetime'], index_col='datetime')
    
    # Merge SMP into DR df
    df = df_dr.join(df_smp, how='inner')
    
    # 1. Prepare Columns
    # Create numeric masks for aggregation
    df['mask_shed_int'] = df['mask_shed'].astype(int)
    df['mask_up_int']   = df['mask_up'].astype(int)
    
    # 2. Resample to 1-Hour
    # Group by [Date, Hour] or just Resample('1H')
    # Resample is safer for time series.
    # Logic:
    # - Mean of Power (kW) -> 1h Power (kW)
    # - Mean of SMP -> 1h SMP
    # - Count of items -> n_intervals
    # - Sum of masks -> effective duration (but we use mean for ratio)
    
    print("Resampling to 1-Hour...")
    
    # Define aggregation dict
    agg_dict = {
        'season': 'first', # Season shouldn't change in an hour usually
        'mask_shed_int': ['count', 'mean'], # count=n_intervals, mean=active_ratio
        'mask_up_int': 'mean',
        'Q_shed_kW': 'mean',
        'Q_up_kW': 'mean',
        'SMP': 'mean'
    }
    
    df_1h = df.resample('1h').agg(agg_dict)
    
    # Flatten MultiIndex columns
    # e.g. (mask_shed_int, count) -> n_intervals
    df_1h.columns = ['season', 'n_intervals', 'active_ratio_shed', 'active_ratio_up', 'Q_shed_kW', 'Q_up_kW', 'SMP_hourly']
    
    # Drop rows with n_intervals == 0 (missing data)
    df_1h = df_1h[df_1h['n_intervals'] > 0].copy()
    
    # 3. Calculate Thresholds (Qmin)
    # Strategy: Qmin = 0.3 * Seasonal Average of "Raw Potential"
    # "Raw Potential": Mean Q when active_ratio > 0? Or active_ratio == 1?
    # User said: "Mean of Q_shed_kW (season별)" as base for calculation.
    # Let's use the mean of Qs where there is *some* potential.
    
    seasons = ['Spring', 'Summer', 'Fall', 'Winter']
    qmin_map_shed = {}
    qmin_map_up = {}
    
    print("\n[Qmin Calculation] (Target: 0.3 * Mean)")
    
    for season in seasons:
        # SHED
        # Filter: Season matches AND Potential > 0
        mask_s = (df_1h['season'] == season) & (df_1h['Q_shed_kW'] > 0)
        if mask_s.any():
            mean_val = df_1h.loc[mask_s, 'Q_shed_kW'].mean()
            qmin = 0.3 * mean_val
        else:
            qmin = 0.0
        qmin_map_shed[season] = qmin
        
        # UP
        mask_u = (df_1h['season'] == season) & (df_1h['Q_up_kW'] > 0)
        if mask_u.any():
            mean_val = df_1h.loc[mask_u, 'Q_up_kW'].mean()
            qmin = 0.3 * mean_val
        else:
            qmin = 0.0
        qmin_map_up[season] = qmin
        
        print(f"  {season}: Shed Qmin={qmin:.2f}, Up Qmin={qmin:.2f}")

    # 4. Define Events
    # Criteria 1: Completeness (active_ratio >= 1.0) -> User said "1.0 (Conservative)"
    # Criteria 2: Quantity (Q >= Qmin)
    
    # Vectorized Qmin using map
    # Handle NaN seasons if any
    df_1h['Qmin_shed'] = df_1h['season'].map(qmin_map_shed).fillna(0)
    df_1h['Qmin_up']   = df_1h['season'].map(qmin_map_up).fillna(0)
    
    # Logic
    # Shed Event
    cond_shed_ratio = df_1h['active_ratio_shed'] >= 1.0
    cond_shed_q     = df_1h['Q_shed_kW'] >= df_1h['Qmin_shed']
    # Also ensure Q > 0 strict
    cond_shed_pos   = df_1h['Q_shed_kW'] > 0
    
    df_1h['is_event_shed'] = cond_shed_ratio & cond_shed_q & cond_shed_pos
    
    # Up Event
    cond_up_ratio = df_1h['active_ratio_up'] >= 1.0
    cond_up_q     = df_1h['Q_up_kW'] >= df_1h['Qmin_up']
    cond_up_pos   = df_1h['Q_up_kW'] > 0
    
    df_1h['is_event_up'] = cond_up_ratio & cond_up_q & cond_up_pos
    
    # 5. Add Energy Columns (kWh)
    # Since it is 1-hour block: E(kWh) = P(kW) * 1h
    # BUT, we only claim energy for VALID events?
    # Or do we store Potential Energy for all, and 'is_event' filters it?
    # User said: "E_shed_kWh = Q_shed_kW * 1.0". 
    # Let's calculate for ALL rows (Potential), filtering happens in analysis.
    df_1h['E_shed_kWh'] = df_1h['Q_shed_kW']
    df_1h['E_up_kWh']   = df_1h['Q_up_kW']
    
    # 6. Save
    # Columns requested: datetime(index), season, type?? (We have shed/cols), Q, E, SMP, n, active, is_event
    cols = ['season', 'n_intervals', 'active_ratio_shed', 'active_ratio_up', 
            'Q_shed_kW', 'Q_up_kW', 'E_shed_kWh', 'E_up_kWh', 'SMP_hourly', 
            'is_event_shed', 'is_event_up']
            
    df_1h[cols].to_csv(output_file)
    print(f"\nSaved standardized events to {output_file}")
    
    # Summary
    print("\n[Event Summary]")
    print(df_1h.groupby('season')[['is_event_shed', 'is_event_up']].sum())

if __name__ == "__main__":
    process_dr_events_1h()
