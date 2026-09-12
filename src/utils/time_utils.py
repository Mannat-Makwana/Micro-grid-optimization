import pandas as pd
def ensure_hourly(df):
    df=df.copy();df['timestamp']=pd.to_datetime(df['timestamp']);return df.sort_values('timestamp').drop_duplicates('timestamp')
