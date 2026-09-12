import pandas as pd

def load_master(path="data/processed/master_hourly_environmental.csv"):
    return pd.read_csv(path,parse_dates=["timestamp"]).sort_values("timestamp").reset_index(drop=True)

def merge_environment_and_load(environment_path="data/processed/master_hourly_environmental.csv",load_path="data/processed/kutch_community_load_hourly.csv",output_path="data/processed/master_hourly.csv"):
    env=load_master(environment_path); load=pd.read_csv(load_path,parse_dates=["timestamp"])
    df=env.merge(load[["timestamp","load_kW"]],on="timestamp",how="left"); df.to_csv(output_path,index=False); return df
