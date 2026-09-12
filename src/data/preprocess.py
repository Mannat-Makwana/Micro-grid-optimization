import numpy as np
import pandas as pd

def add_cyclic_features(df):
    df=df.copy(); df["hour"]=df.timestamp.dt.hour; df["day_of_week"]=df.timestamp.dt.dayofweek; df["month"]=df.timestamp.dt.month; df["is_weekend"]=(df.day_of_week>=5).astype(int)
    df["hour_sin"]=np.sin(2*np.pi*df.hour/24); df["hour_cos"]=np.cos(2*np.pi*df.hour/24); df["dow_sin"]=np.sin(2*np.pi*df.day_of_week/7); df["dow_cos"]=np.cos(2*np.pi*df.day_of_week/7); return df

def chronological_split(df,train_end="2024-12-31 23:00:00",val_end="2025-09-30 23:00:00"):
    a=pd.Timestamp(train_end); b=pd.Timestamp(val_end); return df[df.timestamp<=a].copy(),df[(df.timestamp>a)&(df.timestamp<=b)].copy(),df[df.timestamp>b].copy()
