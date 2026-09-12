from src.data.preprocess import add_cyclic_features
FEATURES=["load_kW","temperature_C","humidity_pct","cloud_cover_pct","ghi_W_m2","wind_speed_mps","precipitation_mm","hour_sin","hour_cos","dow_sin","dow_cos"]
def prepare_features(df):
    df=df.copy(); df.timestamp=df.timestamp.astype("datetime64[ns]"); return add_cyclic_features(df)
def check_required_columns(df):
    missing=[x for x in FEATURES if x not in df.columns]
    if missing: raise ValueError(f"Missing required features: {missing}")
