from pathlib import Path
import json
import numpy as np
import pandas as pd

def generate_load(weather_csv="data/processed/master_hourly_environmental.csv", output_csv="data/processed/kutch_community_load_hourly.csv", metadata_json="data/processed/kutch_load_model_metadata.json", households=100, seed=42):
    rng=np.random.default_rng(seed)
    w=pd.read_csv(weather_csv,parse_dates=["timestamp"]).sort_values("timestamp").drop_duplicates("timestamp")
    h=w.timestamp.dt.hour.to_numpy(); dow=w.timestamp.dt.dayofweek.to_numpy(); doy=w.timestamp.dt.dayofyear.to_numpy()
    per=np.select([(h<5),((h>=5)&(h<10)),((h>=10)&(h<17)),((h>=17)&(h<23)),(h==23)],[.16,.34,.27,.48,.28])
    weekend=np.where(dow>=5,1.08,1.0); seasonal=1+.07*np.sin(2*np.pi*(doy-30)/365.25)
    temp=pd.to_numeric(w.get("temperature_C",pd.Series(28,index=w.index)),errors="coerce").fillna(28).to_numpy()
    cooling=1+.018*np.maximum(temp-27,0)
    residential=households*per*weekend*seasonal*cooling
    commercial=np.where((h>=9)&(h<21),10,3); community=np.where((h>=7)&(h<18),6,2); street=np.where((h>=18)|(h<6),4,.5)
    pumping=20*((h>=7)&(h<17))*(.7+.3*(.5+.5*np.sin(2*np.pi*(doy-100)/365.25)))
    load=np.maximum((residential+commercial+community+street+pumping)*(1+rng.normal(0,.025,len(w))),.1)
    out=pd.DataFrame({"timestamp":w.timestamp,"load_kW":load}); Path(output_csv).parent.mkdir(parents=True,exist_ok=True); out.to_csv(output_csv,index=False)
    meta={"data_type":"modeled_representative_demand","households":households,"location":"Representative off-grid community, Kutch, Gujarat, India","resolution":"1 hour","period_start":str(out.timestamp.min()),"period_end":str(out.timestamp.max()),"components":["residential","commercial","community","street_lighting","water_agriculture"],"warning":"Not measured electricity consumption from a specific village."}
    Path(metadata_json).write_text(json.dumps(meta,indent=2),encoding="utf-8"); return out
if __name__=="__main__":
    d=generate_load(); print(d.head()); print(d.load_kW.describe())
