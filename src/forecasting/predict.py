import joblib,pandas as pd
from tensorflow.keras.models import load_model
from src.data.feature_engineering import prepare_features,FEATURES
from src.forecasting.train_lstm import LOOKBACK

def predict_next_24h(path="data/processed/master_hourly.csv"):
    df=prepare_features(pd.read_csv(path,parse_dates=["timestamp"])).dropna(subset=FEATURES).reset_index(drop=True); sc=joblib.load("models/lstm_feature_scaler.joblib"); model=load_model("models/lstm_demand_24h.keras")
    x=sc.transform(df[FEATURES].tail(LOOKBACK)); p=model.predict(x[None],verbose=0)[0]; i=FEATURES.index("load_kW"); p=p*sc.scale_[i]+sc.mean_[i]; t=pd.date_range(df.timestamp.iloc[-1]+pd.Timedelta(hours=1),periods=24,freq="h"); return pd.DataFrame({"timestamp":t,"forecast_load_kW":p})
