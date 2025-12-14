import pandas as pd

input_file = 'data/power_source_integrated.csv'

def get_season(month):
    if month in [3, 4, 5]:
        return 'Spring'
    elif month in [6, 7, 8]:
        return 'Summer'
    elif month in [9, 10, 11]:
        return 'Autumn'
    else:
        return 'Winter'

def rank_power_sources():
    print("Loading Data...")
    df = pd.read_csv(input_file, parse_dates=['datetime'], index_col='datetime')
    
    # Define primary sources (Using PV_total instead of sub-components)
    sources = ['원자력', '유연탄', '가스', '신재생', '양수', '수력', '풍력', '유류', '국내탄', 'PV_total']
    
    # Filter columns that exist
    available_sources = [c for c in sources if c in df.columns]
    
    # Add Season
    df['month'] = df.index.month
    df['Season'] = df['month'].apply(get_season)
    
    # 1. Overall Ranking
    print("\n" + "="*40)
    print(" OVERALL POWER SOURCE RANKING")
    print("="*40)
    total_gen = df[available_sources].sum().sort_values(ascending=False)
    total_sum = total_gen.sum()
    
    for i, (source, gen) in enumerate(total_gen.items(), 1):
        share = (gen / total_sum) * 100
        print(f"{i}. {source}: {gen:,.0f} (Mean MW) / Share: {share:.1f}%") 
        # Note: Data is 15-min mean MW? Or MWh?
        # Original merging was "resample('15min').mean()".
        # So unit is MW (average power over 15 mins).
        # Summing MW over time isn't Energy (MWh).
        # Energy (MWh) = Sum(MW) * (15/60) hours.
        # But for ranking, relative order is same. Let's label as "Sum of Avgs" or convert to GWh.
        
    print("\n*Note: Values are proportional to Total Energy.*")

    # 2. Seasonal Ranking
    seasons = ['Summer', 'Autumn', 'Winter']
    
    for season in seasons:
        if season not in df['Season'].unique():
            continue
            
        print("\n" + "-"*40)
        print(f" {season.upper()} RANKING")
        print("-"*40)
        
        subset = df[df['Season'] == season]
        season_gen = subset[available_sources].sum().sort_values(ascending=False)
        season_sum = season_gen.sum()
        
        for i, (source, gen) in enumerate(season_gen.items(), 1):
            share = (gen / season_sum) * 100
            print(f"{i}. {source}: {share:.1f}%")

if __name__ == "__main__":
    rank_power_sources()
