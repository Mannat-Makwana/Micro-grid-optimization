from pathlib import Path
import joblib,numpy as np,pandas as pd
from sklearn.preprocessing import StandardScaler
from src.data.feature_engineering import prepare_features,FEATURES
from src.data.preprocess import chronological_split
from src.forecasting.lstm_model import build_lstm
LOOKBACK=168; HORIZON=24

def sequences(a):
    X=[]; y=[]
    for i in range(LOOKBACK,len(a)-HORIZON+1): X.append(a[i-LOOKBACK:i]); y.append(a[i:i+HORIZON,0])
    return np.asarray(X,dtype=np.float32),np.asarray(y,dtype=np.float32)

def train(path="data/processed/master_hourly.csv"):
    df=prepare_features(pd.read_csv(path,parse_dates=["timestamp"])).dropna(subset=FEATURES).reset_index(drop=True)
    tr,va,te=chronological_split(df); sc=StandardScaler().fit(tr[FEATURES]); a,b,c=[sc.transform(x[FEATURES]) for x in (tr,va,te)]; Xtr,ytr=sequences(a); Xv,yv=sequences(b); Xt,yt=sequences(c)
    model=build_lstm(len(FEATURES),HORIZON); import tensorflow as tf
    model.fit(Xtr,ytr,validation_data=(Xv,yv),epochs=50,batch_size=64,callbacks=[tf.keras.callbacks.EarlyStopping(patience=7,restore_best_weights=True)])
    Path("models").mkdir(exist_ok=True); model.save("models/lstm_demand_24h.keras"); joblib.dump(sc,"models/lstm_feature_scaler.joblib"); np.save("models/test_X.npy",Xt); np.save("models/test_y.npy",yt)
if __name__=="__main__": train()
