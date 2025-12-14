import pandas as pd
import numpy as np

input_file = 'data/data_decomposition.csv'
output_file = 'data/dr_simulation_results.csv'

def get_season(month):
    if month in [3, 4, 5]:
        return 'Spring'
    elif month in [6, 7, 8]:
        return 'Summer'
    elif month in [9, 10, 11]:
        return 'Fall' # User used "Fall" in request
    else:
        return 'Winter'

def simulate_dr():
    print("Loading decomposition data...")
    df = pd.read_csv(input_file, parse_dates=['datetime'], index_col='datetime')
    
    # 1. Convert to kW (x4)
    # Columns in decomposition: 'IT_Load', 'Cooling_Load', 'Other_Load', 'measured_kWh', 'realtime_kWh', ...
    # Wait, decomposition likely has kW or kWh? 
    # Usually decomposition was done on kWh 15-min data. 
    # Let's verify if we need to multiply by 4.
    # decompose_load.py used 'measured_kWh'. IT/Cooling/Other were calculated from it.
    # So they are likely in kWh per 15 min.
    # We need Power (kW) = Energy (kWh) * 4.
    
    print("Converting Energy (kWh) to Power (kW)...")
    df['P_IT_kW'] = df['IT'] * 4
    df['P_Cool_kW'] = df['Cooling'] * 4
    df['P_Other_kW'] = df['Other'] * 4
    # df['P_Total_kW'] = df['measured_kWh'] * 4
    
    # 2. Add Time Features
    df['month'] = df.index.month
    df['hour'] = df.index.hour
    df['weekday'] = df.index.weekday # 0=Mon, 6=Sun
    df['season'] = df['month'].apply(get_season)
    
    # 3. Parameters
    alpha_IT = 0.10
    alpha_cool_summer = 0.15
    alpha_cool_other = 0.10
    alpha_IT_forward = 0.10
    
    Q_ESS_fixed_kW = 1250.0 # 1.25 MW
    
    # 4. Define Masks (Weekday Only: 0-4)
    is_weekday = df['weekday'] < 5
    
    # Initialize Masks
    df['mask_shed'] = False
    df['mask_up'] = False
    
    # --- Summer ---
    # Shed: 11-12, 13-17
    # Up: None
    mask_summer = (df['season'] == 'Summer') & is_weekday
    summer_shed_hours = [11, 13, 14, 15, 16] # 11<=h<12, 13<=h<17 -> 13,14,15,16
    df.loc[mask_summer & df['hour'].isin(summer_shed_hours), 'mask_shed'] = True
    
    # --- Fall ---
    # Shed: None
    # Up: 11-14 (11, 12, 13)
    mask_fall = (df['season'] == 'Fall') & is_weekday
    fall_up_hours = [11, 12, 13] # 11<=h<14
    df.loc[mask_fall & df['hour'].isin(fall_up_hours), 'mask_up'] = True
    
    # --- Winter ---
    # Shed: 08-12 (8,9,10,11), 15-16 (15)
    # Up: 12-14 (12, 13)
    mask_winter = (df['season'] == 'Winter') & is_weekday
    winter_shed_hours = [8, 9, 10, 11, 15] 
    winter_up_hours = [12, 13]
    df.loc[mask_winter & df['hour'].isin(winter_shed_hours), 'mask_shed'] = True
    df.loc[mask_winter & df['hour'].isin(winter_up_hours), 'mask_up'] = True

    # --- Spring (New) ---
    # Shed: 10 (10)
    # Up: 12-15 (12, 13, 14)
    mask_spring = (df['season'] == 'Spring') & is_weekday
    spring_shed_hours = [10]
    spring_up_hours = [12, 13, 14]
    df.loc[mask_spring & df['hour'].isin(spring_shed_hours), 'mask_shed'] = True
    df.loc[mask_spring & df['hour'].isin(spring_up_hours), 'mask_up'] = True
    
    # 5. Overlap Handling (Shed Priority)
    # If both True, set Up to False
    overlap_mask = df['mask_shed'] & df['mask_up']
    if overlap_mask.sum() > 0:
        print(f"Overlap detected in {overlap_mask.sum()} timestamps. Prioritizing Shed.")
        df.loc[overlap_mask, 'mask_up'] = False
    
    # 6. Calculate Q (kW)
    # Initialize
    df['Q_shed_kW'] = 0.0
    df['Q_up_kW'] = 0.0
    
    # -- Calc Shed --
    # Q_shed = alpha_IT * P_IT + alpha_cool * P_Cool + Q_ESS
    # Determine alpha_cool per row? Or vectorise by season.
    
    # Summer Shed
    mask_s_shed = (df['season'] == 'Summer') & df['mask_shed']
    df.loc[mask_s_shed, 'Q_shed_kW'] = (
        alpha_IT * df.loc[mask_s_shed, 'P_IT_kW'] + 
        alpha_cool_summer * df.loc[mask_s_shed, 'P_Cool_kW'] + 
        Q_ESS_fixed_kW
    )
    
    # Winter Shed (Fall has no shed, but logic applies generally for 'other')
    mask_w_shed = (df['season'] != 'Summer') & df['mask_shed'] # Fall or Winter
    df.loc[mask_w_shed, 'Q_shed_kW'] = (
        alpha_IT * df.loc[mask_w_shed, 'P_IT_kW'] + 
        alpha_cool_other * df.loc[mask_w_shed, 'P_Cool_kW'] + 
        Q_ESS_fixed_kW
    )
    
    # -- Calc Up --
    # Q_up = alpha_IT_forward * P_IT + Q_ESS
    mask_up_all = df['mask_up']
    df.loc[mask_up_all, 'Q_up_kW'] = (
        alpha_IT_forward * df.loc[mask_up_all, 'P_IT_kW'] + 
        Q_ESS_fixed_kW
    )
    
    # 7. Sanity Checks
    print("\n--- Sanity Checks ---")
    
    # A. Check Q outside windows
    non_shed_q = df.loc[~df['mask_shed'], 'Q_shed_kW'].sum()
    non_up_q = df.loc[~df['mask_up'], 'Q_up_kW'].sum()
    print(f"Sum of Q_shed outside window: {non_shed_q} (Should be 0)")
    print(f"Sum of Q_up outside window:   {non_up_q} (Should be 0)")
    
    # B. Check Seasonal Existence
    print("\nMean Potentials by Season (Active Windows Only):")
    for season in ['Summer', 'Fall', 'Winter']:
        s_mask = df['season'] == season
        
        shed_count = df[s_mask & df['mask_shed']].shape[0]
        shed_mean = df.loc[s_mask & df['mask_shed'], 'Q_shed_kW'].mean()
        
        up_count = df[s_mask & df['mask_up']].shape[0]
        up_mean = df.loc[s_mask & df['mask_up'], 'Q_up_kW'].mean()
        
        print(f"[{season}] Shed Count: {shed_count}, Mean Q_shed: {shed_mean:.2f} kW")
        print(f"[{season}] Up   Count: {up_count}, Mean Q_up:   {up_mean:.2f} kW")
        
    # C. Overlap re-check
    final_overlap = (df['mask_shed'] & df['mask_up']).sum()
    print(f"\nFinal Overlap Count: {final_overlap} (Should be 0)")
    
    # 8. Save
    # Keep requested columns + datetime
    cols_to_save = ['season', 'mask_shed', 'mask_up', 'Q_shed_kW', 'Q_up_kW', 'P_IT_kW', 'P_Cool_kW', 'P_Other_kW']
    output_df = df[cols_to_save]
    output_df.to_csv(output_file)
    print(f"\nSaved results to {output_file}")
    print(output_df.head(10))

if __name__ == "__main__":
    simulate_dr()
